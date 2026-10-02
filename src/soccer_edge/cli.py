"""`soccer` command line. RUN SOCCER == `soccer run --date YYYY-MM-DD`."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
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
    rc, _run = _capture_sweep(args)
    return rc


def _capture_sweep(args: argparse.Namespace):
    """`soccer capture` returning (exit code, DiscoveryRun) so callers can reprice/run on the same sweep."""
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
    return (0 if run.complete else 2), run


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
    import time

    from soccer_edge.archive.ledger import PredictionLedger
    from soccer_edge.kalshi.client import KalshiPublicClient
    from soccer_edge.kalshi.discovery import discover
    from soccer_edge.model.strength_v2 import StrengthConfigV2
    from soccer_edge.model.worlds import world_config_for
    from soccer_edge.pricing.edge import EdgeConfig
    from soccer_edge.run.inputs import DEFAULT_COMPETITIONS, assemble, build_inputs
    from soccer_edge.run.pipeline import RunConfig, run, stamp_decision_time, write_outputs
    from soccer_edge.run.simcache import SimCache

    t_start = time.time()
    timings: dict[str, float | str] = {}
    run_date = date.fromisoformat(args.date) if args.date else utc_now().date()
    as_of = utc_now()
    registry = _registry()
    comps = tuple(args.league) if args.league else DEFAULT_COMPETITIONS
    t_asm = time.time()
    data = assemble(
        registry,
        competitions=comps,
        today=run_date,
        espn_dir=Path(args.espn_dir) if args.espn_dir else None,
        strength_config=(StrengthConfigV2() if args.model_version == "dc_laplace_v2" else None),
    )
    timings["assemble_fit_s"] = round(time.time() - t_asm, 2)
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
    t_disc = time.time()
    sweep_series = known_series = None
    full_index = None
    if args.fast and not args.synthetic_kalshi:
        # INTRADAY RUN (phase 21): sweep only the series that had markets at the last exhaustive
        # discovery (plus any series new since then); the daily exhaustive catalog stays authoritative
        # and the fast sweep is reconciled against it below - unaccounted contracts must stay 0
        idx_path = REPO_ROOT / "data" / "catalog" / "latest_index.json"
        full_index = read_json_or(idx_path, None)
        if full_index and "series_with_markets" in full_index:
            known_series = {x["ticker"] for x in full_index.get("series", [])}
            sweep_series = set(full_index.get("series_with_markets", []))
            print(
                f"[kalshi] fast mode: sweeping {len(sweep_series)} series with markets at the last full discovery"
            )
        else:
            print("[kalshi] --fast requested but no usable committed index; exhaustive discovery")
            full_index = None
    prefetched = getattr(args, "prefetched_discovery", None)
    if prefetched is not None:
        # the caller's capture sweep (seconds old) is the market input: no second discovery
        disc = prefetched
    else:
        disc = discover(client, sweep_series=sweep_series, known_series=known_series)
    timings["discovery_s"] = round(time.time() - t_disc, 2)
    if full_index is not None:
        from soccer_edge.kalshi.reconcile import reconcile_fast_vs_full

        rec = reconcile_fast_vs_full(disc.counters(), full_index)
        write_json(Path(args.out_dir) / "fast_reconcile.json", rec)
        print(
            "[kalshi] fast reconciliation:",
            json.dumps({k: rec.get(k) for k in ("complete_relative_to_full", "evidence_level")}),
        )
        if not rec.get("complete_relative_to_full"):
            print(
                "[kalshi] fast sweep NOT complete relative to the daily catalog; exhaustive fallback"
            )
            t_disc = time.time()
            disc = discover(client)
            timings["discovery_exhaustive_fallback_s"] = round(time.time() - t_disc, 2)
    print(
        "[kalshi]",
        json.dumps({k: v for k, v in disc.counters().items() if k != "failures"}, default=str),
    )
    # decision time is after the sweep: freshness ages and horizon labels are measured from here
    as_of = utc_now()
    inputs = build_inputs(
        registry, data, disc, as_of=as_of, authority_path=REPO_ROOT / "config" / "authority.json"
    )
    slate_roots = _slate_roots(args)
    if slate_roots:
        from soccer_edge.slate.observations import fixture_context, lineup_observations

        inputs.lineup_observations = lineup_observations(
            slate_roots, fixture_context(slate_roots).espn_event_ids, now=as_of
        )
    if not args.synthetic_kalshi and not args.no_reference:
        # reference odds are context: a failure here must never fail the run
        try:
            lookup, observed, stats = _reference_capture(
                registry,
                data.fixtures,
                as_of,
                Path(args.reference_dir) if args.reference_dir else None,
            )
            inputs.reference_lookup = lookup
            inputs.reference_observed_at = observed
            from soccer_edge.reference.quality import quality_for_bookmaker

            inputs.reference_quality = quality_for_bookmaker(inputs.reference_bookmaker).value
        except Exception as exc:
            stats = {"error": str(exc)[:200]}
        print("[reference]", json.dumps(stats, default=str)[:600])
    # the decision time is taken after the LAST input capture (reference odds are fetched above)
    as_of = stamp_decision_time(inputs)
    cfg = RunConfig(
        run_date=run_date,
        window_hours=args.window_hours,
        leagues=tuple(args.league or ()),
        games=tuple(args.game or ()),
        confirmed_lineups_only=args.confirmed_lineups_only,
        n_worlds=args.worlds,
        draws_per_world=args.draws,
        engine_version=args.engine_version,
        world=world_config_for(getattr(args, "worlds_version", "worlds_v1")),
        edge=EdgeConfig(),
        enforce_freshness=not args.no_freshness_gate,
    )
    ledger = PredictionLedger(Path(args.archive_dir)) if args.archive_dir else None
    cache = SimCache(Path(args.sim_cache)) if args.sim_cache else None
    t_run = time.time()
    art = run(inputs, cfg, ledger=ledger, sim_cache=cache)
    timings["simulate_price_archive_s"] = round(time.time() - t_run, 2)
    timings["total_s"] = round(time.time() - t_start, 2)
    timings["mode"] = "fast" if (args.fast and full_index is not None) else "exhaustive"
    if prefetched is not None:
        timings["mode"] += "+prefetched_sweep"
    art.output = art.output.model_copy(
        update={"freshness": {**art.output.freshness, "stage_timings": timings}}
    )
    print("[timings]", json.dumps(timings))
    args.result_stats = {
        "simulated": list(art.fixtures_simulated),
        "reused_from_cache": list(art.fixtures_repriced),
        "resimulated_for_reducer": list(art.fixtures_resimulated_for_reducer),
        "archived_records": len(art.prediction_record_ids),
        "board_fixtures": len(art.board_entries),
        "timings": timings,
    }
    if args.board_out:
        _write_board(args, art, slate_roots)
    if args.slate_out_dir:
        _run_reprice(
            out_root=Path(args.slate_out_dir),
            roots=slate_roots,
            view_disc=disc,
            trigger=args.slate_trigger,
            lookahead_hours=args.slate_lookahead_hours,
            versions=_versions(args),
            compute={
                "mode": "model_refresh_and_reprice",
                "simulations_run": len(art.fixtures_simulated)
                + len(art.fixtures_resimulated_for_reducer),
                "fixtures_resimulated": sorted(
                    {*art.fixtures_simulated, *art.fixtures_resimulated_for_reducer}
                ),
                "fixtures_reused_from_cache": sorted(art.fixtures_repriced),
                "model_refresh_runtime_s": timings["total_s"],
                "kalshi_capture_runtime_s": getattr(args, "capture_runtime_s", None),
            },
        )
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


# ------------------------------------------------------------------------------ live slate (docs/ACTIONABLE_SLATE.md)


def _slate_roots(args: argparse.Namespace) -> list[Path]:
    """Local data roots a reprice / model run reads observations from (newest first, de-duplicated)."""
    roots: list[Path] = []
    for r in [*(getattr(args, "slate_root", None) or []), getattr(args, "espn_dir", None)]:
        if r and Path(r) not in roots:
            roots.append(Path(r))
    return roots


def _versions(args: argparse.Namespace) -> dict[str, str]:
    from soccer_edge.slate.invalidation import expected_versions

    return expected_versions(
        getattr(args, "model_version", None) or getattr(args, "run_model_version", None),
        getattr(args, "engine_version", None) or getattr(args, "run_engine_version", None),
        getattr(args, "worlds_version", None) or getattr(args, "run_worlds_version", None),
    )


def _write_board(args: argparse.Namespace, art, roots: list[Path]) -> dict:
    from soccer_edge.slate.board import BOARD_FILE, load_board, merge_boards, save_board

    now = utc_now()
    base = load_board(
        *[Path(b) for b in (args.board_in or [])],
        Path(args.board_out),
        *[r / BOARD_FILE for r in roots],
        now=now,
    )
    board = merge_boards(base, {"fixtures": art.board_entries}, now=now)
    save_board(Path(args.board_out), board)
    print(
        f"[board] {len(art.board_entries)} fixtures written by this run; "
        f"{len(board['fixtures'])} on the board -> {args.board_out}"
    )
    return board


def _run_reprice(
    *,
    out_root: Path,
    roots: list[Path],
    trigger: str,
    lookahead_hours: float,
    versions: dict[str, str] | None,
    compute: dict | None = None,
    view_disc=None,
    view=None,
) -> dict:
    """Reprice the cached board against one Kalshi sweep and write the slate under `out_root`. Local data
    only: no model fit, no simulation, no network."""
    from soccer_edge.authority.policy import AuthorityMatrix
    from soccer_edge.slate.board import BOARD_FILE, load_board
    from soccer_edge.slate.market_view import MarketView
    from soccer_edge.slate.reprice import RepriceContext, previous_slate, reprice, write_slate

    now = utc_now()
    all_roots = [out_root, *[r for r in roots if r != out_root]]
    board = load_board(*[r / BOARD_FILE for r in all_roots], now=now)
    if view is None and view_disc is not None:
        view = MarketView.from_discovery(view_disc)
    prev = previous_slate(*all_roots)
    slate = reprice(
        RepriceContext(
            board=board,
            view=view,
            roots=all_roots,
            now=now,
            trigger=trigger,
            lookahead_hours=lookahead_hours,
            versions=versions,
            authority=AuthorityMatrix.load(REPO_ROOT / "config" / "authority.json"),
            compute={"trigger": trigger, **(compute or {})},
        )
    )
    row = write_slate(out_root, slate, prev=prev)
    print(
        "[slate]",
        json.dumps(
            {
                k: row[k]
                for k in (
                    "slate_id",
                    "mode",
                    "fixtures",
                    "contract_sides",
                    "simulations_run",
                    "odds_api_calls",
                    "reprice_runtime_s",
                    "price_changes_vs_previous",
                )
            }
        ),
    )
    return row


def cmd_slate_reprice(args: argparse.Namespace) -> int:
    """REPRICE ONLY: cached board x the given Kalshi sweep (latest_catalog.json). No model, no network."""
    from soccer_edge.slate.market_view import MarketView

    view = None
    if args.catalog and Path(args.catalog).exists():
        view = MarketView.from_catalog_json(read_json(Path(args.catalog)))
    _run_reprice(
        out_root=Path(args.out_dir),
        roots=[Path(r) for r in (args.root or [])],
        trigger=args.trigger,
        lookahead_hours=args.lookahead_hours,
        versions=_versions(args),
        view=view,
        compute={
            "mode": "reprice_only",
            "kalshi_capture_runtime_s": args.kalshi_capture_runtime_s,
        },
    )
    return 0


def _restore_state(archive: Path, out: Path) -> None:
    """Change-suppression + ledger-index state a capture/run appends to (same set the tick restores)."""
    import shutil

    for rel in (
        "snapshots/last_fingerprints.json",
        "lineups/last_hashes.json",
        "predictions/index.json",
    ):
        src = archive / rel
        if src.exists() and not (out / rel).exists():
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out / rel)


def _slate_model_refresh(
    out: Path,
    archive: Path,
    disc,
    *,
    games: list[str] | None,
    window_hours: int,
    sim_cache: Path,
    versions_args: argparse.Namespace,
    trigger: str,
    lookahead_hours: float,
    capture_runtime_s: float | None,
) -> dict:
    """Fast model run on the caller's sweep (no second discovery) -> board -> reprice -> slate. Prediction
    records go to out/ledger (immutable evidence of what the model said at this time)."""
    import shutil
    import time

    parser = build_parser()
    pending = out / "runs" / "_pending"
    shutil.rmtree(pending, ignore_errors=True)
    (out / "ledger").mkdir(parents=True, exist_ok=True)
    if (out / "predictions" / "index.json").exists() and not (
        out / "ledger" / "index.json"
    ).exists():
        shutil.copyfile(out / "predictions" / "index.json", out / "ledger" / "index.json")
    argv = [
        "run",
        "--fast",
        "--window",
        str(window_hours),
        "--out-dir",
        str(pending),
        "--archive-dir",
        str(out / "ledger"),
        "--sim-cache",
        str(sim_cache),
        "--reference-dir",
        str(out / "reference"),
        "--espn-dir",
        str(archive),
        "--slate-root",
        str(out),
        "--board-out",
        str(out / "runs" / "latest.model_board.v1.json"),
        "--slate-out-dir",
        str(out),
        "--slate-trigger",
        trigger,
        "--slate-lookahead-hours",
        str(lookahead_hours),
        "--model-version",
        getattr(versions_args, "run_model_version", None) or "dc_laplace_v1",
        "--engine-version",
        getattr(versions_args, "run_engine_version", None) or "world_sim_v2",
        "--worlds-version",
        getattr(versions_args, "run_worlds_version", None) or "worlds_v1",
    ]
    for g in games or []:
        argv += ["--game", g]
    a = parser.parse_args(argv)
    a.prefetched_discovery = disc
    a.capture_runtime_s = capture_runtime_s
    t0 = time.time()
    rc = a.func(a)
    stats = dict(getattr(a, "result_stats", {}) or {})
    stats["rc"] = rc
    stats["runtime_s"] = round(time.time() - t0, 2)
    # archive layout runs/<day>/<run_id>/: `archive verify` resolves every prediction's run_id there
    doc = read_json_or(pending / "run_output.v1.json", None)
    if doc:
        final = out / "runs" / f"{utc_now():%Y-%m-%d}" / doc["run_id"]
        final.parent.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(final, ignore_errors=True)
        pending.rename(final)
        stats["run_dir"] = str(final)
    return stats


def cmd_slate_refresh(args: argparse.Namespace) -> int:
    """REFRESH SOCCER SLATE (manual): fresh Kalshi sweep -> lineups near kickoff -> fast model run that
    reuses every cached simulation whose inputs are unchanged -> reprice -> slate. Never calls The Odds
    API (the paid Pinnacle entry/close stay with the kickoff chain)."""
    import time

    archive, out = Path(args.archive_dir), Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _restore_state(archive, out)
    parser = build_parser()
    t0 = time.time()
    a = parser.parse_args(
        ["capture", "--fast", "--status", "open", "--out-dir", str(out / "snapshots")]
    )
    rc_cap, disc = _capture_sweep(a)
    cap_s = round(time.time() - t0, 2)
    print(f"[refresh] kalshi capture rc={rc_cap} in {cap_s}s ({len(disc.markets)} contracts)")
    if not args.skip_lineups:
        _refresh_lineups(out, archive, hours=args.lineup_hours)
    stats = _slate_model_refresh(
        out,
        archive,
        disc,
        games=None,
        window_hours=args.window,
        sim_cache=Path(args.sim_cache),
        versions_args=args,
        trigger="manual_refresh",
        lookahead_hours=args.lookahead_hours,
        capture_runtime_s=cap_s,
    )
    print("[refresh]", json.dumps({k: v for k, v in stats.items() if k != "timings"}, default=str))
    if args.summary_out:
        write_json(Path(args.summary_out), {"capture_rc": rc_cap, "capture_s": cap_s, **stats})
    return 0 if stats.get("rc") == 0 else 2


def _refresh_lineups(out: Path, archive: Path, *, hours: float) -> str:
    """ESPN lineup sync (free) for the leagues of scheduled fixtures kicking off within `hours`."""
    from datetime import timedelta

    from soccer_edge.dispatch.horizons import load_schedule
    from soccer_edge.providers.espn import ESPN_POOLS, EspnMap

    now = utc_now()
    sched = load_schedule(out / "dispatch" / "schedule.json") or load_schedule(
        archive / "dispatch" / "schedule.json"
    )
    comps = {f.competition_id for f in sched if now < f.kickoff_utc <= now + timedelta(hours=hours)}
    emap = EspnMap.load()
    slugs = sorted(
        {slug for slug, comp in emap.leagues.items() if comp in comps}
        | {s for c in comps for s in ESPN_POOLS.get(c, ())}
    )
    if not slugs:
        return "lineups:none_due"
    try:
        a = build_parser().parse_args(
            [
                "espn-sync",
                "--leagues",
                ",".join(slugs),
                "--back-days",
                "0",
                "--forward-days",
                "1",
                "--max-lineups",
                "60",
                "--out-dir",
                str(out),
            ]
        )
        rc = a.func(a)
        return f"lineups:{'ok' if rc == 0 else 'partial'}:{len(slugs)}"
    except Exception as exc:
        return f"lineups:error:{str(exc)[:80]}"


def cmd_slate_merge_latest(args: argparse.Namespace) -> int:
    """Publish-time merge of a mutable pointer onto the archive copy (scripts/archive_publish.sh): boards
    union by fixture (newer entry wins); slates keep the one with the newer Kalshi observation; the
    predictions index is a union (append-only records)."""
    from soccer_edge.slate.board import merge_boards
    from soccer_edge.slate.reprice import slate_order_key

    src, dst = read_json(Path(args.src)), read_json_or(Path(args.dst), None)
    if args.kind == "index":
        write_json(Path(args.dst), {**(dst or {}), **src})
        return 0
    if args.kind == "board":
        write_json(Path(args.dst), merge_boards(dst, src, now=utc_now()))
        return 0
    if dst is None or slate_order_key(src) >= slate_order_key(dst):
        write_json(Path(args.dst), src)
    else:
        print(f"[slate] kept the archived slate (newer Kalshi observation) over {args.src}")
    return 0


def cmd_settle(args: argparse.Namespace) -> int:
    from soccer_edge.archive.ledger import PredictionLedger
    from soccer_edge.authority.policy import AuthorityMatrix
    from soccer_edge.providers.openfootball import COMPETITION_FILES, OpenFootballProvider
    from soccer_edge.run.inputs import current_season_id
    from soccer_edge.run.settle import (
        CoverageRows,
        build_result_index,
        coverage_report,
        et_possible,
        model_health,
        settle_ledger,
        settlement_v1_rows,
    )

    as_of = utc_now()
    registry = _registry()
    ledger = PredictionLedger(Path(args.archive_dir))
    settlements = PredictionLedger(Path(args.settlements_dir))
    of = OpenFootballProvider(registry)
    comps = {
        r.get("competition_id")
        for r in ledger.iter_records()
        if r.get("schema") == "prediction_record_v1"
    }
    sources: dict[str, list] = {"openfootball": [], "espn_site_api": []}
    with_source: set[str] = set()
    # openfootball: current and previous season (records can straddle the July season boundary)
    for comp in sorted(c for c in comps if c in COMPETITION_FILES):
        with_source.add(comp)
        cur = current_season_id(comp, as_of.date())
        prev = f"{int(cur[:4]) - 1}-{cur[:4][2:]}"
        for season in (prev, cur):
            try:
                sources["openfootball"].extend(of.results(comp, season).payload)
            except Exception as exc:
                print(f"[results] openfootball {comp} {season}: {str(exc)[:120]}")
    # ESPN archive: every league the sync/backfill jobs have captured (universal settlement, audit B4)
    if args.espn_dir:
        from soccer_edge.providers.espn import EspnArchive, EspnMap

        arch = EspnArchive(Path(args.espn_dir))
        emap = EspnMap.load()
        leagues = tuple(
            p.stem for p in sorted((Path(args.espn_dir) / "results" / "espn").glob("*.jsonl"))
        )
        with_source |= {emap.leagues[lg] for lg in leagues if lg in emap.leagues}
        try:
            sources["espn_site_api"].extend(arch.results(leagues))
        except Exception as exc:
            print(f"[results] espn archive: {str(exc)[:160]}")
    index = build_result_index(sources, competitions_with_source=with_source)
    et_map = {
        cid: et_possible(c.format, c.extra_time_in_knockouts)
        for cid, c in registry.competitions.items()
    }
    cov_rows = CoverageRows()
    written = settle_ledger(
        ledger,
        index,
        Path(args.snapshots_dir),
        settlements,
        as_of=as_of,
        reference_dir=Path(args.reference_dir) if args.reference_dir else None,
        et_possible_for=et_map,
        coverage_rows=cov_rows,
        close_attempts=_close_attempts(args, as_of),
    )
    coverage = coverage_report(
        cov_rows, as_of=as_of, grace=__import__("datetime").timedelta(hours=3)
    )
    print(
        "[settlement coverage]",
        json.dumps(
            {
                k: coverage[k]
                for k in (
                    "predictions_total",
                    "settleable_now",
                    "settled",
                    "pending_kickoff",
                    "pending_result",
                    "pending_mapping",
                    "pending_evidence",
                    "unsupported_settlement",
                    "unsettleable",
                    "unaccounted_settlement_records",
                )
            }
        ),
    )
    if coverage["unaccounted_settlement_records"] != 0:
        raise SystemExit("settlement coverage invariant violated: unaccounted records")
    if args.run_log:
        _append_settle_run(Path(args.run_log), as_of, written, cov_rows)
    rows, proposals = model_health(
        settlements, AuthorityMatrix.load(REPO_ROOT / "config" / "authority.json"), as_of=as_of
    )
    out = Path(args.out_dir)
    write_json(out / "settlement_coverage.v1.json", coverage)
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


def _close_attempts(args: argparse.Namespace, as_of) -> dict | None:
    """Per-fixture reference-close attempt states from the archive root (reference dir's parent)."""
    if not args.reference_dir:
        return None
    from soccer_edge.reference.close_attempts import close_attempt_states

    try:
        return close_attempt_states(Path(args.reference_dir).parent, now=as_of)
    except Exception as exc:
        print(f"[close attempts] unavailable: {str(exc)[:120]}")
        return None


def _append_settle_run(path: Path, as_of, written: list, cov_rows) -> None:
    """One row per settlement run: what is settled and what is still pending, so the dispatcher knows when
    another run is due (dispatch/settle_runs.jsonl; docs/SCHEDULER.md)."""
    from soccer_edge.core.serialization import append_jsonl

    pending_states = {"PENDING_RESULT", "PENDING_EVIDENCE", "PENDING_MAPPING"}
    pending: dict[str, str] = {}
    for r in cov_rows:
        state = getattr(r.state, "value", str(r.state))
        if state.upper() in pending_states:
            pending.setdefault(r.fixture_id, r.kickoff_utc)
    append_jsonl(
        path,
        {
            "schema": "settle_run_v1",
            "status": "ok",
            "started_at": as_of.isoformat().replace("+00:00", "Z"),
            "completed_at": utc_now().isoformat().replace("+00:00", "Z"),
            "source": os.environ.get("SETTLE_SOURCE")
            or os.environ.get("GITHUB_EVENT_NAME")
            or "manual",
            "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
            "newly_settled": len(written),
            "pending_fixtures": [
                {"fixture_id": f, "kickoff_utc": k} for f, k in sorted(pending.items())
            ],
        },
    )


def cmd_uncertainty_report(args: argparse.Namespace) -> int:
    from soccer_edge.archive.ledger import PredictionLedger
    from soccer_edge.evaluation.uncertainty import coverage_report, write_report

    recs = list(PredictionLedger(Path(args.settlements_dir)).iter_records())
    rep = coverage_report(recs)
    write_report(rep, Path(args.out))
    print(json.dumps({"n_cells": rep["n_cells"], "verdicts": rep["verdict_counts"]}))
    for c in rep["cells"]:
        if c["horizon"] == "any":
            print(
                f"  {c['model_family']} {c['worlds_version']} {c['market_family']}: n={c['n_settled']} "
                f"coverage80={c['grouped_coverage_80']} market_inside={c['market_mid_inside_share']} {c['verdict']}"
            )
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


def cmd_archive_verify(args: argparse.Namespace) -> int:
    from soccer_edge.archive.manifest import verify_archive

    code, report = verify_archive(
        Path(args.archive_dir), require_manifest=not args.allow_missing_manifest
    )
    if args.out:
        write_json(Path(args.out), report)
    summary = {
        k: report.get(k)
        for k in (
            "ok",
            "manifest_present",
            "files_checked",
            "records_checked",
            "n_problems",
            "n_warnings",
            "n_unmanifested_files",
            "problem_counts",
            "note",
            "error",
        )
    }
    print(json.dumps(summary, indent=1, default=str))
    for pr in report.get("problems", [])[:10]:
        print("PROBLEM", json.dumps(pr, default=str))
    if code == 2:
        print(
            "archive verify: NO MANIFEST (pass --allow-missing-manifest to run intrinsic checks only)"
        )
    return code


def cmd_archive_manifest(args: argparse.Namespace) -> int:
    from soccer_edge.archive.manifest import ArchiveManifest, ArchiveManifestError

    man = ArchiveManifest(Path(args.archive_dir))
    if not man.exists() and not args.init:
        if args.if_present:
            print(json.dumps({"skipped": "no manifest present (--if-present)"}))
            return 0
        print(
            "archive manifest: no manifest present; pass --init to bootstrap one from the current state"
        )
        return 2
    try:
        stats = man.update(init=args.init)
    except ArchiveManifestError as exc:
        print(f"archive manifest: refused: {exc}")
        return 1
    print(json.dumps(stats, indent=1))
    return 0


def cmd_archive_recover(args: argparse.Namespace) -> int:
    from soccer_edge.archive.manifest import ArchiveManifest
    from soccer_edge.archive.recover import (
        RecoveryError,
        apply_recovery,
        dry_run_report,
        scan_history,
    )

    repo = Path(args.repo)
    root = Path(args.archive_dir) if args.archive_dir else None
    recs = scan_history(repo, args.branch, tip_root=root)
    report = dry_run_report(recs, repo=repo, branch=args.branch)
    if args.report:
        write_json(Path(args.report), report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "paths_scanned",
                    "recoverable_lines_total",
                    "conflicts_total",
                    "unverifiable_total",
                    "refused",
                )
            },
            indent=1,
        )
    )
    for pth in report["paths"]:
        print(
            f"  {pth['path']}: union {pth['union_lines']} tip {pth['tip_lines']} recoverable {pth['recoverable_lines']} conflicts {len(pth['conflicts'])}"
        )
    if report["refused"]:
        print(
            "archive recover: REFUSED (conflicting identities or unverifiable rows; nothing written)"
        )
        return 1
    if not args.apply:
        print("archive recover: dry run only (pass --apply with --archive-dir to append the rows)")
        return 0
    if root is None:
        print("archive recover: --apply requires --archive-dir (a working tree of the archive tip)")
        return 2
    try:
        manifest = apply_recovery(recs, archive_root=root, report=report)
    except RecoveryError as exc:
        print(f"archive recover: {exc}")
        return 1
    print(
        json.dumps(
            {"recovery_id": manifest["recovery_id"], "lines_appended": manifest["lines_appended"]},
            indent=1,
        )
    )
    man = ArchiveManifest(root)
    if man.exists():
        stats = man.update(
            recovery_id=manifest["recovery_id"], recovered_paths=set(manifest["lines_appended"])
        )
        print(json.dumps({"manifest": stats}))
    return 0


def _dispatch_schedule(archive: Path, now) -> dict:
    from soccer_edge.core.serialization import read_json_or
    from soccer_edge.dispatch.horizons import build_schedule
    from soccer_edge.providers.espn import ESPN_POOLS, EspnArchive
    from soccer_edge.run.inputs import DEFAULT_COMPETITIONS

    run_out = read_json_or(archive / "runs" / "latest.run_output.v1.json", None)
    espn_rows = []
    try:
        fixtures, _eids, _as_of = EspnArchive(archive).latest_fixtures()
        espn_rows = [f.model_dump(mode="json") for f in fixtures]
    except Exception as exc:
        print(f"[dispatch] espn fixtures unreadable: {str(exc)[:120]}")
    doc = build_schedule(
        run_output=run_out,
        espn_fixtures=espn_rows,
        priced_competitions=set(DEFAULT_COMPETITIONS) | set(ESPN_POOLS),
        now=now,
    )
    # age of the Kalshi listing behind the schedule: the paid-call guard refuses to spend on a stale one
    doc["kalshi_listing_as_of"] = (run_out or {}).get("generated_at")
    return doc


def cmd_dispatch_schedule(args: argparse.Namespace) -> int:
    from soccer_edge.dispatch.horizons import SCHEDULE_FILE

    now = utc_now()
    sched = _dispatch_schedule(Path(args.archive_dir), now)
    out = Path(args.out_dir) / SCHEDULE_FILE
    write_json(out, sched)
    print(json.dumps({"fixtures": len(sched["fixtures"]), "out": str(out)}))
    return 0


def cmd_dispatch_plan(args: argparse.Namespace) -> int:
    from soccer_edge.dispatch.horizons import (
        SCHEDULE_FILE,
        STATE_LOG,
        load_log,
        load_schedule,
        minutes_until_next_window,
        plan,
    )

    now = utc_now()
    archive = Path(args.archive_dir)
    schedule = load_schedule(archive / SCHEDULE_FILE)
    log = load_log(archive / STATE_LOG)
    due, missed, upcoming = plan(schedule, log, now=now)
    print(
        json.dumps(
            {
                "now": now.isoformat(),
                "fixtures_scheduled": len(schedule),
                "due": [
                    (d.fixture.fixture_id, d.horizon, round(d.minutes_to_kickoff, 1)) for d in due
                ],
                "newly_missed": len(missed),
                "next_window_minutes": minutes_until_next_window(upcoming),
            },
            indent=1,
        )
    )
    return 0


def _refresh_archive(archive: Path) -> bool:
    """Fast-forward the archive clone to the current data-archive tip (new run outputs, heartbeats)."""
    import subprocess

    if not (archive / ".git").exists():
        return False
    for cmd in (
        ["git", "-C", str(archive), "fetch", "-q", "--depth", "1", "origin", "data-archive"],
        ["git", "-C", str(archive), "reset", "-q", "--hard", "FETCH_HEAD"],
    ):
        if subprocess.run(cmd, capture_output=True, check=False, timeout=180).returncode != 0:
            print("[dispatch] archive refresh failed; keeping the current clone")
            return False
    return True


def _publish_batch(out: Path, message: str) -> str:
    import subprocess

    p = subprocess.run(
        [str(REPO_ROOT / "scripts" / "kickoff_publish.sh"), str(out), message],
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    return "published" if p.returncode == 0 else f"publish_failed:{p.returncode}"


def _chain_lease():
    from soccer_edge.dispatch.gitstore import ChainLease, github_remote_url

    url = github_remote_url()
    return ChainLease(url) if url else None


def cmd_dispatch_tick(args: argparse.Namespace) -> int:
    """One dispatcher tick: log missed horizons (with an explicit state), run one bounded capture batch for
    every horizon that is satisfiable now, hold for the next window, write diagnostics. Idempotent:
    delivered horizons are never re-captured, paid reference calls are claimed first.

    --chain (docs/SCHEDULER.md): a bounded LINK of the fixture-aware chain. It holds a single-chain lease,
    sleeps between the actual fixture windows (no calls while sleeping), refreshes the archive + schedule
    every --refresh-minutes, publishes after every batch, and ends at --max-tick-minutes or as soon as no
    future window exists. The summary says whether a successor link is needed (chain_continue)."""
    import shutil
    import time
    from datetime import timedelta

    from soccer_edge.core.serialization import read_json_or
    from soccer_edge.dispatch.horizons import (
        DIAGNOSTICS_FILE,
        FIRST_SEEN_FILE,
        SCHEDULE_FILE,
        STATE_LOG,
        _dt,
        _iso,
        append_log,
        classify_missed,
        delivered_rows,
        diagnostics,
        load_log,
        load_schedule,
        minutes_until_next_window,
        plan,
    )
    from soccer_edge.dispatch.wake import load_heartbeats, wake_times

    archive = Path(args.archive_dir)
    out = Path(args.out_dir)
    started = now = utc_now()
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    hard_limit = started + timedelta(minutes=args.max_tick_minutes)
    lease = _chain_lease() if args.chain else None
    if lease is not None and not lease.acquire(run_id, now=now, minutes=args.max_tick_minutes + 15):
        holder = (lease.holder or {}).get("run_id")
        print(f"[dispatch] chain lease held by run {holder}; this link exits (no successor)")
        if args.summary_out:
            write_json(
                Path(args.summary_out),
                {
                    "started_at": _iso(started),
                    "completed_at": _iso(utc_now()),
                    "lease_refused": True,
                    "chain_continue": False,
                    "elapsed_minutes": 0,
                },
            )
        return 0
    prev_sched = read_json_or(archive / SCHEDULE_FILE, {}) or {}
    first_seen = dict(read_json_or(archive / FIRST_SEEN_FILE, {}) or {})
    # a fixture already known before this tick keeps the earliest evidence of that: its first log row or
    # the previous schedule's build time (so a first_seen file started today cannot relabel old misses)
    for r in load_log(archive / STATE_LOG):
        if r.logged_at and r.logged_at < first_seen.get(r.fixture_id, "9999"):
            first_seen[r.fixture_id] = r.logged_at
    if prev_sched.get("generated_at"):
        for d in prev_sched.get("fixtures", []):
            fid = d.get("fixture_id")
            if fid and prev_sched["generated_at"] < first_seen.get(fid, "9999"):
                first_seen[fid] = prev_sched["generated_at"]

    def rebuild_schedule(at):
        doc = _dispatch_schedule(archive, at)
        write_json(out / SCHEDULE_FILE, doc)
        sched = load_schedule(out / SCHEDULE_FILE)
        for fx in sched:
            first_seen.setdefault(fx.fixture_id, _iso(at))
        cutoff = _iso(at - timedelta(days=21))
        for k in [k for k, v in first_seen.items() if v < cutoff]:
            first_seen.pop(k)
        write_json(out / FIRST_SEEN_FILE, first_seen)
        return doc, sched

    sched_doc, schedule = rebuild_schedule(now)
    wakes = wake_times(load_heartbeats(archive, now=now))
    log_path = out / STATE_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if (archive / STATE_LOG).exists():
        shutil.copyfile(archive / STATE_LOG, log_path)
    # restore change-suppression state so captures append only what changed
    for rel in (
        "snapshots/last_fingerprints.json",
        "reference/last_fingerprints.json",
        "lineups/last_hashes.json",
        "predictions/index.json",
    ):
        src = archive / rel
        if src.exists():
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out / rel)
    # the shared Odds API credit ledger: the guard's spend history (append-merged back on publish)
    budget_src = archive / "odds_api" / "budget"
    if budget_src.is_dir():
        (out / "odds_api" / "budget").mkdir(parents=True, exist_ok=True)
        for f in sorted(budget_src.glob("*.jsonl"))[-31:]:
            shutil.copyfile(f, out / "odds_api" / "budget" / f.name)
    batches = 0
    summary: list[dict] = []
    attempted: set[tuple[str, int]] = set()
    missed_states: dict[str, int] = {}
    delivered_n = 0
    held = 0.0
    last_refresh = now
    publishes: list[str] = []
    upcoming: list = []
    end_reason = "no_hold"
    # free Kalshi capture + reprice between horizons while a fixture is near (docs/ACTIONABLE_SLATE.md)
    slate_every = timedelta(minutes=args.slate_refresh_minutes or 0)
    last_slate = None
    slate_refreshes = 0

    def slate_active(at) -> bool:
        if not args.chain or slate_every <= timedelta(0):
            return False
        end = at + timedelta(hours=args.slate_active_hours)
        return any(at < fx.kickoff_utc <= end for fx in schedule)

    while True:
        now = utc_now()
        wakes.append(
            now
        )  # this link is awake: a window closing now without delivery is an execution miss
        if args.chain and now - last_refresh >= timedelta(minutes=args.refresh_minutes):
            if _refresh_archive(archive):
                sched_doc, schedule = rebuild_schedule(now)
                wakes.extend(wake_times(load_heartbeats(archive, now=now)))
            last_refresh = now
        log = load_log(log_path)
        due, missed, upcoming = plan(schedule, log, now=now)
        missed = classify_missed(missed, wakes + [started], first_seen)
        for r in missed:
            missed_states[r.state] = missed_states.get(r.state, 0) + 1
        append_log(log_path, missed)
        due = [d for d in due if (d.fixture.fixture_id, d.horizon) not in attempted]
        if not due:
            wait = minutes_until_next_window(upcoming)
            if args.no_hold:
                end_reason = "no_hold"
                break
            if wait is None:
                end_reason = "no_future_window"
                break
            left = (hard_limit - now).total_seconds() / 60
            if args.chain:
                if left <= 2:
                    end_reason = "link_time_limit"
                    break
                if slate_active(now) and (last_slate is None or now - last_slate >= slate_every):
                    batch_id = f"ks-{now:%Y%m%dT%H%M%SZ}"
                    acts = _slate_refresh(out, batch_id, args)
                    last_slate = now  # the sweep started now: prices are observed from this instant
                    slate_refreshes += 1
                    summary.append(
                        {"batch_id": batch_id, "slate_refresh": True, "due": [], "actions": acts}
                    )
                    if args.publish_each_batch:
                        publishes.append(
                            _publish_batch(out, f"kickoff-dispatch {run_id} {batch_id} slate")
                        )
                    continue
                # wake at the next horizon's NOMINAL time (T-60 at 60 min, T-15 at 15 min, ...), which is
                # inside its window: the paid entry lands at T-60 and the paid close at T-15
                nominal = min(u.minutes_to_kickoff - u.horizon for u in upcoming)
                refresh_left = args.refresh_minutes - (now - last_refresh).total_seconds() / 60
                nap = max(0.5, min(nominal, left - 1, max(refresh_left, 0.5)))
                if slate_active(now) and last_slate is not None:
                    slate_left = (last_slate + slate_every - now).total_seconds() / 60
                    nap = max(0.5, min(nap, slate_left))
            else:
                if not (wait <= args.max_hold_minutes and wait + 3 <= left):
                    end_reason = "next_window_beyond_hold"
                    break
                nap = wait
            print(f"[dispatch] holding {nap:.1f} min (next window opens in {wait:.1f} min)")
            time.sleep(nap * 60 + (0 if args.chain else 5))
            held += nap
            continue
        batch_id = f"kd-{now:%Y%m%dT%H%M%SZ}"
        attempted |= {(d.fixture.fixture_id, d.horizon) for d in due}
        listing = sched_doc.get("kalshi_listing_as_of")
        args.schedule_as_of = _dt(listing) if listing else None
        actions = _dispatch_actions(out, due, batch_id, args)
        captured = any(
            a.startswith(("kalshi_capture:ok", "kalshi_capture:incomplete")) for a in actions
        )
        batches += 1
        if captured:
            last_slate = now  # every horizon batch repriced the slate on its own sweep
            rows = delivered_rows(due, now=utc_now(), batch_id=batch_id, actions=actions)
            append_log(log_path, rows)
            delivered_n += len(rows)
        # a failed capture is not logged: the next wake retries while the window is open, and a window
        # that closes after a failed attempt is classified MISSED_EXECUTION_FAILURE
        summary.append(
            {
                "batch_id": batch_id,
                "captured": captured,
                "due": [
                    (d.fixture.fixture_id, d.horizon, round(d.minutes_to_kickoff, 2)) for d in due
                ],
                "actions": actions,
            }
        )
        if args.publish_each_batch:
            write_json(
                out / DIAGNOSTICS_FILE, diagnostics(load_log(log_path), schedule, now=utc_now())
            )
            publishes.append(_publish_batch(out, f"kickoff-dispatch {run_id} {batch_id}"))
        if args.no_hold:
            end_reason = "no_hold"
            break
    diag = diagnostics(load_log(log_path), schedule, now=utc_now())
    diag["last_tick"] = {"batches": batches, "summary": summary}
    write_json(out / DIAGNOSTICS_FILE, diag)
    odds = [a for b in summary for a in b["actions"] if a.startswith("odds_api:")]
    paid = credits = 0
    for a in odds:
        for part in a.split(":"):
            if part.startswith("credits="):
                credits += int(part.split("=", 1)[1] or 0)
            if part.startswith("paid="):
                paid += int(part.split("=", 1)[1] or 0)
    end = utc_now()
    nxt = minutes_until_next_window(upcoming)
    tick = {
        "started_at": _iso(started),
        "completed_at": _iso(end),
        "elapsed_minutes": round((end - started).total_seconds() / 60, 1),
        "end_reason": end_reason,
        "chain_continue": bool(args.chain and end_reason == "link_time_limit" and nxt is not None),
        "next_window_minutes": None if nxt is None else round(nxt, 1),
        "batches": batches,
        "horizons_delivered": delivered_n,
        "horizons_missed_logged": sum(missed_states.values()),
        "missed_states": missed_states,
        "paid_calls": paid,
        "credits_spent": credits,
        "odds_api": odds,
        "hold_minutes": round(held, 1),
        "publishes": publishes,
        "slate_refreshes": slate_refreshes,
        "model_refreshes": sum(
            1 for b in summary for a in b["actions"] if a.startswith("model_refresh:ok")
        ),
        "simulations": sum(
            int(part.split("=", 1)[1])
            for b in summary
            for a in b["actions"]
            if a.startswith("model_refresh:")
            for part in a.split(":")
            if part.startswith("sim=")
        ),
    }
    if lease is not None:
        lease.release(run_id, now=end)
    if args.summary_out:
        write_json(Path(args.summary_out), tick)
    print(
        json.dumps(
            {
                **{
                    k: tick[k]
                    for k in (
                        "batches",
                        "horizons_delivered",
                        "missed_states",
                        "paid_calls",
                        "credits_spent",
                        "end_reason",
                        "chain_continue",
                    )
                },
                "delivered_total": diag["delivered_total"],
                "missed_total": diag["missed_total"],
                "delivery_rate_total": diag["delivery_rate_total"],
            },
            indent=1,
        )
    )
    return 0


def _dispatch_actions(out: Path, due, batch_id: str, args: argparse.Namespace) -> list[str]:
    """Capture batch, in this order: Kalshi fast snapshot (free) -> football-data reference (free) ->
    Pinnacle via The Odds API (paid, budget-guarded entry/close only) -> ESPN lineups (free) -> selective
    model refresh (slate/refresh.py: T-60, T-15 on input change, invalidated/missing) -> reprice of the
    whole slate on the same sweep. Each action is isolated: a failure is recorded, never fatal."""
    import time

    parser = build_parser()
    done: list[str] = []
    disc = None
    cap_s = None
    try:
        t0 = time.time()
        a = parser.parse_args(
            ["capture", "--fast", "--status", "open", "--out-dir", str(out / "snapshots")]
        )
        rc, disc = _capture_sweep(a)
        cap_s = round(time.time() - t0, 2)
        done.append(f"kalshi_capture:{'ok' if rc == 0 else 'incomplete'}")
    except Exception as exc:
        done.append(f"kalshi_capture:error:{str(exc)[:80]}")
    try:
        a = parser.parse_args(["capture-reference", "--out-dir", str(out / "reference")])
        rc = a.func(a)
        done.append(f"reference:{'ok' if rc == 0 else 'empty'}")
    except Exception as exc:
        done.append(f"reference:error:{str(exc)[:80]}")
    odds = None
    if not args.skip_odds_api:
        odds = _odds_api_action(
            out,
            due,
            batch_id,
            Path(args.archive_dir),
            schedule_as_of=getattr(args, "schedule_as_of", None),
        )
        done.append(odds)
    if not args.skip_lineups:
        # before the model decision: a T-15 refresh depends on whether the XI changed
        comps = {d.fixture.competition_id for d in due}
        done.append(_lineup_action(out, comps))
    if disc is not None:
        done.extend(_slate_actions(out, due, batch_id, args, disc, cap_s, odds))
    return done


def _lineup_action(out: Path, comps: set[str]) -> str:
    from soccer_edge.providers.espn import ESPN_POOLS, EspnMap

    emap = EspnMap.load()
    slugs = sorted(
        {slug for slug, comp in emap.leagues.items() if comp in comps}
        | {s for c in comps for s in ESPN_POOLS.get(c, ())}
    )
    if not slugs:
        return "lineups:none_due"
    try:
        a = build_parser().parse_args(
            [
                "espn-sync",
                "--leagues",
                ",".join(slugs),
                "--back-days",
                "0",
                "--forward-days",
                "1",
                "--max-lineups",
                "60",
                "--out-dir",
                str(out),
            ]
        )
        rc = a.func(a)
        return f"lineups:{'ok' if rc == 0 else 'partial'}:{len(slugs)}"
    except Exception as exc:
        return f"lineups:error:{str(exc)[:80]}"


def _odds_counts(action: str | None) -> tuple[int, int]:
    paid = credits = 0
    for part in (action or "").split(":"):
        if part.startswith("credits="):
            credits = int(part.split("=", 1)[1] or 0)
        if part.startswith("paid="):
            paid = int(part.split("=", 1)[1] or 0)
    return paid, credits


def _slate_actions(  # noqa: PLR0917
    out: Path,
    due,
    batch_id: str,
    args: argparse.Namespace,
    disc,
    cap_s: float | None,
    odds_action: str | None,
) -> list[str]:
    """Selective model refresh for the due fixtures that need one, then reprice everything."""
    from soccer_edge.slate.board import BOARD_FILE, load_board
    from soccer_edge.slate.observations import fixture_context, lineup_observations
    from soccer_edge.slate.refresh import refresh_plan, refresh_window_hours

    archive = Path(args.archive_dir)
    roots = [out, archive]
    now = utc_now()
    mode = "every" if args.with_run else args.model_refresh
    horizons = "/".join(f"T-{h}" for h in sorted({d.horizon for d in due}, reverse=True)) or "none"
    trigger = f"kickoff_chain:{horizons}"
    paid, credits = _odds_counts(odds_action)
    done: list[str] = []
    try:
        board = load_board(*[r / BOARD_FILE for r in roots], now=now)
        ctx = fixture_context(roots)
        lineups = lineup_observations(roots, ctx.espn_event_ids, now=now)
        need = refresh_plan(
            due, board, ctx=ctx, lineups=lineups, versions=_versions(args), mode=mode
        )
    except Exception as exc:
        need = {}
        done.append(f"model_refresh:plan_error:{str(exc)[:80]}")
    if need:
        try:
            stats = _slate_model_refresh(
                out,
                archive,
                disc,
                games=sorted(need),
                window_hours=refresh_window_hours(due, set(need), now),
                sim_cache=_tick_sim_cache(args),
                versions_args=args,
                trigger=trigger,
                lookahead_hours=args.slate_lookahead_hours,
                capture_runtime_s=cap_s,
            )
            reasons = ",".join(sorted({":".join(r.split(":")[:2]) for r in need.values()}))
            done.append(
                f"model_refresh:{'ok' if stats.get('rc') == 0 else 'incomplete'}:"
                f"fixtures={len(need)}:sim={len(stats.get('simulated', []))}:"
                f"cache={len(stats.get('reused_from_cache', []))}:why={reasons}"
            )
            # the run already repriced the whole slate on this sweep; record this batch's paid calls on it
            _annotate_slate_odds(out, paid, credits)
            return [*done, "slate_reprice:ok:via_model_refresh"]
        except SystemExit as exc:
            done.append(f"model_refresh:exit:{exc.code}")
        except Exception as exc:
            done.append(f"model_refresh:error:{str(exc)[:80]}")
    else:
        done.append(f"model_refresh:skipped:{mode}:no_input_change")
    try:
        row = _run_reprice(
            out_root=out,
            roots=[archive],
            trigger=trigger,
            lookahead_hours=args.slate_lookahead_hours,
            versions=_versions(args),
            view_disc=disc,
            compute={
                "mode": "reprice_only",
                "kalshi_capture_runtime_s": cap_s,
                # the batch's paid reference capture (if any) was decided by its own purpose windows and
                # claims; it is reported here, never caused by the reprice
                "odds_api_calls": paid,
                "odds_api_credits": credits,
            },
        )
        done.append(f"slate_reprice:ok:sides={row['contract_sides']}:sim=0")
    except Exception as exc:
        done.append(f"slate_reprice:error:{str(exc)[:80]}")
    return done


def _annotate_slate_odds(out: Path, paid: int, credits: int) -> None:
    from soccer_edge.slate.reprice import SLATE_FILE

    p = out / SLATE_FILE
    doc = read_json_or(p, None)
    if doc is None:
        return
    doc["compute"]["odds_api_calls"] = paid
    doc["compute"]["odds_api_credits"] = credits
    write_json(p, doc)


def _tick_sim_cache(args: argparse.Namespace) -> Path:
    """Simulation cache OUTSIDE the publish payload (kickoff_publish.sh clears <out>/simcache)."""
    p = (
        Path(args.sim_cache_dir)
        if args.sim_cache_dir
        else Path(args.out_dir).resolve().parent / "simcache"
    )
    p.mkdir(parents=True, exist_ok=True)
    return p


def _slate_refresh(out: Path, batch_id: str, args: argparse.Namespace) -> list[str]:
    """Between horizons: free Kalshi capture + reprice of the cached board. No model, no paid call."""
    import time

    try:
        t0 = time.time()
        a = build_parser().parse_args(
            ["capture", "--fast", "--status", "open", "--out-dir", str(out / "snapshots")]
        )
        rc, disc = _capture_sweep(a)
        cap_s = round(time.time() - t0, 2)
    except Exception as exc:
        return [f"kalshi_capture:error:{str(exc)[:80]}"]
    done = [f"kalshi_capture:{'ok' if rc == 0 else 'incomplete'}"]
    try:
        row = _run_reprice(
            out_root=out,
            roots=[Path(args.archive_dir)],
            trigger="kalshi_capture:slate_refresh",
            lookahead_hours=args.slate_lookahead_hours,
            versions=_versions(args),
            view_disc=disc,
            compute={"mode": "reprice_only", "kalshi_capture_runtime_s": cap_s},
        )
        done.append(f"slate_reprice:ok:sides={row['contract_sides']}:sim=0")
    except Exception as exc:
        done.append(f"slate_reprice:error:{str(exc)[:80]}")
    return done


def _claim_fn(archive_dir: Path | None, batch_id: str):
    """First-writer-wins claims on data-archive before any paid call (None when no pushable remote)."""
    import subprocess

    from soccer_edge.dispatch.gitstore import ClaimStore, github_remote_url

    url = github_remote_url()
    if url is None and archive_dir is not None and (archive_dir / ".git").exists():
        p = subprocess.run(
            ["git", "-C", str(archive_dir), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
        )
        url = p.stdout.strip() if p.returncode == 0 and "@" in p.stdout else None
    if url is None:
        return None
    from soccer_edge.reference.odds_budget import BudgetConfig

    cfg = BudgetConfig.load(REPO_ROOT / "config" / "odds_api_budget.json")
    store = ClaimStore(url)
    run = {"batch_id": batch_id, "run_id": os.environ.get("GITHUB_RUN_ID", "local")}
    caps = {"daily": cfg.daily_credit_ceiling, "rolling_30d": cfg.rolling_30d_credit_ceiling}

    def claim(identities: list[str], call_record: dict) -> set[str]:
        won = store.claim(
            identities,
            {**run, "claimed_at": utc_now().isoformat()},
            call_record=call_record,
            caps=caps,
        )
        if store.last_reason:
            print(f"[odds_api] claim: {store.last_reason}")
        return won

    return claim


def _odds_api_action(
    out: Path, due, batch_id: str, archive_dir: Path | None = None, schedule_as_of=None
) -> str:
    """Pinnacle reference via The Odds API for the due Kalshi-listed fixtures (budget-guarded, batched per
    competition). Isolated like every other action: a failure is recorded, never fatal."""
    from soccer_edge.reference.odds_api_capture import DueFixture, capture, status_summary
    from soccer_edge.reference.odds_budget import BudgetConfig

    try:
        now = utc_now()
        fixtures = [
            DueFixture(
                d.fixture.fixture_id,
                d.fixture.competition_id,
                d.fixture.kickoff_utc,
                (d.fixture.kickoff_utc - now).total_seconds() / 60,
                d.fixture.source == "run_output" or d.fixture.markets_discovered > 0,
            )
            for d in due
        ]
        stats = capture(
            fixtures,
            registry=_registry(),
            out_root=out,
            cfg=BudgetConfig.load(REPO_ROOT / "config" / "odds_api_budget.json"),
            now=now,
            batch_id=batch_id,
            claim_fn=_claim_fn(archive_dir, batch_id),
            schedule_as_of=schedule_as_of,
        )
        write_json(out / "odds_api" / "STATUS.json", status_summary(stats, now))
        print("[odds_api]", json.dumps(status_summary(stats, now), default=str)[:800])
        return (
            f"odds_api:{stats.get('status', '?').lower()}:"
            f"credits={stats.get('credits_charged', 0)}:paid={stats.get('paid_calls', 0)}:"
            f"rows={stats.get('snapshots', 0)}"
        )
    except Exception as exc:
        from soccer_edge.providers.the_odds_api import redact

        return f"odds_api:error:{type(exc).__name__}:{redact(str(exc))[:80]}"


def cmd_odds_api_sample(args: argparse.Namespace) -> int:
    """ONE bounded Pinnacle capture (at most one paid call, ~3 credits, budget-guarded) for the Kalshi-listed
    fixtures of a single competition in the published dispatch schedule. Rows are ordinary reference
    snapshots (so they enter the close/CLV path); the ledger marks them purpose='sample', so they never
    stand in for the dispatcher's entry or close captures."""
    from soccer_edge.dispatch.horizons import load_schedule
    from soccer_edge.providers.the_odds_api import SPORT_KEYS
    from soccer_edge.reference.odds_api_capture import DueFixture, capture, status_summary
    from soccer_edge.reference.odds_budget import BudgetConfig

    now = utc_now()
    archive = Path(args.archive_dir)
    out = Path(args.out_dir)
    sched_path = archive / "dispatch" / "schedule.json"
    schedule = load_schedule(sched_path) if sched_path.exists() else []
    horizon = now + timedelta(hours=args.hours)
    listed = [
        f
        for f in schedule
        if (f.source == "run_output" or f.markets_discovered > 0)
        and now < f.kickoff_utc <= horizon
        and f.competition_id in SPORT_KEYS
        and (not args.competition or f.competition_id == args.competition)
    ]
    if not listed:
        print(
            json.dumps({"status": "NO_KALSHI_LISTED_FIXTURE_WITH_SPORT_KEY", "hours": args.hours})
        )
        return 2
    comp = min(listed, key=lambda f: f.kickoff_utc).competition_id
    fixtures = [
        DueFixture(
            f.fixture_id,
            f.competition_id,
            f.kickoff_utc,
            (f.kickoff_utc - now).total_seconds() / 60,
            True,
        )
        for f in listed
        if f.competition_id == comp
    ]
    batch = f"sample-{now:%Y%m%dT%H%M%SZ}"
    stats = capture(
        fixtures,
        registry=_registry(),
        out_root=out,
        cfg=BudgetConfig.load(REPO_ROOT / "config" / "odds_api_budget.json"),
        now=now,
        batch_id=batch,
        force_purpose="sample",
        max_paid_calls=1,
    )
    summary = {"competition": comp, "fixtures": len(fixtures), **status_summary(stats, now)}
    write_json(out / "odds_api" / "SAMPLE_STATUS.json", summary)
    print(json.dumps(summary, indent=1, default=str))
    return 0 if stats.get("snapshots") else 1


def cmd_odds_api_status(args: argparse.Namespace) -> int:
    """Soccer's spend on the shared Odds API account, from the append-only ledger (no HTTP)."""
    from collections import Counter

    from soccer_edge.reference.odds_budget import BudgetConfig, BudgetLedger

    root = Path(args.archive_dir)
    now = utc_now()
    cfg = BudgetConfig.load(REPO_ROOT / "config" / "odds_api_budget.json")
    led = BudgetLedger(root)
    rows = led.rows_since(now, args.days)
    last = next(
        (
            r
            for r in sorted(rows, key=lambda r: r.get("logged_at", ""), reverse=True)
            if r.get("requests_remaining") is not None
        ),
        None,
    )
    by_day: dict[str, int] = {}
    for r in rows:
        day = (r.get("logged_at") or "")[:10]
        by_day[day] = by_day.get(day, 0) + int(r.get("credits_charged") or 0)
    print(
        json.dumps(
            {
                "days": args.days,
                "soccer_credits_charged": sum(by_day.values()),
                "soccer_credits_by_day": dict(sorted(by_day.items())),
                "rows_by_kind_status": Counter(f"{r.get('kind')}:{r.get('status')}" for r in rows),
                "blocked_reasons": Counter(
                    r.get("reason") for r in rows if r.get("status") == "BLOCKED_BUDGET_GUARD"
                ),
                "latest_account_quota": (
                    {
                        k: last.get(k)
                        for k in (
                            "logged_at",
                            "requests_used",
                            "requests_remaining",
                            "requests_last",
                        )
                    }
                    if last
                    else None
                ),
                "guard": {
                    "daily_credit_ceiling": cfg.daily_credit_ceiling,
                    "rolling_30d_credit_ceiling": cfg.rolling_30d_credit_ceiling,
                    "account_reserve_floor": cfg.account_reserve_floor,
                    "spent_30d": led.spent(now, 30),
                },
            },
            indent=1,
            default=str,
        )
    )
    return 0


def cmd_odds_api_probe(args: argparse.Namespace) -> int:
    """FREE endpoints only (/sports, optional /events): which soccer keys are active, the account's quota
    headers, and whether every mapped competition has a live sport key. Spends no credits by design; the
    ledger row proves it (credits_charged = x-requests-last)."""
    from soccer_edge.providers.the_odds_api import SPORT_KEYS, OddsApiClient, api_key_configured
    from soccer_edge.reference.odds_budget import BudgetLedger, charge

    if not api_key_configured():
        print(json.dumps({"status": "NOT_CONFIGURED", "secret": "ODDS_API_KEY"}))
        return 2
    now = utc_now()
    led = BudgetLedger(Path(args.out_dir))
    with OddsApiClient() as client:
        resp = client.get_sports()
        c, basis = charge(resp.quota, 0)
        led.append(
            now,
            {
                **resp.meta(),
                "batch_id": "probe",
                "status": "OK" if resp.ok else "REQUEST_FAILED",
                "credits_charged": c,
                "charge_basis": basis,
            },
        )
        soccer = sorted(
            (s for s in (resp.payload or []) if str(s.get("key", "")).startswith("soccer_")),
            key=lambda s: s["key"],
        )
        active = {s["key"] for s in soccer if s.get("active")}
        events = {}
        for sk in args.events or []:
            ev = client.get_events(sk, now, now + timedelta(days=args.days_ahead))
            c2, b2 = charge(ev.quota, 0)
            led.append(
                now,
                {
                    **ev.meta(),
                    "batch_id": "probe",
                    "status": "OK" if ev.ok else "REQUEST_FAILED",
                    "credits_charged": c2,
                    "charge_basis": b2,
                },
            )
            events[sk] = {
                "meta": ev.meta(),
                "events": len(ev.payload or []),
                "sample": [
                    (e.get("home_team"), e.get("away_team"), e.get("commence_time"))
                    for e in (ev.payload or [])[:5]
                ],
            }
    print(
        json.dumps(
            {
                "sports_call": resp.meta(),
                "soccer_keys_listed": len(soccer),
                "soccer_keys_active": sorted(active),
                "soccer_metadata": {
                    s["key"]: {
                        k: s.get(k) for k in ("title", "description", "active", "has_outrights")
                    }
                    for s in soccer
                },
                "mapped_competitions": {
                    cid: {
                        "sport_key": sk,
                        "active": sk in active,
                        "listed": any(s["key"] == sk for s in soccer),
                    }
                    for cid, sk in sorted(SPORT_KEYS.items())
                },
                "events": events,
            },
            indent=1,
            default=str,
        )
    )
    return 0 if resp.ok else 1


def cmd_dispatch_upcoming(args: argparse.Namespace) -> int:
    """Which (fixture, horizon) captures are required in the next hours, when each window opens and
    whether a paid reference capture is expected. Reads the archive only; triggers nothing."""
    from datetime import timedelta

    from soccer_edge.dispatch.horizons import (
        HORIZON_WINDOWS,
        REQUIRED_HORIZONS,
        SCHEDULE_FILE,
        STATE_LOG,
        _iso,
        load_log,
        load_schedule,
        logged_keys,
        window_bounds,
    )
    from soccer_edge.providers.the_odds_api import SPORT_KEYS

    archive = Path(args.archive_dir)
    now = utc_now()
    end = now + timedelta(hours=args.hours)
    schedule = load_schedule(archive / SCHEDULE_FILE)
    done = logged_keys(load_log(archive / STATE_LOG))
    rows = []
    for fx in schedule:
        for h in REQUIRED_HORIZONS:
            opens, closes = window_bounds(fx.kickoff_utc, h)
            if (fx.fixture_id, h) in done or closes < now or opens > end:
                continue
            listed = fx.source == "run_output" or fx.markets_discovered > 0
            paid = None
            if listed and fx.competition_id in SPORT_KEYS:
                paid = "close" if h in (15, 5) else ("entry" if h == 60 else None)
            rows.append(
                {
                    "window_opens": _iso(opens),
                    "window_closes": _iso(closes),
                    "status": "DUE_NOW" if opens <= now else "PENDING",
                    "horizon": h,
                    "fixture_id": fx.fixture_id,
                    "kickoff_utc": _iso(fx.kickoff_utc),
                    "kalshi_listed": listed,
                    "reference_capture": paid,
                }
            )
    rows.sort(key=lambda r: (r["window_opens"], r["fixture_id"]))
    print(
        json.dumps(
            {
                "now": _iso(now),
                "hours": args.hours,
                "windows": {str(h): list(w) for h, w in HORIZON_WINDOWS.items()},
                "required": rows,
                "n": len(rows),
            },
            indent=1,
        )
    )
    return 0


def cmd_dispatch_reliability(args: argparse.Namespace) -> int:
    from soccer_edge.dispatch.horizons import STATE_LOG, load_log
    from soccer_edge.dispatch.reliability import reliability
    from soccer_edge.dispatch.wake import load_heartbeats

    archive = Path(args.archive_dir)
    now = utc_now()
    cfg = json.loads((REPO_ROOT / "config" / "dispatch.json").read_text())
    cadence = {k: cfg[k] for k in ("external_heartbeat_minutes", "github_backup_minutes")}
    rep = reliability(
        load_heartbeats(archive, now=now), load_log(archive / STATE_LOG), now=now, cadence=cadence
    )
    print(json.dumps(rep, indent=1, default=str))
    return 0


def cmd_dispatch_close_report(args: argparse.Namespace) -> int:
    from collections import Counter

    from soccer_edge.reference.close_attempts import close_attempt_states

    states = close_attempt_states(Path(args.archive_dir), now=utc_now())
    if args.fixture:
        states = {k: v for k, v in states.items() if args.fixture in k}
    print(
        json.dumps(
            {
                "counts": dict(Counter(v["state"] for v in states.values())),
                "fixtures": dict(sorted(states.items())),
            },
            indent=1,
        )
    )
    return 0


def cmd_dispatch_diagnostics(args: argparse.Namespace) -> int:
    from soccer_edge.dispatch.horizons import (
        SCHEDULE_FILE,
        STATE_LOG,
        diagnostics,
        load_log,
        load_schedule,
    )

    archive = Path(args.archive_dir)
    d = diagnostics(
        load_log(archive / STATE_LOG), load_schedule(archive / SCHEDULE_FILE), now=utc_now()
    )
    if args.out:
        write_json(Path(args.out), d)
    keys = (
        "fixtures_tracked",
        "delivered_total",
        "missed_total",
        "delivery_rate_total",
        "n_pending_fixtures",
    )
    print(json.dumps({k: d[k] for k in keys}, indent=1))
    print(json.dumps(d["by_horizon"], indent=1))
    return 0


def cmd_promote_evaluate(args: argparse.Namespace) -> int:
    """Report-only promotion evaluator (audit §Q). Never edits config/authority.json."""
    from soccer_edge.archive.ledger import PredictionLedger
    from soccer_edge.archive.manifest import verify_archive
    from soccer_edge.authority.promotion_v2 import evaluate_all

    as_of = utc_now()
    preds = {
        r["record_id"]: r
        for r in PredictionLedger(Path(args.archive_dir)).iter_records()
        if r.get("schema") == "prediction_record_v1"
    }
    stl = list(PredictionLedger(Path(args.settlements_dir)).iter_records())
    unacc = 0
    runs_root = Path(args.runs_dir) if args.runs_dir else None
    if runs_root and runs_root.exists():
        for cov in runs_root.glob("*/*/coverage.json"):
            try:
                unacc = max(unacc, int(read_json(cov).get("unaccounted_contracts", 0)))
            except Exception:
                unacc = max(unacc, 1)
    manifest_ok = False
    if args.archive_root:
        code, _rep = verify_archive(Path(args.archive_root), require_manifest=True)
        manifest_ok = code == 0
    report = evaluate_all(
        stl,
        preds,
        integrity={
            "unaccounted_contracts_max": unacc,
            "manifest_ok": manifest_ok,
            "runs_checked": bool(runs_root),
        },
        as_of=as_of.isoformat(),
    )
    write_json(Path(args.out), report)
    print(
        json.dumps(
            {k: report[k] for k in ("cells_total", "eligible_for_owner_review", "not_eligible")},
            indent=1,
        )
    )
    if report["closest_cell"]:
        c = report["closest_cell"]
        print("closest cell:", c["cell"], "failed:", c["failed_gates"][:12])
    return 0


def cmd_lineups_report(args: argparse.Namespace) -> int:
    from soccer_edge.evaluation.lineups import lead_time_report, lineup_rows

    rep = lead_time_report(lineup_rows(Path(args.archive_dir)), as_of=utc_now())
    write_json(Path(args.out), rep)
    print(
        json.dumps(
            {
                k: rep[k]
                for k in (
                    "fixtures_tracked",
                    "fixtures_kickoff_passed",
                    "with_pre_kickoff_xi",
                    "with_xi_ge_20min_before_kickoff",
                    "share_xi_ge_20min",
                    "lead_time_minutes",
                )
            },
            indent=1,
        )
    )
    return 0


def cmd_archive_compact(args: argparse.Namespace) -> int:
    from soccer_edge.archive.compact import compact, plan
    from soccer_edge.archive.manifest import ArchiveManifestError

    root = Path(args.archive_dir)
    try:
        cands = plan(root)
    except ArchiveManifestError as exc:
        print(f"archive compact: {exc}")
        return 2
    print(json.dumps({"candidates": len(cands), "bytes": sum(c.bytes_uncompressed for c in cands)}))
    if not args.apply:
        for c in cands[:20]:
            print("  ", c.path, c.bytes_uncompressed)
        return 0
    try:
        man = compact(root, cands)
    except ArchiveManifestError as exc:
        print(f"archive compact: refused: {exc}")
        return 1
    print(
        json.dumps(
            {
                "compaction_id": man["compaction_id"],
                "files": len(man["files"]),
                "bytes_saved": man["bytes_saved"],
            }
        )
    )
    return 0


def cmd_espn_lineup_backfill(args: argparse.Namespace) -> int:
    """Runner-side: post-hoc starting XIs of COMPLETED matches over a date range -> lineups/history/<league>.jsonl
    (input for the lineup oracle study, phase 19). Never used for pregame pricing."""
    from datetime import date, timedelta

    from soccer_edge.core.serialization import append_jsonl, read_jsonl, write_json
    from soccer_edge.providers.espn import EspnProvider

    prov = EspnProvider()
    leagues = [x.strip() for x in args.leagues.split(",") if x.strip()]
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end) if args.end else utc_now().date()
    out = Path(args.out_dir) / "lineups" / "history"
    out.mkdir(parents=True, exist_ok=True)
    stats: dict[str, dict[str, int]] = {}
    budget = args.max_events
    for lg in leagues:
        path = out / f"{lg}.jsonl"
        known = {str(r.get("espn_event_id")) for r in read_jsonl(path)} if path.exists() else set()
        st = stats[lg] = {
            "days": 0,
            "events_completed": 0,
            "fetched": 0,
            "skipped_known": 0,
            "no_xi": 0,
            "failures": 0,
        }
        day = start
        while day <= end and budget > 0:
            st["days"] += 1
            try:
                events = prov.scoreboard(lg, day).payload
            except Exception:
                st["failures"] += 1
                day += timedelta(days=1)
                continue
            for ev in events:
                if ev.state != "post":
                    continue
                st["events_completed"] += 1
                if ev.espn_event_id in known:
                    st["skipped_known"] += 1
                    continue
                if budget <= 0:
                    break
                budget -= 1
                try:
                    snap = prov.lineup(lg, ev.espn_event_id).payload
                except Exception:
                    st["failures"] += 1
                    continue
                rec = snap.to_record()
                rec["lineup_state"] = "post_hoc"
                rec["backfill"] = True
                if not snap.published:
                    st["no_xi"] += 1
                append_jsonl(path, rec)
                known.add(ev.espn_event_id)
                st["fetched"] += 1
            day += timedelta(days=1)
    write_json(
        Path(args.out_dir) / "lineups" / "history" / "BACKFILL_STATUS.json",
        {
            "as_of": utc_now().isoformat(),
            "start": args.start,
            "end": end.isoformat(),
            "stats": stats,
            "budget_left": budget,
        },
    )
    print(json.dumps(stats, indent=1))
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
    r.add_argument(
        "--model-version",
        choices=["dc_laplace_v1", "dc_laplace_v2"],
        default="dc_laplace_v1",
        help="strength model family (v2 = scoring intercept + hard centring; phase 12)",
    )
    r.add_argument(
        "--engine-version",
        choices=["minute_engine_v1", "world_sim_v2"],
        default="world_sim_v2",
        help=(
            "simulation engine; world_sim_v2 (default since 2026-09-29, docs/RESEARCH_DC_V2.md) = exact "
            "DC score matrix + analytic full-time pricing; minute_engine_v1 = the audited v1 path"
        ),
    )
    r.add_argument(
        "--worlds-version",
        choices=["worlds_v1", "worlds_v2"],
        default="worlds_v1",
        help="world layer (worlds_v2 = Laplace x k parameter draw, no hand-set inflation term)",
    )
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
    r.add_argument(
        "--no-reference", action="store_true", help="skip football-data.co.uk reference odds"
    )
    r.add_argument(
        "--reference-dir", default=None, help="append change-suppressed reference snapshots here"
    )
    r.add_argument(
        "--espn-dir",
        default=None,
        help="data-archive checkout with results/espn + fixtures/espn (adds ESPN-fed competitions)",
    )
    r.add_argument(
        "--fast",
        action="store_true",
        help="intraday run: sweep only series with markets at the last exhaustive discovery, reconcile against it",
    )
    r.add_argument("--fail-on-incomplete", action="store_true")
    r.add_argument(
        "--board-in", action="append", help="model board(s) to merge this run's fixtures onto"
    )
    r.add_argument(
        "--board-out",
        default=None,
        help="write the merged model board (latest.model_board.v1.json)",
    )
    r.add_argument(
        "--slate-out-dir",
        default=None,
        help="reprice the board on this run's sweep and write runs/latest.actionable_slate.v1.json here",
    )
    r.add_argument(
        "--slate-root",
        action="append",
        help="local data root(s) for lineups / Pinnacle rows / fixture context (default: --espn-dir)",
    )
    r.add_argument("--slate-trigger", default="run_soccer")
    r.add_argument("--slate-lookahead-hours", type=float, default=48.0)
    r.set_defaults(func=cmd_run)

    sl = sub.add_parser("slate", help="live actionable slate (cached model x fresh Kalshi prices)")
    slsub = sl.add_subparsers(dest="slate_cmd", required=True)
    slr = slsub.add_parser(
        "reprice", help="REPRICE ONLY: cached board x latest Kalshi sweep (no model, no network)"
    )
    slr.add_argument("--catalog", default=None, help="the capture's latest_catalog.json")
    slr.add_argument("--out-dir", required=True, help="payload root (runs/, dispatch/slate_log/)")
    slr.add_argument(
        "--root", action="append", help="archive root(s) to read (board, lineups, ...)"
    )
    slr.add_argument("--trigger", default="kalshi_capture")
    slr.add_argument("--lookahead-hours", type=float, default=48.0)
    slr.add_argument("--kalshi-capture-runtime-s", type=float, default=None)
    slr.add_argument("--run-model-version", default="dc_laplace_v1")
    slr.add_argument("--run-engine-version", default="world_sim_v2")
    slr.add_argument("--run-worlds-version", default="worlds_v1")
    slr.set_defaults(func=cmd_slate_reprice)
    slf = slsub.add_parser(
        "refresh",
        help="REFRESH SOCCER SLATE: capture -> lineups -> fast model (cache reuse) -> reprice (no Odds API)",
    )
    slf.add_argument("--archive-dir", required=True)
    slf.add_argument("--out-dir", required=True)
    slf.add_argument("--sim-cache", default="simcache")
    slf.add_argument("--window", type=int, default=48, help="model window (hours ahead)")
    slf.add_argument("--lookahead-hours", type=float, default=48.0)
    slf.add_argument("--lineup-hours", type=float, default=3.0)
    slf.add_argument("--skip-lineups", action="store_true")
    slf.add_argument("--summary-out", default=None)
    slf.add_argument("--run-model-version", default="dc_laplace_v1")
    slf.add_argument("--run-engine-version", default="world_sim_v2")
    slf.add_argument("--run-worlds-version", default="worlds_v1")
    slf.set_defaults(func=cmd_slate_refresh)
    slm = slsub.add_parser(
        "merge-latest", help="publish-time merge of a latest board/slate pointer"
    )
    slm.add_argument("--src", required=True)
    slm.add_argument("--dst", required=True)
    slm.add_argument("--kind", choices=["board", "slate", "index"], required=True)
    slm.set_defaults(func=cmd_slate_merge_latest)

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
    elb = sub.add_parser(
        "espn-lineup-backfill",
        help="post-hoc starting XIs of completed matches over a date range (lineup oracle input; runner-side)",
    )
    elb.add_argument("--leagues", required=True, help="comma-separated ESPN slugs")
    elb.add_argument("--start", required=True, help="YYYY-MM-DD")
    elb.add_argument("--end", default=None)
    elb.add_argument("--max-events", type=int, default=4000, help="summary fetch budget per run")
    elb.add_argument("--out-dir", required=True)
    elb.set_defaults(func=cmd_espn_lineup_backfill)

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
    st.add_argument(
        "--espn-dir",
        default=None,
        help="archive root holding results/espn/*.jsonl (universal settlement)",
    )
    st.add_argument(
        "--run-log",
        default=None,
        help="append a settle_run_v1 row (settled / pending fixtures) for the dispatcher here",
    )
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

    ar = sub.add_parser(
        "archive", help="archive integrity: manifest, verify (non-zero on corruption), recover"
    )
    arsub = ar.add_subparsers(dest="archive_cmd", required=True)
    av = arsub.add_parser(
        "verify",
        help="verify the archive against its manifest; exit 1 on corruption, 2 if no manifest",
    )
    av.add_argument("--archive-dir", required=True, help="working tree of the data-archive branch")
    av.add_argument("--out", default=None, help="write the full verification report as JSON")
    av.add_argument(
        "--allow-missing-manifest",
        action="store_true",
        help="run intrinsic checks only when no manifest exists yet (exit 0)",
    )
    av.set_defaults(func=cmd_archive_verify)
    am = arsub.add_parser(
        "manifest",
        help="extend the manifest to cover the current archive state (verifies first; refuses on corruption)",
    )
    am.add_argument("--archive-dir", required=True)
    am.add_argument(
        "--init",
        action="store_true",
        help="bootstrap a manifest from the current state when none exists",
    )
    am.add_argument(
        "--if-present", action="store_true", help="no-op (exit 0) when no manifest exists yet"
    )
    am.set_defaults(func=cmd_archive_manifest)
    arc = arsub.add_parser(
        "recover",
        help="one-time recovery of overwritten .jsonl rows from the archive branch history",
    )
    arc.add_argument(
        "--repo", required=True, help="git repository containing the archive branch history"
    )
    arc.add_argument("--branch", default="data-archive")
    arc.add_argument(
        "--archive-dir", default=None, help="working tree of the archive tip (required for --apply)"
    )
    arc.add_argument("--report", default=None, help="write the dry-run report JSON here")
    arc.add_argument(
        "--apply", action="store_true", help="append the recoverable rows (refuses on any conflict)"
    )
    arc.set_defaults(func=cmd_archive_recover)
    acp = arsub.add_parser(
        "compact", help="gzip closed day files (manifest-aware; never deletes evidence)"
    )
    acp.add_argument("--archive-dir", required=True)
    acp.add_argument("--apply", action="store_true")
    acp.set_defaults(func=cmd_archive_compact)

    dp = sub.add_parser(
        "dispatch", help="kickoff-timed capture dispatcher (T-120/60/30/15/5 horizons)"
    )
    dpsub = dp.add_subparsers(dest="dispatch_cmd", required=True)
    ds = dpsub.add_parser(
        "schedule", help="build dispatch/schedule.json from the latest run output + ESPN fixtures"
    )
    ds.add_argument("--archive-dir", required=True)
    ds.add_argument("--out-dir", required=True)
    ds.set_defaults(func=cmd_dispatch_schedule)
    dpl = dpsub.add_parser(
        "plan", help="show horizons due now / newly missed / next window (read-only)"
    )
    dpl.add_argument("--archive-dir", required=True)
    dpl.set_defaults(func=cmd_dispatch_plan)
    dt = dpsub.add_parser(
        "tick", help="one dispatcher tick: capture every horizon satisfiable now, hold for the next"
    )
    dt.add_argument("--archive-dir", required=True, help="clone of data-archive (read)")
    dt.add_argument(
        "--out-dir",
        required=True,
        help="publish payload root (snapshots/, reference/, lineups/, dispatch/)",
    )
    dt.add_argument("--max-hold-minutes", type=float, default=40.0)
    dt.add_argument(
        "--max-tick-minutes",
        type=float,
        default=48.0,
        help="hard bound on the whole tick (job limit 55)",
    )
    dt.add_argument("--summary-out", default=None, help="write the tick summary JSON here")
    dt.add_argument(
        "--chain",
        action="store_true",
        help="bounded link of the fixture-aware chain: lease, hold between windows, refresh, successor flag",
    )
    dt.add_argument("--refresh-minutes", type=float, default=30.0)
    dt.add_argument(
        "--publish-each-batch",
        action="store_true",
        help="publish to data-archive after every batch",
    )
    dt.add_argument("--no-hold", action="store_true")
    dt.add_argument("--skip-lineups", action="store_true")
    dt.add_argument(
        "--with-run",
        action="store_true",
        help="also run a fast, 3-hour-window RUN SOCCER at each due horizon (near-close predictions)",
    )
    dt.add_argument(
        "--skip-odds-api",
        action="store_true",
        help="skip the budget-guarded Pinnacle reference capture (The Odds API)",
    )
    dt.add_argument("--run-model-version", default="dc_laplace_v1")
    dt.add_argument("--run-engine-version", default="world_sim_v2")
    dt.add_argument("--run-worlds-version", default="worlds_v1")
    dt.add_argument(
        "--model-refresh",
        choices=["selective", "every", "off"],
        default="selective",
        help="model runs at due horizons: T-60, T-15 on input change, invalidated/missing (selective)",
    )
    dt.add_argument(
        "--sim-cache-dir",
        default=None,
        help="simulation cache kept outside the publish payload (default: <out>/../simcache)",
    )
    dt.add_argument(
        "--slate-refresh-minutes",
        type=float,
        default=0.0,
        help="chain only: free Kalshi capture + reprice this often between horizons (0 = off)",
    )
    dt.add_argument(
        "--slate-active-hours",
        type=float,
        default=12.0,
        help="periodic slate refresh runs while a scheduled fixture kicks off within this many hours",
    )
    dt.add_argument("--slate-lookahead-hours", type=float, default=48.0)
    dt.set_defaults(func=cmd_dispatch_tick)
    du = dpsub.add_parser(
        "upcoming",
        help="UPCOMING REQUIRED CAPTURES for the next hours (diagnostics only, read-only)",
    )
    du.add_argument("--archive-dir", required=True)
    du.add_argument("--hours", type=float, default=6.0)
    du.set_defaults(func=cmd_dispatch_upcoming)
    drl = dpsub.add_parser(
        "reliability", help="rolling 24 h / 7 d scheduler reliability (read-only)"
    )
    drl.add_argument("--archive-dir", required=True)
    drl.set_defaults(func=cmd_dispatch_reliability)
    dcr = dpsub.add_parser(
        "close-report", help="per-fixture reference-close attempt states (dispatcher vs provider)"
    )
    dcr.add_argument("--archive-dir", required=True)
    dcr.add_argument("--fixture", default=None, help="substring filter on fixture ids")
    dcr.set_defaults(func=cmd_dispatch_close_report)
    dd = dpsub.add_parser("diagnostics", help="horizon-delivery diagnostics from the archived log")
    dd.add_argument("--archive-dir", required=True)
    dd.add_argument("--out", default=None)
    dd.set_defaults(func=cmd_dispatch_diagnostics)

    oa = sub.add_parser(
        "odds-api", help="Pinnacle reference via The Odds API (shared account; budget-guarded)"
    )
    oasub = oa.add_subparsers(dest="odds_api_cmd", required=True)
    oas = oasub.add_parser(
        "status", help="soccer's credit spend + latest account quota (ledger only)"
    )
    oas.add_argument("--archive-dir", required=True, help="root holding odds_api/budget/")
    oas.add_argument("--days", type=int, default=30)
    oas.set_defaults(func=cmd_odds_api_status)
    oap = oasub.add_parser("probe", help="FREE endpoints only: active soccer keys + quota headers")
    oap.add_argument("--out-dir", required=True, help="ledger root (odds_api/budget/ is appended)")
    oap.add_argument("--events", nargs="*", help="sport keys to list upcoming events for (free)")
    oap.add_argument("--days-ahead", type=float, default=7.0)
    oap.set_defaults(func=cmd_odds_api_probe)
    osm = oasub.add_parser(
        "sample",
        help="ONE bounded paid Pinnacle capture for one competition's Kalshi-listed fixtures",
    )
    osm.add_argument(
        "--archive-dir", required=True, help="data-archive clone (dispatch/schedule.json)"
    )
    osm.add_argument("--out-dir", required=True, help="publish root (reference/, odds_api/)")
    osm.add_argument("--hours", type=float, default=48.0)
    osm.add_argument("--competition", default=None)
    osm.set_defaults(func=cmd_odds_api_sample)

    pe = sub.add_parser(
        "promote", help="promotion evaluator (report only; never edits authority.json)"
    )
    pesub = pe.add_subparsers(dest="promote_cmd", required=True)
    pev = pesub.add_parser(
        "evaluate", help="evaluate every model x market x competition-group x horizon cell"
    )
    pev.add_argument("--archive-dir", required=True, help="predictions ledger root")
    pev.add_argument("--settlements-dir", required=True)
    pev.add_argument(
        "--runs-dir", default=None, help="archive runs/ root (unaccounted-contract check)"
    )
    pev.add_argument(
        "--archive-root", default=None, help="archive tree root (manifest verification)"
    )
    pev.add_argument("--out", required=True)
    pev.set_defaults(func=cmd_promote_evaluate)
    un = sub.add_parser("uncertainty", help="interval coverage of settled predictions")
    unsub = un.add_subparsers(dest="uncertainty_cmd", required=True)
    unr = unsub.add_parser("report", help="grouped 80% interval coverage per cell (audit F4)")
    unr.add_argument("--settlements-dir", required=True)
    unr.add_argument("--out", required=True)
    unr.set_defaults(func=cmd_uncertainty_report)

    lu = sub.add_parser("lineups", help="lineup capture reliability")
    lusub = lu.add_subparsers(dest="lineups_cmd", required=True)
    lur = lusub.add_parser("report", help="lead-time distribution and pre-kickoff XI shares")
    lur.add_argument("--archive-dir", required=True, help="archive tree root (reads lineups/)")
    lur.add_argument("--out", required=True)
    lur.set_defaults(func=cmd_lineups_report)
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
