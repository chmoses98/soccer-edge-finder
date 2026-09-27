"""Canonical identity schemas.

Design rules
------------
* Display names are never primary identity. Every entity has a stable slug id.
* Fixture ids are stable across reschedules: they are derived from
  (competition, season, home, away, stage/leg, occurrence) and NOT from kickoff time.
* Two-legged ties are first-class (`Tie` + `MatchLeg`), because Kalshi contracts
  can settle on a single leg, on aggregate, or on qualification.
* Gender, team kind (club / national / reserve / youth) and country are part of
  identity so similarly named clubs never collide.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from soccer_edge.core.time import ensure_utc

_SLUG = re.compile(r"^[a-z0-9][a-z0-9_.\-]*$")


class Gender(str, Enum):
    MEN = "men"
    WOMEN = "women"


class TeamKind(str, Enum):
    CLUB = "club"
    NATIONAL = "national"
    RESERVE = "reserve"
    YOUTH = "youth"


class CompetitionFormat(str, Enum):
    LEAGUE = "league"  # round robin, home & away
    CUP = "cup"  # single-match knockout (may include replays)
    LEAGUE_PHASE_KNOCKOUT = "league_phase_knockout"  # e.g. UCL post-2024
    GROUP_KNOCKOUT = "group_knockout"  # e.g. World Cup
    TWO_LEG_KNOCKOUT = "two_leg_knockout"
    FRIENDLY = "friendly"


class FixtureStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    RESCHEDULED = "rescheduled"  # superseded by another fixture record
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"
    AWARDED = "awarded"  # result decided off the pitch


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


def _check_slug(value: str, what: str) -> str:
    if not _SLUG.match(value):
        raise ValueError(f"{what} must be a lowercase slug, got {value!r}")
    return value


class Competition(_Frozen):
    competition_id: str = Field(description="stable slug, e.g. 'eng.premier_league'")
    name: str
    country: str = Field(
        description="ISO-3166 alpha-3 or confederation code, e.g. 'ENG', 'UEFA', 'FIFA'"
    )
    gender: Gender = Gender.MEN
    tier: int | None = Field(
        default=None, description="1 = top flight; None for cups/international"
    )
    format: CompetitionFormat
    extra_time_in_knockouts: bool = False
    penalties_in_knockouts: bool = False
    aliases: tuple[str, ...] = ()
    former_names: tuple[str, ...] = Field(
        default=(), description="renamed competitions keep old names as aliases"
    )

    @field_validator("competition_id")
    @classmethod
    def _slug(cls, v: str) -> str:
        return _check_slug(v, "competition_id")


class Season(_Frozen):
    season_id: str = Field(
        description="'2026-27' for cross-year seasons, '2026' for calendar-year seasons"
    )
    competition_id: str
    start_date: str | None = None
    end_date: str | None = None

    @field_validator("season_id")
    @classmethod
    def _fmt(cls, v: str) -> str:
        if not re.match(r"^\d{4}(-\d{2})?$", v):
            raise ValueError(f"season_id must look like 2026 or 2026-27, got {v!r}")
        return v


class Team(_Frozen):
    team_id: str = Field(description="stable slug, e.g. 'eng.arsenal'")
    name: str
    country: str
    gender: Gender = Gender.MEN
    kind: TeamKind = TeamKind.CLUB
    parent_team_id: str | None = Field(
        default=None, description="reserve/youth teams point at the senior side"
    )
    aliases: tuple[str, ...] = ()
    provider_ids: dict[str, str] = Field(
        default_factory=dict, description="provider -> provider-native id"
    )

    @field_validator("team_id")
    @classmethod
    def _slug(cls, v: str) -> str:
        return _check_slug(v, "team_id")

    @model_validator(mode="after")
    def _reserve_needs_parent(self) -> Team:
        if self.kind in (TeamKind.RESERVE, TeamKind.YOUTH) and not self.parent_team_id:
            raise ValueError("reserve/youth teams must declare parent_team_id")
        return self


class Player(_Frozen):
    player_id: str
    name: str
    birth_date: str | None = None
    nationality: str | None = None
    aliases: tuple[str, ...] = ()
    provider_ids: dict[str, str] = Field(default_factory=dict)

    @field_validator("player_id")
    @classmethod
    def _slug(cls, v: str) -> str:
        return _check_slug(v, "player_id")


class Venue(_Frozen):
    venue_id: str
    name: str
    city: str | None = None
    country: str | None = None
    home_team_ids: tuple[str, ...] = ()
    latitude: float | None = None
    longitude: float | None = None


class Fixture(_Frozen):
    fixture_id: str
    competition_id: str
    season_id: str
    home_team_id: str
    away_team_id: str
    kickoff_utc: datetime | None = Field(
        default=None, description="None when only the date is known"
    )
    kickoff_date: str = Field(description="ISO date in competition-local calendar")
    status: FixtureStatus = FixtureStatus.SCHEDULED
    stage: str | None = Field(
        default=None, description="'Matchday 7', 'Round of 16', 'Group A' ..."
    )
    venue_id: str | None = None
    neutral_site: bool = False
    tie_id: str | None = None
    leg_number: int | None = Field(default=None, ge=1, le=2)
    extra_time_possible: bool = False
    penalties_possible: bool = False
    superseded_by: str | None = Field(
        default=None, description="fixture_id of the replacement when rescheduled"
    )
    supersedes: str | None = None
    occurrence: int = Field(
        default=1, ge=1, description="disambiguates replays / re-arranged matches"
    )

    @field_validator("kickoff_utc")
    @classmethod
    def _utc(cls, v: datetime | None) -> datetime | None:
        return ensure_utc(v) if v is not None else v

    @model_validator(mode="after")
    def _consistency(self) -> Fixture:
        if self.home_team_id == self.away_team_id:
            raise ValueError("home and away teams must differ")
        if (self.tie_id is None) != (self.leg_number is None):
            raise ValueError("tie_id and leg_number must be set together")
        if self.status == FixtureStatus.RESCHEDULED and not self.superseded_by:
            raise ValueError("rescheduled fixtures must point at superseded_by")
        return self

    @staticmethod
    def make_id(
        competition_id: str,
        season_id: str,
        home_team_id: str,
        away_team_id: str,
        *,
        stage: str | None = None,
        leg_number: int | None = None,
        occurrence: int = 1,
    ) -> str:
        parts = [competition_id, season_id, home_team_id, away_team_id]
        if stage:
            parts.append(re.sub(r"[^a-z0-9]+", "_", stage.lower()).strip("_"))
        if leg_number:
            parts.append(f"leg{leg_number}")
        if occurrence > 1:
            parts.append(f"occ{occurrence}")
        return "fx:" + ":".join(parts)


class MatchLeg(_Frozen):
    """A fixture's role inside a two-legged tie."""

    tie_id: str
    fixture_id: str
    leg_number: int = Field(ge=1, le=2)


class Tie(_Frozen):
    tie_id: str
    competition_id: str
    season_id: str
    stage: str
    team_a_id: str
    team_b_id: str
    legs: tuple[MatchLeg, ...] = ()
    away_goals_rule: bool = Field(
        default=False, description="UEFA abolished it in 2021; some competitions kept it"
    )
    extra_time_in_second_leg: bool = True
    penalties_after_extra_time: bool = True

    @model_validator(mode="after")
    def _legs_ok(self) -> Tie:
        nums = [leg.leg_number for leg in self.legs]
        if len(nums) != len(set(nums)):
            raise ValueError("duplicate leg numbers in tie")
        if any(leg.tie_id != self.tie_id for leg in self.legs):
            raise ValueError("leg tie_id mismatch")
        return self
