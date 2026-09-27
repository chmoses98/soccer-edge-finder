"""Decide whether a Kalshi series is soccer. Fail closed on ambiguity: AMBIGUOUS is retained
and dispositioned, never dropped. Bare 'Football' is ambiguous (NFL/CFB/soccer)."""

from __future__ import annotations

import re

from soccer_edge.kalshi.schemas import Ownership, RawSeries
from soccer_edge.kalshi.taxonomy import COMPETITION_CODES, FAMILY_TOKENS

SOCCER_TAGS = {"soccer", "football (soccer)", "association football", "futbol", "fútbol"}
AMERICAN_FOOTBALL_HINTS = {
    "nfl",
    "ncaa",
    "college football",
    "super bowl",
    "cfb",
    "touchdown",
    "quarterback",
}
SOCCER_TITLE_HINTS = (
    "premier league",
    "la liga",
    "laliga",
    "bundesliga",
    "serie a",
    "ligue 1",
    "champions league",
    "europa league",
    "mls",
    "major league soccer",
    "world cup",
    "copa ",
    "uefa",
    "concacaf",
    "conmebol",
    "eredivisie",
    "primeira liga",
    "liga mx",
    "nwsl",
    "soccer",
    "goals",
    "fifa",
)
_BODY = re.compile(r"^KX([A-Z0-9]+)$")
# Verified from a sibling repo's live series registry: 349 NFL series carry ONLY the tag 'Football'.
AMERICAN_FOOTBALL_PREFIXES = (
    "KXNFL",
    "KXNCAAF",
    "KXCFB",
    "KXSUPERBOWL",
    "KXSB",
    "KXPROFOOTBALL",
    "KXCOLLEGEFOOTBALL",
    "KXHEISMAN",
    "KXAFC",
    "KXNFC",
)
AMERICAN_FOOTBALL_TITLE_HINTS = (
    "nfl",
    "ncaa",
    "college football",
    "super bowl",
    "afc championship",
    "nfc championship",
    "touchdown",
    "quarterback",
    "heisman",
    "passing yards",
    "rushing yards",
    "receiving yards",
    "field goal",
)


def _matches_soccer_grammar(ticker: str) -> bool:
    m = _BODY.match(ticker)
    if not m:
        return False
    body = m.group(1)
    for tok in sorted(FAMILY_TOKENS, key=len, reverse=True):
        if body.endswith(tok) and body[: -len(tok)] in COMPETITION_CODES:
            return True
    return body in COMPETITION_CODES


def has_soccer_wording(series: RawSeries) -> bool:
    title = series.title.lower()
    return any(h in title for h in SOCCER_TITLE_HINTS) and not any(
        h in title for h in AMERICAN_FOOTBALL_TITLE_HINTS
    )


def classify_ownership(series: RawSeries) -> tuple[Ownership, str]:
    tags = {t.lower() for t in series.tags}
    title = series.title.lower()
    cat = series.category.lower()
    if tags & SOCCER_TAGS:
        if series.ticker.startswith(AMERICAN_FOOTBALL_PREFIXES) or any(
            h in title for h in AMERICAN_FOOTBALL_TITLE_HINTS
        ):
            return (
                Ownership.AMBIGUOUS,
                "soccer tag but american-football ticker/wording (known Kalshi mis-tags)",
            )
        return Ownership.SOCCER, "soccer tag"
    if series.ticker.startswith(AMERICAN_FOOTBALL_PREFIXES):
        return Ownership.NOT_SOCCER, "american-football ticker prefix"
    if _matches_soccer_grammar(series.ticker):
        if any(h in title for h in AMERICAN_FOOTBALL_HINTS):
            return Ownership.AMBIGUOUS, "soccer ticker grammar but american-football wording"
        return Ownership.SOCCER, "ticker matches soccer competition grammar"
    if cat == "sports" and any(h in title for h in SOCCER_TITLE_HINTS):
        if any(h in title for h in AMERICAN_FOOTBALL_HINTS):
            return Ownership.AMBIGUOUS, "mixed soccer/american-football wording"
        return Ownership.SOCCER, "sports category with soccer competition wording"
    if "football" in tags and not (tags & {"nfl", "college football", "ncaaf"}):
        if any(h in title for h in AMERICAN_FOOTBALL_TITLE_HINTS):
            return Ownership.NOT_SOCCER, "bare 'Football' tag with american-football wording"
        return Ownership.AMBIGUOUS, "bare 'Football' tag"
    return Ownership.NOT_SOCCER, "no soccer evidence"
