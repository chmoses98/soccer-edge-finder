"""Canonical soccer identities and alias resolution."""

from soccer_edge.identity.models import (
    Competition,
    CompetitionFormat,
    Fixture,
    FixtureStatus,
    Gender,
    MatchLeg,
    Player,
    Season,
    Team,
    TeamKind,
    Tie,
    Venue,
)
from soccer_edge.identity.registry import AliasRegistry, normalize_alias

__all__ = [
    "AliasRegistry",
    "Competition",
    "CompetitionFormat",
    "Fixture",
    "FixtureStatus",
    "Gender",
    "MatchLeg",
    "Player",
    "Season",
    "Team",
    "TeamKind",
    "Tie",
    "Venue",
    "normalize_alias",
]
