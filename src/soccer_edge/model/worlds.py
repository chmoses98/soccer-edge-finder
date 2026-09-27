"""Coherent 'world' generation.

A world is one joint draw of every uncertain input. Dependencies are explicit:
    parameter draw (attack, defence, home adv, rho)  ~ ParameterPosterior
    lineup draw  (who plays)                          ~ per-player availability
        -> team attack/defence adjustment via player importance
        -> player goal shares renormalised over players on the pitch (research-only layer)
    competition environment draw                      ~ prior on scoring environment
    red-card hazard draw                              ~ Gamma around competition rate
    game-state behaviour draw                         ~ small uncertainty on lead/trail multipliers
    model-uncertainty inflation                       ~ N(0, sigma_model) on log rates

The three uncertainty types are kept distinct (docs/UNCERTAINTY_MODEL.md):
  aleatoric  -> simulated *within* a world by the match engine
  parameter  -> variation *across* worlds from the posterior + lineup + environment draws
  model      -> the specification inflation term + family mixing at the family layer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from soccer_edge.core.serialization import content_hash
from soccer_edge.model.context import LineupState, MatchContext, PlayerAvailability
from soccer_edge.model.strength import ParameterPosterior


@dataclass(frozen=True)
class WorldConfig:
    # model-uncertainty inflation on log scoring rates (research prior; interval calibration will tune it)
    sigma_model_log_rate: float = 0.05
    # competition scoring environment: multiplicative log-normal jitter (unknown-league default)
    sigma_environment: float = 0.03
    # red cards: mean per team per match and its uncertainty (Gamma shape); ~0.10-0.14 in top leagues
    red_card_mean_per_team: float = 0.12
    red_card_shape: float = 20.0
    # game-state behaviour multipliers (Dixon & Robinson 1998 style); uncertain across worlds
    trailing_attack_mult: float = 1.08
    leading_attack_mult: float = 0.93
    state_mult_sd: float = 0.04
    # effect of a red card: own attack x, opponent attack x (literature: ~-35% / +25%)
    red_own_attack_mult: float = 0.65
    red_opp_attack_mult: float = 1.25
    # lineup layer: how much of a team's attack is 'explained' by named players (rest is depth)
    lineup_effect_cap: float = 0.35
    version: str = "worlds_v1"


@dataclass
class WorldSet:
    n_worlds: int
    lam_home: np.ndarray  # (W,) expected regulation goals for home team, before state effects
    mu_away: np.ndarray
    rho: np.ndarray
    red_hazard_home: np.ndarray  # per-minute hazard of a red card for the home team
    red_hazard_away: np.ndarray
    trailing_mult: np.ndarray
    leading_mult: np.ndarray
    home_players_on: np.ndarray | None = None  # (W, n_home_players) bool: appears in this world
    away_players_on: np.ndarray | None = None
    home_goal_shares: np.ndarray | None = (
        None  # (W, n_home_players) shares among players who appear
    )
    away_goal_shares: np.ndarray | None = None
    components: dict[str, Any] = field(default_factory=dict)
    posterior_hash: str = ""
    config: WorldConfig = field(default_factory=WorldConfig)

    def world_hash(self) -> str:
        return content_hash(
            {
                "posterior": self.posterior_hash,
                "cfg": self.config.__dict__,
                "n": self.n_worlds,
                "lam": np.round(self.lam_home[:8], 6),
                "mu": np.round(self.mu_away[:8], 6),
            }
        )

    def summary(self) -> dict[str, Any]:
        return {
            "n_worlds": self.n_worlds,
            "lam_home_mean": float(self.lam_home.mean()),
            "lam_home_sd": float(self.lam_home.std()),
            "mu_away_mean": float(self.mu_away.mean()),
            "mu_away_sd": float(self.mu_away.std()),
            "rho_mean": float(self.rho.mean()),
            "red_hazard_home_mean_per_match": float(self.red_hazard_home.mean() * 90),
            "components": self.components,
        }


def _lineup_draw(
    players: tuple[PlayerAvailability, ...],
    state: LineupState,
    rng: np.random.Generator,
    n: int,
    cap: float,
):
    """Sample who appears; return (on (n,k) bool, attack multiplier (n,), goal shares (n,k))."""
    if not players:
        return None, np.ones(n), None
    p_play = np.array([p.p_play for p in players])
    if state is LineupState.CONFIRMED:
        p_play = np.where(
            p_play >= 0.5, 1.0, 0.0
        )  # confirmed sheet: no residual availability noise
    on = rng.random((n, len(players))) < p_play
    imp = np.array([p.importance for p in players])
    # attack lost = importance of absent players, capped; replacement recovers a share of it
    lost = ((~on) * imp).sum(axis=1)
    lost = np.minimum(lost, cap)
    attack_mult = 1.0 - 0.6 * lost  # 60% of a missing player's importance is not recovered by depth
    shares = np.array([p.goal_share_if_play for p in players]) * on
    tot = shares.sum(axis=1, keepdims=True)
    shares = np.where(tot > 0, shares / np.where(tot > 0, tot, 1.0), 0.0)
    return on, attack_mult, shares


class WorldGenerator:
    def __init__(self, posterior: ParameterPosterior, config: WorldConfig | None = None) -> None:
        self.posterior = posterior
        self.config = config or WorldConfig()

    def generate(self, ctx: MatchContext, n_worlds: int, rng: np.random.Generator) -> WorldSet:
        cfg = self.config
        post = self.posterior
        params = post.sample(n_worlds, rng)
        lam, mu, rho = post.rates_for(
            params, ctx.home_team_id, ctx.away_team_id, neutral=ctx.neutral_site
        )

        # lineups (correlated: absent striker -> lower attack, reshuffled goal shares)
        h_on, h_mult, h_shares = _lineup_draw(
            ctx.home_players, ctx.lineup_state, rng, n_worlds, cfg.lineup_effect_cap
        )
        a_on, a_mult, a_shares = _lineup_draw(
            ctx.away_players, ctx.lineup_state, rng, n_worlds, cfg.lineup_effect_cap
        )
        lam = lam * h_mult
        mu = mu * a_mult

        # competition environment + model-specification inflation (shared across both teams -> correlated)
        env = np.exp(rng.normal(0.0, cfg.sigma_environment, n_worlds))
        model_infl = np.exp(rng.normal(0.0, cfg.sigma_model_log_rate, n_worlds))
        lam = lam * env * model_infl
        mu = mu * env * model_infl

        # red-card hazard per minute, uncertain per world
        shape = cfg.red_card_shape
        red_h = rng.gamma(shape, cfg.red_card_mean_per_team / shape, n_worlds) / 90.0
        red_a = rng.gamma(shape, cfg.red_card_mean_per_team / shape, n_worlds) / 90.0

        trailing = np.clip(
            rng.normal(cfg.trailing_attack_mult, cfg.state_mult_sd, n_worlds), 0.8, 1.4
        )
        leading = np.clip(
            rng.normal(cfg.leading_attack_mult, cfg.state_mult_sd, n_worlds), 0.6, 1.1
        )

        components = {
            "parameter_posterior": True,
            "lineup_state": ctx.lineup_state.value,
            "lineup_players_home": len(ctx.home_players),
            "lineup_players_away": len(ctx.away_players),
            "environment_sigma": cfg.sigma_environment,
            "model_sigma_log_rate": cfg.sigma_model_log_rate,
            "red_card_prior_mean": cfg.red_card_mean_per_team,
            "state_effects": {
                "trailing": cfg.trailing_attack_mult,
                "leading": cfg.leading_attack_mult,
            },
            "not_modelled": [
                "weather",
                "referee",
                "travel",
                "tactical formation state",
                "goalkeeper-specific effects",
            ],
        }
        return WorldSet(
            n_worlds=n_worlds,
            lam_home=lam,
            mu_away=mu,
            rho=rho,
            red_hazard_home=red_h,
            red_hazard_away=red_a,
            trailing_mult=trailing,
            leading_mult=leading,
            home_players_on=h_on,
            away_players_on=a_on,
            home_goal_shares=h_shares,
            away_goal_shares=a_shares,
            components=components,
            posterior_hash=post.param_hash(),
            config=cfg,
        )
