"""The SOCCER app export against the vendored Edge Finder contract (docs/APP_EXPORT.md).

Fixtures under tests/fixtures/app_export are trimmed copies of real data-archive records
(2026-10-02: two fixtures, nine tickers incl. the day's RESEARCH_CANDIDATE, one shadow
recommendation, ESPN ids, status pointers, one heartbeat).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from edge_finder_contract import publish, sync
from edge_finder_contract import routed_ledger as rl

from soccer_edge import app_export
from soccer_edge.accounting import SPEC
from soccer_edge.archive.manifest import classify_path, verify_archive
from soccer_edge.cli import main as cli_main

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "fixtures" / "app_export"
NOW = datetime(2026, 10, 2, 17, 30, tzinfo=UTC)
TICKER = "KXBRASILEIROBTTS-26OCT03ATLRBB-BTTS"
KEY = "kalshi:order:soccer-test-0001"
SECRETS = ("PRIVATE KEY", "ghp_", "github_pat_", "Bearer ", "AIRTABLE")


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    root = tmp_path / "archive"
    shutil.copytree(FIXTURES, root)
    return root


@pytest.fixture
def accounting_dir(tmp_path: Path) -> Path:
    base = tmp_path / "accounting-data"
    base.mkdir()
    wager = {
        "source_bet_key": KEY,
        "import_batch_id": "kalshi-router-v1",
        "entry_method": rl.ENTRY_METHOD,
        "game_date": "2026-10-03",
        "market_ticker": TICKER,
        "side": "NO",
        "executed_at": "2026-10-02T17:25:00Z",
        "contracts": 10,
        "execution_price": 0.45,
        "stake": 10 * 0.45 + 0.17,
        "fees_paid": 0.17,
        "fees_are_estimated": False,
        "venue": "kalshi",
    }
    ghost = dict(wager, source_bet_key="kalshi:order:ghost", market_ticker="KXGHOST-26OCT03XY-Z")
    res = rl.import_wagers(SPEC, base, [wager, ghost], import_batch_id="kalshi-router-v1")
    assert res.written == 2
    settlement = {
        "source_bet_key": KEY,
        "market_ticker": TICKER,
        "side": "NO",
        "settlement_status": "SETTLED",
        "settled_at": "2026-10-04T00:10:00Z",
        "result": "WON",
        "gross_return": 10.0,
        "net_profit_loss": 10.0 - (10 * 0.45 + 0.17),
        "refusals": [],
        "venue": "kalshi",
        "economics_version": rl.ECONOMICS_V2,
    }
    assert rl.import_settlements(SPEC, base, [settlement]).written == 1
    return base


def _export(root: Path, out: Path, *, accounting: Path | None = None, now: datetime = NOW) -> int:
    return app_export.export(
        data_root=root, out=out, accounting_dir=accounting, now=now, log=lambda *_: None
    )


def _snapshot(out: Path) -> dict[str, str]:
    return {
        p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(out.rglob("*.json"))
    }


def _load(out: Path, kind: str) -> list[dict]:
    return json.loads((out / f"{kind}.json").read_text(encoding="utf-8"))["items"]


def test_vendored_contract_is_intact():
    assert sync.check() == []


def test_export_end_to_end(data_root: Path, accounting_dir: Path, tmp_path: Path):
    out = tmp_path / "app" / "latest"
    assert _export(data_root, out, accounting=accounting_dir) == 0
    assert publish.verify_published(out) == []
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["source_repo"] == "chmoses98/soccer-edge-finder"
    assert manifest["source_branch"] == "data-archive"
    assert manifest["commit_sha"] == "56fd30bb79f7"  # from the newest dispatch heartbeat
    counts = manifest["counts"]
    assert counts["events"] == 2 and counts["markets"] == 10  # 9 slate tickers + 1 ledger stub
    assert counts["model_prices"] == 9 and counts["recommendations"] == 1 and counts["theses"] == 1
    assert counts["wagers"] == 2 and counts["settlements"] == 1

    events = {e["event_id"]: e for e in _load(out, "events")}
    for e in events.values():
        assert e["source_ids"]["fixture_id"].startswith("fx:")
        assert e["source_ids"]["espn_event_id"].isdigit()
        assert e["status"] == "SCHEDULED" and e["start_time_confidence"] == "SCHEDULED"
        assert len(e["participants"]) == 2 and e["home_participant"] != e["away_participant"]

    markets = {m["kalshi_ticker"]: m for m in _load(out, "markets")}
    sides = {t: m["side"] for t, m in markets.items()}
    assert sides["KXUEFANLGAME-26OCT02BELTUR-BEL"] == "HOME"
    assert sides["KXUEFANL1HSPREAD-26OCT02BELTUR-BEL2"] == "HOME"
    assert markets["KXUEFANL1HSPREAD-26OCT02BELTUR-BEL2"]["line"] == 1.5
    assert sides["KXUEFANL1HTOTAL-26OCT02BELTUR-1"] == "OVER"
    assert sides[TICKER] is None and sides["KXUEFANLSCORE-26OCT02BELTUR-BEL0TUR0"] is None
    assert (
        markets["KXGHOST-26OCT03XY-Z"]["market_status"] == "SETTLED"
    )  # stub for the ledger-only ticker
    m = markets[TICKER]
    assert (m["yes_bid"], m["yes_ask"], m["no_bid"], m["no_ask"]) == (0.55, 0.57, 0.43, 0.45)
    assert m["kalshi_event_ticker"] == "KXBRASILEIROBTTS-26OCT03ATLRBB"
    assert m["extensions"]["actions"] == {"no": "RESEARCH_CANDIDATE", "yes": "NO_EDGE"}

    prices = {p["market_id"]: p for p in _load(out, "model_prices")}
    p = prices[m["market_id"]]
    assert p["fair_probability"] == pytest.approx(
        1 - 0.558466, abs=1e-6
    )  # P(YES) from the NO row / board
    assert p["lower_bound"] < p["fair_probability"] < p["upper_bound"]
    assert p["market_probability"] == 0.57 and p["data_quality_status"] == "OK"
    assert p["model_version"] == "dc_laplace_v1" and p["support_status"] == "VALID"

    (rec,) = _load(out, "recommendations")
    assert rec["selection"] == "NO" and rec["status"] == "RESEARCH_CANDIDATE"
    assert rec["authority"] == "RESEARCH_ONLY" and rec["research_only"] is True
    assert rec["current_price"] == 0.45 and rec["fair_probability"] == pytest.approx(0.558466)
    assert rec["edge"] == pytest.approx(0.091141) and rec["bet_up_to_price"] == 0.46
    assert rec["expires_at"] == "2026-10-02T17:41:34Z" and rec["market_id"] == m["market_id"]
    assert rec["source_ids"]["slate_id"] == "slate-20261002T172404Z-39df8c"
    assert rec["thesis_id"] is not None

    (thesis,) = _load(out, "theses")
    assert thesis["summary"].startswith("Atlético Mineiro vs Red Bull Bragantino: model xG")
    assert thesis["opposing_factors"] and thesis["event_id"] == rec["event_id"]

    wagers = {w["source_bet_key"]: w for w in _load(out, "wagers")}
    settlements = _load(out, "settlements")
    w = wagers[KEY]
    assert (
        w["source"] == "KALSHI_ROUTER"
        and w["selection"] == "NO"
        and w["market_id"] == m["market_id"]
    )
    assert w["event_id"] == rec["event_id"]
    assert (
        w["settlement_status"] == "SETTLED"
        and w["settlement_id"] == settlements[0]["settlement_id"]
    )
    assert (
        settlements[0]["verification_status"] == "EXCHANGE_CONFIRMED"
        and settlements[0]["result"] == "WON"
    )
    assert settlements[0]["wager_id"] == w["wager_id"]
    # wagers placed at 17:25 predate nothing on the slate (17:24): temporal links are legitimate
    assert (
        w["model_price_id"] == p["model_price_id"]
        and w["recommendation_id"] == rec["recommendation_id"]
    )
    assert wagers["kalshi:order:ghost"]["settlement_status"] == "PENDING"
    assert wagers["kalshi:order:ghost"]["model_price_id"] is None
    # P&L totals equal the ledger's own sums
    ledger = rl.read_jsonl(SPEC.settlements_path(accounting_dir))
    assert sum(s["net_pnl"] for s in settlements) == pytest.approx(
        sum(r["net_profit_loss"] for r in ledger)
    )
    assert sum(w["stake"] for w in wagers.values()) == pytest.approx(
        sum(r["stake"] for r in rl.read_jsonl(SPEC.wagers_path(accounting_dir)))
    )

    health = json.loads((out / "health.json").read_text())
    assert (
        health["overall_status"] == "RESEARCH_ONLY" and health["bet_authority"] == "RESEARCH_ONLY"
    )
    assert health["last_market_capture"] == "2026-10-02T17:21:34Z"
    assert health["last_model_generated"] == "2026-10-02T14:20:20Z"
    assert health["router_status"] == "OK" and health["settlement_status"] in (
        "OK",
        "AGING",
        "STALE",
    )
    assert health["thresholds"]["market_data"] == {
        "fresh_after_seconds": 1200,
        "stale_after_seconds": 3600,
    }
    assert health["thresholds"]["model"] == {
        "fresh_after_seconds": 43200,
        "stale_after_seconds": 129600,
    }
    (run,) = _load(out, "runs")
    assert run["source_ids"]["native_run_id"] == "slate-20261002T172404Z-39df8c"
    assert run["source_ids"]["run_id"] == "run-20261002T142020Z-e11a59"
    assert sorted(p.name for p in (out / "event_detail").iterdir()) == sorted(
        f"{e}.json" for e in events
    )


def test_export_is_deterministic(data_root: Path, accounting_dir: Path, tmp_path: Path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert _export(data_root, a, accounting=accounting_dir) == 0
    assert _export(data_root, b, accounting=accounting_dir) == 0
    assert _snapshot(a) == _snapshot(b)
    ma = json.loads((a / "manifest.json").read_text())["files"]
    mb = json.loads((b / "manifest.json").read_text())["files"]
    assert ma == mb


def test_failure_keeps_payload_and_writes_health_only(data_root: Path, tmp_path: Path):
    out = tmp_path / "latest"
    assert _export(data_root, out) == 0
    before = _snapshot(out)
    slate = data_root / app_export.SLATE_FILE
    slate.write_text(slate.read_text()[:-200])  # truncated JSON: the build raises
    later = NOW + timedelta(minutes=15)
    assert _export(data_root, out, now=later) == 1
    after = _snapshot(out)
    assert {k: v for k, v in after.items() if k != "health.json"} == {
        k: v for k, v in before.items() if k != "health.json"
    }
    health = json.loads((out / "health.json").read_text())
    assert health["components"]["export"]["status"] == "DEGRADED"
    assert health["overall_status"] in ("DEGRADED", "UNAVAILABLE")
    assert health["payload_run_id"] == json.loads((out / "manifest.json").read_text())["run_id"]
    assert health["errors"] and "health-only" not in health["errors"][0]
    assert publish.verify_published(out) == []


def test_failure_with_no_previous_payload_is_unavailable(data_root: Path, tmp_path: Path):
    out = tmp_path / "empty"
    (data_root / app_export.SLATE_FILE).unlink()
    assert _export(data_root, out) == 1
    health = json.loads((out / "health.json").read_text())
    assert health["overall_status"] == "UNAVAILABLE" and health["payload_run_id"] is None
    assert sorted(p.name for p in out.iterdir()) == ["health.json"]


def test_stale_inputs_report_stale(data_root: Path, tmp_path: Path):
    out = tmp_path / "stale"
    assert _export(data_root, out, now=NOW + timedelta(days=30)) == 0
    health = json.loads((out / "health.json").read_text())
    assert health["overall_status"] == "STALE"
    assert health["market_data_status"] == "STALE" and health["model_status"] == "STALE"


def test_naive_timestamp_is_refused(data_root: Path, tmp_path: Path):
    slate_path = data_root / app_export.SLATE_FILE
    doc = json.loads(slate_path.read_text())
    doc["fixtures"][0]["kickoff"] = "2026-10-03T21:30:00"
    for c in doc["contracts"]:
        c["kickoff"] = "2026-10-03T21:30:00"
    slate_path.write_text(json.dumps(doc))
    out = tmp_path / "naive"
    assert _export(data_root, out) == 1
    health = json.loads((out / "health.json").read_text())
    assert "naive" in health["errors"][0].lower()
    assert not (out / "events.json").exists()


def test_no_secret_shaped_strings_and_only_aware_timestamps(
    data_root: Path, accounting_dir: Path, tmp_path: Path
):
    out = tmp_path / "latest"
    assert _export(data_root, out, accounting=accounting_dir) == 0
    for p in out.rglob("*.json"):
        text = p.read_text(encoding="utf-8")
        for s in SECRETS:
            assert s not in text, p

        def walk(v):
            if isinstance(v, dict):
                for x in v.values():
                    walk(x)
            elif isinstance(v, list):
                for x in v:
                    walk(x)
            elif (
                isinstance(v, str)
                and len(v) >= 19
                and v[4] == "-"
                and v[10] == "T"
                and v[:4].isdigit()
            ):
                assert v.endswith("Z") or "+" in v[10:], (p, v)

        walk(json.loads(text))


def test_cli_subcommand_and_script(data_root: Path, tmp_path: Path):
    out = tmp_path / "cli"
    rc = cli_main(
        ["app-export", "--data-root", str(data_root), "--out", str(out), "--now", NOW.isoformat()]
    )
    assert rc == 0 and publish.verify_published(out) == []
    assert (REPO / "scripts" / "app_export.py").exists()


def test_archive_verify_tolerates_app_latest(data_root: Path, tmp_path: Path):
    out = data_root / "app" / "latest"
    assert _export(data_root, out) == 0
    for rel in (
        "app/latest/manifest.json",
        "app/latest/health.json",
        "app/latest/event_detail/evt_x.json",
    ):
        assert classify_path(rel) is None
    code, report = verify_archive(data_root, require_manifest=False)
    assert code == 0
    assert not [f for f in report.get("unmanifested_files", []) if f.startswith("app/")]


def test_publish_hook_never_aborts_the_publish():
    text = (REPO / "scripts" / "archive_publish.sh").read_text()
    hook = [
        ln for ln in text.splitlines() if "app-export" in ln and "python -m soccer_edge.cli" in ln
    ]
    assert hook, "archive_publish.sh must run soccer app-export"
    i = text.index("app-export --data-root")
    assert "|| echo" in text[i : i + 400], "the app export must not abort the publish"
    assert (
        text.index("LATEST_ACTIONABLE_SLATE.md") < i < text.index("archive manifest --archive-dir")
    )


def _real_archive() -> Path | None:
    for cand in (os.environ.get("SOCCER_EDGE_ARCHIVE_DIR"), str(REPO / "archive")):
        if cand and (Path(cand) / app_export.SLATE_FILE).exists():
            return Path(cand)
    return None


@pytest.mark.skipif(
    _real_archive() is None,
    reason="production data lives on the data-archive branch; set SOCCER_EDGE_ARCHIVE_DIR to a checkout",
)
def test_real_data_smoke(tmp_path: Path):
    root = _real_archive()
    assert root is not None
    out = tmp_path / "real"
    assert _export(root, out, now=datetime.now(UTC)) == 0
    assert publish.verify_published(out) == []
    counts = json.loads((out / "manifest.json").read_text())["counts"]
    assert counts["events"] >= 1 and counts["markets"] == counts["model_prices"] >= 1
