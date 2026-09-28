"""Close capture and classification, source x timing (remediation phase 8; audit §K).

    class            definition
    TRUE_CLOSE       REFERENCE quote captured in [KO - 15 min, KO)
    NEAR_CLOSE       REFERENCE quote captured in [KO - 120 min, KO - 15 min)
    KALSHI_CLOSE     last VALID two-sided Kalshi book captured in [KO - 30 min, KO)
    STALE            an observation exists but is older than its window
    NONE             no pre-kickoff observation

A valid Kalshi book: status active/open, 0 < yes_bid <= yes_ask < 1, spread <= 10 cents. A suspended
market, an empty side (bid 0 / ask 1) or a one-sided book is never a close observation; the search steps
back to the previous valid snapshot inside the window, else NONE.

Everything is side-aware (`p_side` for NO is 1 - p_yes; Kalshi NO executable is 1 - yes_bid), timestamped,
tied to the exact contract/fixture and de-vigged by the method recorded on the reference row.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any

from soccer_edge.core.time import iso_utc, parse_iso_utc
from soccer_edge.reference.quality import SourceQuality, quality_for_bookmaker

TRUE_CLOSE_MAX_MINUTES = 15
NEAR_CLOSE_MAX_MINUTES = 120
KALSHI_CLOSE_MAX_MINUTES = 30
KALSHI_MAX_SPREAD = Decimal("0.10")
_VALID_STATUSES = {"active", "open"}


class CloseClassV2(str, Enum):
    TRUE_CLOSE = "TRUE_CLOSE"
    NEAR_CLOSE = "NEAR_CLOSE"
    KALSHI_CLOSE = "KALSHI_CLOSE"
    STALE = "STALE"
    NONE = "NONE"


def classify_reference_close(minutes_before_kickoff: float | None) -> CloseClassV2:
    if minutes_before_kickoff is None or minutes_before_kickoff < 0:
        return CloseClassV2.NONE
    if minutes_before_kickoff <= TRUE_CLOSE_MAX_MINUTES:
        return CloseClassV2.TRUE_CLOSE
    if minutes_before_kickoff <= NEAR_CLOSE_MAX_MINUTES:
        return CloseClassV2.NEAR_CLOSE
    return CloseClassV2.STALE


def classify_kalshi_close(minutes_before_kickoff: float | None, *, valid: bool) -> CloseClassV2:
    if minutes_before_kickoff is None or minutes_before_kickoff < 0 or not valid:
        return CloseClassV2.NONE
    if minutes_before_kickoff <= KALSHI_CLOSE_MAX_MINUTES:
        return CloseClassV2.KALSHI_CLOSE
    return CloseClassV2.STALE


def _dec(v: Any) -> Decimal | None:
    if v is None or v in ("None", ""):
        return None
    try:
        return Decimal(str(v))
    except (ValueError, ArithmeticError):
        return None


def book_is_valid(status: str | None, yes_bid: Any, yes_ask: Any) -> tuple[bool, str]:
    """(valid, reason) for a Kalshi book: two-sided, non-sentinel, tight, not suspended."""
    if status is not None and status not in _VALID_STATUSES:
        return False, f"status {status}"
    b, a = _dec(yes_bid), _dec(yes_ask)
    if b is None or a is None:
        return False, "one-sided or empty book"
    if not (Decimal(0) < b <= a < Decimal(1)):
        return False, "sentinel or crossed book (bid 0 / ask 1)"
    if a - b > KALSHI_MAX_SPREAD:
        return False, f"spread {a - b} > {KALSHI_MAX_SPREAD}"
    return True, "ok"


@dataclass(frozen=True)
class KalshiClose:
    close_class: CloseClassV2
    captured_at: datetime | None
    minutes_before_kickoff: float | None
    yes_bid: Decimal | None
    yes_ask: Decimal | None
    valid: bool
    reason: str
    snapshots_in_window: int
    invalid_in_window: int

    def to_json(self) -> dict[str, Any]:
        return {
            "close_class": self.close_class.value,
            "captured_at": iso_utc(self.captured_at) if self.captured_at else None,
            "minutes_before_kickoff": round(self.minutes_before_kickoff, 2)
            if self.minutes_before_kickoff is not None
            else None,
            "yes_bid": str(self.yes_bid) if self.yes_bid is not None else None,
            "yes_ask": str(self.yes_ask) if self.yes_ask is not None else None,
            "yes_mid": float((self.yes_bid + self.yes_ask) / 2) if self.valid else None,
            "no_executable": str(Decimal(1) - self.yes_bid) if self.valid else None,
            "valid": self.valid,
            "reason": self.reason,
            "snapshots_in_window": self.snapshots_in_window,
            "invalid_in_window": self.invalid_in_window,
        }


def kalshi_close_for(rows: list[dict[str, Any]], kickoff: datetime) -> KalshiClose:
    """`rows` are archived MarketSnapshot records for ONE ticker (any order). Picks the last valid book in
    [KO - 30 min, KO), stepping back over invalid books; STALE when the only valid book is older."""
    window_start = kickoff - timedelta(minutes=KALSHI_CLOSE_MAX_MINUTES)
    pre = []
    for r in rows:
        try:
            t = parse_iso_utc(r["captured_at"])
        except (KeyError, ValueError):
            continue
        if t < kickoff:
            pre.append((t, r))
    pre.sort(key=lambda x: x[0])
    in_window = [(t, r) for t, r in pre if t >= window_start]
    invalid = 0
    for t, r in reversed(in_window):
        ok, why = book_is_valid(r.get("status"), r.get("yes_bid"), r.get("yes_ask"))
        if ok:
            m = (kickoff - t).total_seconds() / 60
            return KalshiClose(
                CloseClassV2.KALSHI_CLOSE,
                t,
                m,
                _dec(r["yes_bid"]),
                _dec(r["yes_ask"]),
                True,
                why,
                len(in_window),
                invalid,
            )
        invalid += 1
    # nothing valid inside the window: report the last valid book before it as STALE
    for t, r in reversed(pre):
        if t >= window_start:
            continue
        ok, why = book_is_valid(r.get("status"), r.get("yes_bid"), r.get("yes_ask"))
        if ok:
            m = (kickoff - t).total_seconds() / 60
            return KalshiClose(
                CloseClassV2.STALE,
                t,
                m,
                _dec(r["yes_bid"]),
                _dec(r["yes_ask"]),
                True,
                "valid book older than the close window",
                len(in_window),
                invalid,
            )
    reason = (
        "no valid book before kickoff" if not in_window else "every book in the window was invalid"
    )
    return KalshiClose(
        CloseClassV2.NONE, None, None, None, None, False, reason, len(in_window), invalid
    )


@dataclass(frozen=True)
class ReferenceClose:
    close_class: CloseClassV2
    captured_at: datetime | None
    minutes_before_kickoff: float | None
    bookmaker: str | None
    source_quality: SourceQuality
    probability_yes: float | None
    devig_method: str | None

    def to_json(self) -> dict[str, Any]:
        return {
            "close_class": self.close_class.value,
            "captured_at": iso_utc(self.captured_at) if self.captured_at else None,
            "minutes_before_kickoff": round(self.minutes_before_kickoff, 2)
            if self.minutes_before_kickoff is not None
            else None,
            "bookmaker": self.bookmaker,
            "source_quality": self.source_quality.value,
            "probability_yes": self.probability_yes,
            "devig_method": self.devig_method,
        }


def reference_close_for(rows: list[dict[str, Any]], kickoff: datetime) -> ReferenceClose:
    """`rows` are archived reference rows for ONE (fixture, market, selection, line), possibly from several
    bookmakers. Prefers the sharpest quality, then the latest capture before kickoff."""
    best: tuple[int, datetime, dict[str, Any]] | None = None
    rank = {SourceQuality.SHARP_REFERENCE: 2, SourceQuality.SECONDARY_REFERENCE: 1}
    for r in rows:
        try:
            t = parse_iso_utc(r["captured_at"])
        except (KeyError, ValueError):
            continue
        if t >= kickoff:
            continue
        q = quality_for_bookmaker(r.get("bookmaker", ""))
        key = (rank.get(q, 0), t)
        if best is None or key > (best[0], best[1]):
            best = (key[0], t, r)
    if best is None:
        return ReferenceClose(
            CloseClassV2.NONE, None, None, None, SourceQuality.UNAVAILABLE, None, None
        )
    _, t, r = best
    m = (kickoff - t).total_seconds() / 60
    return ReferenceClose(
        classify_reference_close(m),
        t,
        m,
        r.get("bookmaker"),
        quality_for_bookmaker(r.get("bookmaker", "")),
        float(r["devigged_probability"]) if r.get("devigged_probability") is not None else None,
        r.get("devig_method"),
    )


def side_probability(p_yes: float | None, side: str) -> float | None:
    if p_yes is None:
        return None
    return p_yes if side == "yes" else round(1.0 - p_yes, 6)


def close_completeness(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate close-capture completeness over settlement/coverage rows carrying `close_v2`."""
    ref = {c.value: 0 for c in CloseClassV2}
    kal = {c.value: 0 for c in CloseClassV2}
    n = 0
    for r in records:
        cv = r.get("close_v2") or {}
        if not cv:
            continue
        n += 1
        ref[cv["reference"]["close_class"]] = ref.get(cv["reference"]["close_class"], 0) + 1
        kal[cv["kalshi"]["close_class"]] = kal.get(cv["kalshi"]["close_class"], 0) + 1
    usable_ref = ref["TRUE_CLOSE"] + ref["NEAR_CLOSE"]
    return {
        "records": n,
        "reference": ref,
        "kalshi": kal,
        "true_close_share": (ref["TRUE_CLOSE"] / n) if n else None,
        "reference_close_share": (usable_ref / n) if n else None,
        "kalshi_close_share": (kal["KALSHI_CLOSE"] / n) if n else None,
        "missing_reference_close_rate": (1 - usable_ref / n) if n else None,
        "missing_kalshi_close_rate": (1 - kal["KALSHI_CLOSE"] / n) if n else None,
    }
