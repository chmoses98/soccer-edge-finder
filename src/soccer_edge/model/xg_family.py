"""data_only.xg_strength_v1 — RESEARCH_ONLY, NOT_EVALUATED (Phase 11).

Same Dixon-Coles machinery as the benchmark, but each match's intensity target is a blend of expected goals and
goals where xG is available: target = w * xG + (1 - w) * goals, with w = XG_WEIGHT; matches without xG use goals
(w = 0). Poisson log-likelihood is evaluated at the (possibly non-integer) target; the Dixon-Coles low-score
correction applies only to exact 0/1 counts, i.e. to goal-only rows.

Why it is not evaluated: free xG exists only for 2026-27 onward (docs/XG_DATA_AUDIT.md). The frozen walk-forward
benchmark (docs/RESEARCH_RESULTS.md) spans 2018-19 → 2025-26, so no like-for-like comparison is possible yet. The
family is registered so that its parameters can be archived prospectively; it is never priced in production.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from soccer_edge.model.strength import (
    DixonColesFitter,
    MatchRow,
    ParameterPosterior,
    StrengthConfig,
)
from soccer_edge.providers.interfaces import MatchResult

FAMILY_ID = "data_only.xg_strength_v1"
XG_WEIGHT = 0.7
EVIDENCE = "NOT_EVALUATED: no historical xG for the benchmark window; prospective only"


@dataclass(frozen=True)
class XgFitReport:
    family: FAMILY_ID.__class__ = FAMILY_ID
    rows_total: int = 0
    rows_with_xg: int = 0
    xg_weight: float = XG_WEIGHT
    evidence: str = EVIDENCE


def rows_from_results_xg(
    results: list[MatchResult], *, weight: float = XG_WEIGHT
) -> tuple[list[MatchRow], int]:
    rows: list[MatchRow] = []
    n_xg = 0
    for r in results:
        if r.home_xg is not None and r.away_xg is not None:
            n_xg += 1
            h = weight * r.home_xg + (1 - weight) * r.home_goals
            a = weight * r.away_xg + (1 - weight) * r.away_goals
        else:
            h, a = float(r.home_goals), float(r.away_goals)
        rows.append(
            MatchRow(date.fromisoformat(r.match_date), r.home_team_id, r.away_team_id, h, a)
        )  # type: ignore[arg-type]
    return rows, n_xg


def fit_xg_family(
    results: list[MatchResult],
    *,
    as_of: date,
    config: StrengthConfig | None = None,
    weight: float = XG_WEIGHT,
) -> tuple[ParameterPosterior, XgFitReport]:
    rows, n_xg = rows_from_results_xg(results, weight=weight)
    post = DixonColesFitter(config).fit(rows, as_of=as_of)
    return post, XgFitReport(rows_total=len(rows), rows_with_xg=n_xg, xg_weight=weight)
