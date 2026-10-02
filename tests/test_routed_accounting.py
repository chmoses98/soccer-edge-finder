"""The SOCCER routed-wager accounting ledger (docs/ACCOUNTING.md).

The kalshi-bet-router delivers SOCCER wagers through the contract's shared ledger
(``edge_finder_contract.routed_ledger``) parameterised by ``soccer_edge.accounting.SPEC``; the three
scripts under scripts/accounting/ are thin wrappers it runs with the stdlib only. Pinned here:
NEW then DUPLICATE_NOOP is byte-identical, CONFLICT never rewrites, provenance is refused, an orphan
settlement is refused, the validator's verdict, and the scripts' exact router argv printing no
ticker, price, stake or key.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from edge_finder_contract import routed_ledger as rl

from soccer_edge.accounting import SPEC

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts" / "accounting"
TICKER = "KXBRASILEIROBTTS-26OCT03ATLRBB-BTTS"
KEY = "kalshi:order:soccer-0001"
BATCH = "kalshi-router-v1"


def wager_row(**over) -> dict:
    row = {
        "source_bet_key": KEY,
        "import_batch_id": BATCH,
        "entry_method": rl.ENTRY_METHOD,
        "game_date": "2026-10-03",
        "market_ticker": TICKER,
        "side": "NO",
        "executed_at": "2026-10-02T17:30:00Z",
        "contracts": 10,
        "execution_price": 0.45,
        "stake": 10 * 0.45 + 0.17,
        "fees_paid": 0.17,
        "fees_are_estimated": False,
        "venue": "kalshi",
    }
    row.update(over)
    return row


def settlement_row(**over) -> dict:
    row = {
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
    row.update(over)
    return row


def test_spec_is_the_soccer_ledger():
    assert SPEC.sport == "SOCCER"
    assert SPEC.mint_wager_id(KEY).startswith("socw-")
    assert SPEC.mint_settlement_id(KEY).startswith("socs-")
    assert len(SPEC.mint_wager_id(KEY)) == len("socw-") + 24
    assert SPEC.wager_schema == "soccer_accounted_wager.v1"
    assert SPEC.settlement_schema == "soccer_wager_settlement.v1"
    assert SPEC.wagers_path(Path("/x")) == Path("/x/data/accounting/wagers.jsonl")


def test_new_then_duplicate_noop_is_byte_identical(tmp_path: Path):
    first = rl.import_wagers(SPEC, tmp_path, [wager_row()], import_batch_id=BATCH)
    assert (first.written, first.duplicate, first.refused) == (1, 0, 0)
    assert first.rows[0]["status"] == rl.NEW
    path = SPEC.wagers_path(tmp_path)
    before = path.read_bytes()
    rec = json.loads(before)
    assert rec["wager_id"] == SPEC.mint_wager_id(KEY)
    assert rec["schema_version"] == SPEC.wager_schema
    second = rl.import_wagers(SPEC, tmp_path, [wager_row()], import_batch_id=BATCH)
    assert (second.written, second.duplicate, second.refused) == (0, 1, 0)
    assert second.rows[0]["status"] == rl.DUPLICATE_NOOP and second.rows[0]["success"]
    assert path.read_bytes() == before


def test_conflict_never_rewrites(tmp_path: Path):
    rl.import_wagers(SPEC, tmp_path, [wager_row()], import_batch_id=BATCH)
    path = SPEC.wagers_path(tmp_path)
    before = path.read_bytes()
    res = rl.import_wagers(
        SPEC,
        tmp_path,
        [wager_row(contracts=12, stake=12 * 0.45 + 0.17)],
        import_batch_id=BATCH,
    )
    assert res.refused == 1 and res.conflicted
    assert res.rows[0]["status"] == rl.CONFLICT
    assert set(res.rows[0]["conflicting_fields"]) == {"contracts", "stake"}
    assert path.read_bytes() == before


@pytest.mark.parametrize("field", ["recommendation_id", "model_probability", "fair_prob", "edge"])
def test_provenance_is_refused(tmp_path: Path, field: str):
    res = rl.import_wagers(SPEC, tmp_path, [wager_row(**{field: "x"})], import_batch_id=BATCH)
    assert res.refused == 1 and res.rows[0]["status"] == rl.REFUSED
    assert "provenance" in res.rows[0]["reason"]
    assert not SPEC.wagers_path(tmp_path).exists()


def test_orphan_settlement_is_refused(tmp_path: Path):
    res = rl.import_settlements(SPEC, tmp_path, [settlement_row()])
    assert res.refused == 1 and res.rows[0]["status"] == rl.REFUSED
    assert "ORPHAN" in res.rows[0]["reason"]
    assert not SPEC.settlements_path(tmp_path).exists()


def test_settlement_new_duplicate_conflict(tmp_path: Path):
    rl.import_wagers(SPEC, tmp_path, [wager_row()], import_batch_id=BATCH)
    first = rl.import_settlements(SPEC, tmp_path, [settlement_row()])
    assert first.written == 1 and first.rows[0]["settlement_id"] == SPEC.mint_settlement_id(KEY)
    path = SPEC.settlements_path(tmp_path)
    before = path.read_bytes()
    again = rl.import_settlements(SPEC, tmp_path, [settlement_row()])
    assert again.duplicate == 1 and path.read_bytes() == before
    conflict = rl.import_settlements(
        SPEC, tmp_path, [settlement_row(result="LOST", gross_return=0.0, net_profit_loss=-4.67)]
    )
    assert conflict.refused == 1 and conflict.rows[0]["status"] == rl.CONFLICT
    assert path.read_bytes() == before
    verdict = rl.validate_ledger(SPEC, tmp_path)
    assert verdict["ok"] and verdict["counts"] == {"wagers": 1, "settlements": 1}


def test_validator_catches_orphan_and_bad_line(tmp_path: Path):
    rl.import_wagers(SPEC, tmp_path, [wager_row()], import_batch_id=BATCH)
    rl.import_settlements(SPEC, tmp_path, [settlement_row()])
    orphan = rl.build_settlement(SPEC, settlement_row(source_bet_key="kalshi:order:ghost"))
    with SPEC.settlements_path(tmp_path).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(orphan, sort_keys=True) + "\n")
        fh.write("not json\n")
    verdict = rl.validate_ledger(SPEC, tmp_path)
    assert not verdict["ok"]
    assert any("ORPHAN" in f for f in verdict["failures"])
    assert any("not JSON" in f for f in verdict["failures"])
    for f in verdict["failures"]:
        assert TICKER not in f and KEY not in f and "ghost" not in f


def _run_script(name: str, argv: list[str]) -> subprocess.CompletedProcess:
    """Run the script exactly as the router does, with this repository's third-party deps BLOCKED:
    the router's runner installs nothing from here, so the scripts must be stdlib-only."""
    bootstrap = (
        "import runpy, sys\n"
        "for m in ('pydantic', 'numpy', 'scipy', 'httpx'):\n"
        "    sys.modules[m] = None\n"
        "sys.argv = [sys.argv[1], *sys.argv[2:]]\n"
        "runpy.run_path(sys.argv[0], run_name='__main__')\n"
    )
    return subprocess.run(
        [sys.executable, "-c", bootstrap, str(SCRIPTS / name), *argv],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO),
        env={"PATH": "/usr/bin:/bin"},
    )


def _assert_private(text: str) -> None:
    for secret in (TICKER, KEY, "0.45", "4.67", "10.0"):
        assert secret not in text, text


def test_scripts_run_with_router_argv_and_stdlib_only(tmp_path: Path):
    base = tmp_path / "accounting-data"
    base.mkdir()
    payload = tmp_path / "SOCCER.json"
    payload.write_text(json.dumps({"importBatchId": BATCH, "rows": [wager_row()]}))
    receipts = tmp_path / "receipts.json"
    argv = ["--payload", str(payload), "--base-dir", str(base), "--receipts-out", str(receipts)]

    p = _run_script("import_routed_wagers.py", argv)
    assert p.returncode == 0, p.stderr
    assert "written:         1" in p.stdout
    _assert_private(p.stdout + p.stderr)
    r = json.loads(receipts.read_text())
    assert r["importBatchId"] == BATCH and r["kind"] == "wagers"
    assert r["rows"][0]["status"] == rl.NEW and r["rows"][0]["wager_id"] == SPEC.mint_wager_id(KEY)
    ledger_bytes = SPEC.wagers_path(base).read_bytes()

    p = _run_script("import_routed_wagers.py", argv)  # idempotency proof: the router runs it twice
    assert p.returncode == 0, p.stderr
    assert "already present: 1" in p.stdout
    assert SPEC.wagers_path(base).read_bytes() == ledger_bytes
    _assert_private(p.stdout + p.stderr)

    spay = tmp_path / "SOCCER-settlements.json"
    spay.write_text(json.dumps({"settlements": [settlement_row()]}))
    sargv = ["--payload", str(spay), "--base-dir", str(base), "--receipts-out", str(receipts)]
    p = _run_script("import_routed_settlements.py", sargv)
    assert p.returncode == 0, p.stderr
    assert "written:         1" in p.stdout
    _assert_private(p.stdout + p.stderr)
    assert json.loads(receipts.read_text())["rows"][0]["settlement_id"] == SPEC.mint_settlement_id(
        KEY
    )

    result = tmp_path / "result.json"
    p = _run_script(
        "validate_routed_ledger.py", ["--base-dir", str(base), "--result-out", str(result)]
    )
    assert p.returncode == 0, p.stderr
    assert "wagers=1 settlements=1 problems=0" in p.stdout
    _assert_private(p.stdout + p.stderr)
    assert json.loads(result.read_text())["passed"] is True

    # a conflicting re-delivery exits 1 (the router's merge gate fails) and reveals nothing
    payload.write_text(
        json.dumps(
            {"importBatchId": BATCH, "rows": [wager_row(contracts=99, stake=99 * 0.45 + 0.17)]}
        )
    )
    p = _run_script("import_routed_wagers.py", argv)
    assert p.returncode == rl.EXIT_REFUSED
    assert "CONFLICT" in p.stdout
    _assert_private(p.stdout + p.stderr)
    assert SPEC.wagers_path(base).read_bytes() == ledger_bytes


def test_scripts_exit_2_on_unreadable_payload(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("[]")
    p = _run_script("import_routed_wagers.py", ["--payload", str(bad), "--base-dir", str(tmp_path)])
    assert p.returncode == rl.EXIT_BAD_INPUT
