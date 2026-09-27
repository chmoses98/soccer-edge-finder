"""Render the 'live catalog' Markdown section from data/catalog/latest_index.json (evidence, not prose)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    idx = json.loads((REPO / "data" / "catalog" / "latest_index.json").read_text())
    c = idx["counters"]
    lines = [
        f"Discovery `{idx['run_id']}` finished {idx['finished_at']} — complete: **{idx['complete']}** · "
        f"series in Kalshi: {c['series_total']} · soccer series swept: {c['series_swept']} · ambiguous unswept: {c.get('series_ambiguous_unswept', 0)} · "
        f"events: {idx['event_count']} · **contracts discovered: {c['contracts_discovered']}** · unknown-family: {c['contracts_unknown_family']} · "
        f"requests: {c['request_count']} (retries {c['retry_count']})",
        "",
        "Contracts by family:",
        "",
        "| family | contracts |",
        "|---|---|",
        *[
            f"| {k} | {v} |"
            for k, v in sorted(c["contracts_by_family"].items(), key=lambda kv: -kv[1])
        ],
        "",
        "Contracts by competition code:",
        "",
        "| code | contracts |",
        "|---|---|",
        *[
            f"| {k} | {v} |"
            for k, v in sorted(c["contracts_by_competition_code"].items(), key=lambda kv: -kv[1])
        ],
        "",
    ]
    if idx.get("unknown_body_histogram"):
        lines += [
            "Unknown ticker bodies (top 40) — the next taxonomy work items:",
            "",
            "| body | n | example ticker | example title |",
            "|---|---|---|---|",
        ]
        for body, rec in list(idx["unknown_body_histogram"].items())[:40]:
            lines.append(
                f"| {body} | {rec['n']} | `{rec['example_ticker']}` | {rec['example_title'].replace('|', '/')} |"
            )
        lines.append("")
    if idx.get("events_sanity"):
        lines += [
            "Events sanity: " + ", ".join(f"{k}={v}" for k, v in idx["events_sanity"].items()),
            "",
        ]
    if idx.get("market_status_histogram"):
        lines += [
            "Market status histogram: "
            + ", ".join(f"{k}={v}" for k, v in idx["market_status_histogram"].items()),
            "",
        ]
    if c.get("failures"):
        lines += ["Failures:", *[f"- {f}" for f in c["failures"][:20]], ""]
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
