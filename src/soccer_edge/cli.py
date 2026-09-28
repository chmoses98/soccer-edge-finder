"""`soccer` command line. RUN SOCCER == `soccer run --date YYYY-MM-DD`."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from soccer_edge.core.serialization import read_json, read_json_or, write_json
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
    from soccer_edge.core.serialization import append_jsonl
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
    prev = read_json_or(prev_path, {})
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


def _reference_capture(registry, fixtures, as_of, out_dir: Path | None):
    """Fetch football-data.co.uk upcoming odds, build snapshots, optionally append them (change-suppressed)."""
    from soccer_edge.core.serialization import append_jsonl, read_json_or
    from soccer_edge.providers.football_data_couk import FootballDataCoUkProvider
    from soccer_edge.reference.capture import build_snapshots, reference_lookup

    try:
        obs = FootballDataCoUkProvider(registry=registry).upcoming_odds()
    except Exception as exc:
        print(f"[reference] football-data.co.uk unavailable: {str(exc)[:120]}")
        return {}, None, {"error": str(exc)[:200]}
    snaps, stats = build_snapshots(obs.payload, fixtures, captured_at=as_of)
    stats["provider_notes"] = list(obs.notes)
    if out_dir is not None:
        fp_path = out_dir / "last_fingerprints.json"
        prev = read_json_or(fp_path, {})
        new_fp = {}
        batch = f"ref-{as_of:%Y%m%dT%H%M%SZ}"
        written = 0
        path = out_dir / f"{as_of:%Y-%m-%d}" / f"{batch}.jsonl"
        for sn in snaps:
            key = f"{sn.bookmaker}|{sn.fixture_id}|{sn.market}|{sn.selection}|{sn.line}"
            fp = sn.fingerprint()
            new_fp[key] = fp
            if prev.get(key) == fp:
                continue
            append_jsonl(path, sn.to_record(batch))
            written += 1
        write_json(fp_path, new_fp)
        write_json(
            out_dir / "STATUS.json",
            {
                "batch_id": batch,
                "captured_at": as_of.isoformat(),
                "snapshots": len(snaps),
                "written": written,
                **stats,
            },
        )
        stats["written"] = written
    return reference_lookup(snaps), obs.provenance.observed_at, stats


def cmd_capture_reference(args: argparse.Namespace) -> int:
    from soccer_edge.run.inputs import DEFAULT_COMPETITIONS, assemble

    as_of = utc_now()
    registry = _registry()
    data = assemble(registry, competitions=DEFAULT_COMPETITIONS, today=as_of.date())
    lookup, observed, stats = _reference_capture(registry, data.fixtures, as_of, Path(args.out_dir))
    print(
        json.dumps(
            {"reference_probabilities": len(lookup), "observed_at": str(observed), **stats},
            indent=2,
            default=str,
        )
    )
    return 0 if lookup else 2


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
    data = assemble(
        registry,
        competitions=comps,
        today=run_date,
        espn_dir=Path(args.espn_dir) if args.espn_dir else None,
    )
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
    written = settle_ledger(
        ledger,
        results,
        Path(args.snapshots_dir),
        settlements,
        as_of=as_of,
        reference_dir=Path(args.reference_dir) if args.reference_dir else None,
    )
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


def cmd_import_wagers(args: argparse.Namespace) -> int:
    """kalshi-bet-router wager importer: counts and field names on stdout, values only in files."""
    from soccer_edge.router import import_wagers

    outcome = import_wagers(
        Path(args.payload),
        Path(args.ledger_root),
        Path(args.receipts_out) if args.receipts_out else None,
    )
    print("\n".join(outcome.summary_lines()))
    return outcome.exit_code


def cmd_import_settlements(args: argparse.Namespace) -> int:
    from soccer_edge.router import import_settlements

    outcome = import_settlements(
        Path(args.payload),
        Path(args.ledger_root),
        Path(args.receipts_out) if args.receipts_out else None,
    )
    print("\n".join(outcome.summary_lines()))
    return outcome.exit_code


def cmd_validate_positions_ledger(args: argparse.Namespace) -> int:
    from soccer_edge.router import validate_ledger

    result = validate_ledger(Path(args.ledger_root))
    if args.result_out:
        write_json(Path(args.result_out), result.as_dict())
    print("\n".join(result.summary_lines()))
    return result.exit_code


def cmd_microstructure(args: argparse.Namespace) -> int:
    """Phase 18 (research only): summarise archived snapshot microstructure -> JSON."""
    from soccer_edge.kalshi.microstructure import build_summary

    since = date.fromisoformat(args.since) if args.since else None
    summary = build_summary(Path(args.snapshots_dir), since=since)
    out = Path(args.out)
    write_json(out, summary)
    print(
        json.dumps(
            {
                "rows": summary["rows"],
                "tickers": summary["tickers"],
                "date_range": summary["date_range"],
                "two_sided_share": summary["quote_state"]["two_sided_share"],
                "spread_yes_median": summary["spread_yes"]["median"],
                "mid_edge_erased_share_3c": summary["mid_edge_erased_share_3c"],
                "mid_edge_erased_share_5c": summary["mid_edge_erased_share_5c"],
                "path": str(out),
            },
            indent=2,
        )
    )
    return 0


def cmd_reconcile_discovery(args: argparse.Namespace) -> int:
    """Phase 23: prove a fast capture complete relative to the full discovery (non-zero if not)."""
    from soccer_edge.core.serialization import read_json
    from soccer_edge.kalshi.reconcile import reconcile_fast_vs_full

    report = reconcile_fast_vs_full(read_json(Path(args.fast)), read_json(Path(args.full)))
    out = Path(args.out)
    write_json(out, report)
    print(
        json.dumps(
            {
                "evidence_level": report["evidence_level"],
                "complete_relative_to_full": report["complete_relative_to_full"],
                "violations": [v["kind"] for v in report["violations"]],
                "markets": report["markets"]["full_not_fast_breakdown"],
                "path": str(out),
            },
            indent=2,
        )
    )
    return 0 if report["complete_relative_to_full"] else 1


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

    cr = sub.add_parser(
        "capture-reference",
        help="capture football-data.co.uk reference odds as point-in-time snapshots",
    )
    cr.add_argument("--out-dir", default=str(DATA / "reference"))
    cr.set_defaults(func=cmd_capture_reference)

    es = sub.add_parser(
        "espn-sync", help="ESPN fixtures window + prospective lineup snapshots + map proposals"
    )
    es.add_argument(
        "--leagues",
        default=None,
        help="comma-separated ESPN slugs; default = verified leagues in espn_map.json",
    )
    es.add_argument("--back-days", type=int, default=3)
    es.add_argument("--forward-days", type=int, default=8)
    es.add_argument("--max-lineups", type=int, default=150)
    es.add_argument("--out-dir", required=True)
    es.set_defaults(func=cmd_espn_sync)

    eb = sub.add_parser(
        "espn-backfill",
        help="ESPN per-day scoreboards over a date range -> archived results (runner-side)",
    )
    eb.add_argument("--leagues", required=True, help="comma-separated ESPN slugs")
    eb.add_argument("--start", required=True, help="YYYY-MM-DD")
    eb.add_argument("--end", default=None, help="YYYY-MM-DD (default today)")
    eb.add_argument("--out-dir", required=True)
    eb.set_defaults(func=cmd_espn_backfill)

    rp = sub.add_parser(
        "replay-policies", help="replay versioned selection policies against the archive (research)"
    )
    rp.add_argument("--archive-dir", required=True)
    rp.add_argument("--settlements-dir", required=True)
    rp.add_argument("--out", required=True)
    rp.set_defaults(func=cmd_replay_policies)

    st = sub.add_parser("settle", help="settle archived predictions + evaluate + propose authority")
    st.add_argument("--archive-dir", required=True)
    st.add_argument("--snapshots-dir", required=True)
    st.add_argument("--settlements-dir", required=True)
    st.add_argument("--out-dir", required=True)
    st.add_argument("--reference-dir", default=None)
    st.set_defaults(func=cmd_settle)

    e = sub.add_parser("export-schemas", help="write JSON Schemas for the app contract")
    e.add_argument("--out", default=str(REPO_ROOT / "docs" / "schemas"))
    e.set_defaults(func=cmd_export_schemas)

    # --- kalshi-bet-router destination contract (no live routing is enabled by these) ---
    iw = sub.add_parser(
        "import-wagers",
        help="import a kalshi-bet-router wager payload into the append-only positions ledger",
    )
    iw.add_argument("payload", help="router payload JSON ({importBatchId, rows})")
    iw.add_argument(
        "--ledger-root",
        default=str(REPO_ROOT / "archive" / "positions"),
        help="directory holding wagers/<YYYY>.jsonl and settlements/<YYYY>.jsonl",
    )
    iw.add_argument("--receipts-out", default=None, help="one receipt per row, JSON")
    iw.add_argument(
        "--season", default=None, help="accepted and ignored: the ledger is per calendar year"
    )
    iw.set_defaults(func=cmd_import_wagers)

    ist = sub.add_parser(
        "import-settlements",
        help="import kalshi-bet-router settlement rows for positions already on the ledger",
    )
    ist.add_argument("payload", help="router settlement payload JSON ({settlements})")
    ist.add_argument("--ledger-root", default=str(REPO_ROOT / "archive" / "positions"))
    ist.add_argument("--receipts-out", default=None)
    ist.add_argument("--season", default=None, help="accepted and ignored")
    ist.set_defaults(func=cmd_import_settlements)

    vl = sub.add_parser(
        "validate-positions-ledger",
        help="whole-ledger check of the routed positions ledger (counts only; non-zero on any violation)",
    )
    vl.add_argument("--ledger-root", default=str(REPO_ROOT / "archive" / "positions"))
    vl.add_argument("--result-out", default=None, help="write the counts as JSON")
    vl.set_defaults(func=cmd_validate_positions_ledger)
    ms = sub.add_parser(
        "microstructure", help="(research) summarise archived Kalshi snapshot microstructure"
    )
    ms.add_argument("--snapshots-dir", required=True)
    ms.add_argument("--out", required=True)
    ms.add_argument("--since", default=None, help="only rows captured on/after YYYY-MM-DD")
    ms.set_defaults(func=cmd_microstructure)

    rd = sub.add_parser(
        "reconcile-discovery",
        help="prove a fast capture is complete relative to the full discovery (exit 1 if not)",
    )
    rd.add_argument("--fast", required=True, help="fast run latest_catalog.json (or STATUS.json)")
    rd.add_argument("--full", required=True, help="full latest_catalog.json or latest_index.json")
    rd.add_argument("--out", required=True)
    rd.set_defaults(func=cmd_reconcile_discovery)
    return p


def cmd_espn_sync(args: argparse.Namespace) -> int:
    """Runner-side: ESPN fixtures window + prospective lineup snapshots + identity-map proposals (no guessing)."""
    from datetime import timedelta

    from soccer_edge.core.serialization import write_json
    from soccer_edge.providers.espn import (
        EspnMap,
        EspnProvider,
        MappingReport,
        capture_lineups,
        events_to_fixtures,
        propose_team_map,
    )

    as_of = utc_now()
    emap = EspnMap.load()
    leagues = (
        args.leagues.split(",")
        if args.leagues
        else list(json.loads(Path(emap_path_default()).read_text())["verified_leagues"])
    )
    prov = EspnProvider(emap=emap)
    start = (as_of - timedelta(days=args.back_days)).date()
    events, failures = prov.fixtures_window(leagues, start, args.back_days + args.forward_days)
    rep = MappingReport()
    fixtures = events_to_fixtures(events, emap, rep)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # lineups: events kicking off within [-3h, +26h] of now (pre-kickoff sheets + post-match sheets for history)
    lo, hi = as_of - timedelta(hours=3), as_of + timedelta(hours=26)
    todo = [e for e in events if lo <= e.kickoff_utc <= hi]
    ln_stats = capture_lineups(
        prov, todo, out_dir / "lineups", as_of=as_of, max_events=args.max_lineups
    )
    # weather (context only): Open-Meteo forecast at kickoff hour for events within 72h
    from soccer_edge.providers.open_meteo import OpenMeteoProvider, capture_weather

    try:
        wx = capture_weather(
            OpenMeteoProvider(cache_path=out_dir / "weather" / "geocode_cache.json"),
            events,
            out_dir / "weather",
            as_of=as_of,
        )
    except Exception as exc:
        wx = {"error": str(exc)[:200]}
    # map proposals for unmapped teams (exact alias only; humans extend data/mappings/espn_map.json)
    proposals: dict[str, dict] = {}
    if rep.unmapped_team_ids:
        reg = _registry()
        by_league: dict[str, list[dict[str, str]]] = {}
        for e in events:
            for tid, name, abbr in (
                (e.home_espn_id, e.home_name, e.home_abbr),
                (e.away_espn_id, e.away_name, e.away_abbr),
            ):
                if tid in rep.unmapped_team_ids:
                    by_league.setdefault(e.league, []).append(
                        {
                            "id": tid,
                            "displayName": name,
                            "abbreviation": abbr,
                            "shortDisplayName": "",
                            "name": name,
                            "location": "",
                        }
                    )
        for lg, teams in by_league.items():
            uniq = {t["id"]: t for t in teams}.values()
            country = None
            comp = emap.leagues.get(lg)
            if (
                comp
                and "." in comp
                and comp.split(".")[0] not in ("uefa", "fifa", "conmebol", "concacaf")
            ):
                country = comp.split(".")[0].upper()
            proposals[lg] = propose_team_map(list(uniq), reg, country=country, existing=emap.teams)
    fx_rows = [
        f.model_dump(mode="json") | {"espn_event_id": rep.espn_event_by_fixture.get(f.fixture_id)}
        for f in fixtures
    ]
    from soccer_edge.providers.espn import EspnArchive, result_record, results_from_events

    arch = EspnArchive(out_dir)
    res_written = 0
    for lg in leagues:
        evs = [e for e in events if e.league == lg]
        rows = []
        for e in evs:
            for r in results_from_events([e], emap):
                rows.append(result_record(r, e.espn_event_id, lg))
        res_written += arch.append_results(lg, rows)
    write_json(
        out_dir / "fixtures" / f"{as_of:%Y-%m-%d}" / f"espn-{as_of:%H%M%S}.json",
        {
            "as_of": as_of.isoformat(),
            "provider": "espn_site_api",
            "leagues": leagues,
            "fixtures": fx_rows,
            "results": {k: list(v) for k, v in rep.results.items()},
        },
    )
    status = {
        "as_of": as_of.isoformat(),
        "leagues": leagues,
        "events": len(events),
        "fixtures_mapped": rep.mapped,
        "events_skipped_unmapped": rep.skipped_events,
        "unmapped_team_ids": rep.unmapped_team_ids,
        "unmapped_leagues": sorted(rep.unmapped_leagues),
        "scoreboard_failures": failures[:50],
        "lineups": ln_stats,
        "results_appended": res_written,
        "weather": wx,
        "map_proposals": proposals,
        "map_version": emap.version,
    }
    write_json(out_dir / "STATUS.json", status)
    print(
        json.dumps(
            {k: v for k, v in status.items() if k not in ("map_proposals", "unmapped_team_ids")},
            indent=1,
            default=str,
        )
    )
    print(
        "unmapped teams:",
        len(rep.unmapped_team_ids),
        "| proposals:",
        {k: len(v["proposed"]) for k, v in proposals.items()},
    )
    return 0


def cmd_espn_backfill(args: argparse.Namespace) -> int:
    """Runner-side, one-off/incremental: per-day scoreboards over a date range -> results/espn/<league>.jsonl."""
    from datetime import date as _date

    from soccer_edge.core.serialization import write_json
    from soccer_edge.providers.espn import (
        EspnArchive,
        EspnMap,
        EspnProvider,
        MappingReport,
        result_record,
        results_from_events,
    )

    emap = EspnMap.load()
    prov = EspnProvider(emap=emap)
    arch = EspnArchive(Path(args.out_dir))
    start, end = (
        _date.fromisoformat(args.start),
        _date.fromisoformat(args.end) if args.end else utc_now().date(),
    )
    days = (end - start).days + 1
    summary: dict[str, object] = {"start": str(start), "end": str(end), "leagues": {}}
    for lg in args.leagues.split(","):
        events, failures = prov.fixtures_window([lg], start, days)
        rep = MappingReport()
        rows = []
        for e in events:
            for r in results_from_events([e], emap, rep):
                rows.append(result_record(r, e.espn_event_id, lg))
        n = arch.append_results(lg, rows)
        summary["leagues"][lg] = {
            "events": len(events),
            "finished_mapped": len(rows),
            "appended": n,
            "failures": len(failures),
            "unmapped_team_ids": rep.unmapped_team_ids,
            "skipped": rep.skipped_events,
        }
        print(
            lg,
            json.dumps(
                {k: v for k, v in summary["leagues"][lg].items() if k != "unmapped_team_ids"}
            ),
            "unmapped:",
            len(rep.unmapped_team_ids),
        )
    write_json(Path(args.out_dir) / "BACKFILL_STATUS.json", summary)
    return 0


def emap_path_default() -> Path:
    from soccer_edge.providers.espn import DEFAULT_MAP_PATH

    return DEFAULT_MAP_PATH


def cmd_replay_policies(args: argparse.Namespace) -> int:
    from soccer_edge.archive.ledger import PredictionLedger
    from soccer_edge.core.serialization import write_json
    from soccer_edge.policy.replay import replay
    from soccer_edge.policy.versions import SELECTION_VARIANTS

    ledger = PredictionLedger(Path(args.archive_dir))
    settlements = PredictionLedger(Path(args.settlements_dir))
    records = [r for r in ledger.iter_records() if r.get("schema") == "prediction_record_v1"]
    sett = {
        s["prediction_record_id"]: s
        for s in settlements.iter_records()
        if s.get("schema") == "settlement_record_v1"
    }
    out = replay(records, sett, SELECTION_VARIANTS)
    out["generated_at"] = utc_now().isoformat()
    write_json(Path(args.out), out)
    print(json.dumps({k: v["total"] for k, v in out["policies"].items()}, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "status", None) is None and args.cmd in ("discover", "capture"):
        args.status = ["open", "unopened"]
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
