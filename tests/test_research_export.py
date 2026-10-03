"""The SOCCER research explorer (``app/latest/explorer``) against the vendored contract 1.1.0.

Inputs: the v1 app-export fixtures (tests/fixtures/app_export) overlaid with tests/fixtures/research_export,
trimmed copies of real data-archive rows for the same two fixtures (Belgium-Türkiye, Atlético
Mineiro-Bragantino) up to 2026-10-02T18:00Z: their Kalshi captures and prediction-ledger rows of that day,
one settled fixture (Korea Republic-Venezuela, 3 tickers), ESPN results (UEFA Nations League since
2025-09, friendlies since 2026-03, Brasileirão since 2026-05-15), the confirmed Belgium-Türkiye lineup
sheet and the weather rows. National-team Elo history and the registry are read from main
(data/international, data/registry).
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
from edge_finder_contract import packet, publish, sync
from edge_finder_contract import research as R

from soccer_edge import app_export, research_export
from soccer_edge.archive.manifest import classify_path
from soccer_edge.cli import main as cli_main

REPO = Path(__file__).resolve().parents[1]
V1_FIXTURES = REPO / "tests" / "fixtures" / "app_export"
RX_FIXTURES = REPO / "tests" / "fixtures" / "research_export"
NOW = datetime(2026, 10, 2, 18, 0, tzinfo=UTC)
BEL_TUR = "fx:uefa.nations_league:2026-27:nat.bel:nat.tur"
SETTLED = "fx:fifa.friendly:2026:nat.kor:nat.ven"

#: The capability matrix of scratchpad/phase2/audit_soccer.md (§4 + §10, 2026-10-03), mapped onto the
#: contract vocabulary. Structural capabilities the audit does not rate (rankings, time_series,
#: comparisons, search) follow the status of the data they are built from.
AUDIT_MATRIX = {
    "team_profiles": "PARTIAL",
    "player_profiles": "UNAVAILABLE",
    "event_research": "VERIFIED",
    "team_metrics": "PARTIAL",
    "player_metrics": "UNAVAILABLE",
    "team_game_logs": "PARTIAL",
    "player_game_logs": "PARTIAL",
    "historical_results": "PARTIAL",
    "opponents": "PARTIAL",
    "opponent_adjustment": "PARTIAL",
    "schedule_strength": "UNAVAILABLE",
    "recent_form_windows": "PARTIAL",
    "usage": "UNAVAILABLE",
    "lineups": "PARTIAL",
    "injuries": "UNAVAILABLE",
    "matchup_metrics": "UNAVAILABLE",
    "projection_distributions": "PARTIAL",
    "raw_projections": "VERIFIED",
    "market_prices": "VERIFIED",
    "market_price_history": "VERIFIED",
    "advanced_stats": "RESEARCH",
    "situational_splits": "PARTIAL",
    "player_props": "UNAVAILABLE",
    "team_props": "VERIFIED",
    "game_markets": "VERIFIED",
    "play_by_play": "UNAVAILABLE",
    "weather": "PARTIAL",
    "venue_effects": "UNAVAILABLE",
    "calibration": "VERIFIED",
    "historical_accuracy": "VERIFIED",
    "clv": "PARTIAL",
    "wager_history": "UNAVAILABLE",
    "rankings": "PARTIAL",
    "time_series": "PARTIAL",
    "comparisons": "PARTIAL",
    "search": "VERIFIED",
}
#: The trimmed fixture cannot prove two capabilities, and the exporter says so instead of claiming them:
#: the v1 fixture board was committed without its q[100] quantiles, and the fixture model_health has no
#: cell for the world_sim_v2 families of these events. The real-data test asserts the full matrix.
FIXTURE_GAPS = {"projection_distributions": "UNAVAILABLE", "calibration": "UNAVAILABLE"}
BUDGETS = {"events": 150_000, "teams": 150_000, "market_history": 400_000}


def _noop(*_a, **_k) -> None:
    return None


def _publish(base: Path) -> tuple[Path, Path]:
    root = base / "archive"
    shutil.copytree(V1_FIXTURES, root)
    shutil.copytree(RX_FIXTURES, root, dirs_exist_ok=True)
    out = root / "app" / "latest"
    assert app_export.export(data_root=root, out=out, now=NOW, log=_noop) == 0
    assert research_export.export_explorer(app_root=out, data_root=root, log=_noop) == 0
    return root, out


@pytest.fixture(scope="module")
def published(tmp_path_factory) -> tuple[Path, Path]:
    return _publish(tmp_path_factory.mktemp("rx"))


def _items(out: Path, kind: str) -> list[dict]:
    return json.loads((out / f"{kind}.json").read_text(encoding="utf-8"))["items"]


def _explorer(out: Path) -> tuple[dict, dict[str, dict]]:
    return R.load_explorer(out)


def test_contract_untouched():
    assert sync.check() == []


def test_explorer_verifies_and_shares_the_v1_publication(published):
    _, out = published
    assert R.verify_explorer(out) == []
    assert publish.verify_published(out) == []
    manifest = json.loads((out / "manifest.json").read_text())
    index, docs = _explorer(out)
    assert index["run_id"] == manifest["run_id"] == index["base_manifest_run_id"]
    assert index["generated_at"] == manifest["generated_at"]
    assert all(d["run_id"] == manifest["run_id"] for d in docs.values())
    assert index["counts"]["teams"] >= 4 and index["counts"]["events"] == 3  # 2 v1 + 1 settled
    assert index["counts"]["players"] == 0
    assert index["as_of"] <= manifest["generated_at"]


def test_every_v1_event_and_participant_is_covered(published):
    _, out = published
    _, docs = _explorer(out)
    markets = _items(out, "markets")
    prices = {mp["market_id"] for mp in _items(out, "model_prices")}
    for ev in _items(out, "events"):
        doc = docs[f"events/{ev['event_id']}.json"]
        assert doc["event"] == ev  # the v1 event object itself: same evt_/prt_ ids
        assert {m["market_id"] for m in doc["markets"]} == {
            m["market_id"] for m in markets if m.get("event_id") == ev["event_id"]
        }
        assert {p["market_id"] for p in doc["projections"]} <= prices
        assert all(p["research_only"] and p["authority"] for p in doc["projections"])
        for p in ev["participants"]:
            prof = docs[f"teams/{p['participant_id']}.json"]
            assert prof["entity"] == p
            assert any(g["event_id"] == ev["event_id"] for g in prof["games"])
        assert doc["market_history_path"] == R.market_history_path(ev["event_id"])


def test_capabilities_match_the_audit(published):
    _, out = published
    _, docs = _explorer(out)
    got = {c["capability"]: c["status"] for c in docs["capabilities.json"]["items"]}
    assert got == {**AUDIT_MATRIX, **FIXTURE_GAPS}
    caps = {c["capability"]: c for c in docs["capabilities.json"]["items"]}
    assert docs["capabilities.json"]["audit_date"] == "2026-10-03"
    for c in caps.values():
        if c["status"] in ("PARTIAL", "RESEARCH"):
            assert c["limitations"], c["capability"]
        if c["status"] == "UNAVAILABLE":
            assert c["reasons"], c["capability"]
    assert any("change-suppressed" in x for x in caps["market_price_history"]["limitations"])


def test_packet_for_a_v1_game(published):
    _, out = published
    ev = next(e for e in _items(out, "events") if e["source_ids"]["fixture_id"] == BEL_TUR)
    pk = packet.build(app_root=out, scope_kind="GAME", event_id=ev["event_id"])
    assert pk["quality"]["missing"] == []
    assert {m["event_id"] for m in pk["markets"]} == {ev["event_id"]} and len(pk["markets"]) == 8
    assert {e["entity_id"] for e in pk["evidence"]} >= {
        p["participant_id"] for p in ev["participants"]
    }
    assert pk["quality"]["capabilities"]["market_price_history"] == "VERIFIED"
    notes = pk["events"][0]["context_notes"]
    assert any("NOT VALIDATED" in n for n in notes) and any("RESEARCH_ONLY" in n for n in notes)
    assert packet.build(app_root=out, scope_kind="GAME", event_id=ev["event_id"]) == pk


def test_research_status_survives_into_profiles_and_packet(published):
    _, out = published
    _, docs = _explorer(out)
    reg = {m["metric_id"]: m for m in docs["metrics.json"]["items"]}
    dc = "met_soccer.dc_attack"
    assert reg[dc]["quality"]["status"] == "RESEARCH" and not reg[dc]["quality"]["production"]
    ev = next(e for e in _items(out, "events") if e["source_ids"]["fixture_id"] == BEL_TUR)
    for p in ev["participants"]:
        obs = [
            o for o in docs[f"teams/{p['participant_id']}.json"]["metrics"] if o["metric_id"] == dc
        ]
        assert obs and all(o["quality_status"] == "RESEARCH" for o in obs)
        assert all(o["extensions"]["not_production_posterior"] for o in obs)
    pk = packet.build(app_root=out, scope_kind="GAME", event_id=ev["event_id"])
    pobs = [o for e in pk["evidence"] for o in e["observations"] if o["metric_id"] == dc]
    assert pobs and all(o["quality_status"] == "RESEARCH" for o in pobs)
    assert dc in pk["quality"]["research_only_items"]
    # the international-pool projections are RESEARCH, inside the event document
    doc = docs[f"events/{ev['event_id']}.json"]
    assert doc["projections"] and all(p["quality_status"] == "RESEARCH" for p in doc["projections"])


def test_market_history_projection_history_and_settlement(published):
    _, out = published
    _, docs = _explorer(out)
    ev = next(e for e in _items(out, "events") if e["source_ids"]["fixture_id"] == BEL_TUR)
    mh = docs[f"market_history/{ev['event_id']}.json"]
    assert mh["series"] and all(
        p["source"].startswith("kalshi:cap-") for s in mh["series"] for p in s["points"]
    )
    assert all(
        p["captured_at"] <= "2026-10-02T18:00:00Z" for s in mh["series"] for p in s["points"]
    )
    doc = docs[f"events/{ev['event_id']}.json"]
    summ = doc["extensions"]["market_history_summary"]
    assert summ["minutes_before_kickoff_last"] > 0 and summ["change_suppressed"]
    assert doc["extensions"]["projection_history"]
    assert doc["context"]["lineups"] and doc["context"]["lineups"][0]["home"]["players"]
    assert doc["context"]["weather"]["provider"] == "open_meteo"
    assert [s for s in docs.values() if s["kind"] == "time_series" and s["x_axis"] == "RUN"]
    settled = next(
        d
        for d in docs.values()
        if d["kind"] == "event_research" and d["extensions"]["fixture_id"] == SETTLED
    )
    assert settled["event"]["status"] == "FINAL" and settled["markets"] == []
    st = settled["extensions"]["settlement"]
    assert st["summary"]["tickers"] == 3 and {t["outcome"] for t in st["tickers"]} <= {"yes", "no"}


def test_rankings_contexts_and_budgets(published):
    _, out = published
    index, docs = _explorer(out)
    rankings = {d["ranking_id"]: d for d in docs.values() if d["kind"] == "ranking"}
    assert rankings
    for d in docs.values():
        if d["kind"] != "entity_profile":
            continue
        for o in d["metrics"]:
            if o.get("context"):
                rk = rankings[o["context"]["ranking_id"]]
                assert R.context_from_ranking(rk, o["entity_id"]) == o["context"]
    for rel, entry in index["files"].items():
        sub = rel.split("/")[0]
        if sub in BUDGETS:
            assert entry["bytes"] <= BUDGETS[sub], rel
    assert (out / "explorer" / "index.json").stat().st_size <= 300_000


def test_no_secret_shaped_strings(published):
    _, out = published
    assert R.no_secret_shaped_strings(out) == []


def test_deterministic(published, tmp_path):
    _, out = published
    _, out2 = _publish(tmp_path)
    assert R.digest_tree(out) == R.digest_tree(out2)


def test_failed_publish_keeps_the_previous_tree(published, tmp_path, monkeypatch):
    root, out = published
    work = tmp_path / "copy"
    shutil.copytree(root, work)
    app = work / "app" / "latest"
    before = R.digest_tree(app)
    v1_before = {p: p.read_bytes() for p in app.glob("*.json")}
    real = research_export.build_explorer

    def without_registry(inputs, **kw):
        docs, meta = real(inputs, **kw)
        return [d for d in docs if d["kind"] != "metric_registry"], meta

    monkeypatch.setattr(research_export, "build_explorer", without_registry)
    assert research_export.export_explorer(app_root=app, data_root=work, log=_noop) == 1
    assert R.digest_tree(app) == before
    assert {p: p.read_bytes() for p in app.glob("*.json")} == v1_before
    assert R.verify_explorer(app) == []


def test_missing_v1_payload_fails_cleanly(tmp_path):
    assert (
        research_export.export_explorer(
            app_root=tmp_path / "nothing", data_root=tmp_path, log=_noop
        )
        == 1
    )
    assert not (tmp_path / "nothing" / "explorer").exists()


def test_cli_script_and_publish_hook(published, tmp_path):
    root, _ = published
    work = tmp_path / "cli"
    shutil.copytree(root, work)
    out = work / "app" / "latest"
    rc = cli_main(["research-export", "--data-root", str(work), "--out", str(out)])
    assert rc == 0 and R.verify_explorer(out) == []
    assert (REPO / "scripts" / "research_export.py").exists()
    for rel in ("app/latest/explorer/index.json", "app/latest/explorer/teams/prt_x.json"):
        assert classify_path(rel) is None  # derived view, never a ledger record
    text = (REPO / "scripts" / "archive_publish.sh").read_text()
    i, j = text.index("app-export --data-root"), text.index("research-export --data-root")
    assert i < j < text.index("archive manifest --archive-dir")
    assert (
        "research_export" in text[j - 1500 : j + 800] and "GITHUB_STEP_SUMMARY" in text[j : j + 800]
    )


def _real_archive() -> Path | None:
    cand = os.environ.get("SOCCER_EDGE_ARCHIVE_DIR")
    if (
        cand
        and (Path(cand) / app_export.SLATE_FILE).exists()
        and (Path(cand) / "snapshots").is_dir()
    ):
        return Path(cand)
    return None


@pytest.mark.skipif(
    _real_archive() is None,
    reason="production data lives on the data-archive branch; set SOCCER_EDGE_ARCHIVE_DIR to a checkout",
)
def test_real_data_explorer(tmp_path):
    root = _real_archive()
    assert root is not None
    out = tmp_path / "real"
    assert app_export.export(data_root=root, out=out, log=_noop) == 0
    assert research_export.export_explorer(app_root=out, data_root=root, log=_noop) == 0
    assert R.verify_explorer(out) == [] and R.no_secret_shaped_strings(out) == []
    index, docs = _explorer(out)
    got = {c["capability"]: c["status"] for c in docs["capabilities.json"]["items"]}
    assert got == AUDIT_MATRIX
    for rel, entry in index["files"].items():
        if rel.split("/")[0] in BUDGETS:
            assert entry["bytes"] <= BUDGETS[rel.split("/")[0]], rel
    assert (out / "explorer" / "index.json").stat().st_size <= 300_000
    events = _items(out, "events")
    assert all(f"events/{e['event_id']}.json" in docs for e in events)
    with_markets = {m["event_id"] for m in _items(out, "markets")}
    ev = next(e for e in events if e["event_id"] in with_markets)
    assert (
        packet.build(app_root=out, scope_kind="GAME", event_id=ev["event_id"])["quality"]["missing"]
        == []
    )
