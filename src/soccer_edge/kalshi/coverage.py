"""Coverage accounting. Every discovered contract receives exactly one terminal disposition.

unaccounted_contracts = contracts_discovered - sum(dispositions)  and MUST be 0.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from soccer_edge.core.errors import CoverageInvariantError


class Disposition(str, Enum):
    PRICED = "priced"  # priced and evaluated (may or may not be recommended)
    CLOSED = "closed"  # status closed/finalized
    STARTED = "started"  # kickoff already passed at pricing time
    NO_QUOTE = "no_quote"  # empty / zero-size book on both sides
    STALE_QUOTE = "stale_quote"  # quote older than the freshness gate
    DUPLICATE = "duplicate"
    AMBIGUOUS_OWNERSHIP = "ambiguous_ownership"
    UNKNOWN_FAMILY = "unknown_family"
    UNSUPPORTED_FAMILY = "unsupported_family"  # known family, no pricer yet (futures, cards ...)
    UNMAPPED_EVENT = "unmapped_event"
    UNMAPPED_TEAM = "unmapped_team"
    NO_FIXTURE = "no_fixture"
    NO_MODEL = (
        "no_model"  # fixture mapped but no simulation available (e.g. competition not modelled)
    )
    FEE_UNVERIFIED = "fee_unverified"
    INFERRED_FAMILY_UNCONFIRMED = (
        "inferred_family_unconfirmed"  # family guessed from grammar; not priced
    )
    OUT_OF_WINDOW = "out_of_window"  # kickoff outside the requested run window
    FILTERED_BY_OPERATOR = "filtered_by_operator"  # --league/--game filters
    UNPRICEABLE = (
        "unpriceable"  # pricer raised / semantics not derivable from the joint distribution
    )

    @property
    def is_evaluated(self) -> bool:
        return self is Disposition.PRICED


@dataclass
class CoverageLedger:
    discovered: set[str] = field(default_factory=set)
    dispositions: dict[str, tuple[Disposition, str]] = field(default_factory=dict)

    def discover(self, tickers: list[str] | set[str]) -> None:
        self.discovered.update(tickers)

    def set(self, ticker: str, disposition: Disposition, reason: str = "") -> None:
        if ticker not in self.discovered:
            raise CoverageInvariantError(f"disposition for undiscovered ticker {ticker}")
        if ticker in self.dispositions and self.dispositions[ticker][0] is not disposition:
            prev = self.dispositions[ticker][0]
            raise CoverageInvariantError(
                f"{ticker} already dispositioned {prev.value}; refusing {disposition.value}"
            )
        self.dispositions[ticker] = (disposition, reason)

    @property
    def unaccounted(self) -> set[str]:
        return self.discovered - set(self.dispositions)

    def summary(self) -> dict[str, Any]:
        c = Counter(d.value for d, _ in self.dispositions.values())
        out = {
            "contracts_discovered": len(self.discovered),
            "contracts_evaluated": c.get(Disposition.PRICED.value, 0),
            "contracts_excluded_mechanically": sum(
                v
                for k, v in c.items()
                if k
                not in (
                    Disposition.PRICED.value,
                    Disposition.UNSUPPORTED_FAMILY.value,
                    Disposition.UNKNOWN_FAMILY.value,
                )
            ),
            "contracts_unsupported": c.get(Disposition.UNSUPPORTED_FAMILY.value, 0)
            + c.get(Disposition.UNKNOWN_FAMILY.value, 0),
            "unaccounted_contracts": len(self.unaccounted),
            "by_disposition": {d.value: c.get(d.value, 0) for d in Disposition},
        }
        return out

    def assert_invariant(self) -> None:
        if self.unaccounted:
            sample = sorted(self.unaccounted)[:10]
            raise CoverageInvariantError(
                f"{len(self.unaccounted)} unaccounted contracts, e.g. {sample}"
            )
        s = self.summary()
        if s["contracts_discovered"] != sum(s["by_disposition"].values()):
            raise CoverageInvariantError("disposition partition does not sum to discovered")
