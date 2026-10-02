"""Per-input freshness thresholds for the actionable slate (docs/ACTIONABLE_SLATE.md §Freshness).

Every input is classified separately: CURRENT while its age <= current_max, AGING while <= aging_max,
STALE beyond, UNAVAILABLE when there is no observation. The thresholds are deliberately coarse; they say
how old an input may be before it is not trusted as "current", not how precisely it was measured.

* KALSHI: the approved live market gate is 30 min (run/freshness.py `max_market_age`). A price is CURRENT
  for 20 min (the 15-minute free capture cadence plus the capture's own ~3 min), AGING to 30 min, then
  STALE. Any action needs a CURRENT price.
* REFERENCE (Pinnacle via The Odds API): CURRENT for 15 min (edge_v2 `max_reference_age_minutes`, the
  same limit that evaluates reference-anchored EV), AGING to 75 min (an entry capture at T-60 stays visible
  until kickoff), then STALE. Never fetched by a reprice; only what the kickoff chain already captured.
* LINEUP: CURRENT for 30 min after the last lineup sync that covered the fixture's league, AGING to 2 h.
* CONTEXT (fixture list: kickoff, venue): CURRENT for 12 h, AGING to 36 h (run/freshness.py fixture limit).
* MODEL: a cached probability is usable only while its pricing inputs are unchanged (VALID); its age is
  CURRENT for 12 h and AGING to 36 h (one result day), then STALE.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from soccer_edge.contracts.slate_v1 import InputFreshnessV1, SlateFreshnessPolicyV1
from soccer_edge.core.time import ensure_utc


@dataclass(frozen=True)
class Thresholds:
    current_max: float  # minutes
    aging_max: float


@dataclass(frozen=True)
class SlateFreshnessPolicy:
    kalshi: Thresholds = Thresholds(20, 30)
    reference: Thresholds = Thresholds(15, 75)
    lineup: Thresholds = Thresholds(30, 120)
    context: Thresholds = Thresholds(12 * 60, 36 * 60)
    model: Thresholds = Thresholds(12 * 60, 36 * 60)

    def to_contract(self) -> SlateFreshnessPolicyV1:
        return SlateFreshnessPolicyV1(
            kalshi_current_max=self.kalshi.current_max,
            kalshi_aging_max=self.kalshi.aging_max,
            reference_current_max=self.reference.current_max,
            reference_aging_max=self.reference.aging_max,
            lineup_current_max=self.lineup.current_max,
            lineup_aging_max=self.lineup.aging_max,
            context_current_max=self.context.current_max,
            context_aging_max=self.context.aging_max,
            model_current_max=self.model.current_max,
            model_aging_max=self.model.aging_max,
            action_requires=["kalshi:CURRENT", "model:VALID and not STALE", "fee_regime:verified"],
        )


def classify(
    observed_at: datetime | None, now: datetime, t: Thresholds, *, detail: str | None = None
) -> InputFreshnessV1:
    if observed_at is None:
        return InputFreshnessV1(status="UNAVAILABLE", detail=detail)
    obs = ensure_utc(observed_at)
    age = (ensure_utc(now) - obs).total_seconds() / 60
    if age <= t.current_max:
        status = "CURRENT"
    elif age <= t.aging_max:
        status = "AGING"
    else:
        status = "STALE"
    return InputFreshnessV1(
        observed_at=obs,
        age_minutes_at_publish=round(age, 2),
        status=status,
        current_until=obs + timedelta(minutes=t.current_max),
        stale_after=obs + timedelta(minutes=t.aging_max),
        detail=detail,
    )
