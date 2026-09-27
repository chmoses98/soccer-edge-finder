"""Synthetic Kalshi transport for tests and offline demos. Clearly labelled SYNTHETIC.

Generates a plausible soccer surface (totals ladders, spreads, team totals, a 3-way GAME family,
one player prop, one unknown family) for given fixtures, with cursor pagination and optional
injected failures so completeness logic can be exercised.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from soccer_edge.core.time import iso_utc
from soccer_edge.identity.models import Fixture
from soccer_edge.identity.registry import AliasRegistry

COMP_CODE = {
    "eng.premier_league": "EPL",
    "esp.la_liga": "LALIGA",
    "ger.bundesliga": "BUNDESLIGA",
    "ita.serie_a": "SERIEA",
    "fra.ligue_1": "LIGUE1",
    "usa.mls": "MLS",
}


def _code(name: str) -> str:
    letters = "".join(ch for ch in name.upper() if ch.isalpha())
    return letters[:3]


def _mon(d) -> str:
    return f"{d:%y}{d:%b}{d:%d}".upper()


def _px(p: float) -> tuple[str, str, str, str]:
    p = min(max(p, 0.03), 0.97)
    bid = math.floor(p * 100 - 1.5) / 100
    ask = math.ceil(p * 100 + 1.5) / 100
    bid = min(max(bid, 0.01), 0.98)
    ask = min(max(ask, bid + 0.01), 0.99)
    return f"{bid:.4f}", f"{ask:.4f}", f"{1 - ask:.4f}", f"{1 - bid:.4f}"


@dataclass
class FakeKalshi:
    fixtures: list[Fixture]
    registry: AliasRegistry
    fair: Callable[[Fixture], dict[str, float]] | None = (
        None  # fixture -> {'home','draw','away','mean_total'}
    )
    page_size: int = 50
    fail_on: set[str] = field(default_factory=set)  # e.g. {'/markets:KXEPLTOTAL'} to inject failure
    include_unknown_family: bool = True
    extra_series: list[dict[str, Any]] = field(default_factory=list)
    _series: list[dict[str, Any]] = field(default_factory=list, init=False)
    _markets: dict[str, list[dict[str, Any]]] = field(default_factory=dict, init=False)
    _events: dict[str, list[dict[str, Any]]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.build()

    def build(self) -> None:
        self._series = [
            {
                "ticker": "KXNFLGAME",
                "title": "NFL game winner",
                "category": "Sports",
                "tags": ["Football", "NFL"],
                "fee_type": "quadratic",
            },
            {
                "ticker": "KXBTC",
                "title": "Bitcoin price",
                "category": "Financials",
                "tags": ["Crypto"],
                "fee_type": "quadratic",
            },
            {
                "ticker": "KXFOOTBALLMYSTERY",
                "title": "Football something",
                "category": "Sports",
                "tags": ["Football"],
                "fee_type": "quadratic",
            },
            *self.extra_series,
        ]
        comps = sorted({f.competition_id for f in self.fixtures})
        for comp in comps:
            code = COMP_CODE.get(comp, "EPL")
            fams = ["GAME", "TOTAL", "SPREAD", "TEAMTOTAL", "GOAL"] + (
                ["CORNERS"] if self.include_unknown_family else []
            )
            for fam in fams:
                st = f"KX{code}{fam}"
                self._series.append(
                    {
                        "ticker": st,
                        "title": f"{comp} {fam.lower()}",
                        "category": "Sports",
                        "tags": ["Soccer"],
                        "fee_type": "quadratic",
                        "fee_multiplier": 1,
                        "frequency": "daily",
                    }
                )
                self._markets[st] = []
                self._events[st] = []
        for fx in self.fixtures:
            comp = COMP_CODE.get(fx.competition_id, "EPL")
            home, away = self.registry.teams[fx.home_team_id], self.registry.teams[fx.away_team_id]
            hc, ac = _code(home.name), _code(away.name)
            if hc == ac:
                ac = ac[:2] + "X"
            ev = f"{_mon(fx.kickoff_utc or __import__('datetime').datetime.fromisoformat(fx.kickoff_date + 'T15:00:00+00:00'))}{ac}{hc}"
            close = fx.kickoff_utc or __import__("datetime").datetime.fromisoformat(
                fx.kickoff_date + "T15:00:00+00:00"
            )
            f = (
                self.fair(fx)
                if self.fair
                else {"home": 0.45, "draw": 0.27, "away": 0.28, "mean_total": 2.7}
            )
            title = f"{home.name} vs {away.name}"
            common = {
                "close_time": iso_utc(close),
                "expected_expiration_time": iso_utc(close + timedelta(hours=3)),
                "status": "active",
                "market_type": "binary",
                "event_title": title,
            }

            def add(
                st: str, tk: str, mtitle: str, p: float, extra: dict[str, Any] | None = None
            ) -> None:
                yb, ya, nb, na = _px(p)
                m = {
                    "ticker": tk,
                    "event_ticker": f"{st}-{ev}",
                    "series_ticker": st,
                    "title": mtitle,
                    "yes_bid_dollars": yb,
                    "yes_ask_dollars": ya,
                    "no_bid_dollars": nb,
                    "no_ask_dollars": na,
                    "yes_ask_size_fp": "500",
                    "no_ask_size_fp": "500",
                    "volume_fp": "100",
                    "rules_primary": f"Settles YES if {mtitle}",
                    **common,
                    **(extra or {}),
                }
                self._markets[st].append(m)
                if not any(e["event_ticker"] == f"{st}-{ev}" for e in self._events[st]):
                    self._events[st].append(
                        {
                            "event_ticker": f"{st}-{ev}",
                            "series_ticker": st,
                            "title": title,
                            "sub_title": fx.stage or "",
                            "category": "Sports",
                            "strike_date": iso_utc(close),
                        }
                    )

            g = f"KX{comp}GAME"
            add(g, f"{g}-{ev}-{hc}", f"{home.name} wins?", f["home"])
            add(g, f"{g}-{ev}-{ac}", f"{away.name} wins?", f["away"])
            add(g, f"{g}-{ev}-TIE", "Draw?", f["draw"])
            mt = f["mean_total"]
            for n in (1, 2, 3, 4, 5):
                line = n + 0.5
                p_over = 1 - _poisson_cdf(n, mt)
                add(
                    f"KX{comp}TOTAL",
                    f"KX{comp}TOTAL-{ev}-{n + 1}",
                    f"Will over {line} goals be scored?",
                    p_over,
                    {"floor_strike": line},
                )
            for n in (1, 2):
                add(
                    f"KX{comp}SPREAD",
                    f"KX{comp}SPREAD-{ev}-{hc}{n + 1}",
                    f"{home.name} wins by more than {n + 0.5} goals?",
                    max(0.02, f["home"] * 0.5**n),
                    {"floor_strike": n + 0.5},
                )
            for n in (1, 2):
                add(
                    f"KX{comp}TEAMTOTAL",
                    f"KX{comp}TEAMTOTAL-{ev}-{hc}{n + 1}",
                    f"Will {home.name} score over {n + 0.5} goals?",
                    1 - _poisson_cdf(n, mt * 0.55),
                    {"floor_strike": n + 0.5},
                )
            add(f"KX{comp}GOAL", f"KX{comp}GOAL-{ev}-{hc}JDOE9-1", "John Doe: 1+ goals", 0.3)
            if self.include_unknown_family:
                add(
                    f"KX{comp}CORNERS",
                    f"KX{comp}CORNERS-{ev}-10",
                    "Will there be over 9.5 corners?",
                    0.5,
                )

    def transport(self, path: str, params: dict[str, Any]) -> tuple[int, Any]:
        cursor = params.get("cursor")
        start = int(cursor) if cursor else 0
        if path == "/series":
            items = self._series
            key = "series"
        elif path == "/markets":
            st = params.get("series_ticker")
            if f"/markets:{st}" in self.fail_on:
                return 429, {"error": "rate limited"}
            status = params.get("status")
            items = list(self._markets.get(st, [])) if status in (None, "open") else []
            key = "markets"
        elif path == "/events":
            st = params.get("series_ticker")
            items = list(self._events.get(st, []))
            key = "events"
        elif path == "/milestones":
            items, key = [], "milestones"
        elif path.startswith("/markets/") and path.endswith("/orderbook"):
            return 200, {
                "orderbook_fp": {
                    "yes_dollars": [["0.40", "100"], ["0.42", "50"]],
                    "no_dollars": [["0.50", "100"], ["0.55", "80"]],
                }
            }
        else:
            return 404, {"error": "unknown path"}
        page = items[start : start + self.page_size]
        nxt = str(start + self.page_size) if start + self.page_size < len(items) else ""
        return 200, {key: page, "cursor": nxt}


def _poisson_cdf(k: int, lam: float) -> float:
    return sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(k + 1))
