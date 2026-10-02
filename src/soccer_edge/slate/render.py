"""Human summary of the actionable slate (LATEST_ACTIONABLE_SLATE.md). The JSON is the contract."""

from __future__ import annotations

from soccer_edge.contracts.slate_v1 import ActionableSlateV1
from soccer_edge.core.time import iso_utc


def _t(d) -> str:
    return iso_utc(d) if d else "-"


def render_slate_markdown(s: ActionableSlateV1, *, max_rows: int = 40) -> str:
    k = s.kalshi
    lines = [
        "# ACTIONABLE SOCCER SLATE (latest state, not evidence)",
        "",
        f"slate `{s.slate_id}` · generated {_t(s.generated_at)} · trigger `{s.compute.trigger}` · "
        f"mode `{s.compute.mode}`",
        "",
        f"**Kalshi prices observed {_t(k.observed_at)} ({k.status} at publish; CURRENT until "
        f"{_t(k.current_until)}, STALE after {_t(k.stale_after)}).** After that instant every price "
        "below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.",
        "",
        f"model board generated {_t(s.model_board_generated_at)} · simulations this update: "
        f"{s.compute.simulations_run} · Odds API calls this update: {s.compute.odds_api_calls} "
        f"(credits {s.compute.odds_api_credits}) · reprice {s.compute.reprice_runtime_s:.2f}s",
        "",
        f"**{'NO BETS' if s.no_bets else 'BETS PERMITTED'}** — {s.authority_summary}",
        "",
        "## Fixtures",
        "",
        "| kickoff | fixture | model | lineup | reference | context | priced | no model |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in s.fixtures:
        model = f.model.validity
        if f.model.validity == "VALID":
            model += f" ({f.model.freshness.status})"
        elif f.model.invalidation_reasons:
            model += f": {f.model.invalidation_reasons[0][:60]}"
        lines.append(
            f"| {_t(f.kickoff)} | {f.event_name} ({f.competition}) | {model} | "
            f"{f.lineup.status} ({f.lineup.freshness.status}) | {f.reference.freshness.status}"
            f"{' ' + f.reference.role if f.reference.role else ''} | {f.context.status} | "
            f"{f.contracts_priced} | {f.contracts_without_model} |"
        )
    cands = [c for c in s.contracts if c.action in ("ACTIONABLE", "RESEARCH_CANDIDATE")]
    cands.sort(key=lambda c: -(c.worst_case_edge or 0))
    lines += [
        "",
        f"## Candidates on CURRENT prices ({len(cands)}; RESEARCH_ONLY = analysis, never a bet)",
        "",
        "| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in cands[:max_rows]:
        lines.append(
            f"| {c.event_name} | {c.market_description} | {c.side} | {c.kalshi_price} | "
            f"{c.model_probability:.3f} [{c.model_probability_low:.3f}, {c.model_probability_high:.3f}] | "
            f"{(c.fee_adjusted_ev or 0):+.3f} | {(c.worst_case_edge or 0):+.3f} | {c.bet_up_to_price} | "
            f"{'-' if c.reference_probability is None else f'{c.reference_probability:.3f}'} | "
            f"{'*' if c.best_expression else ''} | {c.action} |"
        )
    lines += [
        "",
        "## Counts",
        "",
        "```",
        *(f"{k}: {v}" for k, v in sorted(s.counts.items())),
        "```",
    ]
    if s.removed_started:
        lines += ["", f"Removed (kicked off): {len(s.removed_started)}"]
    for w in s.warnings:
        lines.append(f"\nWARNING: {w}")
    lines += ["", s.consumer_rule, ""]
    return "\n".join(lines)
