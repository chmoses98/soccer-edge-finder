"""xG historical path (remediation phase 20; audit §J).

Tries, in order, the reproducible downloadable sources the audit identified, without violating any
source's terms:

1. FiveThirtyEight `spi_matches.csv` (CC-BY 4.0; project retired). The original endpoint and the
   Internet Archive's snapshots of it are tried; the first response whose header carries the `xg1/xg2`
   columns is hash-pinned and written to `data/cache/xg/spi_matches.csv`.
2. football-data.co.uk 2026-27 season CSVs (`HxG/AxG`), the prospective base (from 2026-27 only).

If (1) yields nothing, `xg_strength_v1` stays NOT_EVALUATED and the result file says so; nothing is
invented. If it yields the file, a normalised xG history (`data/research/xg_history_v1.csv.gz`) is built
and `xg_strength_v1` is evaluated chronologically (walk-forward, weekly refit) against `dc_laplace_v2`'s
goal-only likelihood on the same matches, per the audit's design (joint Poisson goals + quasi-Poisson xG
pseudo-likelihood, weight omega in {0.25, 0.5, 0.75} chosen on 2017-18..2020-21, holdout 2021-22..2022-23).

Understat, FBref/Opta and any scraped source are excluded (terms).
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

CANDIDATE_URLS = (
    "https://projects.fivethirtyeight.com/soccer-api/club/spi_matches.csv",
    "https://web.archive.org/web/2023id_/https://projects.fivethirtyeight.com/soccer-api/club/spi_matches.csv",
    "https://web.archive.org/web/2022id_/https://projects.fivethirtyeight.com/soccer-api/club/spi_matches.csv",
    "https://raw.githubusercontent.com/fivethirtyeight/data/master/soccer-spi/spi_matches.csv",
)
CACHE = REPO / "data" / "cache" / "xg"
OUT = REPO / "data" / "research" / "xg_history_v1.json"
LEAGUES_538 = {
    "Barclays Premier League": "E0",
    "Spanish Primera Division": "SP1",
    "German Bundesliga": "D1",
    "Italy Serie A": "I1",
    "French Ligue 1": "F1",
}


def fetch_candidates(timeout: int = 60) -> dict[str, Any]:
    CACHE.mkdir(parents=True, exist_ok=True)
    attempts = []
    for url in CANDIDATE_URLS:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "soccer-edge-finder/0.1 (research; +https://github.com/chmoses98/soccer-edge-finder)"
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
        except Exception as exc:
            attempts.append({"url": url, "ok": False, "error": str(exc)[:120]})
            continue
        head = data[:4096].decode("utf-8", errors="replace").splitlines()[0] if data else ""
        has_xg = "xg1" in head and "xg2" in head
        digest = hashlib.sha256(data).hexdigest()
        attempts.append(
            {
                "url": url,
                "ok": True,
                "bytes": len(data),
                "has_xg_columns": has_xg,
                "sha256": digest,
                "header": head[:300],
            }
        )
        if has_xg and len(data) > 1_000_000:
            (CACHE / "spi_matches.csv").write_bytes(data)
            (CACHE / "spi_matches.sha256").write_text(digest + "\n")
            return {
                "found": True,
                "url": url,
                "sha256": digest,
                "bytes": len(data),
                "attempts": attempts,
            }
    return {"found": False, "attempts": attempts}


def build_history(csv_path: Path) -> dict[str, Any]:
    rows = []
    with csv_path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("league") not in LEAGUES_538 or not r.get("xg1") or not r.get("score1"):
                continue
            try:
                rows.append(
                    {
                        "division": LEAGUES_538[r["league"]],
                        "date": r["date"],
                        "home": r["team1"],
                        "away": r["team2"],
                        "home_goals": int(float(r["score1"])),
                        "away_goals": int(float(r["score2"])),
                        "home_xg": float(r["xg1"]),
                        "away_xg": float(r["xg2"]),
                        "home_nsxg": float(r["nsxg1"]) if r.get("nsxg1") else None,
                        "away_nsxg": float(r["nsxg2"]) if r.get("nsxg2") else None,
                        "season": r.get("season"),
                    }
                )
            except (ValueError, KeyError):
                continue
    out = REPO / "data" / "research" / "xg_history_v1.csv.gz"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]) if rows else ["division"])
    w.writeheader()
    for r in rows:
        w.writerow(r)
    data = buf.getvalue().encode()
    with out.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as fh:
        fh.write(data)
    seasons = sorted({r["season"] for r in rows})
    per_div = {}
    for d in LEAGUES_538.values():
        rs = [r for r in rows if r["division"] == d]
        if rs:
            per_div[d] = {
                "n": len(rs),
                "mean_xg_per_match": sum(r["home_xg"] + r["away_xg"] for r in rs) / len(rs),
                "mean_goals_per_match": sum(r["home_goals"] + r["away_goals"] for r in rs)
                / len(rs),
            }
    return {
        "rows": len(rows),
        "seasons": seasons,
        "by_division": per_div,
        "file": str(out.relative_to(REPO)),
        "sha256_uncompressed": hashlib.sha256(data).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args(argv)
    result: dict[str, Any] = {
        "schema": "xg_history_result_v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "sources_excluded_by_terms": ["understat", "fbref/opta", "any scraped site"],
    }
    csv_path = CACHE / "spi_matches.csv"
    if a.fetch or not csv_path.exists():
        result["fetch"] = fetch_candidates()
    if csv_path.exists():
        result["history"] = build_history(csv_path)
        result["xg_strength_v1_status"] = "HISTORY_AVAILABLE_EVALUATION_PENDING"
        result["next"] = (
            "run research/xg_strength_eval.py (walk-forward omega grid 2017-18..2020-21, holdout 2021-22..2022-23)"
        )
    else:
        result["history"] = None
        result["xg_strength_v1_status"] = "NOT_EVALUATED"
        result["reason"] = (
            "no licence-clean reproducible historical xG source reachable; prospective accumulation from football-data.co.uk 2026-27 HxG/AxG continues (docs/XG_DATA_AUDIT.md)"
        )
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("xg_strength_v1_status",) if k in result}, indent=1))
    if result.get("fetch"):
        for at in result["fetch"]["attempts"]:
            print(
                " ",
                at.get("url"),
                "ok" if at.get("ok") else "FAIL",
                at.get("has_xg_columns"),
                at.get("bytes"),
                at.get("error", ""),
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
