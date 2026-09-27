"""Compact, committable summary of a discovery catalog (never the raw markets)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("catalog")
    ap.add_argument("--out", required=True)
    ap.add_argument("--md", required=True)
    a = ap.parse_args()
    path = Path(a.catalog)
    if not path.exists():
        Path(a.md).parent.mkdir(parents=True, exist_ok=True)
        Path(a.md).write_text("# Discovery\n\nno catalog produced\n")
        print("no catalog produced")
        return 0
    cat = json.loads(path.read_text())
    counters = cat["counters"]
    fam_by_comp: dict[str, Counter] = {}
    examples: dict[str, str] = {}
    for s in cat["specs"]:
        fam_by_comp.setdefault(s["competition_code"] or "?", Counter())[s["family"]] += 1
        examples.setdefault(f"{s['competition_code']}|{s['family']}", s["ticker"])
    unknown = [s for s in cat["specs"] if s["family"] == "unknown"][:50]
    index = {
        "run_id": cat["run_id"],
        "finished_at": cat["finished_at"],
        "complete": cat["complete"],
        "counters": {k: v for k, v in counters.items() if k != "failures"},
        "failures": counters.get("failures", [])[:20],
        "series": [
            {
                k: s[k]
                for k in (
                    "ticker",
                    "title",
                    "tags",
                    "fee_type",
                    "fee_multiplier",
                    "ownership",
                    "ownership_reason",
                )
            }
            for s in cat["series"]
        ],
        "families_by_competition": {c: dict(v) for c, v in sorted(fam_by_comp.items())},
        "example_tickers": examples,
        "unknown_examples": [{"ticker": u["ticker"], "rationale": u["rationale"]} for u in unknown],
        "event_count": len(cat["events"]),
        "market_count": len(cat["markets"]),
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(index, indent=1, sort_keys=True) + "\n")
    lines = [
        f"# Kalshi soccer discovery {cat['run_id']}",
        "",
        f"complete: **{cat['complete']}** · series total {counters['series_total']} · soccer-owned series {counters['series_swept']} · events {len(cat['events'])} · contracts {len(cat['markets'])} · unknown-family {counters['contracts_unknown_family']}",
        "",
    ]
    lines.append(
        "| competition | " + " | ".join(sorted({f for c in fam_by_comp.values() for f in c})) + " |"
    )
    fams = sorted({f for c in fam_by_comp.values() for f in c})
    lines.append("|---|" + "---|" * len(fams))
    for c, v in sorted(fam_by_comp.items()):
        lines.append(f"| {c} | " + " | ".join(str(v.get(f, 0)) for f in fams) + " |")
    if counters.get("failures"):
        lines += ["", "## failures", *[f"- {f}" for f in counters["failures"][:20]]]
    Path(a.md).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
