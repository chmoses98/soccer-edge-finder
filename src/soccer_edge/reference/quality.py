"""Reference-price source quality classes and the provider registry (remediation phase 7; audit §H, §K, §R1).

A reference price is only as useful as its source is sharp and its timing is close. Every reference
snapshot therefore carries an explicit `source_quality`, and nothing downstream may treat a soft book or
the Kalshi book itself as a sharp reference.

    SHARP_REFERENCE      a bookmaker whose closing line is an accepted efficiency benchmark (Pinnacle)
    SECONDARY_REFERENCE  a soft/retail book or a multi-book average (Bet365, football-data 'average',
                         'max', our 'consensus'); useful context, never a CLV anchor on its own
    KALSHI_ONLY          the Kalshi order book; a separate axis (KALSHI_CLOSE), never an external reference
    UNAVAILABLE          no quote

Free-source research (2026-09-28), see docs/REFERENCE_SOURCES.md for the evidence:

* football-data.co.uk `fixtures.csv` (keyless, free): Bet365 / Pinnacle / average / max 1X2 and O/U 2.5
  for upcoming fixtures of its covered divisions. Pinnacle column present -> SHARP_REFERENCE, but the file
  is refreshed a few times per week, so quotes are pre-match snapshots of unknown age: `is_close_candidate`
  is only set when the capture lands inside the close window, and that is rare by construction.
* football-data.co.uk season CSVs: Pinnacle/Bet365 *opening* (PSH/B365H) and *closing* (PSCH/B365CH)
  1X2, O/U and AH odds since 2019-20 -> historical SHARP_REFERENCE open/close pairs for research
  (`research/move_v1.py`), never live.
* Kalshi public API: KALSHI_ONLY.
* No keyless, ToS-compliant, live near-kickoff sharp feed exists: Pinnacle's API, Betfair's exchange API
  and every aggregator (The Odds API, OddsAPI, Betfair historical) require credentials or a paid plan;
  scraping OddsPortal/Sofascore/Oddschecker violates their terms. `live_sharp_reference_available()` is
  therefore False and the promotion evaluator keeps reference-anchored authority blocked until the owner
  provides a credentialed source.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SourceQuality(str, Enum):
    SHARP_REFERENCE = "SHARP_REFERENCE"
    SECONDARY_REFERENCE = "SECONDARY_REFERENCE"
    KALSHI_ONLY = "KALSHI_ONLY"
    UNAVAILABLE = "UNAVAILABLE"


BOOKMAKER_QUALITY: dict[str, SourceQuality] = {
    "pinnacle": SourceQuality.SHARP_REFERENCE,
    "bet365": SourceQuality.SECONDARY_REFERENCE,
    "average": SourceQuality.SECONDARY_REFERENCE,
    "max": SourceQuality.SECONDARY_REFERENCE,
    "consensus": SourceQuality.SECONDARY_REFERENCE,
    "kalshi": SourceQuality.KALSHI_ONLY,
}


def quality_for_bookmaker(bookmaker: str) -> SourceQuality:
    return BOOKMAKER_QUALITY.get(bookmaker, SourceQuality.UNAVAILABLE)


@dataclass(frozen=True)
class ReferenceProviderSpec:
    provider_id: str
    description: str
    credentials_required: bool
    cost: str  # 'free' | 'paid'
    live: bool  # quotes for upcoming fixtures
    near_kickoff: bool  # can be captured inside the close window with a known quote time
    historical_open_close: bool
    bookmakers: tuple[str, ...]
    best_quality: SourceQuality
    terms_ok: bool
    note: str = ""


REFERENCE_PROVIDERS: dict[str, ReferenceProviderSpec] = {
    "football_data_couk_fixtures": ReferenceProviderSpec(
        "football_data_couk_fixtures",
        "football-data.co.uk fixtures.csv: upcoming odds (Bet365, Pinnacle, average, max)",
        credentials_required=False,
        cost="free",
        live=True,
        near_kickoff=False,
        historical_open_close=False,
        bookmakers=("bet365", "pinnacle", "average", "max"),
        best_quality=SourceQuality.SHARP_REFERENCE,
        terms_ok=True,
        note="refreshed a few times per week; quote time unknown (stamped at our capture); blocked from some egress, fine from Actions",
    ),
    "football_data_couk_historical": ReferenceProviderSpec(
        "football_data_couk_historical",
        "football-data.co.uk season CSVs: opening + closing odds (PSH/PSCH, B365H/B365CH, AH, O/U)",
        credentials_required=False,
        cost="free",
        live=False,
        near_kickoff=True,
        historical_open_close=True,
        bookmakers=("bet365", "pinnacle", "average", "max"),
        best_quality=SourceQuality.SHARP_REFERENCE,
        terms_ok=True,
        note="research only (move_v1, close benchmarks); closing columns exist from 2019-20",
    ),
    "kalshi_public": ReferenceProviderSpec(
        "kalshi_public",
        "Kalshi public order book (the market being priced)",
        credentials_required=False,
        cost="free",
        live=True,
        near_kickoff=True,
        historical_open_close=False,
        bookmakers=("kalshi",),
        best_quality=SourceQuality.KALSHI_ONLY,
        terms_ok=True,
        note="KALSHI_CLOSE axis only; never an external sharp reference",
    ),
    "the_odds_api": ReferenceProviderSpec(
        "the_odds_api",
        "The Odds API (includes Pinnacle): near-kickoff sharp quotes",
        credentials_required=True,
        cost="paid (free tier needs an API key)",
        live=True,
        near_kickoff=True,
        historical_open_close=False,
        bookmakers=("pinnacle", "bet365"),
        best_quality=SourceQuality.SHARP_REFERENCE,
        terms_ok=True,
        note="NOT implemented: requires an owner-provided key (audit §R1); adapter slot reserved",
    ),
}


def live_sharp_reference_available() -> tuple[bool, str]:
    """Is there an implemented, credential-free, terms-compliant source of near-kickoff SHARP quotes?"""
    for spec in REFERENCE_PROVIDERS.values():
        if (
            spec.live
            and spec.near_kickoff
            and spec.best_quality is SourceQuality.SHARP_REFERENCE
            and not spec.credentials_required
            and spec.terms_ok
        ):
            return True, spec.provider_id
    return (
        False,
        "no free, keyless, terms-compliant live near-kickoff sharp source exists; football-data fixtures.csv "
        "carries Pinnacle but refreshes a few times per week (pre-match, not close); reference-anchored "
        "authority stays blocked (audit §R1)",
    )
