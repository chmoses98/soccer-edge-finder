"""The kalshi-bet-router destination contract, proven against synthetic fills.

Every ticker, key, price and stake here is invented. The router's real contract
(`kalshi_router.destinations.DestinationProfile`, main `2322bd7`): one receipt per row,
identity from `source_bet_key` alone, a second identical import changes no byte,
CONFLICT never rewrites, refusals do not block the rest, exit non-zero on any refusal.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from soccer_edge.cli import main
from soccer_edge.router import (
    ROUTER_IMPORT_BATCH_ID,
    SOCCER_WAGER_FIELDS,
    event_ticker_for,
    import_settlements,
    import_wagers,
    mint_position_id,
    mint_settlement_id,
    validate_ledger,
)

KEYS = [f"kalshi:v1:{i:064x}" for i in range(1, 5)]
TICKERS = [
    "KXEPLGAME-26OCT10ARSLEE-ARS",
    "KXEPLTOTAL-26OCT10ARSLEE-3",
    "KXEPLGAME-26OCT10CHEBOU-CHE",
    "KXEPLTOTAL-26OCT10LIVMCI-2",
]


def wager_row(i: int, **over):
    row = {
        "source_bet_key": KEYS[i],
        "import_batch_id": ROUTER_IMPORT_BATCH_ID,
        "entry_method": "IMPORTED_RECEIPT",
        "game_date": "2026-10-10",
        "market_ticker": TICKERS[i],
        "side": "YES" if i % 2 == 0 else "NO",
        "executed_at": "2026-10-09T18:30:00Z",
        "contracts": 20.0,
        "actual_price": 0.53,
        "stake": 10.74,
        "fees_paid": 0.14,
        "fees_are_estimated": False,
        "venue": "kalshi",
    }
    row.update(over)
    return row


def settlement_row(i: int, **over):
    row = {
        "source_bet_key": KEYS[i],
        "market_ticker": TICKERS[i],
        "side": "YES" if i % 2 == 0 else "NO",
        "settlement_status": "SETTLED",
        "settled_at": "2026-10-10T16:05:00Z",
        "result": "WON",
        "gross_return": 20.0,
        "net_profit_loss": 9.26,
        "refusals": [],
        "venue": "kalshi",
        "economics_version": "router-settlement-economics.v2",
    }
    row.update(over)
    return row


def write_payload(path: Path, rows, key="rows"):
    body = {"importBatchId": ROUTER_IMPORT_BATCH_ID, key: rows}
    path.write_text(json.dumps(body, indent=2, sort_keys=True))
    return path


def ledger_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


def receipts(path: Path) -> dict[str, dict]:
    body = json.loads(path.read_text())
    return {r["source_bet_key"]: r for r in body["rows"]}


@pytest.fixture
def world(tmp_path):
    root = tmp_path / "archive" / "positions"
    payload = write_payload(tmp_path / "SOCCER.json", [wager_row(i) for i in range(4)])
    return {"root": root, "payload": payload, "tmp": tmp_path}


# ------------------------------------------------------------------ identity


def test_identity_is_a_function_of_the_source_key_only():
    assert mint_position_id("k") == "pos_" + hashlib.sha256(b"k").hexdigest()[:24]
    assert mint_position_id("k") == mint_position_id("k")
    assert mint_settlement_id("k") == "stl_" + hashlib.sha256(b"k").hexdigest()[:24]
    assert event_ticker_for("KXEPLGAME-26OCT10ARSLEE-ARS") == "KXEPLGAME-26OCT10ARSLEE"
    assert event_ticker_for("KXEPLGOAL-26AUG22ARSCOV-ARSMZUBIM36-1") == "KXEPLGOAL-26AUG22ARSCOV"
    assert event_ticker_for("nonsense") == "nonsense"


def test_vocabulary_is_explicit_and_snake_case():
    assert {
        "source_bet_key",
        "market_ticker",
        "actual_price",
        "execution_price",
    } <= SOCCER_WAGER_FIELDS
    assert all(f == f.lower() for f in SOCCER_WAGER_FIELDS)
    assert not any(f.startswith(("model_", "fair_", "edge_")) for f in SOCCER_WAGER_FIELDS)


# --------------------------------------------------------------- wager import


def test_new_then_duplicate_noop_with_byte_identical_ledger(world):
    first = import_wagers(world["payload"], world["root"], world["tmp"] / "r1.json")
    assert first.exit_code == 0
    assert first.counts == {"NEW": 4, "DUPLICATE_NOOP": 0, "CONFLICT": 0, "REFUSED": 0}
    files = ledger_bytes(world["root"])
    assert list(files) == ["wagers/2026.jsonl"]
    rows = [json.loads(line) for line in files["wagers/2026.jsonl"].decode().splitlines()]
    assert len(rows) == 4
    assert rows[0]["schema"] == "soccer_routed_wager.v1"
    pos = rows[0]["position"]
    assert pos["position_id"] == mint_position_id(KEYS[0])
    assert pos["source"] == "kalshi-router" and pos["sport"] == "soccer"
    assert pos["event_id"] == "KXEPLGAME-26OCT10ARSLEE"
    assert pos["side"] == "yes" and pos["average_price"] == "0.53" and pos["contracts"] == "20.0"
    assert rows[0]["imported"]["stake"] == "10.74"
    assert Decimal(rows[0]["imported"]["fees_paid"]) == Decimal("0.14")

    second = import_wagers(world["payload"], world["root"], world["tmp"] / "r2.json")
    assert second.exit_code == 0
    assert second.counts["DUPLICATE_NOOP"] == 4 and second.files_written == 0
    assert ledger_bytes(world["root"]) == files
    for r in receipts(world["tmp"] / "r2.json").values():
        assert r["status"] == "DUPLICATE_NOOP" and r["success"] is True
        assert r["wager_id"] == mint_position_id(r["source_bet_key"])
    assert not list(world["root"].rglob("*.tmp")), "no residue"


def test_conflict_on_changed_price_never_rewrites(world):
    import_wagers(world["payload"], world["root"])
    before = ledger_bytes(world["root"])
    changed = [wager_row(i) for i in range(4)]
    changed[1]["actual_price"] = 0.61
    changed[1]["stake"] = 12.34
    payload = write_payload(world["tmp"] / "changed.json", changed)
    out = import_wagers(payload, world["root"], world["tmp"] / "r.json")
    assert out.exit_code == 1
    assert out.counts == {"NEW": 0, "DUPLICATE_NOOP": 3, "CONFLICT": 1, "REFUSED": 0}
    assert ledger_bytes(world["root"]) == before
    r = receipts(world["tmp"] / "r.json")[KEYS[1]]
    assert r["status"] == "CONFLICT" and r["success"] is False
    assert r["conflicting_fields"] == ["price", "stake"]
    assert "0.61" not in json.dumps(r) and "12.34" not in json.dumps(r)


def test_execution_price_spelling_is_the_same_price(world):
    import_wagers(world["payload"], world["root"])
    rows = [wager_row(i) for i in range(4)]
    for row in rows:
        row["execution_price"] = row.pop("actual_price")
    out = import_wagers(write_payload(world["tmp"] / "p.json", rows), world["root"])
    assert out.counts["DUPLICATE_NOOP"] == 4


def test_refused_rows_do_not_block_the_others_and_exit_non_zero(world):
    rows = [
        wager_row(0, a_field_this_ledger_does_not_model=True),
        wager_row(1, model_fair_probability=0.61),
        wager_row(2, side="yes"),
        {k: v for k, v in wager_row(3).items() if k != "source_bet_key"},
    ]
    out = import_wagers(
        write_payload(world["tmp"] / "bad.json", rows), world["root"], world["tmp"] / "r.json"
    )
    assert out.exit_code == 1
    assert out.counts["REFUSED"] == 4 and out.counts["NEW"] == 0
    body = json.loads((world["tmp"] / "r.json").read_text())
    reasons = {r["source_bet_key"]: r["reason"] for r in body["rows"]}
    assert reasons[KEYS[0]] == "unknown_field:a_field_this_ledger_does_not_model"
    assert reasons[KEYS[1]] == "model_provenance_field:model_fair_probability"
    assert reasons[KEYS[2]] == "invalid_value:side"
    assert reasons[None] == "missing_field:source_bet_key"
    assert body["rows"][3]["wager_id"] is None

    # ...and the good rows in a mixed batch still land.
    mixed = [
        wager_row(0),
        wager_row(1, recommendation_id="rec_1"),
        wager_row(2),
        wager_row(3, actual_price=1.5),
    ]
    out = import_wagers(
        write_payload(world["tmp"] / "mixed.json", mixed), world["root"], world["tmp"] / "r2.json"
    )
    assert out.exit_code == 1
    assert out.counts == {"NEW": 2, "DUPLICATE_NOOP": 0, "CONFLICT": 0, "REFUSED": 2}
    assert len(ledger_bytes(world["root"])["wagers/2026.jsonl"].splitlines()) == 2
    assert (
        receipts(world["tmp"] / "r2.json")[KEYS[1]]["reason"]
        == "model_provenance_field:recommendation_id"
    )
    assert receipts(world["tmp"] / "r2.json")[KEYS[3]]["reason"] == "invalid_value:actual_price"


def test_row_batch_must_agree_with_envelope_and_exactly_one_price(world):
    rows = [wager_row(0, import_batch_id="somebody-else"), wager_row(1, execution_price=0.53)]
    out = import_wagers(
        write_payload(world["tmp"] / "b.json", rows), world["root"], world["tmp"] / "r.json"
    )
    assert out.counts["REFUSED"] == 2
    got = receipts(world["tmp"] / "r.json")
    assert got[KEYS[0]]["reason"] == "import_batch_id:disagrees_with_envelope"
    assert got[KEYS[1]]["reason"].startswith("price_field:exactly_one_of")


def test_unreadable_payload_exits_2_with_empty_receipts(world):
    bad = world["tmp"] / "bad.json"
    bad.write_text("{not json")
    out = import_wagers(bad, world["root"], world["tmp"] / "r.json")
    assert out.exit_code == 2 and out.receipts == []
    assert json.loads((world["tmp"] / "r.json").read_text())["rows"] == []
    assert not world["root"].exists()


def test_wagers_shard_by_game_date_year(world):
    rows = [wager_row(0), wager_row(1, game_date="2027-01-02")]
    out = import_wagers(write_payload(world["tmp"] / "y.json", rows), world["root"])
    assert out.files_written == 2
    assert sorted(ledger_bytes(world["root"])) == ["wagers/2026.jsonl", "wagers/2027.jsonl"]


# ---------------------------------------------------------- settlement import


def test_settlements_orphan_refused_void_accepted_duplicate_noop_conflict(world):
    import_wagers(world["payload"], world["root"])
    rows = [
        settlement_row(0),
        settlement_row(1, result="LOST", gross_return=0.0, net_profit_loss=-10.74),
        settlement_row(
            2, result=None, gross_return=None, net_profit_loss=None, refusals=["VOID_MARKET"]
        ),
        settlement_row(3, source_bet_key="kalshi:v1:" + "f" * 64),
    ]
    payload = write_payload(world["tmp"] / "S.json", rows, key="settlements")
    out = import_settlements(payload, world["root"], world["tmp"] / "s1.json")
    assert out.exit_code == 1
    assert out.counts == {"NEW": 3, "DUPLICATE_NOOP": 0, "CONFLICT": 0, "REFUSED": 1}
    got = receipts(world["tmp"] / "s1.json")
    assert got["kalshi:v1:" + "f" * 64]["reason"] == "orphan:source_bet_key"
    assert got[KEYS[0]]["settlement_id"] == mint_settlement_id(KEYS[0])

    files = ledger_bytes(world["root"])
    recs = [json.loads(line) for line in files["settlements/2026.jsonl"].decode().splitlines()]
    by_key = {r["source_bet_key"]: r["settlement"] for r in recs}
    assert by_key[KEYS[0]]["outcome"] == "yes" and by_key[KEYS[0]]["realised_pnl"] == "9.26"
    assert by_key[KEYS[1]]["outcome"] == "yes"  # NO side lost -> market resolved yes
    assert by_key[KEYS[2]]["outcome"] == "void" and by_key[KEYS[2]]["realised_pnl"] is None
    assert by_key[KEYS[2]]["refusal_reason"] == "VOID_MARKET"
    assert by_key[KEYS[0]]["position_id"] == mint_position_id(KEYS[0])
    assert by_key[KEYS[0]]["event_id"] == "KXEPLGAME-26OCT10ARSLEE"

    again = import_settlements(payload, world["root"], world["tmp"] / "s2.json")
    assert again.counts == {"NEW": 0, "DUPLICATE_NOOP": 3, "CONFLICT": 0, "REFUSED": 1}
    assert ledger_bytes(world["root"]) == files

    rows[0]["net_profit_loss"] = 9.4
    conflicting = write_payload(world["tmp"] / "S2.json", rows[:1], key="settlements")
    out = import_settlements(conflicting, world["root"], world["tmp"] / "s3.json")
    assert out.counts["CONFLICT"] == 1 and out.exit_code == 1
    assert receipts(world["tmp"] / "s3.json")[KEYS[0]]["conflicting_fields"] == ["net_profit_loss"]
    assert ledger_bytes(world["root"]) == files


def test_settlement_disagreeing_with_its_position_is_refused(world):
    import_wagers(world["payload"], world["root"])
    rows = [settlement_row(0, side="NO"), settlement_row(1, market_ticker=TICKERS[0])]
    out = import_settlements(
        write_payload(world["tmp"] / "S.json", rows, key="settlements"),
        world["root"],
        world["tmp"] / "s.json",
    )
    got = receipts(world["tmp"] / "s.json")
    assert got[KEYS[0]]["reason"] == "position_disagrees:side"
    assert got[KEYS[1]]["reason"] == "position_disagrees:market_ticker"
    assert out.counts["REFUSED"] == 2 and not world["root"].joinpath("settlements").exists()


# -------------------------------------------------------------------- validator


def test_validator_passes_good_ledger_and_fails_tampered_id(world):
    import_wagers(world["payload"], world["root"])
    import_settlements(
        write_payload(world["tmp"] / "S.json", [settlement_row(0)], key="settlements"),
        world["root"],
    )
    ok = validate_ledger(world["root"])
    assert ok.passed and ok.exit_code == 0
    assert (ok.wager_rows, ok.settlement_rows, ok.files) == (4, 1, 2)

    ledger = world["root"] / "wagers" / "2026.jsonl"
    lines = ledger.read_text().splitlines()
    tampered = json.loads(lines[0])
    tampered["position"]["position_id"] = "pos_" + "0" * 24
    lines[0] = json.dumps(tampered, sort_keys=True)
    ledger.write_text("\n".join(lines) + "\n")
    bad = validate_ledger(world["root"])
    assert not bad.passed and bad.exit_code == 1
    assert bad.violations == {"position_id_not_minted_from_key": 1, "settlement_orphan": 1}


def test_validator_flags_stray_files_bad_json_and_contract_violations(world):
    import_wagers(world["payload"], world["root"])
    (world["root"] / "notes.txt").write_text("x")
    (world["root"] / "wagers" / "2026.jsonl.bak").write_text("x")
    ledger = world["root"] / "wagers" / "2026.jsonl"
    lines = ledger.read_text().splitlines()
    broken = json.loads(lines[1])
    broken["position"]["sport"] = "nfl"  # valid contract value, wrong provenance
    lines[1] = json.dumps(broken, sort_keys=True)
    invalid = json.loads(lines[2])
    invalid["position"]["side"] = "maybe"  # fails the pydantic contract
    lines[2] = json.dumps(invalid, sort_keys=True)
    lines.append(lines[0])  # a duplicate line
    ledger.write_text("\n".join(lines) + "\n")
    (world["root"] / "settlements").mkdir()
    (world["root"] / "settlements" / "2026.jsonl").write_text("{not json\n")
    res = validate_ledger(world["root"])
    assert res.violations == {
        "unexpected_file": 2,
        "position_provenance": 1,
        "position_contract": 1,
        "duplicate_position": 1,
        "settlement_file_unparseable": 1,
    }


# ------------------------------------------------------------ CLI and privacy


SECRETS = (
    "KXEPL",
    "ARSLEE",
    "0.53",
    "10.74",
    "0.14",
    "9.26",
    "kalshi:v1",
    "pos_",
    "stl_",
    "IMPORTED_RECEIPT",
    "2026-10-10",
    "2026-10-09",
)


def test_cli_full_import_prints_counts_and_field_names_only(world, capsys):
    argv = lambda *a: [str(x) for x in a]
    root, tmp = world["root"], world["tmp"]
    rows = [
        wager_row(0),
        wager_row(1, actual_price=0.61),
        wager_row(2, model_version="x"),
        wager_row(3),
    ]
    assert (
        main(
            argv(
                "import-wagers",
                world["payload"],
                "--ledger-root",
                root,
                "--receipts-out",
                tmp / "r1.json",
                "--season",
                "2026",
            )
        )
        == 0
    )
    assert (
        main(
            argv(
                "import-wagers",
                write_payload(tmp / "p2.json", rows),
                "--ledger-root",
                root,
                "--receipts-out",
                tmp / "r2.json",
            )
        )
        == 1
    )
    srows = [
        settlement_row(0),
        settlement_row(1, source_bet_key="kalshi:v1:" + "e" * 64),
        settlement_row(2, result=None, gross_return=None, net_profit_loss=None),
    ]
    assert (
        main(
            argv(
                "import-settlements",
                write_payload(tmp / "S.json", srows, key="settlements"),
                "--ledger-root",
                root,
                "--receipts-out",
                tmp / "s.json",
            )
        )
        == 1
    )
    assert (
        main(
            argv("validate-positions-ledger", "--ledger-root", root, "--result-out", tmp / "v.json")
        )
        == 0
    )
    out = capsys.readouterr()
    combined = out.out + out.err
    for secret in SECRETS:
        assert secret not in combined, f"stdout leaked {secret!r}"
    assert "CONFLICT=1" in combined and "REFUSED=1" in combined
    assert "conflicting fields (names only): price" in combined
    assert "model_provenance_field:model_version" in combined
    assert "orphan:source_bet_key" in combined
    assert (
        "validate-positions-ledger: files=2 wager_rows=4 settlement_rows=2 violations=0 passed=true"
        in combined
    )
    assert json.loads((tmp / "v.json").read_text())["passed"] is True
    assert json.loads((tmp / "r1.json").read_text())["written"] == 4


# ------------------------------------------------ the router's argv, as a subprocess


def test_shim_argv_template_from_the_ledger_checkout_is_idempotent_by_write_tree(world, tmp_path):
    """The exact `PROFILES[Sport.SOCCER]` templates from docs/ROUTER_INTEGRATION.md, run the way
    `deliver-wagers.yml` runs them: cwd is the LEDGER checkout, code is elsewhere, and the
    idempotency proof is `git write-tree` unchanged after a second identical import."""
    import shutil
    import subprocess
    import sys

    if shutil.which("git") is None:  # pragma: no cover
        pytest.skip("git is required")
    code = Path(__file__).resolve().parents[1]
    work = tmp_path / "work"
    work.mkdir()
    git = lambda *a: subprocess.run(
        ["git", *a], cwd=work, check=True, capture_output=True, text=True
    ).stdout.strip()
    git("init", "--quiet")
    shim = code / "scripts" / "kalshi_router_import.py"

    def run(*argv):
        return subprocess.run(
            [sys.executable, str(shim), *argv],
            cwd=work,
            capture_output=True,
            text=True,
            check=False,
        )

    common = ["--ledger-root", str(work / "archive" / "positions")]
    first = run(
        "import-wagers", str(world["payload"]), *common, "--receipts-out", str(tmp_path / "r1.json")
    )
    assert first.returncode == 0, first.stdout + first.stderr
    git("add", "-A")
    tree_before = git("write-tree")
    second = run(
        "import-wagers", str(world["payload"]), *common, "--receipts-out", str(tmp_path / "r2.json")
    )
    assert second.returncode == 0, second.stdout + second.stderr
    git("add", "-A")
    assert git("write-tree") == tree_before
    assert receipts(tmp_path / "r2.json")[KEYS[0]]["status"] == "DUPLICATE_NOOP"
    assert git("status", "--porcelain", "--untracked-files=all").splitlines() == [
        "A  archive/positions/wagers/2026.jsonl"
    ], "the importer writes only under archive/positions/"

    validated = run("validate-positions-ledger", *common, "--result-out", str(tmp_path / "v.json"))
    assert validated.returncode == 0, validated.stdout + validated.stderr
    for secret in SECRETS:
        assert secret not in first.stdout + second.stdout + validated.stdout
