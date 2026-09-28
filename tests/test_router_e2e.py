"""Router compatibility (remediation phase 25): a synthetic end-to-end path from a RUN SOCCER output
(app contract 1.2, new fields) through the router importer and settlement importer, with the new
settlement schema alongside. No live routing exists; this only proves the contracts still fit."""

from __future__ import annotations

import json
from datetime import date

import pytest

from soccer_edge.archive.ledger import PredictionLedger
from soccer_edge.cli import main
from soccer_edge.kalshi.client import KalshiPublicClient
from soccer_edge.kalshi.discovery import discover
from soccer_edge.kalshi.fake import FakeKalshi
from soccer_edge.run.pipeline import RunConfig, run
from tests.test_run_pipeline import _inputs

ROUTER_BATCH = "batch-2026-10-09T18:00:00Z"


@pytest.fixture
def run_output(registry, epl_fixtures, tmp_path):
    # a mispriced synthetic book so that shadow recommendations exist (still withheld: no_bets stays True)
    fake = FakeKalshi(
        epl_fixtures,
        registry,
        fair=lambda f: {"home": 0.2, "draw": 0.2, "away": 0.6, "mean_total": 1.0},
    )
    disc = discover(KalshiPublicClient(transport=fake.transport, max_retries=0))
    inp = _inputs(registry, epl_fixtures, disc)
    art = run(
        inp,
        RunConfig(run_date=date(2026, 10, 10), n_worlds=60, draws_per_world=20),
        ledger=PredictionLedger(tmp_path / "ledger"),
    )
    return art.output


def test_run_output_carries_the_new_fields_and_router_import_round_trips(run_output, tmp_path):
    out = run_output.model_dump(mode="json")
    assert out["schema_version"] == "1.2.0"
    recs = out["shadow_recommendations"] or out["recommendations"]
    assert recs, "the synthetic surface should produce shadow recommendations"
    r0 = recs[0]
    for k in (
        "model_posterior_edge_share",
        "selection_policy",
        "edge_v2_status",
        "prediction_record_id",
    ):
        assert k in r0
    assert r0["selection_policy"] == "selection_v2" and out["no_bets"] is True
    # build a router wager payload from the shadow recommendation exactly as the router would ship it
    rows = []
    for i, r in enumerate(recs[:3]):
        rows.append(
            {
                "source_bet_key": f"kalshi:v1:{i + 1:064x}",
                "import_batch_id": ROUTER_BATCH,
                "entry_method": "IMPORTED_RECEIPT",
                "game_date": r["start_time"][:10],
                "market_ticker": r["market_ticker"],
                "side": r["side"].upper(),
                "executed_at": "2026-10-09T18:30:00Z",
                "contracts": 5.0,
                "actual_price": float(r["current_price"]),
                "stake": round(5.0 * float(r["current_price"]), 2),
                "fees_paid": 0.05,
                "fees_are_estimated": False,
                "venue": "kalshi",
                "prediction_record_id": r["prediction_record_id"],
            }
        )
    # the router must never claim MODEL PROVENANCE: a row carrying prediction_record_id is refused as a
    # whole (the prediction record is joined later by ticker/side/time in evaluation, never by the router)
    payload = tmp_path / "SOCCER_provenance.json"
    payload.write_text(json.dumps({"importBatchId": ROUTER_BATCH, "rows": rows}))
    root = tmp_path / "positions"
    receipts = tmp_path / "receipts_refused.json"
    main(
        ["import-wagers", str(payload), "--ledger-root", str(root), "--receipts-out", str(receipts)]
    )
    rec = json.loads(receipts.read_text())["rows"]
    assert {x["status"] for x in rec} == {"REFUSED"}
    assert all("prediction_record_id" in (x.get("reason") or "") for x in rec)
    for r in rows:
        r.pop("prediction_record_id")
    payload = tmp_path / "SOCCER.json"
    payload.write_text(json.dumps({"importBatchId": ROUTER_BATCH, "rows": rows}))
    receipts = tmp_path / "receipts.json"
    code = main(
        ["import-wagers", str(payload), "--ledger-root", str(root), "--receipts-out", str(receipts)]
    )
    assert code == 0
    rec = json.loads(receipts.read_text())["rows"]
    assert len(rec) == len(rows) and all(x["status"] in ("NEW", "DUPLICATE_NOOP") for x in rec)
    # settlements for those positions (router settlement rows; independent of our settlement records)
    srows = [
        {
            "source_bet_key": w["source_bet_key"],
            "market_ticker": w["market_ticker"],
            "side": w["side"],
            "settlement_status": "SETTLED",
            "settled_at": "2026-10-10T16:05:00Z",
            "result": "WON",
            "gross_return": 5.0,
            "net_profit_loss": 2.0,
            "refusals": [],
            "venue": "kalshi",
            "economics_version": "router-settlement-economics.v2",
        }
        for w in rows
    ]
    spayload = tmp_path / "SETTLE.json"
    spayload.write_text(json.dumps({"importBatchId": ROUTER_BATCH, "settlements": srows}))
    sreceipts = tmp_path / "sreceipts.json"
    assert (
        main(
            [
                "import-settlements",
                str(spayload),
                "--ledger-root",
                str(root),
                "--receipts-out",
                str(sreceipts),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "validate-positions-ledger",
                "--ledger-root",
                str(root),
                "--result-out",
                str(tmp_path / "v.json"),
            ]
        )
        == 0
    )
