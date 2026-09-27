"""`soccer` command line. RUN SOCCER == `soccer run --date YYYY-MM-DD`."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from soccer_edge.core.serialization import write_json
from soccer_edge.core.time import utc_now

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "data"


def _registry():
    from soccer_edge.identity.registry import AliasRegistry

    return AliasRegistry.from_directory(DATA / "registry")


def cmd_export_schemas(args: argparse.Namespace) -> int:
    from soccer_edge.contracts import export_json_schemas

    paths = export_json_schemas(Path(args.out))
    for p in paths:
        print(p)
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    from soccer_edge.kalshi.client import KalshiPublicClient
    from soccer_edge.kalshi.discovery import discover

    client = KalshiPublicClient()
    run = discover(client, statuses=tuple(args.status))
    out = Path(args.out)
    write_json(out, run.to_json())
    c = run.counters()
    print(json.dumps({k: v for k, v in c.items() if k not in ("failures",)}, indent=2, default=str))
    if c["failures"]:
        print("FAILURES:", *c["failures"][:20], sep="\n  ", file=sys.stderr)
    print(f"wrote {out}")
    return 0 if run.complete else 2


def cmd_capture(args: argparse.Namespace) -> int:
    """Discovery + snapshot batch (change-suppressed) written as JSONL."""
    from soccer_edge.core.serialization import append_jsonl, read_json
    from soccer_edge.kalshi.capture import MarketSnapshot, SnapshotBatch
    from soccer_edge.kalshi.client import KalshiPublicClient
    from soccer_edge.kalshi.discovery import discover
    from soccer_edge.kalshi.fees import FEE_SCHEDULE_VERSION

    client = KalshiPublicClient()
    sweep_series = known_series = None
    if args.fast:
        idx_path = REPO_ROOT / "data" / "catalog" / "latest_index.json"
        if idx_path.exists() and "series_with_markets" in read_json(idx_path):
            idx = read_json(idx_path)
            known_series = {x["ticker"] for x in idx.get("series", [])}
            sweep_series = set(idx.get("series_with_markets", []))
            print(
                f"[capture] fast mode: {len(sweep_series)} series with markets at last full discovery; new series are always swept"
            )
        else:
            print(
                "[capture] --fast requested but no usable committed index; running exhaustive discovery"
            )
    run = discover(
        client,
        statuses=tuple(args.status),
        fetch_events=True,
        sweep_series=sweep_series,
        known_series=known_series,
    )
    now = utc_now()
    snaps = []
    prev_path = Path(args.out_dir) / "last_fingerprints.json"
    prev = read_json(prev_path) if prev_path.exists() else {}
    new_fp = {}
    for tk, m in run.markets.items():
        srec = run.series_records.get(m.series_ticker or "")
        mins = None
        if m.close_time:
            mins = (m.close_time - now).total_seconds() / 60
        s = MarketSnapshot.from_market(
            m, srec.series if srec else None, now, minutes_to_kickoff=mins
        )
        fp = s.quote_fingerprint()
        new_fp[tk] = fp
        if prev.get(tk) == fp and not args.no_suppress:
            continue
        snaps.append(s)
    batch = SnapshotBatch(
        batch_id=f"cap-{now:%Y%m%dT%H%M%SZ}",
        discovery_run_id=run.run_id,
        discovery_complete=run.complete,
        captured_at=now,
        snapshots=tuple(snaps),
        fee_schedule_version=FEE_SCHEDULE_VERSION,
    )
    out_dir = Path(args.out_dir) / f"{now:%Y-%m-%d}"
    path = out_dir / f"{batch.batch_id}.jsonl"
    for rec in batch.to_records():
        append_jsonl(path, rec)
    write_json(Path(args.out_dir) / "last_fingerprints.json", new_fp)
    write_json(Path(args.out_dir) / "latest_catalog.json", run.to_json())
    write_json(
        Path(args.out_dir) / "STATUS.json",
        {
            "batch_id": batch.batch_id,
            "captured_at": now.isoformat(),
            "discovery_complete": run.complete,
            "contracts_discovered": len(run.markets),
            "snapshots_written": len(snaps),
            "counters": run.counters(),
        },
    )
    print(
        json.dumps(
            {
                "batch": batch.batch_id,
                "complete": run.complete,
                "discovered": len(run.markets),
                "written": len(snaps),
                "path": str(path),
            },
            indent=2,
        )
    )
    return 0 if run.complete else 2


def cmd_run(args: argparse.Namespace) -> int:
    from soccer_edge.archive.ledger import PredictionLedger
    from soccer_edge.kalshi.client import KalshiPublicClient
    from soccer_edge.kalshi.discovery import discover
    from soccer_edge.pricing.edge import EdgeConfig
    from soccer_edge.run.inputs import DEFAULT_COMPETITIONS, assemble, build_inputs
    from soccer_edge.run.pipeline import RunConfig, run, write_outputs
    from soccer_edge.run.simcache import SimCache

    run_date = date.fromisoformat(args.date) if args.date else utc_now().date()
    as_of = utc_now()
    registry = _registry()
    comps = tuple(args.league) if args.league else DEFAULT_COMPETITIONS
    data = assemble(registry, competitions=comps, today=run_date)
    for n in data.notes:
        print("[data]", n)
    if args.catalog:
        from soccer_edge.kalshi.discovery import DiscoveryRun  # noqa: F401

        raise SystemExit(
            "replaying a saved catalog is only supported through the Python API (see docs/RUN_SOCCER.md)"
        )
    if args.synthetic_kalshi:
        from soccer_edge.kalshi.fake import FakeKalshi

        fx_in_window = [
            f
            for f in data.fixtures
            if f.kickoff_utc
            and 0 < (f.kickoff_utc - as_of).total_seconds() < args.window_hours * 3600
        ]
        fake = FakeKalshi(fx_in_window, registry)
        client = KalshiPublicClient(transport=fake.transport)
        print(f"[kalshi] SYNTHETIC surface for {len(fx_in_window)} fixtures (not real markets)")
    else:
        client = KalshiPublicClient()
    disc = discover(client)
    print(
        "[kalshi]",
        json.dumps({k: v for k, v in disc.counters().items() if k != "failures"}, default=str),
    )
    inputs = build_inputs(
        registry, data, disc, as_of=as_of, authority_path=REPO_ROOT / "config" / "authority.json"
    )
    cfg = RunConfig(
        run_date=run_date,
        window_hours=args.window_hours,
        leagues=tuple(args.league or ()),
        games=tuple(args.game or ()),
        confirmed_lineups_only=args.confirmed_lineups_only,
        n_worlds=args.worlds,
        draws_per_world=args.draws,
        edge=EdgeConfig(),
        enforce_freshness=not args.no_freshness_gate,
    )
    ledger = PredictionLedger(Path(args.archive_dir)) if args.archive_dir else None
    cache = SimCache(Path(args.sim_cache)) if args.sim_cache else None
    art = run(inputs, cfg, ledger=ledger, sim_cache=cache)
    paths = write_outputs(art, Path(args.out_dir))
    print(art.markdown)
    print(
        json.dumps(
            {
                "outputs": {k: str(v) for k, v in paths.items()},
                "simulated": art.fixtures_simulated,
                "repriced": art.fixtures_repriced,
                "archived_records": len(art.prediction_record_ids),
            },
            indent=2,
        )
    )
    if args.fail_on_incomplete and not disc.complete:
        return 2
    return 0


def cmd_settle(args: argparse.Namespace) -> int:
    from soccer_edge.archive.ledger import PredictionLedger
    from soccer_edge.authority.policy import AuthorityMatrix
    from soccer_edge.providers.openfootball import COMPETITION_FILES, OpenFootballProvider
    from soccer_edge.run.inputs import current_season_id
    from soccer_edge.run.settle import model_health, settle_ledger, settlement_v1_rows

    as_of = utc_now()
    registry = _registry()
    ledger = PredictionLedger(Path(args.archive_dir))
    settlements = PredictionLedger(Path(args.settlements_dir))
    of = OpenFootballProvider(registry)
    results = {}
    comps = {
        r.get("competition_id")
        for r in ledger.iter_records()
        if r.get("schema") == "prediction_record_v1"
    }
    for comp in sorted(c for c in comps if c in COMPETITION_FILES):
        try:
            for r in of.results(comp, current_season_id(comp, as_of.date())).payload:
                results[r.fixture_id] = r
        except Exception as exc:
            print(f"[results] {comp}: {exc}")
    written = settle_ledger(ledger, results, Path(args.snapshots_dir), settlements, as_of=as_of)
    rows, proposals = model_health(
        settlements, AuthorityMatrix.load(REPO_ROOT / "config" / "authority.json"), as_of=as_of
    )
    out = Path(args.out_dir)
    write_json(out / "model_health.v1.json", [r.model_dump(mode="json") for r in rows])
    write_json(out / "authority_proposals.json", proposals)
    write_json(
        out / "settlements_written.v1.json",
        [s.model_dump(mode="json") for s in settlement_v1_rows(written)],
    )
    lines = [
        f"# settle-evaluate {as_of:%Y-%m-%d %H:%M}Z",
        "",
        f"- newly settled: {len(written)}",
        f"- cells evaluated: {len(rows)}",
        f"- authority proposals: {len(proposals['proposals'])}",
        "",
        "| model | family | horizon | n | log loss | market LL | ECE | 80% cov | CLV | authority |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.model_family} | {r.market_family} | {r.horizon} | {r.n_settled} | {r.log_loss} | {r.market_log_loss} | {r.ece} | {r.interval_coverage_80} | {r.clv_points_mean} | {r.authority} |"
        )
    (out / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="soccer", description="soccer-edge-finder operator CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser(
        "run", help="RUN SOCCER: discover, simulate, price, recommend, prove coverage"
    )
    r.add_argument("--date", help="run date YYYY-MM-DD (default today UTC)")
    r.add_argument("--league", action="append", help="canonical competition id filter (repeatable)")
    r.add_argument(
        "--game", action="append", help="fixture id or 'home-away' substring filter (repeatable)"
    )
    r.add_argument(
        "--window", dest="window_hours", type=int, default=48, help="hours ahead to include"
    )
    r.add_argument("--confirmed-lineups-only", action="store_true")
    r.add_argument("--worlds", type=int, default=1000)
    r.add_argument("--draws", type=int, default=100)
    r.add_argument("--out-dir", default=str(DATA / "runs" / "latest"))
    r.add_argument("--archive-dir", default=None, help="prediction ledger root (append-only)")
    r.add_argument("--sim-cache", default=None)
    r.add_argument("--catalog", default=None, help="(python API only) replay a saved catalog")
    r.add_argument(
        "--synthetic-kalshi",
        action="store_true",
        help="use a SYNTHETIC Kalshi surface (offline demo)",
    )
    r.add_argument(
        "--no-freshness-gate", action="store_true", help="report violations instead of failing"
    )
    r.add_argument("--fail-on-incomplete", action="store_true")
    r.set_defaults(func=cmd_run)

    d = sub.add_parser("discover", help="exhaustive Kalshi soccer discovery -> catalog JSON")
    d.add_argument("--out", default=str(DATA / "catalog" / "latest_catalog.json"))
    d.add_argument("--status", action="append", default=None)
    d.set_defaults(func=cmd_discover)

    c = sub.add_parser("capture", help="discover + change-suppressed market snapshots")
    c.add_argument("--out-dir", default=str(DATA / "snapshots"))
    c.add_argument("--status", action="append", default=None)
    c.add_argument("--no-suppress", action="store_true")
    c.add_argument(
        "--fast",
        action="store_true",
        help="sweep only series that had markets in the last committed full discovery, plus new series",
    )
    c.set_defaults(func=cmd_capture)

    st = sub.add_parser("settle", help="settle archived predictions + evaluate + propose authority")
    st.add_argument("--archive-dir", required=True)
    st.add_argument("--snapshots-dir", required=True)
    st.add_argument("--settlements-dir", required=True)
    st.add_argument("--out-dir", required=True)
    st.set_defaults(func=cmd_settle)

    e = sub.add_parser("export-schemas", help="write JSON Schemas for the app contract")
    e.add_argument("--out", default=str(REPO_ROOT / "docs" / "schemas"))
    e.set_defaults(func=cmd_export_schemas)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "status", None) is None and args.cmd in ("discover", "capture"):
        args.status = ["open", "unopened"]
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
