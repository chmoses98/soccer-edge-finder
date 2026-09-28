"""Deterministic identities for routed rows.

An id is a function of `source_bet_key` and NOTHING else -- never of a timestamp, a row index
or the batch. That is what lets the router deliver the same fill twice and land on the same
record, and it is what the validator re-derives to prove nobody edited an id by hand.
"""

from __future__ import annotations

import hashlib
import re

POSITION_ID_PREFIX = "pos_"
SETTLEMENT_ID_PREFIX = "stl_"
_DIGEST_CHARS = 24

#: `KX<SERIES>-<EVENTCODE>[-<LEG>]`; the event ticker is the first two segments. Same grammar
#: as `soccer_edge.kalshi.taxonomy._TICKER_RE`, restated here so this module stays import-light.
_EVENT_TICKER_RE = re.compile(r"^(KX[A-Z0-9]+-[A-Z0-9]+)(?:-|$)")


def _digest(source_bet_key: str) -> str:
    return hashlib.sha256(source_bet_key.encode("utf-8")).hexdigest()[:_DIGEST_CHARS]


def mint_position_id(source_bet_key: str) -> str:
    """`pos_` + sha256(source_bet_key)[:24]."""
    return POSITION_ID_PREFIX + _digest(source_bet_key)


def mint_settlement_id(source_bet_key: str) -> str:
    """`stl_` + sha256(source_bet_key)[:24]. One settlement per position, keyed the same way."""
    return SETTLEMENT_ID_PREFIX + _digest(source_bet_key)


def event_ticker_for(market_ticker: str) -> str:
    """The Kalshi EVENT ticker a market belongs to, from the market ticker alone.

    `KXEPLGAME-26OCT10ARSLEE-ARS` -> `KXEPLGAME-26OCT10ARSLEE`. This is `PositionV1.event_id`
    for a routed position: it is derivable offline from the one identifier the router sends,
    and it needs no registry lookup. Resolving it to a fixture id (`fx:...`) would need the
    fixture data that lives on `main` at run time and is deliberately not done at import time.
    A ticker that does not follow the grammar is used verbatim rather than refused.
    """
    match = _EVENT_TICKER_RE.match(market_ticker)
    return match.group(1) if match else market_ticker
