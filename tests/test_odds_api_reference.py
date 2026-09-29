"""The Odds API (Pinnacle) reference capture: batching, budget guard, quota ledger, key hygiene, close use."""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from soccer_edge.core.serialization import read_jsonl
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.providers.the_odds_api import OddsApiClient, expected_cost, redact
from soccer_edge.reference.close import CloseClassV2, reference_close_for
from soccer_edge.reference.odds_api_capture import DueFixture, capture
from soccer_edge.reference.odds_budget import BudgetConfig, BudgetLedger
from soccer_edge.reference.quality import SourceQuality, live_sharp_reference_available

ROOT = Path(__file__).resolve().parents[1]
KEY = "sekret-test-key-123"
NOW = datetime(2026, 10, 3, 13, 50, tzinfo=UTC)
KO = datetime(2026, 10, 3, 14, 0, tzinfo=UTC)
KO_LATE = datetime(2026, 10, 3, 14, 45, tzinfo=UTC)


@pytest.fixture(scope="module")
def registry() -> AliasRegistry:
    return AliasRegistry.from_directory(ROOT / "data" / "registry")


@pytest.fixture
def cfg() -> BudgetConfig:
    return BudgetConfig.load(ROOT / "config" / "odds_api_budget.json")


def _event(eid, home, away, ko, *, spreads=True):
    markets = [
        {
            "key": "h2h",
            "last_update": "2026-10-03T13:49:00Z",
            "outcomes": [
                {"name": home, "price": 2.10},
                {"name": away, "price": 3.60},
                {"name": "Draw", "price": 3.40},
            ],
        },
        {
            "key": "totals",
            "last_update": "2026-10-03T13:49:00Z",
            "outcomes": [
                {"name": "Over", "price": 1.95, "point": 2.5},
                {"name": "Under", "price": 1.93, "point": 2.5},
            ],
        },
    ]
    if spreads:
        markets.append(
            {
                "key": "spreads",
                "last_update": "2026-10-03T13:49:00Z",
                "outcomes": [
                    {"name": home, "price": 2.05, "point": -0.5},
                    {"name": away, "price": 1.85, "point": 0.5},
                ],
            }
        )
    return {
        "id": eid,
        "sport_key": "soccer_epl",
        "commence_time": ko.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "home_team": home,
        "away_team": away,
        "bookmakers": [
            {"key": "pinnacle", "last_update": "2026-10-03T13:49:00Z", "markets": markets}
        ],
    }


class FakeProvider:
    """httpx transport imitating The Odds API; counts every request and its credit cost."""

    def __init__(self, remaining=11000, events=None):
        self.remaining = remaining
        self.used = 20000 - remaining
        self.requests: list[httpx.Request] = []
        self.events = events or [
            _event("ev1", "Arsenal", "Chelsea", KO),
            _event("ev2", "Aston Villa", "Brighton and Hove Albion", KO_LATE),
        ]

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        cost = 0
        if path.endswith("/sports"):
            body = [
                {"key": "soccer_epl", "active": True},
                {"key": "soccer_efl_champ", "active": False},
            ]
        elif path.endswith("/events"):
            body = [{k: v for k, v in e.items() if k != "bookmakers"} for e in self.events]
        elif path.endswith("/odds"):
            ids = request.url.params["eventIds"].split(",")
            markets = request.url.params["markets"].split(",")
            cost = len(markets)
            body = [e for e in self.events if e["id"] in ids]
        else:
            return httpx.Response(404, text=f"unknown {request.url}")
        self.used += cost
        self.remaining -= cost
        return httpx.Response(
            200,
            json=body,
            headers={
                "x-requests-last": str(cost),
                "x-requests-used": str(self.used),
                "x-requests-remaining": str(self.remaining),
            },
        )

    def factory(self):
        return lambda: OddsApiClient(KEY, transport=httpx.MockTransport(self.handler))

    def paid(self):
        return [r for r in self.requests if r.url.path.endswith("/odds")]


def _due(minutes_close=9.5, minutes_entry=55.0, kalshi=True):
    return [
        DueFixture(
            "fx:eng.premier_league:2026-27:eng.arsenal:eng.chelsea",
            "eng.premier_league",
            KO,
            minutes_close,
            kalshi,
        ),
        DueFixture(
            "fx:eng.premier_league:2026-27:eng.aston_villa:eng.brighton",
            "eng.premier_league",
            KO_LATE,
            minutes_entry,
            kalshi,
        ),
    ]


def test_cost_rule_matches_the_accounts_measured_rule():
    # measured on the shared account (MLB ledgers): x-requests-last == markets x region-equivalents
    assert expected_cost(("h2h", "totals", "spreads"), ("pinnacle",)) == 3
    assert expected_cost(("h2h", "totals"), ("pinnacle", "draftkings", "fanduel", "betmgm")) == 2
    assert expected_cost(("h2h",), tuple(f"b{i}" for i in range(11))) == 2


def test_one_paid_call_per_competition_covers_entry_and_close(tmp_path, registry, cfg):
    fp = FakeProvider()
    stats = capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd-1",
        client_factory=fp.factory(),
    )
    assert stats["status"] == "OK"
    kinds = [r.url.path.rsplit("/", 1)[-1] for r in fp.requests]
    assert kinds == ["sports", "events", "odds"]
    odds_req = fp.paid()[0]
    assert set(odds_req.url.params["eventIds"].split(",")) == {"ev1", "ev2"}
    assert odds_req.url.params["bookmakers"] == "pinnacle"
    assert stats["credits_charged"] == 3
    ps = stats["per_sport"]["soccer_epl"]
    assert ps["close_fixtures"] == 1 and ps["entry_fixtures"] == 1
    # 1X2 (3) + totals (2) + spreads (2) per fixture
    assert ps["snapshots"] == 14 and ps["incomplete_markets"] == 0
    rows = read_jsonl(next((tmp_path / "reference").glob("*/oddsapi-kd-1.jsonl")))
    one = [r for r in rows if r["fixture_id"].endswith("eng.chelsea")]
    x12 = {r["selection"]: r for r in one if r["market"] == "1x2"}
    assert abs(sum(r["devigged_probability"] for r in x12.values()) - 1) < 1e-9
    assert (
        x12["home"]["bookmaker"] == "pinnacle"
        and x12["home"]["source_quality"] == "SHARP_REFERENCE"
    )
    assert x12["home"]["devig_method"] == "power" and x12["home"]["quoted_at"].startswith(
        "2026-10-03T13:49"
    )
    ah = {r["selection"]: r["line"] for r in one if r["market"] == "ah"}
    assert ah == {"home": "-0.5", "away": "0.5"}
    # ledger: every call recorded with the provider's quota headers
    led = BudgetLedger(tmp_path).rows("2026-10-03")
    assert [r["kind"] for r in led] == ["sports", "events", "odds"]
    assert all(r["requests_remaining"] is not None for r in led)
    assert [r["credits_charged"] for r in led] == [0, 0, 3]
    assert led[-1]["charge_basis"] == "PROVIDER_HEADER"


def test_second_tick_does_not_repay_captured_purposes(tmp_path, registry, cfg):
    fp = FakeProvider()
    capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd-1",
        client_factory=fp.factory(),
    )
    n = len(fp.requests)
    stats = capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd-2",
        client_factory=fp.factory(),
    )
    assert stats["status"] == "NOTHING_ELIGIBLE" and len(fp.requests) == n
    # the later fixture reaches its close window: exactly one more paid call, for the close only
    stats = capture(
        _due(minutes_close=-5, minutes_entry=8.0),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW + timedelta(minutes=47),
        batch_id="kd-3",
        client_factory=fp.factory(),
    )
    assert len(fp.paid()) == 2 and stats["per_sport"]["soccer_epl"]["close_fixtures"] == 1


def test_no_http_when_nothing_is_eligible(tmp_path, registry, cfg):
    fp = FakeProvider()
    for due in (_due(kalshi=False), _due(minutes_close=20, minutes_entry=90)):
        stats = capture(
            due,
            registry=registry,
            out_root=tmp_path,
            cfg=cfg,
            now=NOW,
            batch_id="kd",
            client_factory=fp.factory(),
        )
        assert stats["status"] == "NOTHING_ELIGIBLE"
    assert fp.requests == []


def test_reserve_floor_protects_the_shared_account(tmp_path, registry, cfg):
    fp = FakeProvider(remaining=cfg.account_reserve_floor + 2)
    stats = capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd",
        client_factory=fp.factory(),
    )
    assert fp.paid() == []
    assert stats["per_sport"]["soccer_epl"]["status"].endswith("ACCOUNT_RESERVE_FLOOR")
    blocked = [
        r
        for r in BudgetLedger(tmp_path).rows("2026-10-03")
        if r.get("status") == "BLOCKED_BUDGET_GUARD"
    ]
    assert (
        blocked
        and blocked[0]["request_made"] is False
        and blocked[0]["remaining_evidence"] == fp.remaining
    )


def test_daily_ceiling_keeps_a_share_for_closes(tmp_path, registry, cfg):
    led = BudgetLedger(tmp_path)
    led.append(
        NOW,
        {
            "kind": "odds",
            "status": "OK",
            "credits_charged": cfg.daily_credit_ceiling - cfg.close_priority_credits,
        },
    )
    fp = FakeProvider()
    entry_only = [_due()[1]]
    stats = capture(
        entry_only,
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd",
        client_factory=fp.factory(),
    )
    assert (
        stats["per_sport"]["soccer_epl"]["status"].endswith("DAILY_CEILING_ENTRY_SHARE")
        and fp.paid() == []
    )
    stats = capture(
        [_due()[0]],
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd2",
        client_factory=fp.factory(),
    )
    assert stats["per_sport"]["soccer_epl"]["status"] == "OK" and len(fp.paid()) == 1


def test_missing_quota_header_blocks_paid_calls(tmp_path, registry, cfg):
    fp = FakeProvider()
    inner = fp.handler

    def no_headers(request):
        r = inner(request)
        return httpx.Response(r.status_code, content=r.content)

    stats = capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd",
        client_factory=lambda: OddsApiClient(KEY, transport=httpx.MockTransport(no_headers)),
    )
    assert stats["per_sport"]["soccer_epl"]["status"].endswith("REMAINING_QUOTA_UNKNOWN")
    assert fp.paid() == []


def test_not_configured_makes_no_request(tmp_path, registry, cfg, monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    stats = capture(_due(), registry=registry, out_root=tmp_path, cfg=cfg, now=NOW, batch_id="kd")
    assert stats["status"] == "NOT_CONFIGURED"
    assert BudgetLedger(tmp_path).rows("2026-10-03")[0]["credits_charged"] == 0


def test_api_key_never_reaches_disk_or_messages(tmp_path, registry, cfg, monkeypatch):
    monkeypatch.setenv("ODDS_API_KEY", KEY)
    fp = FakeProvider()
    stats = capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd",
        client_factory=fp.factory(),
    )
    assert KEY in str(fp.requests[0].url)  # it is sent to the provider ...
    blob = json.dumps(stats, default=str)
    for f in tmp_path.rglob("*"):
        if f.is_file():
            data = f.read_bytes()
            blob += gzip.decompress(data).decode() if f.suffix == ".gz" else data.decode()
    assert KEY not in blob and "apiKey=***" in blob  # ... and nowhere else
    assert redact(f"https://x/v4/sports?apiKey={KEY}&a=1") == "https://x/v4/sports?apiKey=***&a=1"

    def boom(request):
        raise httpx.ConnectError(f"failed {request.url}")

    r = OddsApiClient(KEY, transport=httpx.MockTransport(boom)).get_sports()
    assert r.http_status is None and KEY not in (r.error or "") and KEY not in r.endpoint


def test_pinnacle_rows_become_a_sharp_true_close(tmp_path, registry, cfg, monkeypatch):
    import soccer_edge.providers.the_odds_api as toa

    monkeypatch.setattr(toa, "utc_now", lambda: NOW)  # the response time is the capture time
    fp = FakeProvider()
    capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd",
        client_factory=fp.factory(),
    )
    rows = [
        r
        for r in read_jsonl(next((tmp_path / "reference").glob("*/oddsapi-kd.jsonl")))
        if r["fixture_id"].endswith("eng.chelsea")
        and r["market"] == "1x2"
        and r["selection"] == "home"
    ]
    rc = reference_close_for(rows, KO)
    assert rc.close_class is CloseClassV2.TRUE_CLOSE
    assert rc.source_quality is SourceQuality.SHARP_REFERENCE and rc.bookmaker == "pinnacle"


def test_sharp_availability_follows_the_credential(monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    monkeypatch.delenv("SOCCER_ODDS_API_CONFIGURED", raising=False)
    assert live_sharp_reference_available()[0] is False
    monkeypatch.setenv("SOCCER_ODDS_API_CONFIGURED", "true")
    assert live_sharp_reference_available() == (True, "the_odds_api")
    monkeypatch.delenv("SOCCER_ODDS_API_CONFIGURED")
    monkeypatch.setenv("ODDS_API_KEY", KEY)
    assert live_sharp_reference_available() == (True, "the_odds_api")


def test_feed_quality_latency_and_timestamps(tmp_path, registry, cfg, monkeypatch):
    import soccer_edge.providers.the_odds_api as toa

    monkeypatch.setattr(toa, "utc_now", lambda: NOW)
    fp = FakeProvider()
    capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd",
        client_factory=fp.factory(),
    )
    rows = read_jsonl(next((tmp_path / "reference").glob("*/oddsapi-kd.jsonl")))
    assert rows and all(r["feed_quality"] == "PINNACLE_AGGREGATED_DELAYED" for r in rows)
    r = rows[0]
    assert r["quoted_at"].startswith("2026-10-03T13:49:00") and r["captured_at"].startswith(
        "2026-10-03T13:50"
    )
    assert r["observation_latency_seconds"] == 60.0
    assert r["kickoff_utc"].startswith("2026-10-03T14:00") or r["kickoff_utc"].startswith(
        "2026-10-03T14:45"
    )


def test_sample_capture_is_bounded_and_never_counts_as_entry_or_close(tmp_path, registry, cfg):
    fp = FakeProvider()
    far = [DueFixture(d.fixture_id, d.competition_id, d.kickoff_utc, 600.0, True) for d in _due()]
    stats = capture(
        far,
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="s1",
        client_factory=fp.factory(),
        force_purpose="sample",
        max_paid_calls=1,
    )
    assert len(fp.paid()) == 1 and stats["credits_charged"] == 3 and stats["snapshots"] == 14
    led = BudgetLedger(tmp_path)
    assert (
        led.fixtures_captured(NOW, "entry") == set()
        and led.fixtures_captured(NOW, "close") == set()
    )
    assert led.rows("2026-10-03")[-1]["purpose"] == "sample"
    # the windows still decide the dispatcher: a close tick after the sample still pays for its close
    capture(
        _due(),
        registry=registry,
        out_root=tmp_path,
        cfg=cfg,
        now=NOW,
        batch_id="kd",
        client_factory=fp.factory(),
    )
    assert len(fp.paid()) == 2


def test_httpx_request_logging_cannot_leak_the_key():
    import logging

    import soccer_edge.providers.the_odds_api  # noqa: F401

    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() >= logging.WARNING
