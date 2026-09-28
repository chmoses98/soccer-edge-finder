"""Lineup uncertainty layer (Phase 4).

Turns a history of point-in-time ESPN lineup snapshots into, per player and per information state:
  P(start), P(bench), P(unavailable)  and  E[minutes | start], E[minutes | bench]
and a fixture-level state:
  UNCONFIRMED -> no XI published; probabilities come from recent starting history (decayed)
  PROJECTED   -> a projected XI is available (external source; not produced here yet) — reserved
  CONFIRMED   -> the XI was published BEFORE kickoff (snapshot.event_state == 'pre'); P(start) in {0,1}
A snapshot captured at/after kickoff ('post_hoc') is never used to confirm the same fixture: that would be
backward leakage. It IS valid history for later fixtures.

Everything is empirical and shrunk toward priors; nothing here changes contract pricing until MatchContext
consumers opt in (the world generator reads MatchContext.home_players/away_players when present).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from soccer_edge.core.time import ensure_utc
from soccer_edge.model.context import LineupState, PlayerAvailability

# Priors (soccer-generic; documented in docs/LINEUPS.md). Starters average ~80 minutes; bench appearances ~15.
PRIOR_P_START = 0.35  # a random squad member's chance to start (≈11/ (18..25))
PRIOR_STRENGTH = 1.0  # pseudo-sheets behind the prior (weak: a month of sheets dominates)
HALF_LIFE_DAYS = 42.0  # recency weighting of starting history
MINUTES_IF_START = 80.0
MINUTES_IF_BENCH = 15.0


@dataclass(frozen=True)
class LineupObservation:
    """One player's status in one historical, *finished* fixture (from a published team sheet)."""

    player_id: str
    team_id: str
    fixture_key: str  # espn event id or fixture id
    kickoff_utc: datetime
    started: bool
    in_squad: bool  # on the team sheet at all (starter or bench)
    minutes: float | None = None  # if known (ESPN summary lacks minutes; left None → priors)


@dataclass(frozen=True)
class PlayerLineupEstimate:
    player_id: str
    team_id: str
    p_start: float
    p_bench: float
    p_unavailable: float
    exp_minutes_if_start: float
    exp_minutes_if_bench: float
    n_obs: int
    effective_obs: float
    state: LineupState

    def to_availability(self, *, importance: float = 0.0) -> PlayerAvailability:
        return PlayerAvailability(
            player_id=self.player_id,
            team_id=self.team_id,
            p_start=self.p_start,
            p_play=min(
                1.0, self.p_start + self.p_bench * 0.6
            ),  # bench players appear ~60% of the time
            importance=importance,
            exp_minutes_if_start=self.exp_minutes_if_start,
            exp_minutes_if_bench=self.exp_minutes_if_bench,
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "team_id": self.team_id,
            "p_start": round(self.p_start, 4),
            "p_bench": round(self.p_bench, 4),
            "p_unavailable": round(self.p_unavailable, 4),
            "exp_minutes_if_start": round(self.exp_minutes_if_start, 1),
            "exp_minutes_if_bench": round(self.exp_minutes_if_bench, 1),
            "n_obs": self.n_obs,
            "effective_obs": round(self.effective_obs, 3),
            "state": self.state.value,
        }


def _weight(kickoff: datetime, as_of: datetime) -> float:
    age_days = max(0.0, (as_of - kickoff).total_seconds() / 86400.0)
    return 0.5 ** (age_days / HALF_LIFE_DAYS)


def estimate_team(
    history: list[LineupObservation],
    *,
    team_id: str,
    as_of: datetime,
    confirmed_xi: dict[str, bool] | None = None,
    squad_window_days: float = 60.0,
) -> tuple[LineupState, list[PlayerLineupEstimate]]:
    """Estimate every player seen on a team sheet within `squad_window_days`.

    history: observations with kickoff_utc < as_of only (the caller must not pass future fixtures).
    confirmed_xi: {player_id: started} from a pre-kickoff published XI for THIS fixture → CONFIRMED state.
    """
    as_of = ensure_utc(as_of)
    per: dict[str, list[LineupObservation]] = defaultdict(list)
    for ob in history:
        if ob.team_id != team_id:
            continue
        ko = ensure_utc(ob.kickoff_utc)
        if ko >= as_of:
            raise ValueError(
                f"lineup history contains a fixture at/after as_of ({ob.fixture_key}) — backward leakage"
            )
        if (as_of - ko).total_seconds() / 86400.0 <= squad_window_days:
            per[ob.player_id].append(ob)
    # team sheets seen (denominator for "in squad" rate)
    sheets: dict[str, datetime] = {}
    for ob in history:
        if ob.team_id == team_id:
            sheets[ob.fixture_key] = ensure_utc(ob.kickoff_utc)
    sheet_weight = sum(_weight(k, as_of) for (k,) in ((v,) for v in sheets.values()))

    out: list[PlayerLineupEstimate] = []
    if confirmed_xi:
        state = LineupState.CONFIRMED
        for pid, started in confirmed_xi.items():
            obs = per.get(pid, [])
            mins_start = _mean(
                [o.minutes for o in obs if o.started and o.minutes is not None], MINUTES_IF_START
            )
            mins_bench = _mean(
                [o.minutes for o in obs if not o.started and o.in_squad and o.minutes is not None],
                MINUTES_IF_BENCH,
            )
            out.append(
                PlayerLineupEstimate(
                    pid,
                    team_id,
                    1.0 if started else 0.0,
                    0.0 if started else 1.0,
                    0.0,
                    mins_start,
                    mins_bench,
                    len(obs),
                    float(len(obs)),
                    state,
                )
            )
        return state, sorted(out, key=lambda e: (-e.p_start, e.player_id))

    state = (
        LineupState.UNKNOWN
    )  # 'UNCONFIRMED' in docs; the enum's UNKNOWN is the archive vocabulary
    for pid, obs in per.items():
        w = [_weight(ensure_utc(o.kickoff_utc), as_of) for o in obs]
        w_sum = sum(w)
        w_start = sum(wi for wi, o in zip(w, obs, strict=True) if o.started)
        w_squad = sum(wi for wi, o in zip(w, obs, strict=True) if o.in_squad)
        # shrink toward the prior with PRIOR_STRENGTH pseudo-sheets
        p_start = (w_start + PRIOR_P_START * PRIOR_STRENGTH) / (w_sum + PRIOR_STRENGTH)
        # availability: share of the team's recent sheets this player appeared on (missing sheets = absent)
        denom = max(sheet_weight, w_sum) + PRIOR_STRENGTH
        p_in_squad = (w_squad + 0.7 * PRIOR_STRENGTH) / denom
        p_unavail = max(0.0, 1.0 - p_in_squad)
        p_start = min(p_start, p_in_squad)
        p_bench = max(0.0, p_in_squad - p_start)
        mins_start = _mean(
            [o.minutes for o in obs if o.started and o.minutes is not None], MINUTES_IF_START
        )
        mins_bench = _mean(
            [o.minutes for o in obs if not o.started and o.in_squad and o.minutes is not None],
            MINUTES_IF_BENCH,
        )
        out.append(
            PlayerLineupEstimate(
                pid,
                team_id,
                p_start,
                p_bench,
                p_unavail,
                mins_start,
                mins_bench,
                len(obs),
                w_sum,
                state,
            )
        )
    return state, sorted(out, key=lambda e: (-e.p_start, e.player_id))


def _mean(xs: list[float], default: float) -> float:
    return sum(xs) / len(xs) if xs else default


def observations_from_snapshots(
    snapshots: list[dict[str, Any]], team_map: dict[str, str]
) -> list[LineupObservation]:
    """Build history from archived `espn_lineup_snapshot_v1` rows. Uses, per event, the LAST published snapshot
    (post-match sheets carry subs); players not on the sheet are simply absent (=> counted unavailable)."""
    by_event: dict[str, dict[str, Any]] = {}
    for r in snapshots:
        if not r.get("published") or not r.get("kickoff_utc"):
            continue
        prev = by_event.get(r["espn_event_id"])
        if prev is None or r["captured_at"] >= prev["captured_at"]:
            by_event[r["espn_event_id"]] = r
    out: list[LineupObservation] = []
    for eid, r in by_event.items():
        ko = datetime.fromisoformat(r["kickoff_utc"])
        for side in ("home", "away"):
            espn_tid = r.get(f"{side}_espn_id")
            tid = team_map.get(str(espn_tid)) if espn_tid is not None else None
            if tid is None:
                continue
            for p in r.get(side) or []:
                out.append(
                    LineupObservation(
                        player_id=f"espn:{p['athlete_id']}",
                        team_id=tid,
                        fixture_key=eid,
                        kickoff_utc=ko,
                        started=bool(p["starter"]),
                        in_squad=True,
                    )
                )
    return out


@dataclass
class LineupStateTracker:
    """Prospective per-fixture state transitions, appended to the archive (never rewritten)."""

    transitions: list[dict[str, Any]] = field(default_factory=list)

    def observe(
        self,
        fixture_id: str,
        new_state: str,
        at: datetime,
        *,
        source: str,
        minutes_to_kickoff: float | None,
    ) -> bool:
        last = next((t for t in reversed(self.transitions) if t["fixture_id"] == fixture_id), None)
        if last and last["state"] == new_state:
            return False
        self.transitions.append(
            {
                "fixture_id": fixture_id,
                "state": new_state,
                "previous": last["state"] if last else None,
                "at": ensure_utc(at).isoformat(),
                "minutes_to_kickoff": None
                if minutes_to_kickoff is None
                else round(minutes_to_kickoff, 1),
                "source": source,
            }
        )
        return True

    def confirmation_lead_minutes(self) -> list[float]:
        """How long before kickoff XIs were confirmed (the answer to 'when does ESPN publish?')."""
        return [
            t["minutes_to_kickoff"]
            for t in self.transitions
            if t["state"] == "confirmed"
            and t["minutes_to_kickoff"] is not None
            and not math.isnan(t["minutes_to_kickoff"])
        ]
