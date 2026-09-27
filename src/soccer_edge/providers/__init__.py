"""Data provider abstraction.

Every provider returns `Observation`-wrapped payloads carrying provenance
(source, observed_at, effective_at, freshness, quality flags). The model never
talks to a provider directly; it receives observations through the interfaces in
`soccer_edge.providers.interfaces` so premium adapters can be added later.
"""

from soccer_edge.providers.base import Observation, Provenance, QualityFlag
from soccer_edge.providers.interfaces import (
    EventDataProvider,
    FixtureProvider,
    InjuryProvider,
    LineupProvider,
    OddsProvider,
    PlayerStatsProvider,
    TeamStatsProvider,
    WeatherProvider,
)

__all__ = [
    "EventDataProvider",
    "FixtureProvider",
    "InjuryProvider",
    "LineupProvider",
    "Observation",
    "OddsProvider",
    "PlayerStatsProvider",
    "Provenance",
    "QualityFlag",
    "TeamStatsProvider",
    "WeatherProvider",
]
