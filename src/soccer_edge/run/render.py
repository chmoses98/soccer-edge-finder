"""Human-readable RUN SOCCER report. Markdown is for humans; the app consumes the JSON."""

from __future__ import annotations

from typing import Any

from soccer_edge.contracts.v1 import RecommendationV1, RunOutputV1
from soccer_edge.core.time import iso_utc
from soccer_edge.pricing.expression import ExpressionResult


def _rec_block(r: RecommendationV1) -> str:
    lines = [
        f"### {r.event_name} — {r.market_description} ({r.side.upper()})",
        f"- League: {r.league} · Kickoff: {iso_utc(r.start_time)} · Ticker: `{r.market_ticker}`",
        f"- Executable price: {r.current_price} · Fair: {r.fair_probability:.1%} ({r.fair_probability_low:.1%}–{r.fair_probability_high:.1%}) · Fee-adj edge: {r.fee_adjusted_edge:+.1%} · Worst-case: {r.worst_case_edge:+.1%} · P(edge>0): {r.probability_edge_positive:.0%}",
        f"- Bet-up-to: {r.bet_up_to_price} · Size: {r.available_size} · Authority: **{r.authority}** · Lineups: {r.lineup_status} · Coverage: {r.coverage_status}",
        f"- Model: {r.model_family}@{r.model_version} · data as of {iso_utc(r.data_as_of)} · market as of {iso_utc(r.market_as_of)}",
        f"- Thesis: {r.thesis}",
        f"- Risks: {'; '.join(r.risks)}",
        f"- Correlation group: `{r.correlation_group}`",
    ]
    return "\n".join(lines)


def render_markdown(
    out: RunOutputV1, reduced: ExpressionResult, fixture_summaries: dict[str, dict[str, Any]]
) -> str:
    c = out.coverage
    parts = [
        f"# RUN SOCCER — {out.run_date}",
        f"Run `{out.run_id}` generated {iso_utc(out.generated_at)} · filters: {out.filters}",
        "",
        "## Coverage",
        f"- contracts discovered: **{c.contracts_discovered}** (discovery complete: {c.discovery_complete})",
        f"- contracts evaluated: {c.contracts_evaluated} · excluded mechanically: {c.contracts_excluded_mechanically} · unsupported/unknown: {c.contracts_unsupported}",
        f"- **unaccounted contracts: {c.unaccounted_contracts}**",
        "- by disposition: " + ", ".join(f"{k}={v}" for k, v in c.by_disposition.items() if v),
        "- competitions discovered: " + ", ".join(c.competitions_discovered),
        "",
        "## Freshness",
        "- " + "; ".join(f"{k}: {v}" for k, v in out.freshness.items() if k != "violations"),
        ("- violations: " + "; ".join(out.freshness.get("violations", [])))
        if out.freshness.get("violations")
        else "- no freshness violations",
        "",
    ]
    if out.warnings:
        parts += ["## Warnings", *[f"- {w}" for w in out.warnings], ""]
    parts.append("## Recommendations")
    if out.no_bets:
        parts.append(
            "**NO BETS** — no contract met the robust-edge bar under an authority level that permits recommendations."
        )
    else:
        parts.extend(_rec_block(r) for r in out.recommendations)
    parts.append("")
    parts.append(f"## Shadow / research-only expressions ({len(out.shadow_recommendations)})")
    parts.append(
        "These pass the robust-edge bar but their model family is RESEARCH_ONLY or SHADOW. They are NOT recommendations."
    )
    for r in out.shadow_recommendations[:40]:
        parts.append(
            f"- {r.event_name} · {r.market_description} · {r.side.upper()} @ {r.current_price} · fair {r.fair_probability:.1%} [{r.fair_probability_low:.1%}–{r.fair_probability_high:.1%}] · edge {r.fee_adjusted_edge:+.1%} · P(+) {r.probability_edge_positive:.0%} · {r.authority} · `{r.market_ticker}`"
        )
    if reduced.removed:
        parts.append("")
        parts.append(f"## Expressions removed by the reducer ({len(reduced.removed)})")
        for cand, reason in reduced.removed[:40]:
            parts.append(f"- `{cand.assessment.ticker}` {cand.assessment.side}: {reason}")
    parts.append("")
    parts.append("## Events")
    for e in out.events:
        s = fixture_summaries.get(e.event_id, {})
        line = f"- {e.event_name} ({e.league}) {iso_utc(e.start_time)} · markets {e.markets_evaluated}/{e.markets_discovered} evaluated · lineups {e.lineup_status}"
        if s:
            line += f" · xG {s.get('mean_home_goals', 0):.2f}-{s.get('mean_away_goals', 0):.2f} · 1X2 {s.get('p_home', 0):.0%}/{s.get('p_draw', 0):.0%}/{s.get('p_away', 0):.0%}"
        parts.append(line)
    parts.append("")
    return "\n".join(parts)
