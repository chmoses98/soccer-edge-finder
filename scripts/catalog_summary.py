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
    unknown = [s for s in cat["specs"] if s["family"] == "unknown"]
    # Learn the live grammar: histogram of ticker bodies (text between 'KX' and the first '-') for
    # unknown-family contracts, with an example ticker/title/rules snippet each.
    import re

    markets_by_ticker = {m["ticker"]: m for m in cat["markets"]}
    body_hist: dict[str, dict] = {}
    for u in unknown:
        mm = re.match(r"^KX([A-Z0-9]+)-", u["ticker"])
        body = mm.group(1) if mm else "?"
        rec = body_hist.setdefault(
            body,
            {
                "n": 0,
                "example_ticker": u["ticker"],
                "example_title": "",
                "example_yes_sub_title": "",
                "rules_primary": "",
            },
        )
        rec["n"] += 1
        if not rec["example_title"]:
            m = markets_by_ticker.get(u["ticker"], {})
            rec["example_title"] = (m.get("title") or "")[:140]
            rec["example_yes_sub_title"] = (m.get("yes_sub_title") or "")[:100]
            rec["rules_primary"] = (m.get("rules_primary") or "")[:400]
    body_hist = dict(sorted(body_hist.items(), key=lambda kv: -kv[1]["n"]))
    # one rules sample per KNOWN family token so semantics can be verified against Kalshi's text
    family_rules: dict[str, dict] = {}
    for sp in cat["specs"]:
        if sp["family"] == "unknown":
            continue
        key = sp["family"]
        if key in family_rules:
            continue
        m = markets_by_ticker.get(sp["ticker"], {})
        family_rules[key] = {
            "ticker": sp["ticker"],
            "title": (m.get("title") or "")[:140],
            "yes_sub_title": (m.get("yes_sub_title") or "")[:100],
            "floor_strike": m.get("floor_strike"),
            "rules_primary": (m.get("rules_primary") or "")[:500],
            "status": m.get("status"),
        }
    # sanity: did /events?series_ticker= honour the filter?
    swept = {s["ticker"] for s in cat["series"] if s.get("swept", True)}
    ev_total = len(cat["events"])
    ev_mismatch = sum(
        1
        for e in cat["events"]
        if (e.get("series_ticker") or e.get("event_ticker", "").split("-")[0]) not in swept
    )
    market_event_tickers = {m.get("event_ticker") for m in cat["markets"]}
    ev_for_markets = sum(1 for e in cat["events"] if e.get("event_ticker") in market_event_tickers)
    ev_missing = len(
        [t for t in market_event_tickers if t not in {e.get("event_ticker") for e in cat["events"]}]
    )
    status_hist: dict[str, int] = {}
    for m in cat["markets"]:
        status_hist[m.get("status", "?")] = status_hist.get(m.get("status", "?"), 0) + 1
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
        "unknown_examples": [
            {"ticker": u["ticker"], "rationale": u["rationale"]} for u in unknown[:50]
        ],
        "unknown_body_histogram": body_hist,
        "family_rules_samples": family_rules,
        "events_sanity": {
            "events_total": ev_total,
            "events_not_in_swept_series": ev_mismatch,
            "events_matching_a_market_event": ev_for_markets,
            "market_event_tickers": len(market_event_tickers),
            "market_event_tickers_without_event_row": ev_missing,
        },
        "market_status_histogram": status_hist,
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
