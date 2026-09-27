"""Match context: everything the world generator needs beyond team strengths."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class LineupState(str, Enum):
    UNKNOWN = "unknown"  # nothing known beyond squad
    PROJECTED = "projected"  # predicted XI / availability news
    CONFIRMED = "confirmed"  # official team sheets published


@dataclass(frozen=True)
class PlayerAvailability:
    player_id: str
    team_id: str
    p_start: float  # P(starts) in the current information state
    p_play: float  # P(appears at all)
    importance: float = (
        0.0  # share of team attack attributable to this player (0..1), from research
    )
    exp_minutes_if_start: float = 80.0
    exp_minutes_if_bench: float = 15.0
    goal_share_if_play: float = 0.0  # share of team goals when on the pitch (research-only)
    penalty_taker_prob: float = 0.0


@dataclass(frozen=True)
class MatchContext:
    fixture_id: str
    competition_id: str
    home_team_id: str
    away_team_id: str
    kickoff_utc: datetime | None
    neutral_site: bool = False
    requires_winner: bool = False  # knockout leg that must produce a winner (ET/pens)
    two_leg_second_leg: bool = False
    first_leg_home_goals: int = 0  # goals scored by this leg's HOME team in the first leg
    first_leg_away_goals: int = 0
    away_goals_rule: bool = False
    lineup_state: LineupState = LineupState.UNKNOWN
    home_players: tuple[PlayerAvailability, ...] = ()
    away_players: tuple[PlayerAvailability, ...] = ()
    rest_days_home: int | None = None
    rest_days_away: int | None = None
    notes: tuple[str, ...] = field(default=())
