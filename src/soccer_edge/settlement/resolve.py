"""Universal, refusal-first result resolution for archived predictions (audit B4, remediation phase 4).

Every priced prediction record ends in exactly one explicit settlement state:

    SETTLED                 an official result settled the contract (yes / no / void)
    PENDING_KICKOFF         kickoff + grace is still in the future
    PENDING_RESULT          the fixture's competition has a result source, no result has arrived yet
    PENDING_MAPPING         results exist but none can be tied unambiguously to this fixture
    PENDING_EVIDENCE        a result exists but is insufficient for the contract semantics (no half-time
                            split, unknown extra-time status, unknown first scorer, conflicting sources,
                            abandoned/postponed pending reschedule, incomplete semantics on the record)
    UNSUPPORTED_SETTLEMENT  the settlement engine has no rule for the family (player data, futures)
    UNSETTLEABLE            no result source exists for the competition at all

`unaccounted_settlement_records` is zero by construction: every record gets a state.

Result sources are merged, never guessed. A fixture is matched by exact `fixture_id` first, then by
(competition, home team, away team, kickoff date ±1 day). Two candidates → PENDING_MAPPING. Two sources
that disagree on the final score → PENDING_EVIDENCE (conflict). Openfootball reports regulation scores;
ESPN reports the score as displayed (including extra time when played), so a regulation-period contract
needs either a derived regulation split or a full-time status token unless the competition format cannot
have extra time.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any

from soccer_edge.identity.models import CompetitionFormat, FixtureStatus
from soccer_edge.kalshi.taxonomy import MarketFamily
from soccer_edge.pricing.semantics import Semantics
from soccer_edge.providers.interfaces import MatchResult
from soccer_edge.settlement.engine import OfficialResult, SettlementOutcome


class SettlementState(str, Enum):
    SETTLED = "SETTLED"
    PENDING_KICKOFF = "PENDING_KICKOFF"
    PENDING_RESULT = "PENDING_RESULT"
    PENDING_MAPPING = "PENDING_MAPPING"
    PENDING_EVIDENCE = "PENDING_EVIDENCE"
    UNSUPPORTED_SETTLEMENT = "UNSUPPORTED_SETTLEMENT"
    UNSETTLEABLE = "UNSETTLEABLE"


# competitions whose format cannot produce extra time in any match (regular-season leagues, friendlies,
# group phases are handled through the registry format below)
_NO_ET_FORMATS = {CompetitionFormat.LEAGUE, CompetitionFormat.FRIENDLY}

# status tokens (ESPN) that end a match in regulation
_FULL_TIME_TOKENS = {"STATUS_FULL_TIME", "STATUS_FINAL", "FT"}
_NOT_PLAYED_TOKENS = {
    "STATUS_POSTPONED": FixtureStatus.POSTPONED,
    "STATUS_CANCELED": FixtureStatus.CANCELLED,
    "STATUS_CANCELLED": FixtureStatus.CANCELLED,
    "STATUS_ABANDONED": FixtureStatus.ABANDONED,
    "STATUS_SUSPENDED": FixtureStatus.ABANDONED,
}


def parse_fixture_id(fid: str) -> tuple[str, str, str, str] | None:
    """fx:<comp>:<season>:<home>:<away>[:stage...] → (comp, season, home, away)."""
    parts = fid.split(":")
    if len(parts) < 5 or parts[0] != "fx":
        return None
    return parts[1], parts[2], parts[3], parts[4]


@dataclass
class Resolution:
    state: SettlementState
    reason: str
    result: MatchResult | None = None
    sources: list[str] = field(default_factory=list)
    candidates: int = 0


@dataclass
class ResultIndex:
    """Merged results from every source, keyed for exact and fuzzy fixture matching."""

    by_fixture_id: dict[str, list[MatchResult]] = field(default_factory=lambda: defaultdict(list))
    by_teams: dict[tuple[str, str, str], list[MatchResult]] = field(
        default_factory=lambda: defaultdict(list)
    )
    competitions_with_source: set[str] = field(default_factory=set)

    def add(self, r: MatchResult, *, source: str) -> None:
        r = r if r.result_source else r.model_copy(update={"result_source": source})
        self.by_fixture_id[r.fixture_id].append(r)
        self.by_teams[(r.competition_id, r.home_team_id, r.away_team_id)].append(r)
        self.competitions_with_source.add(r.competition_id)

    def resolve(self, fixture_id: str, kickoff: datetime, *, competition_id: str) -> Resolution:
        cands = list(self.by_fixture_id.get(fixture_id, []))
        parsed = parse_fixture_id(fixture_id)
        if not cands and parsed is not None:
            comp, _season, home, away = parsed
            ko_date = kickoff.date()
            for r in self.by_teams.get((comp, home, away), []):
                try:
                    d = date.fromisoformat(r.match_date)
                except ValueError:
                    continue
                if abs((d - ko_date).days) <= 1:
                    cands.append(r)
        if not cands:
            if competition_id not in self.competitions_with_source:
                return Resolution(SettlementState.UNSETTLEABLE, "no result source for competition")
            return Resolution(SettlementState.PENDING_RESULT, "no result reported yet")
        return _merge_candidates(cands)


def _merge_candidates(cands: list[MatchResult]) -> Resolution:
    """One result per (source, event); several sources may describe the same match."""
    # de-duplicate per source: same source with two different matches on the key is ambiguous
    per_source: dict[str, list[MatchResult]] = defaultdict(list)
    for r in cands:
        per_source[r.result_source or "unknown"].append(r)
    for src, rs in per_source.items():
        distinct = {(r.fixture_id, r.match_date, r.home_goals, r.away_goals) for r in rs}
        if len(distinct) > 1:
            return Resolution(
                SettlementState.PENDING_MAPPING,
                f"{len(distinct)} candidate results from {src}",
                sources=sorted(per_source),
                candidates=len(cands),
            )
    firsts = [rs[0] for rs in per_source.values()]
    scores = {(r.home_goals, r.away_goals) for r in firsts}
    if len(scores) > 1:
        return Resolution(
            SettlementState.PENDING_EVIDENCE,
            "sources disagree on the final score",
            sources=sorted(per_source),
            candidates=len(cands),
        )
    # prefer the richest evidence (regulation split known, then half-time known)
    best = max(
        firsts,
        key=lambda r: (
            r.home_goals_regulation is not None,
            r.home_goals_ht is not None,
            r.status_name is not None,
        ),
    )
    return Resolution(SettlementState.SETTLED, "result found", best, sorted(per_source), len(cands))


def et_possible(
    competition_format: CompetitionFormat | None, extra_time_in_knockouts: bool | None
) -> bool:
    if competition_format in _NO_ET_FORMATS:
        return False
    return extra_time_in_knockouts is not False


def official_from_result(
    r: MatchResult, *, et_possible_in_competition: bool
) -> tuple[OfficialResult | None, str | None]:
    """(OfficialResult, None) when the result carries enough evidence for a regulation-period
    settlement, else (None, reason). Extra-time and penalty fields are passed through for the
    INCLUDING_ET / INCLUDING_PENS periods; the engine refuses those when the data is absent."""
    status_token = r.status_name or ""
    if status_token in _NOT_PLAYED_TOKENS:
        return (
            OfficialResult(
                r.fixture_id,
                _NOT_PLAYED_TOKENS[status_token],
                None,
                None,
                source=r.result_source or "",
            ),
            None,
        )
    if r.home_goals_regulation is not None and r.away_goals_regulation is not None:
        h, a = r.home_goals_regulation, r.away_goals_regulation
    elif (
        status_token in _FULL_TIME_TOKENS
        or not et_possible_in_competition
        or r.result_source == "openfootball"
    ):
        # full-time token, a format without extra time, or a source that reports 90' scores
        if r.extra_time_played and (r.home_goals_et is None or r.away_goals_et is None):
            return None, "extra time played but the regulation split is unknown"
        h, a = r.home_goals, r.away_goals
    else:
        return None, "extra-time status unknown for a competition where extra time is possible"
    winner_after_pens = r.winner_after_penalties
    if r.decided_on_penalties and winner_after_pens is None:
        winner_after_pens = None  # engine refuses INCLUDING_PENS contracts without a winner
    return (
        OfficialResult(
            r.fixture_id,
            FixtureStatus.FINISHED,
            h,
            a,
            r.home_goals_ht,
            r.away_goals_ht,
            r.home_goals_et,
            r.away_goals_et,
            winner_after_pens,
            r.first_scorer_team,
            None,
            source=r.result_source or "",
        ),
        None,
    )


_EXACT_DESC_RE = re.compile(r"^Exact score (\d+)-(\d+) \(home-away\)$")


def derive_exact_score_k(ticker: str, description: str) -> int | None:
    """Legacy prediction records (before 2026-09-28) did not store `k` for exact-score contracts. The
    record's `description` is text this system generated from the resolved semantics
    ("Exact score H-A (home-away)"), so it is a faithful record of what was priced; it is accepted only
    when it matches that exact format and, when the ticker suffix carries a digit pair, agrees with it."""
    m = _EXACT_DESC_RE.match(description or "")
    if m is None:
        return None
    h, a = int(m.group(1)), int(m.group(2))
    suffix = ticker.rsplit("-", 1)[-1]
    digits = re.findall(r"\d+", suffix)
    if len(digits) == 2 and (int(digits[0]), int(digits[1])) != (h, a):
        return None
    return h * 100 + a


def semantics_complete(sem: Semantics) -> str | None:
    """Reason the record's semantics cannot be settled, or None."""
    if (
        sem.family in (MarketFamily.EXACT_SCORE, MarketFamily.FIRST_HALF_EXACT_SCORE)
        and sem.k is None
    ):
        return "exact-score record has no k and none could be derived; settlement would guess 0-0"
    return None


_REFUSAL_TO_STATE = {
    SettlementOutcome.REFUSED_NO_RESULT: (
        SettlementState.PENDING_EVIDENCE,
        "result has no final score",
    ),
    SettlementOutcome.REFUSED_ABANDONED: (
        SettlementState.PENDING_EVIDENCE,
        "abandoned/postponed/cancelled; void or reschedule per contract rules not yet evidenced",
    ),
    SettlementOutcome.REFUSED_MISSING_PERIOD_DATA: (
        SettlementState.PENDING_EVIDENCE,
        "period data missing (half-time split, extra time, penalties or first scorer)",
    ),
    SettlementOutcome.REFUSED_UNSUPPORTED: (
        SettlementState.UNSUPPORTED_SETTLEMENT,
        "family not supported",
    ),
    SettlementOutcome.REFUSED_PLAYER_DATA: (
        SettlementState.UNSUPPORTED_SETTLEMENT,
        "player data unavailable",
    ),
}


def state_for_outcome(outcome: SettlementOutcome) -> tuple[SettlementState, str]:
    if outcome in (SettlementOutcome.YES, SettlementOutcome.NO, SettlementOutcome.VOID):
        return SettlementState.SETTLED, outcome.value
    return _REFUSAL_TO_STATE[outcome]


class CoverageRows(list):
    """A list of CoverageRow that can also carry aggregate close-capture completeness."""

    close_completeness: dict[str, Any] | None = None


@dataclass
class CoverageRow:
    prediction_record_id: str
    fixture_id: str
    competition_id: str
    family: str
    period: str | None
    kickoff_utc: str
    state: SettlementState
    reason: str
    sources: list[str] = field(default_factory=list)
    outcome: str | None = None


def coverage_report(
    rows: list[CoverageRow], *, as_of: datetime, grace: timedelta
) -> dict[str, Any]:
    counts = {s.value: 0 for s in SettlementState}
    by_comp: dict[str, dict[str, int]] = defaultdict(lambda: {s.value: 0 for s in SettlementState})
    by_family: dict[str, dict[str, int]] = defaultdict(
        lambda: {s.value: 0 for s in SettlementState}
    )
    reasons: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r.state.value] += 1
        by_comp[r.competition_id][r.state.value] += 1
        by_family[r.family][r.state.value] += 1
        if r.state is not SettlementState.SETTLED:
            reasons[f"{r.state.value}: {r.reason}"] += 1
    total = len(rows)
    due = total - counts[SettlementState.PENDING_KICKOFF.value]
    settled = counts[SettlementState.SETTLED.value]
    accounted = sum(counts.values())
    return {
        "schema": "settlement_coverage_v1",
        "close_completeness": getattr(rows, "close_completeness", None),
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "grace_hours": grace.total_seconds() / 3600,
        "predictions_total": total,
        "settleable_now": due,
        "settled": settled,
        "pending_kickoff": counts[SettlementState.PENDING_KICKOFF.value],
        "pending_result": counts[SettlementState.PENDING_RESULT.value],
        "pending_mapping": counts[SettlementState.PENDING_MAPPING.value],
        "pending_evidence": counts[SettlementState.PENDING_EVIDENCE.value],
        "unsupported_settlement": counts[SettlementState.UNSUPPORTED_SETTLEMENT.value],
        "unsettleable": counts[SettlementState.UNSETTLEABLE.value],
        "unaccounted_settlement_records": total - accounted,
        "settled_share_of_due": (settled / due) if due else None,
        "by_competition": {k: v for k, v in sorted(by_comp.items())},
        "by_family": {k: v for k, v in sorted(by_family.items())},
        "reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
        "pending_examples": [
            {
                "prediction_record_id": r.prediction_record_id,
                "fixture_id": r.fixture_id,
                "state": r.state.value,
                "reason": r.reason,
            }
            for r in rows
            if r.state not in (SettlementState.SETTLED, SettlementState.PENDING_KICKOFF)
        ][:50],
    }
