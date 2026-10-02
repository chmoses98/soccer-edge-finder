"""CI failure semantics (alert fatigue): bounded optional weather capture, espn-sync health classification,
the single health gate, and the grow-only predictions index merge used by every archive publisher.

All tests are deterministic: fake clocks / fake providers / a local bare git remote; no network, no
dependency on the calendar date or on committed live data."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from soccer_edge.archive.manifest import verify_archive
from soccer_edge.providers.espn import espn_sync_health
from soccer_edge.providers.open_meteo import Geo, capture_weather

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


health_gate = _load_script("health_gate")
merge_json_index = _load_script("merge_json_index")


# ---------------------------------------------------------------- bounded weather capture

AS_OF = datetime(2026, 9, 19, 12, tzinfo=UTC)


def _events(n: int) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            espn_event_id=str(i),
            league="eng.1",
            kickoff_utc=AS_OF + timedelta(hours=2 + i),
            venue="V",
            venue_city=f"City{i}",
            venue_country="England",
        )
        for i in range(n)
    ]


class _FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def _forecast(ko):
    return {"forecast_time_utc": ko.strftime("%Y-%m-%dT%H:00"), "temperature_2m": 10.0}, AS_OF


def test_weather_time_budget_skips_remaining_events(tmp_path):
    clock = _FakeClock()

    class SlowProvider:
        def geocode(self, city, country):
            clock.t += 60.0  # every fetch costs a 60 s timeout's worth of wall time
            return Geo(51.0, 0.0, city, country)

        def forecast_at(self, geo, ko):
            return _forecast(ko)

    st = capture_weather(
        SlowProvider(), _events(10), tmp_path, as_of=AS_OF, time_budget_s=150, clock=clock
    )
    # attempts at t=0, 60, 120 run; at t=180 the budget is spent and the other 7 are skipped, not fetched
    assert st["captured"] == 3 and st["skipped"] == 7 and st["stopped"] == "time_budget"
    assert st["events"] == 10
    assert len((tmp_path / "2026-09-19.jsonl").read_text().splitlines()) == 3


def test_weather_consecutive_failures_stop_and_answers_reset_the_breaker(tmp_path):
    class Down:
        calls = 0

        def geocode(self, city, country):
            Down.calls += 1
            raise RuntimeError("fetch failed: timeout")

        def forecast_at(self, geo, ko):  # pragma: no cover - never reached
            raise AssertionError

    st = capture_weather(Down(), _events(8), tmp_path, as_of=AS_OF, max_consecutive_failures=3)
    assert Down.calls == 3 and len(st["failures"]) == 3
    assert st["stopped"] == "consecutive_failures" and st["skipped"] == 5

    class Flaky:
        n = 0

        def geocode(self, city, country):
            Flaky.n += 1
            if Flaky.n % 2:
                raise RuntimeError("fetch failed")
            return None  # answered (geocode miss) -> resets the breaker

        def forecast_at(self, geo, ko):  # pragma: no cover
            raise AssertionError

    st = capture_weather(Flaky(), _events(8), tmp_path, as_of=AS_OF, max_consecutive_failures=2)
    assert st["stopped"] is None and st["skipped"] == 0
    assert len(st["failures"]) == 4 and st["geocode_miss"] == 4


def test_weather_unbounded_by_default(tmp_path):
    class Ok:
        def geocode(self, city, country):
            return Geo(51.0, 0.0, city, country)

        def forecast_at(self, geo, ko):
            return _forecast(ko)

    st = capture_weather(Ok(), _events(4), tmp_path, as_of=AS_OF)
    assert st["captured"] == 4 and st["stopped"] is None and st["skipped"] == 0


# ---------------------------------------------------------------- espn-sync health


def _status(**over):
    base = {
        "events": 400,
        "scoreboard_queries": 748,
        "scoreboard_failures_n": 0,
        "scoreboard_failures": [],
        "lineups": {"events": 20, "failures": []},
        "weather": {"events": 30, "failures": [], "stopped": None, "skipped": 0},
        "unmapped_team_ids": {"1": "Some Club"},  # standing mapping backlog: never a health signal
    }
    base.update(over)
    return base


def test_espn_health_healthy():
    assert espn_sync_health(_status()) == {"state": "HEALTHY", "reasons": []}


@pytest.mark.parametrize(
    "over,reason",
    [
        (
            {"scoreboard_failures_n": 3, "scoreboard_failures": ["a", "b", "c"]},
            "scoreboard_partial_failures:3/748",
        ),
        ({"lineups": {"events": 20, "failures": ["x"]}}, "lineups_partial_failures:1/20"),
        ({"weather": {"failures": ["t"], "stopped": None}}, "weather_failures:1"),
        (
            {"weather": {"failures": [], "stopped": "time_budget", "skipped": 12}},
            "weather_stopped:time_budget:skipped=12",
        ),
        ({"weather": {"error": "boom"}}, "weather_error"),
        ({"events": 0, "lineups": {"events": 0, "failures": []}}, "no_events_returned"),
    ],
)
def test_espn_health_degraded(over, reason):
    h = espn_sync_health(_status(**over))
    assert h["state"] == "DEGRADED" and reason in h["reasons"]


def test_espn_health_failed_when_no_fixture_window_or_no_due_lineups():
    h = espn_sync_health(
        _status(
            events=0,
            scoreboard_failures_n=748,
            scoreboard_failures=["x"] * 50,
            lineups={"events": 0, "failures": []},
        )
    )
    assert h["state"] == "FAILED" and h["reasons"][0] == "scoreboard_all_failed:748/748"
    h = espn_sync_health(_status(lineups={"events": 3, "failures": ["a", "b", "c"]}))
    assert h == {"state": "FAILED", "reasons": ["lineups_all_failed:3/3"]}


def test_espn_sync_writes_health_and_never_raises_on_classified_failure(tmp_path, monkeypatch):
    """ESPN unreachable: the CLI still writes STATUS.json (health FAILED) and exits 0; the workflow's single
    health gate turns that red."""
    from soccer_edge import cli
    from soccer_edge.providers import espn

    def boom(self, leagues, start, days):
        return [], [
            f"{lg} {start + timedelta(days=i)}: fetch failed" for lg in leagues for i in range(days)
        ]

    monkeypatch.setattr(espn.EspnProvider, "fixtures_window", boom)
    args = cli.build_parser().parse_args(
        [
            "espn-sync",
            "--leagues",
            "eng.1,esp.1",
            "--back-days",
            "1",
            "--forward-days",
            "2",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert args.func(args) == 0
    st = json.loads((tmp_path / "STATUS.json").read_text())
    assert st["scoreboard_queries"] == 6 and st["scoreboard_failures_n"] == 6
    assert st["health"]["state"] == "FAILED"
    assert health_gate.evaluate(tmp_path / "STATUS.json") == (
        "FAILED",
        ["scoreboard_all_failed:6/6"],
        1,
    )


# ---------------------------------------------------------------- the health gate


def _write(p: Path, doc) -> Path:
    p.write_text(json.dumps(doc))
    return p


def test_health_gate_exit_codes(tmp_path):
    ev = health_gate.evaluate
    assert ev(_write(tmp_path / "h.json", {"health": {"state": "HEALTHY", "reasons": []}}))[2] == 0
    assert ev(_write(tmp_path / "n.json", {"health": {"state": "NOT_APPLICABLE"}}))[2] == 0
    assert ev(_write(tmp_path / "d.json", {"health": {"state": "DEGRADED", "reasons": ["w"]}})) == (
        "DEGRADED",
        ["w"],
        0,
    )
    assert ev(_write(tmp_path / "f.json", {"health": {"state": "FAILED", "reasons": ["x"]}})) == (
        "FAILED",
        ["x"],
        1,
    )
    # fail closed: no evidence is never green
    assert ev(tmp_path / "missing.json") == ("FAILED", ["status_missing"], 1)
    assert ev(_write(tmp_path / "nohealth.json", {"events": 3}))[2] == 1
    assert ev(_write(tmp_path / "bogus.json", {"health": {"state": "FINE"}}))[2] == 1
    (tmp_path / "bad.json").write_text("{not json")
    assert ev(tmp_path / "bad.json")[0] == "FAILED"
    # the upstream step already failed the job: record FAILED, do not add a second failing step
    assert ev(tmp_path / "missing.json", "failure") == ("FAILED", ["upstream_step_failure"], 0)


def test_health_gate_degraded_warns_and_summarises(tmp_path, monkeypatch, capsys):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    st = _write(
        tmp_path / "s.json", {"health": {"state": "DEGRADED", "reasons": ["weather_failures:2"]}}
    )
    assert health_gate.main([str(st), "--label", "espn-lineups"]) == 0
    assert "::warning::espn-lineups health DEGRADED: weather_failures:2" in capsys.readouterr().out
    assert "espn-lineups health: DEGRADED" in summary.read_text()
    st = _write(tmp_path / "f.json", {"health": {"state": "FAILED", "reasons": ["x"]}})
    assert health_gate.main([str(st), "--label", "espn-lineups"]) == 1
    assert "::error::" in capsys.readouterr().out


def test_espn_lineups_workflow_has_one_enforcement_point():
    wf = (ROOT / ".github" / "workflows" / "espn-lineups.yml").read_text()
    assert "id: sync" in wf and 'PYTHONUNBUFFERED: "1"' in wf
    gate = wf.split("- name: Health")[1]
    assert "if: always()" in gate and "scripts/health_gate.py work/espn/STATUS.json" in gate
    assert '--upstream-outcome "${{ steps.sync.outcome }}"' in gate
    assert "continue-on-error" not in wf
    assert wf.count("- name: Health") == 1 and wf.rstrip().endswith(gate.rstrip())


# ---------------------------------------------------------------- grow-only predictions index


def test_merge_index_union_archived_wins():
    merged, st = merge_json_index.merge_index(
        {"a": "d1/p.jsonl", "b": "d1/p.jsonl", "c": "d2/p.jsonl"},
        {"a": "d1/p.jsonl", "d": "d3/p.jsonl", "c": "dX/p.jsonl"},
    )
    assert merged == {"a": "d1/p.jsonl", "b": "d1/p.jsonl", "c": "d2/p.jsonl", "d": "d3/p.jsonl"}
    assert st == {"kept": 3, "added": 1, "conflicts": 1}


def test_merge_index_refuses_corrupt_input(tmp_path):
    dst = _write(tmp_path / "index.json", {"a": "x"})
    (tmp_path / "in.json").write_text("[1, 2")
    assert merge_json_index.main([str(dst), str(tmp_path / "in.json")]) == 2
    assert json.loads(dst.read_text()) == {"a": "x"}  # untouched
    _write(tmp_path / "list.json", ["a"])
    assert merge_json_index.main([str(dst), str(tmp_path / "list.json")]) == 2


def _pred_line(rid: str, run_id: str) -> str:
    from soccer_edge.archive.ledger import PredictionLedger
    from soccer_edge.core.serialization import canonical_json

    body = {"schema": "prediction_record_v1", "run_id": run_id, "ticker": rid}
    return canonical_json(
        {
            **body,
            "record_id": PredictionLedger.record_id(body),
            "archived_at": "2026-09-28T12:00:00Z",
        }
    )


def _git(cwd: Path, *a: str, env=None) -> str:
    return subprocess.run(
        ["git", *a], cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout


@pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None, reason="needs git + bash"
)
def test_archive_publish_keeps_index_entries_added_by_a_concurrent_writer(tmp_path):
    """Regression for kickoff-dispatch runs 36876149810 / 36983392414: a long link restored the index at
    start, run-soccer published new predictions + index mid-link, and the link's final publish replaced the
    index with its stale copy -> `index_missing_record` -> publish refused, batch data left unpublished."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GITHUB_TOKEN", "GITHUB_REPOSITORY", "ARCHIVE_BRANCH")
    }
    env.update(
        HOME=str(tmp_path / "home"),
        GIT_CONFIG_NOSYSTEM="1",
        PATH=os.pathsep.join([str(Path(sys.executable).parent), env.get("PATH", "")]),
    )
    (tmp_path / "home").mkdir()
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote), env=env)
    # seed data-archive: run A's predictions (indexed) + run B's, published "mid-link" by another writer
    seed = tmp_path / "seed"
    _git(tmp_path, "init", "-q", "-b", "data-archive", str(seed), env=env)
    day = seed / "predictions" / "2026-09-28"
    day.mkdir(parents=True)
    a, b = _pred_line("A", "run-a"), _pred_line("B", "run-b")
    (day / "predictions.jsonl").write_text(a + "\n" + b + "\n")
    rid = lambda line: json.loads(line)["record_id"]
    (seed / "predictions" / "index.json").write_text(
        json.dumps({rid(a): "2026-09-28/predictions.jsonl", rid(b): "2026-09-28/predictions.jsonl"})
    )
    for run in ("run-a", "run-b", "run-c"):
        rd = seed / "runs" / "2026-09-28" / run
        rd.mkdir(parents=True)
        (rd / "run_output.v1.json").write_text("{}")
    _git(seed, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A", env=env)
    _git(seed, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "seed", env=env)
    _git(seed, "push", "-q", str(remote), "data-archive", env=env)
    # the publisher's work dir: index restored BEFORE run B existed, plus its own new prediction C
    clone = tmp_path / "checkout"
    _git(tmp_path, "clone", "-q", str(remote), str(clone), env=env)
    work = tmp_path / "work"
    (work / "predictions" / "2026-09-28").mkdir(parents=True)
    c = _pred_line("C", "run-c")
    (work / "predictions" / "2026-09-28" / "predictions.jsonl").write_text(c + "\n")
    (work / "predictions" / "index.json").write_text(
        json.dumps({rid(a): "2026-09-28/predictions.jsonl", rid(c): "2026-09-28/predictions.jsonl"})
    )
    p = subprocess.run(
        ["bash", str(ROOT / "scripts" / "archive_publish.sh"), str(work), ".", "test publish"],
        cwd=clone,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    assert '"added": 1' in p.stdout and "archive: pushed to data-archive" in p.stdout
    out = tmp_path / "out"
    _git(tmp_path, "clone", "-q", "--branch", "data-archive", str(remote), str(out), env=env)
    idx = json.loads((out / "predictions" / "index.json").read_text())
    assert set(idx) == {rid(a), rid(b), rid(c)}  # run B's entry survived the stale publisher
    code, rep = verify_archive(out, require_manifest=False, today=date(2026, 10, 1))
    assert "index_missing_record" not in rep["problem_counts"]
    assert "index_dangling" not in rep["problem_counts"]
