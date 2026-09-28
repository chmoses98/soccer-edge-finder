"""Provider protocols. Concrete adapters implement one or more of these.

Payload types are deliberately simple dataclass-like Pydantic models so the model layer
depends on *our* schema, never on a vendor's.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from soccer_edge.identity.models import Fixture
from soccer_edge.providers.base import Observation


class _Row(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MatchResult(_Row):
    """A completed match with whatever detail the source supplies."""

    fixture_id: str
    competition_id: str
    season_id: str
    match_date: str
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int
    home_goals_ht: int | None = None
    away_goals_ht: int | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_shots_on_target: int | None = None
    away_shots_on_target: int | None = None
    home_corners: int | None = None
    away_corners: int | None = None
    home_yellow: int | None = None
    away_yellow: int | None = None
    home_red: int | None = None
    away_red: int | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    neutral_site: bool = False
    extra_time_played: bool = False
    decided_on_penalties: bool = False
    # --- settlement evidence (optional; added 2026-09-28 for universal settlement, audit B4) ---
    # `home_goals`/`away_goals` are the source's final score as reported (openfootball: 90'; ESPN
    # scoreboard: including extra time when played). The regulation split below is derived from timed
    # goal events when the source exposes them; settlement fails closed when it needs a split it lacks.
    status_name: str | None = (
        None  # source status token, e.g. ESPN STATUS_FULL_TIME / STATUS_FINAL_PEN
    )
    kickoff_utc: str | None = None
    home_goals_regulation: int | None = None
    away_goals_regulation: int | None = None
    home_goals_et: int | None = None  # goals scored in extra time only
    away_goals_et: int | None = None
    home_shootout: int | None = None
    away_shootout: int | None = None
    winner_after_penalties: str | None = None  # 'home' | 'away'
    first_scorer_team: str | None = None  # 'home' | 'away' | None (unknown / no goals)
    goal_events_source: str | None = (
        None  # provenance of the timed goal events (e.g. espn_scoreboard_details)
    )
    result_source: str | None = None  # provider that reported the result


class TeamSeasonStats(_Row):
    team_id: str
    competition_id: str
    season_id: str
    as_of: date
    matches: int
    goals_for: int
    goals_against: int
    xg_for: float | None = None
    xg_against: float | None = None
    shots_for: int | None = None
    shots_against: int | None = None
    shots_on_target_for: int | None = None
    shots_on_target_against: int | None = None


class PlayerMatchStats(_Row):
    player_id: str
    team_id: str
    fixture_id: str
    minutes: int
    started: bool
    goals: int = 0
    assists: int = 0
    shots: int | None = None
    shots_on_target: int | None = None
    yellow: int = 0
    red: int = 0
    penalties_taken: int = 0
    position: str | None = None


class LineupEntry(_Row):
    player_id: str
    team_id: str
    starting: bool
    position: str | None = None
    shirt_number: int | None = None


class Lineup(_Row):
    fixture_id: str
    confirmed: bool
    published_at: datetime | None = None
    entries: tuple[LineupEntry, ...] = ()
    formation_home: str | None = None
    formation_away: str | None = None


class Availability(_Row):
    """Injury / suspension / doubt for a player."""

    player_id: str
    team_id: str
    status: str = Field(description="out | doubtful | suspended | fit | unknown")
    reason: str | None = None
    expected_return: date | None = None
    reported_at: datetime | None = None


class OddsQuote(_Row):
    fixture_id: str
    bookmaker: str
    market: str = Field(description="'1x2' | 'ou_2.5' | 'ah' ...")
    selection: str
    decimal_odds: float
    line: float | None = None
    quoted_at: datetime | None = None
    is_closing: bool | None = Field(default=None, description="None when the source cannot say")


class WeatherReport(_Row):
    fixture_id: str
    temperature_c: float | None = None
    wind_kph: float | None = None
    precipitation_mm: float | None = None
    forecast_at: datetime | None = None


class MatchEvent(_Row):
    fixture_id: str
    minute: int
    added_time: int = 0
    kind: str = Field(
        description="goal | own_goal | penalty_goal | penalty_miss | yellow | red | sub | var"
    )
    team_id: str
    player_id: str | None = None
    detail: str | None = None


@runtime_checkable
class FixtureProvider(Protocol):
    provider_id: str

    def fixtures(self, competition_id: str, season_id: str) -> Observation[list[Fixture]]: ...

    def results(self, competition_id: str, season_id: str) -> Observation[list[MatchResult]]: ...


@runtime_checkable
class TeamStatsProvider(Protocol):
    provider_id: str

    def team_season_stats(
        self, competition_id: str, season_id: str
    ) -> Observation[list[TeamSeasonStats]]: ...


@runtime_checkable
class PlayerStatsProvider(Protocol):
    provider_id: str

    def player_match_stats(self, fixture_id: str) -> Observation[list[PlayerMatchStats]]: ...


@runtime_checkable
class EventDataProvider(Protocol):
    provider_id: str

    def match_events(self, fixture_id: str) -> Observation[list[MatchEvent]]: ...


@runtime_checkable
class LineupProvider(Protocol):
    provider_id: str

    def lineup(self, fixture_id: str) -> Observation[Lineup]: ...


@runtime_checkable
class InjuryProvider(Protocol):
    provider_id: str

    def availability(self, team_id: str) -> Observation[list[Availability]]: ...


@runtime_checkable
class OddsProvider(Protocol):
    provider_id: str

    def odds(self, fixture_id: str) -> Observation[list[OddsQuote]]: ...


@runtime_checkable
class WeatherProvider(Protocol):
    provider_id: str

    def weather(self, fixture_id: str) -> Observation[WeatherReport]: ...
