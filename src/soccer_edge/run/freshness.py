"""Freshness gates measured at the decision `as_of`, not at file write time."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from soccer_edge.core.errors import FreshnessError
from soccer_edge.core.time import ensure_utc


@dataclass(frozen=True)
class FreshnessPolicy:
    max_market_age: timedelta = timedelta(minutes=30)
    max_fixture_age: timedelta = timedelta(hours=36)
    max_results_age: timedelta = timedelta(days=8)  # model inputs (last results)
    max_model_age: timedelta = timedelta(days=3)


@dataclass(frozen=True)
class FreshnessReport:
    as_of: datetime
    market_observed_at: datetime | None
    fixtures_observed_at: datetime | None
    results_observed_at: datetime | None
    model_fitted_at: datetime | None
    policy: FreshnessPolicy

    def _age(self, t: datetime | None) -> timedelta | None:
        return None if t is None else ensure_utc(self.as_of) - ensure_utc(t)

    def violations(self) -> list[str]:
        v = []
        checks = (
            ("market", self.market_observed_at, self.policy.max_market_age),
            ("fixtures", self.fixtures_observed_at, self.policy.max_fixture_age),
            ("results", self.results_observed_at, self.policy.max_results_age),
            ("model", self.model_fitted_at, self.policy.max_model_age),
        )
        for name, t, limit in checks:
            age = self._age(t)
            if age is None:
                v.append(f"{name}: no observation")
            elif age > limit:
                v.append(f"{name}: age {age} exceeds {limit}")
        return v

    def to_json(self) -> dict:
        from soccer_edge.core.time import iso_utc

        def f(t):
            return iso_utc(t) if t else None

        return {
            "as_of": iso_utc(self.as_of),
            "market_observed_at": f(self.market_observed_at),
            "fixtures_observed_at": f(self.fixtures_observed_at),
            "results_observed_at": f(self.results_observed_at),
            "model_fitted_at": f(self.model_fitted_at),
            "violations": self.violations(),
        }

    def require(self) -> None:
        v = self.violations()
        if v:
            raise FreshnessError("; ".join(v))
