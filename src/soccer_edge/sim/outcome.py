"""Joint outcome arrays. Every priced contract derives from these same realisations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from soccer_edge.core.serialization import content_hash


@dataclass
class JointOutcome:
    n_worlds: int
    draws_per_world: int
    world_index: np.ndarray  # (N,) int32 -> which world produced draw i
    home_ft: np.ndarray  # regulation goals (90' + stoppage)
    away_ft: np.ndarray
    home_ht: np.ndarray
    away_ht: np.ndarray
    home_red: np.ndarray
    away_red: np.ndarray
    first_goal_team: np.ndarray  # 0 none, 1 home, 2 away
    first_goal_minute: np.ndarray  # 0 when none
    home_et: np.ndarray  # goals in extra time (0 if none played)
    away_et: np.ndarray
    et_played: np.ndarray  # bool
    pens_played: np.ndarray  # bool
    winner_final: np.ndarray  # 0 draw/none, 1 home, 2 away (after ET/pens when applicable)
    home_player_goals: np.ndarray | None = None  # (N, k) research-only
    away_player_goals: np.ndarray | None = None
    home_players_on: np.ndarray | None = None  # (N, k) bool, expanded from worlds
    away_players_on: np.ndarray | None = None
    seed: int = 0
    engine_version: str = ""
    world_hash: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return int(self.home_ft.shape[0])

    @property
    def total_ft(self) -> np.ndarray:
        return self.home_ft + self.away_ft

    @property
    def total_ht(self) -> np.ndarray:
        return self.home_ht + self.away_ht

    @property
    def home_full(self) -> np.ndarray:
        """Goals including extra time (excludes shoot-out)."""
        return self.home_ft + self.home_et

    @property
    def away_full(self) -> np.ndarray:
        return self.away_ft + self.away_et

    def result_ft(self) -> np.ndarray:
        """1 home, 0 draw, 2 away on regulation score."""
        return np.where(self.home_ft > self.away_ft, 1, np.where(self.home_ft < self.away_ft, 2, 0))

    def outcome_hash(self) -> str:
        return content_hash(
            {
                "seed": self.seed,
                "engine": self.engine_version,
                "world_hash": self.world_hash,
                "n": self.n,
                "mean_home": float(self.home_ft.mean()),
                "mean_away": float(self.away_ft.mean()),
            }
        )

    def compact_summary(self, max_goals: int = 8) -> dict[str, Any]:
        """Small, storable summary (never store raw realisations)."""
        hf = np.minimum(self.home_ft, max_goals)
        af = np.minimum(self.away_ft, max_goals)
        grid = np.zeros((max_goals + 1, max_goals + 1))
        np.add.at(grid, (hf, af), 1.0)
        grid /= self.n
        r = self.result_ft()
        return {
            "n_draws": self.n,
            "n_worlds": self.n_worlds,
            "p_home": float((r == 1).mean()),
            "p_draw": float((r == 0).mean()),
            "p_away": float((r == 2).mean()),
            "mean_home_goals": float(self.home_ft.mean()),
            "mean_away_goals": float(self.away_ft.mean()),
            "p_btts": float(((self.home_ft > 0) & (self.away_ft > 0)).mean()),
            "p_over_2_5": float((self.total_ft > 2.5).mean()),
            "p_any_red": float(((self.home_red + self.away_red) > 0).mean()),
            "score_grid": np.round(grid, 5).tolist(),
            "engine_version": self.engine_version,
            "seed": self.seed,
            "world_hash": self.world_hash,
        }
