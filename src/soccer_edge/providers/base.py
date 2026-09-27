"""Observation envelope shared by every provider."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from soccer_edge.core.time import ensure_utc, utc_now

T = TypeVar("T")


class QualityFlag(str, Enum):
    OK = "ok"
    STALE = "stale"
    PARTIAL = "partial"  # payload known to be incomplete (e.g. missing odds columns)
    CONFLICTING = "conflicting"  # disagrees with another source
    UNVERIFIED = "unverified"  # source could not be cross-checked
    DERIVED = "derived"  # computed by us from another observation, not observed
    SYNTHETIC = "synthetic"  # test fixture / offline stub; never for production


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(
        description="provider id, e.g. 'openfootball', 'football_data_couk', 'kalshi_public'"
    )
    source_url: str | None = None
    source_version: str | None = Field(
        default=None, description="ETag/commit/hash of the upstream payload if known"
    )
    observed_at: datetime = Field(description="when WE fetched it (UTC)")
    effective_at: datetime | None = Field(
        default=None, description="when the upstream state was true, if known"
    )
    content_hash: str | None = None
    license: str | None = None

    @field_validator("observed_at", "effective_at")
    @classmethod
    def _utc(cls, v: datetime | None) -> datetime | None:
        return ensure_utc(v) if v is not None else v


class Observation(BaseModel, Generic[T]):
    """A payload plus provenance and quality flags."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    payload: T
    provenance: Provenance
    flags: tuple[QualityFlag, ...] = (QualityFlag.OK,)
    notes: tuple[str, ...] = ()

    def age(self, now: datetime | None = None) -> timedelta:
        return (now or utc_now()) - self.provenance.observed_at

    @property
    def is_usable_for_production(self) -> bool:
        return QualityFlag.SYNTHETIC not in self.flags

    def with_flag(self, flag: QualityFlag, note: str | None = None) -> Observation[T]:
        flags = tuple(f for f in self.flags if f != QualityFlag.OK) + (flag,)
        notes = self.notes + ((note,) if note else ())
        return self.model_copy(update={"flags": flags, "notes": notes})
