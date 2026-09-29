"""The Odds API v4 client: Pinnacle as an external REFERENCE market (never discovery, never execution).

The account and key are SHARED with chmoses98/edge-finder-api (MLB); see docs/ODDS_API_REFERENCE.md for the
audit of that repo's consumption. This module therefore:

* reads the key only from the environment (`ODDS_API_KEY`, the same secret name the MLB repo uses) and
  never puts it in a log line, an exception message, a ledger row or an archived file: every URL that
  leaves this module is the redacted form (`apiKey=***`);
* spends credits only through `get_odds`, which the caller gates with the budget guard
  (`reference/odds_budget.py`); `/sports` and `/events` are the provider's free endpoints and are used to
  find out whether a paid call would return anything before one is made;
* records the provider's quota headers (`x-requests-last/used/remaining`) on every response, free or paid.

Cost rule (measured on this same account by the MLB collectors, `x-requests-last`): a live `/odds` call
costs (number of markets) x (region-equivalents); an explicit `bookmakers` list of up to 10 books counts as
one region-equivalent. Pinnacle-only h2h + totals + spreads = 3 credits per call regardless of how many
events the call returns, so calls are batched per competition (sport key), never per match.

Kalshi remains the market-discovery surface, the execution venue and the source of executable prices and
fees. Nothing here is consulted to decide WHICH markets exist; the caller only asks for reference quotes on
fixtures Kalshi already lists.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from soccer_edge.core.time import ensure_utc, iso_utc, utc_now

BASE_URL = "https://api.the-odds-api.com/v4"
API_KEY_ENV = "ODDS_API_KEY"
REFERENCE_BOOKMAKER = "pinnacle"
DEFAULT_MARKETS: tuple[str, ...] = ("h2h", "totals", "spreads")
QUOTA_HEADERS = ("x-requests-last", "x-requests-used", "x-requests-remaining")

# canonical competition_id -> The Odds API sport key. Keys that the provider does not list as active are
# skipped at run time (the free /sports call is authoritative), so an entry here never costs a credit on
# its own. Competitions without a key are recorded as `no_sport_key`, never guessed.
SPORT_KEYS: dict[str, str] = {
    "eng.premier_league": "soccer_epl",
    "eng.championship": "soccer_efl_champ",
    "eng.fa_cup": "soccer_fa_cup",
    "eng.efl_cup": "soccer_england_efl_cup",
    "esp.la_liga": "soccer_spain_la_liga",
    "esp.copa_del_rey": "soccer_spain_copa_del_rey",
    "ger.bundesliga": "soccer_germany_bundesliga",
    "ger.dfb_pokal": "soccer_germany_dfb_pokal",
    "ita.serie_a": "soccer_italy_serie_a",
    "ita.coppa_italia": "soccer_italy_coppa_italia",
    "fra.ligue_1": "soccer_france_ligue_one",
    "fra.coupe_de_france": "soccer_france_coupe_de_france",
    "ned.eredivisie": "soccer_netherlands_eredivisie",
    "por.primeira_liga": "soccer_portugal_primeira_liga",
    "sco.premiership": "soccer_spl",
    "tur.super_lig": "soccer_turkey_super_league",
    "usa.mls": "soccer_usa_mls",
    "mex.liga_mx": "soccer_mexico_ligamx",
    "bra.serie_a": "soccer_brazil_campeonato",
    "arg.primera": "soccer_argentina_primera_division",
    "ksa.pro_league": "soccer_saudi_arabia_pro_league",
    "uefa.champions_league": "soccer_uefa_champs_league",
    "uefa.europa_league": "soccer_uefa_europa_league",
    "uefa.conference_league": "soccer_uefa_europa_conference_league",
    "uefa.nations_league": "soccer_uefa_nations_league",
    "uefa.euro": "soccer_uefa_european_championship",
    "uefa.euro_qualifiers": "soccer_uefa_euro_qualification",
    "conmebol.libertadores": "soccer_conmebol_copa_libertadores",
    "conmebol.copa_america": "soccer_conmebol_copa_america",
    "fifa.world_cup": "soccer_fifa_world_cup",
    "fifa.club_world_cup": "soccer_fifa_club_world_cup",
    "fifa.womens_world_cup": "soccer_fifa_world_cup_womens",
    "usa.nwsl": "soccer_usa_nwsl",
}

# httpx/httpcore log every request URL at INFO/DEBUG, and our URLs carry the key as a query parameter.
# Nothing in this repo enables those levels, but pin them so no future logging config can leak the key.
for _name in ("httpx", "httpcore"):
    logging.getLogger(_name).setLevel(logging.WARNING)

_KEY_RE = re.compile(r"(apiKey=)[^&\s]+", re.IGNORECASE)


def redact(text: str) -> str:
    """Remove any apiKey query value from a URL or message."""
    key = os.environ.get(API_KEY_ENV)
    out = _KEY_RE.sub(r"\1***", text)
    if key:
        out = out.replace(key, "***")
    return out


def api_key_configured() -> bool:
    return bool(os.environ.get(API_KEY_ENV, "").strip())


@dataclass
class OddsApiResponse:
    endpoint: str  # redacted URL
    kind: str  # 'sports' | 'events' | 'odds'
    sport_key: str | None
    requested_at: datetime
    responded_at: datetime | None
    http_status: int | None
    payload: Any = None
    error: str | None = None
    quota: dict[str, str | None] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.http_status == 200 and self.error is None

    def meta(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "kind": self.kind,
            "sport_key": self.sport_key,
            "requested_at": iso_utc(self.requested_at),
            "responded_at": iso_utc(self.responded_at) if self.responded_at else None,
            "http_status": self.http_status,
            "error": self.error,
            "requests_last": self.quota.get("x-requests-last"),
            "requests_used": self.quota.get("x-requests-used"),
            "requests_remaining": self.quota.get("x-requests-remaining"),
        }


class OddsApiClient:
    """Thin, synchronous, key-redacting client. `transport` lets tests inject an httpx.MockTransport."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = BASE_URL,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._key = (api_key if api_key is not None else os.environ.get(API_KEY_ENV, "")).strip()
        if not self._key:
            raise RuntimeError(f"{API_KEY_ENV} is not configured")
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OddsApiClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get(
        self, path: str, params: dict[str, str], kind: str, sport_key: str | None
    ) -> OddsApiResponse:
        q = {"apiKey": self._key, **params}
        url = f"{self._base}{path}"
        shown = redact(str(httpx.URL(url, params=q)))
        req_at = utc_now()
        try:
            r = self._client.get(url, params=q)
        except httpx.HTTPError as exc:
            return OddsApiResponse(
                shown,
                kind,
                sport_key,
                req_at,
                None,
                None,
                error=redact(type(exc).__name__ + ": " + str(exc))[:300],
            )
        quota = {h: r.headers.get(h) for h in QUOTA_HEADERS}
        resp = OddsApiResponse(
            shown, kind, sport_key, req_at, utc_now(), r.status_code, quota=quota
        )
        if r.status_code != 200:
            resp.error = redact(r.text)[:300]
            return resp
        try:
            resp.payload = r.json()
        except ValueError:
            resp.error = "non-JSON response"
        return resp

    # ---- free endpoints (documented as not counting against the quota; the ledger verifies it) ----
    def get_sports(self) -> OddsApiResponse:
        return self._get("/sports", {}, "sports", None)

    def get_events(
        self, sport_key: str, commence_from: datetime, commence_to: datetime
    ) -> OddsApiResponse:
        return self._get(
            f"/sports/{sport_key}/events",
            {
                "commenceTimeFrom": _z(commence_from),
                "commenceTimeTo": _z(commence_to),
                "dateFormat": "iso",
            },
            "events",
            sport_key,
        )

    # ---- the only credit-spending call ----
    def get_odds(
        self,
        sport_key: str,
        *,
        event_ids: list[str],
        markets: tuple[str, ...] = DEFAULT_MARKETS,
        bookmakers: tuple[str, ...] = (REFERENCE_BOOKMAKER,),
    ) -> OddsApiResponse:
        if not event_ids:
            raise ValueError("refusing a paid /odds call without event ids")
        return self._get(
            f"/sports/{sport_key}/odds",
            {
                "bookmakers": ",".join(bookmakers),
                "markets": ",".join(markets),
                "eventIds": ",".join(event_ids),
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
            "odds",
            sport_key,
        )


def expected_cost(markets: tuple[str, ...], bookmakers: tuple[str, ...]) -> int:
    """Design cost of one /odds call: markets x ceil(books / 10) region-equivalents."""
    return len(markets) * max(1, -(-len(bookmakers) // 10))


def _z(dt: datetime) -> str:
    return ensure_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")
