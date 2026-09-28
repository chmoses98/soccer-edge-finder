"""Phase 18 — Kalshi microstructure diagnostics over archived snapshot rows (RESEARCH ONLY).

Reads every archived `MarketSnapshot` row (JSONL under `<snapshots-dir>/<date>/*.jsonl`, prices as
strings in dollars 0..1) and summarises what the top of book looked like: spreads, executable vs
mid, taker-fee impact, sizes, quote state, how these evolve toward kickoff, and how complete the
capture cadence was. Nothing here selects, prices or recommends; the output feeds documentation and
future research decisions only (see docs/KALSHI_MICROSTRUCTURE.md).

Conventions
    executable YES cost = yes_ask ; executable NO cost = no_ask
    mid                 = (yes_bid + yes_ask) / 2                  (YES-probability space)
    spread_yes          = yes_ask - yes_bid
    gap_yes             = yes_ask - mid ; gap_no = no_ask - (1 - mid)
    fee impact (side)   = taker_fee(ask, 1 contract, series regime) / ask   (fraction of price)
    erased-edge (side)  = spread_yes / 2 + taker fee at that side's ask  >=  threshold
A bid of 0 or an ask of 1 is Kalshi's empty-book sentinel and is treated as "no order" on that side.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from soccer_edge.core.errors import FeeMechanicsUnverifiedError
from soccer_edge.core.serialization import read_jsonl
from soccer_edge.core.time import iso_utc, parse_iso_utc, utc_now
from soccer_edge.kalshi.capture import label_horizon
from soccer_edge.kalshi.fees import FEE_SCHEDULE_VERSION, FeeRegime, taker_fee
from soccer_edge.kalshi.schemas import RawMarket
from soccer_edge.kalshi.taxonomy import _TICKER_RE, classify, split_competition_and_family

SCHEMA = "microstructure_summary_v1"

HORIZON_BUCKETS: tuple[str, ...] = (
    "T-24h+",
    "T-6h..24h",
    "T-1h..6h",
    "T-10m..1h",
    "<10m",
    "unknown",
)
EDGE_THRESHOLDS: dict[str, Decimal] = {"3c": Decimal("0.03"), "5c": Decimal("0.05")}
_ZERO = Decimal(0)
_ONE = Decimal(1)


def horizon_bucket(minutes_to_kickoff: float | None) -> str:
    """Coarse pre-kickoff bucket. Negative minutes (in-play / post-close rows) land in '<10m'."""
    if minutes_to_kickoff is None:
        return "unknown"
    m = float(minutes_to_kickoff)
    if m >= 1440:
        return "T-24h+"
    if m >= 360:
        return "T-6h..24h"
    if m >= 60:
        return "T-1h..6h"
    if m >= 10:
        return "T-10m..1h"
    return "<10m"


def _dec(v: Any) -> Decimal | None:
    if v in (None, "", "None"):
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def _float(v: Any) -> float | None:
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


_ticker_cache: dict[str, tuple[str, str]] = {}


def family_and_competition(ticker: str, event_ticker: str | None = None) -> tuple[str, str]:
    """(family, competition_code) from the ticker alone. Uses the real classifier on a minimal
    RawMarket (title-free), falling back to token splitting when that fails. Cached per ticker."""
    hit = _ticker_cache.get(ticker)
    if hit is not None:
        return hit
    fam, comp = "unknown", "?"
    try:
        ev = event_ticker or ticker.rsplit("-", 1)[0]
        spec = classify(RawMarket(ticker=ticker, event_ticker=ev))
        fam = spec.family.value
        comp = spec.competition_code or "?"
    except Exception:
        m = _TICKER_RE.match(ticker)
        if m:
            c, _tok = split_competition_and_family(m["body"])
            comp = c or "?"
    _ticker_cache[ticker] = (fam, comp)
    return fam, comp


@dataclass(frozen=True)
class RowMetrics:
    ticker: str
    captured_at: datetime
    family: str
    competition: str
    horizon_label: str
    horizon_recomputed: str | None
    bucket: str
    minutes_to_kickoff: float | None
    yes_bid: Decimal | None
    yes_ask: Decimal | None
    no_bid: Decimal | None
    no_ask: Decimal | None
    bid_present: bool
    ask_present: bool
    quote_state: str  # two_sided | one_sided | no_quote
    spread_yes: Decimal | None
    mid: Decimal | None
    exec_yes: Decimal | None
    exec_no: Decimal | None
    gap_yes: Decimal | None
    gap_no: Decimal | None
    yes_bid_size: Decimal | None
    yes_ask_size: Decimal | None
    no_bid_size: Decimal | None
    no_ask_size: Decimal | None
    fee_yes: Decimal | None  # dollars per contract at exec_yes
    fee_no: Decimal | None
    fee_impact_yes: Decimal | None  # fee / price
    fee_impact_no: Decimal | None
    fee_status: str  # ok | unverified_regime | not_computable
    volume: Decimal | None
    open_interest: Decimal | None
    has_orderbook: bool

    def erased(self, side: str, threshold: Decimal) -> bool | None:
        """True when a mid-based edge of `threshold` on `side` is erased by half-spread + taker fee.
        None when the side is not executable or the fee cannot be verified."""
        fee = self.fee_yes if side == "yes" else self.fee_no
        if self.spread_yes is None or fee is None:
            return None
        return (self.spread_yes / 2 + fee) >= threshold


def _fee_at(price: Decimal | None, regime: FeeRegime | None) -> tuple[Decimal | None, str]:
    if regime is None:
        return None, "unverified_regime"
    if price is None or not (_ZERO < price < _ONE):
        return None, "not_computable"
    try:
        return taker_fee(price, 1, regime), "ok"
    except FeeMechanicsUnverifiedError:
        return None, "unverified_regime"


def derive_row(rec: dict[str, Any]) -> RowMetrics | None:
    """Per-row derivations. Returns None only when the row has no ticker/captured_at."""
    tk = rec.get("ticker")
    cat_raw = rec.get("captured_at")
    if not tk or not cat_raw:
        return None
    try:
        cat = parse_iso_utc(str(cat_raw))
    except ValueError:
        return None
    yb, ya, nb, na = (_dec(rec.get(k)) for k in ("yes_bid", "yes_ask", "no_bid", "no_ask"))
    bid_present = yb is not None and yb > _ZERO
    ask_present = ya is not None and ya < _ONE
    if bid_present and ask_present:
        state = "two_sided"
    elif bid_present or ask_present:
        state = "one_sided"
    else:
        state = "no_quote"
    spread = ya - yb if state == "two_sided" else None
    mid = (ya + yb) / 2 if state == "two_sided" else None
    exec_yes = ya if ask_present else None
    exec_no = na if (na is not None and na < _ONE) else None
    gap_yes = exec_yes - mid if (exec_yes is not None and mid is not None) else None
    gap_no = exec_no - (_ONE - mid) if (exec_no is not None and mid is not None) else None

    fee_type = rec.get("fee_type")
    mult = _dec(rec.get("fee_multiplier"))
    regime = None
    if fee_type:
        regime = FeeRegime(fee_type=str(fee_type), fee_multiplier=mult if mult else Decimal(1))
        try:
            regime.verify()
        except FeeMechanicsUnverifiedError:
            regime = None
    fee_yes, st_yes = _fee_at(exec_yes, regime)
    fee_no, st_no = _fee_at(exec_no, regime)
    fee_status = "ok" if "ok" in (st_yes, st_no) else st_yes

    mins = _float(rec.get("minutes_to_kickoff"))
    fam, comp = family_and_competition(str(tk), rec.get("event_ticker"))
    return RowMetrics(
        ticker=str(tk),
        captured_at=cat,
        family=fam,
        competition=comp,
        horizon_label=str(rec.get("horizon") or "adhoc"),
        horizon_recomputed=label_horizon(mins).value if mins is not None else None,
        bucket=horizon_bucket(mins),
        minutes_to_kickoff=mins,
        yes_bid=yb,
        yes_ask=ya,
        no_bid=nb,
        no_ask=na,
        bid_present=bid_present,
        ask_present=ask_present,
        quote_state=state,
        spread_yes=spread,
        mid=mid,
        exec_yes=exec_yes,
        exec_no=exec_no,
        gap_yes=gap_yes,
        gap_no=gap_no,
        yes_bid_size=_dec(rec.get("yes_bid_size")),
        yes_ask_size=_dec(rec.get("yes_ask_size")),
        no_bid_size=_dec(rec.get("no_bid_size")),
        no_ask_size=_dec(rec.get("no_ask_size")),
        fee_yes=fee_yes,
        fee_no=fee_no,
        fee_impact_yes=(fee_yes / exec_yes) if (fee_yes is not None and exec_yes) else None,
        fee_impact_no=(fee_no / exec_no) if (fee_no is not None and exec_no) else None,
        fee_status=fee_status,
        volume=_dec(rec.get("volume")),
        open_interest=_dec(rec.get("open_interest")),
        has_orderbook=bool(rec.get("orderbook")),
    )


# ----------------------------------------------------------------------------- statistics


def _pct(sorted_vals: list[float], q: float) -> float:
    """Linear-interpolated percentile (numpy default) on an already sorted list."""
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = (n - 1) * q
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def dist(values: list[Decimal | float | int | None]) -> dict[str, Any]:
    """{n, mean, median, p10, p90, min, max}; Decimals become floats here and only here."""
    xs = sorted(float(v) for v in values if v is not None)
    if not xs:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "p10": None,
            "p90": None,
            "min": None,
            "max": None,
        }
    return {
        "n": len(xs),
        "mean": round(statistics.fmean(xs), 6),
        "median": round(_pct(xs, 0.5), 6),
        "p10": round(_pct(xs, 0.1), 6),
        "p90": round(_pct(xs, 0.9), 6),
        "min": round(xs[0], 6),
        "max": round(xs[-1], 6),
    }


def _share(num: int, den: int) -> float | None:
    return round(num / den, 6) if den else None


def _erased_share(rows: list[RowMetrics], threshold: Decimal) -> tuple[float | None, int]:
    hits = total = 0
    for r in rows:
        for side in ("yes", "no"):
            e = r.erased(side, threshold)
            if e is None:
                continue
            total += 1
            hits += int(e)
    return _share(hits, total), total


def _last_row_per_ticker(rows: list[RowMetrics]) -> dict[str, RowMetrics]:
    last: dict[str, RowMetrics] = {}
    for r in rows:
        prev = last.get(r.ticker)
        if prev is None or r.captured_at >= prev.captured_at:
            last[r.ticker] = r
    return last


def group_summary(rows: list[RowMetrics]) -> dict[str, Any]:
    states = Counter(r.quote_state for r in rows)
    last = _last_row_per_ticker(rows)
    e3, n3 = _erased_share(rows, EDGE_THRESHOLDS["3c"])
    e5, _n5 = _erased_share(rows, EDGE_THRESHOLDS["5c"])  # same eligible sides as 3c
    return {
        "rows": len(rows),
        "tickers": len({r.ticker for r in rows}),
        "quote_state": {
            "two_sided": states.get("two_sided", 0),
            "one_sided": states.get("one_sided", 0),
            "no_quote": states.get("no_quote", 0),
            "two_sided_share": _share(states.get("two_sided", 0), len(rows)),
        },
        "spread_yes": dist([r.spread_yes for r in rows]),
        "gap_yes": dist([r.gap_yes for r in rows]),
        "gap_no": dist([r.gap_no for r in rows]),
        "fee_impact_yes": dist([r.fee_impact_yes for r in rows]),
        "fee_impact_no": dist([r.fee_impact_no for r in rows]),
        "fee_status": dict(sorted(Counter(r.fee_status for r in rows).items())),
        "sizes": {
            "yes_bid_size": dist([r.yes_bid_size for r in rows]),
            "yes_ask_size": dist([r.yes_ask_size for r in rows]),
            "no_bid_size": dist([r.no_bid_size for r in rows]),
            "no_ask_size": dist([r.no_ask_size for r in rows]),
        },
        "mid_edge_erased_share_3c": e3,
        "mid_edge_erased_share_5c": e5,
        "mid_edge_erased_sides_n": n3,
        "volume_last_row_per_ticker": dist([r.volume for r in last.values()]),
        "open_interest_last_row_per_ticker": dist([r.open_interest for r in last.values()]),
        "volume_total_last_row": float(
            sum(r.volume for r in last.values() if r.volume is not None)
        ),
        "open_interest_total_last_row": float(
            sum(r.open_interest for r in last.values() if r.open_interest is not None)
        ),
        "orderbook_rows": sum(1 for r in rows if r.has_orderbook),
    }


def cadence_summary(rows: list[RowMetrics]) -> dict[str, Any]:
    """Capture completeness: per-ticker gaps between consecutive rows (tickers with >= 3 rows)."""
    by_tk: dict[str, list[datetime]] = defaultdict(list)
    for r in rows:
        by_tk[r.ticker].append(r.captured_at)
    medians: list[float] = []
    maxes: list[float] = []
    all_gaps: list[float] = []
    eligible = 0
    for ts in by_tk.values():
        if len(ts) < 3:
            continue
        ts = sorted(ts)
        gaps = [(b - a).total_seconds() / 60 for a, b in zip(ts, ts[1:])]
        eligible += 1
        medians.append(statistics.median(gaps))
        maxes.append(max(gaps))
        all_gaps.extend(gaps)
    return {
        "tickers_total": len(by_tk),
        "tickers_with_3plus_rows": eligible,
        "rows_per_ticker": dist([len(v) for v in by_tk.values()]),
        "gap_minutes_all": dist(all_gaps),
        "gap_minutes_per_ticker_median": dist(medians),
        "gap_minutes_per_ticker_max": dist(maxes),
    }


def coverage_summary(rows: list[RowMetrics]) -> dict[str, Any]:
    hours_rows = Counter(f"{r.captured_at.hour:02d}" for r in rows)
    batches = {r.captured_at for r in rows}
    hours_caps = Counter(f"{t.hour:02d}" for t in batches)
    days = sorted({r.captured_at.date().isoformat() for r in rows})
    return {
        "distinct_capture_timestamps": len(batches),
        "days_with_rows": len(days),
        "rows_by_utc_hour": {f"{h:02d}": hours_rows.get(f"{h:02d}", 0) for h in range(24)},
        "captures_by_utc_hour": {f"{h:02d}": hours_caps.get(f"{h:02d}", 0) for h in range(24)},
        "rows_by_day": {
            d: sum(1 for r in rows if r.captured_at.date().isoformat() == d) for d in days
        },
    }


# ----------------------------------------------------------------------------- driver


def load_rows(
    snapshots_dir: Path, *, since: date | None = None
) -> tuple[list[RowMetrics], dict[str, int]]:
    """All snapshot rows under `snapshots_dir` (recursive *.jsonl), derived. Deterministic order."""
    rows: list[RowMetrics] = []
    counters = {"files": 0, "rows_read": 0, "rows_skipped": 0, "rows_before_since": 0}
    if not snapshots_dir.exists():
        return rows, counters
    for path in sorted(snapshots_dir.rglob("*.jsonl")):
        counters["files"] += 1
        for rec in read_jsonl(path):
            counters["rows_read"] += 1
            r = derive_row(rec)
            if r is None:
                counters["rows_skipped"] += 1
                continue
            if since is not None and r.captured_at.date() < since:
                counters["rows_before_since"] += 1
                continue
            rows.append(r)
    rows.sort(key=lambda r: (r.captured_at, r.ticker))
    return rows, counters


def _grouped(rows: list[RowMetrics], key) -> dict[str, dict[str, Any]]:
    g: dict[str, list[RowMetrics]] = defaultdict(list)
    for r in rows:
        g[key(r)].append(r)
    return {k: group_summary(v) for k, v in sorted(g.items())}


def summarise(rows: list[RowMetrics], *, counters: dict[str, int] | None = None) -> dict[str, Any]:
    counters = counters or {}
    by_bucket = _grouped(rows, lambda r: r.bucket)
    toward = []
    for b in HORIZON_BUCKETS:
        gs = by_bucket.get(b)
        if gs is None:
            continue
        toward.append(
            {
                "bucket": b,
                "rows": gs["rows"],
                "tickers": gs["tickers"],
                "two_sided_share": gs["quote_state"]["two_sided_share"],
                "spread_yes_median": gs["spread_yes"]["median"],
                "spread_yes_p90": gs["spread_yes"]["p90"],
                "yes_ask_size_median": gs["sizes"]["yes_ask_size"]["median"],
                "no_ask_size_median": gs["sizes"]["no_ask_size"]["median"],
                "fee_impact_yes_median": gs["fee_impact_yes"]["median"],
                "mid_edge_erased_share_3c": gs["mid_edge_erased_share_3c"],
                "mid_edge_erased_share_5c": gs["mid_edge_erased_share_5c"],
            }
        )
    overall = group_summary(rows)
    fam_hz = _grouped(rows, lambda r: f"{r.family}|{r.bucket}")
    label_mismatch = sum(
        1
        for r in rows
        if r.horizon_recomputed is not None and r.horizon_recomputed != r.horizon_label
    )
    return {
        "schema": SCHEMA,
        "generated_at": iso_utc(utc_now()),
        "fee_schedule_version": FEE_SCHEDULE_VERSION,
        "rows": len(rows),
        "tickers": len({r.ticker for r in rows}),
        "date_range": {
            "first_captured_at": iso_utc(rows[0].captured_at) if rows else None,
            "last_captured_at": iso_utc(rows[-1].captured_at) if rows else None,
        },
        "input": {
            "files": counters.get("files", 0),
            "rows_read": counters.get("rows_read", 0),
            "rows_skipped_unparseable": counters.get("rows_skipped", 0),
            "rows_before_since": counters.get("rows_before_since", 0),
        },
        "definitions": {
            "executable": "YES cost = yes_ask; NO cost = no_ask (top of book, taker)",
            "mid": "(yes_bid + yes_ask) / 2 when both sides carry orders",
            "spread_yes": "yes_ask - yes_bid",
            "fee_impact": "taker_fee(ask, 1 contract, series fee regime) / ask",
            "mid_edge_erased_share": "share of executable sides where spread_yes/2 + taker fee at the ask >= threshold",
            "empty_book_sentinel": "bid == 0 or ask == 1 counts as no order on that side",
            "horizon_buckets": list(HORIZON_BUCKETS),
        },
        "overall": overall,
        "quote_state": overall["quote_state"],
        "spread_yes": overall["spread_yes"],
        "fee_impact": {"yes": overall["fee_impact_yes"], "no": overall["fee_impact_no"]},
        "sizes": overall["sizes"],
        "mid_edge_erased_share_3c": overall["mid_edge_erased_share_3c"],
        "mid_edge_erased_share_5c": overall["mid_edge_erased_share_5c"],
        "mid_edge_erased_sides_n": overall["mid_edge_erased_sides_n"],
        "by_family": _grouped(rows, lambda r: r.family),
        "by_competition": _grouped(rows, lambda r: r.competition),
        "by_horizon_bucket": by_bucket,
        "by_family_horizon": fam_hz,
        "toward_kickoff": toward,
        "volume_open_interest_by_family": {
            fam: {
                "tickers": gs["tickers"],
                "volume_total_last_row": gs["volume_total_last_row"],
                "volume_last_row_per_ticker": gs["volume_last_row_per_ticker"],
                "open_interest_total_last_row": gs["open_interest_total_last_row"],
                "open_interest_last_row_per_ticker": gs["open_interest_last_row_per_ticker"],
            }
            for fam, gs in _grouped(rows, lambda r: r.family).items()
        },
        "horizon_labels": {
            "stored_label_histogram": dict(sorted(Counter(r.horizon_label for r in rows).items())),
            "recomputed_label_histogram": dict(
                sorted(Counter(r.horizon_recomputed or "adhoc" for r in rows).items())
            ),
            "stored_vs_recomputed_mismatch_rows": label_mismatch,
        },
        "capture_coverage": coverage_summary(rows),
        "capture_cadence": cadence_summary(rows),
    }


def build_summary(snapshots_dir: Path, *, since: date | None = None) -> dict[str, Any]:
    rows, counters = load_rows(snapshots_dir, since=since)
    out = summarise(rows, counters=counters)
    out["snapshots_dir"] = str(snapshots_dir)
    out["since"] = since.isoformat() if since else None
    return out
