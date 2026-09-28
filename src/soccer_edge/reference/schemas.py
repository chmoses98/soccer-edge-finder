"""ReferenceMarketSnapshot: one bookmaker quote for one selection, point-in-time, never overwritten."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from soccer_edge.core.serialization import content_hash
from soccer_edge.core.time import iso_utc


class DevigMethod(str, Enum):
    PROPORTIONAL = "proportional"  # p_i = (1/o_i) / sum(1/o_j)
    POWER = "power"  # find k: sum (1/o_j)^k = 1
    NONE = "none"  # raw implied only


class CloseClass(str, Enum):
    TRUE_CLOSE = "TRUE_CLOSE"  # last observation <= 30 min before kickoff
    NEAR_CLOSE = "NEAR_CLOSE"  # last observation <= 6 h before kickoff
    PRE_CLOSE = "PRE_CLOSE"  # earlier than 6 h
    NONE = "NONE"  # no pre-kickoff observation


TRUE_CLOSE_MINUTES = 30
NEAR_CLOSE_MINUTES = 360


def classify_close(minutes_before_kickoff: float | None) -> CloseClass:
    if minutes_before_kickoff is None or minutes_before_kickoff < 0:
        return CloseClass.NONE
    if minutes_before_kickoff <= TRUE_CLOSE_MINUTES:
        return CloseClass.TRUE_CLOSE
    if minutes_before_kickoff <= NEAR_CLOSE_MINUTES:
        return CloseClass.NEAR_CLOSE
    return CloseClass.PRE_CLOSE


class ReferenceMarketSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(description="e.g. 'football_data_couk_fixtures'")
    bookmaker: str = Field(description="'bet365' | 'pinnacle' | 'average' | 'max' | 'consensus'")
    fixture_id: str
    competition_id: str
    home_team_id: str
    away_team_id: str
    kickoff_utc: datetime | None
    market: str = Field(description="'1x2' | 'ou' | 'ah'")
    selection: str = Field(description="'home'|'draw'|'away'|'over'|'under'")
    line: Decimal | None = None
    raw_odds: Decimal
    implied_probability: float = Field(ge=0, le=1)
    devig_method: DevigMethod
    devigged_probability: float = Field(ge=0, le=1)
    overround: float = Field(description="sum of implied probabilities in the market before de-vig")
    captured_at: datetime
    quoted_at: datetime | None = Field(
        default=None, description="upstream quote time if known, else None (= captured_at)"
    )
    is_closing: bool = False
    minutes_to_kickoff: float | None = None
    liquidity_note: str = "bookmaker screen price; no size information"

    def fingerprint(self) -> str:
        return content_hash(
            {
                "b": self.bookmaker,
                "f": self.fixture_id,
                "m": self.market,
                "s": self.selection,
                "l": self.line,
                "o": self.raw_odds,
            }
        )

    def to_record(self, batch_id: str) -> dict[str, Any]:
        d = self.model_dump(mode="json")
        d["captured_at"] = iso_utc(self.captured_at)
        d["kickoff_utc"] = iso_utc(self.kickoff_utc) if self.kickoff_utc else None
        d["batch_id"] = batch_id
        return d
