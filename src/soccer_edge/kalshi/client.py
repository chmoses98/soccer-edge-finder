"""Fail-closed Kalshi public client.

Verified facts (see docs/KALSHI_MARKET_MAP.md, sourced from sibling repos' live probes):
* base: https://api.elections.kalshi.com/trade-api/v2 ; unauthenticated GETs work with a UA.
* /series?limit=1000&include_product_metadata=true returns the whole series list (tags, fee_type,
  fee_multiplier).  /markets accepts status in {open, unopened, closed, settled}; responses use
  status in {active, closed, finalized}. Prices arrive as *_dollars 4-dp strings (also legacy cents).
* /events?with_nested_markets=true TRUNCATES nested markets -> never use it for completeness.
* Cursor pagination: a sweep is complete only when the final page carries NO cursor and no page
  failed. Silent 429 truncation destroyed a third of a sibling repo's universe; we never let a
  partial sweep pose as a catalog.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
USER_AGENT = (
    "soccer-edge-finder/0.1 (+https://github.com/chmoses98/soccer-edge-finder; public read-only)"
)

Transport = Callable[[str, dict[str, Any]], tuple[int, Any]]
"""(path, params) -> (status_code, json_body). Injected for tests / replay."""


@dataclass
class PageSweep:
    """Result of walking a cursor chain. Structurally cannot be 'complete with failures'."""

    path: str
    params: dict[str, Any]
    items: list[dict[str, Any]] = field(default_factory=list)
    pages: int = 0
    failures: list[str] = field(default_factory=list)
    saw_terminal_page: bool = False
    truncated_by_cap: bool = False

    @property
    def complete(self) -> bool:
        return self.saw_terminal_page and not self.failures and not self.truncated_by_cap


class KalshiPublicClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        transport: Transport | None = None,
        max_rps: float = 4.0,
        max_retries: int = 4,
        timeout: float = 30.0,
        max_pages: int = 500,
    ) -> None:
        self.base_url = (
            base_url or os.environ.get("SOCCER_EDGE_KALSHI_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self._transport = transport
        self._min_interval = 1.0 / max_rps if max_rps > 0 else 0.0
        self._last_call = 0.0
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_pages = max_pages
        self.request_count = 0
        self.retry_count = 0
        self._client: httpx.Client | None = None

    # ---- low level ---------------------------------------------------------------------
    def _http(self, path: str, params: dict[str, Any]) -> tuple[int, Any]:
        if self._transport is not None:
            return self._transport(path, params)
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
        resp = self._client.get(path, params=params)
        try:
            body = resp.json()
        except ValueError:
            body = {"_raw": resp.text[:500]}
        return resp.status_code, body

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        delay = 1.0
        last_err = "no attempt"
        for attempt in range(self.max_retries + 1):
            wait = self._min_interval - (time.monotonic() - self._last_call)
            if wait > 0 and self._transport is None:
                time.sleep(wait)
            self._last_call = time.monotonic()
            self.request_count += 1
            try:
                status, body = self._http(path, params)
            except httpx.HTTPError as exc:
                status, body = 0, {"error": str(exc)}
            if status == 200:
                return body
            last_err = f"HTTP {status} on {path} {params}: {str(body)[:200]}"
            if status in (429, 500, 502, 503, 504, 0) and attempt < self.max_retries:
                self.retry_count += 1
                if self._transport is None:
                    time.sleep(delay)
                delay = min(delay * 2, 16.0)
                continue
            break
        raise KalshiRequestError(last_err)

    # ---- pagination ---------------------------------------------------------------------
    def sweep(self, path: str, key: str, params: dict[str, Any] | None = None) -> PageSweep:
        params = dict(params or {})
        sw = PageSweep(path=path, params=dict(params))
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            if sw.pages >= self.max_pages:
                sw.truncated_by_cap = True
                sw.failures.append(f"page cap {self.max_pages} reached")
                break
            try:
                body = self.get(path, {**params, "cursor": cursor})
            except KalshiRequestError as exc:
                sw.failures.append(str(exc))
                break
            sw.pages += 1
            page_items = body.get(key)
            if page_items is None:
                sw.failures.append(f"response missing key {key!r} on {path}")
                break
            sw.items.extend(page_items)
            cursor = body.get("cursor") or None
            if not cursor:
                sw.saw_terminal_page = True
                break
            if cursor in seen_cursors:
                sw.failures.append("cursor loop detected")
                break
            seen_cursors.add(cursor)
        return sw

    # ---- endpoints ------------------------------------------------------------------------
    def series(
        self, *, category: str | None = None, include_product_metadata: bool = True
    ) -> PageSweep:
        return self.sweep(
            "/series",
            "series",
            {
                "limit": 1000,
                "category": category,
                "include_product_metadata": "true" if include_product_metadata else None,
            },
        )

    def markets(
        self,
        *,
        series_ticker: str | None = None,
        event_ticker: str | None = None,
        status: str | None = None,
        limit: int = 1000,
        min_close_ts: int | None = None,
    ) -> PageSweep:
        return self.sweep(
            "/markets",
            "markets",
            {
                "limit": limit,
                "series_ticker": series_ticker,
                "event_ticker": event_ticker,
                "status": status,
                "min_close_ts": min_close_ts,
            },
        )

    def events(
        self, *, series_ticker: str | None = None, status: str | None = None, limit: int = 200
    ) -> PageSweep:
        return self.sweep(
            "/events",
            "events",
            {
                "limit": limit,
                "series_ticker": series_ticker,
                "status": status,
                "with_nested_markets": "false",
            },
        )

    def milestones(self, *, milestone_type: str | None = None, limit: int = 200) -> PageSweep:
        return self.sweep("/milestones", "milestones", {"limit": limit, "type": milestone_type})

    def multivariate_event_collections(self, *, limit: int = 200) -> PageSweep:
        return self.sweep(
            "/multivariate_event_collections", "multivariate_contracts", {"limit": limit}
        )

    def market(self, ticker: str) -> dict[str, Any]:
        return self.get(f"/markets/{ticker}")["market"]

    def orderbook(self, ticker: str, depth: int = 10) -> dict[str, Any]:
        return self.get(f"/markets/{ticker}/orderbook", {"depth": depth})

    def iter_market_pages(self, **kwargs: Any) -> Iterator[dict[str, Any]]:
        yield from self.markets(**kwargs).items


class KalshiRequestError(RuntimeError):
    pass
