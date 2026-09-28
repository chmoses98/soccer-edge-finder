"""App contract V1. Additive changes only within V1; breaking changes bump to V2 side by side.

Numbers are plain JSON numbers/strings: prices and money are strings of Decimals to avoid
float drift; probabilities are floats in [0,1]; timestamps are ISO-8601 UTC with 'Z'.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

APP_CONTRACT_VERSION = "1.2.0"

Sport = Literal["soccer", "mlb", "nfl", "cfb", "nba", "other"]
AuthorityLevel = Literal["RESEARCH_ONLY", "SHADOW", "LIMITED", "TRUSTED"]
LineupStatus = Literal["unknown", "projected", "confirmed"]
CoverageStatus = Literal["complete", "incomplete"]


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: str = APP_CONTRACT_VERSION

    @field_serializer("*", when_used="json")
    def _ser(self, v: Any) -> Any:
        if isinstance(v, Decimal):
            return str(v)
        if isinstance(v, datetime):
            from soccer_edge.core.time import iso_utc

            return iso_utc(v)
        return v


class EventV1(_Base):
    event_id: str
    sport: Sport
    league: str
    league_id: str
    event_name: str
    start_time: datetime
    home: str
    away: str
    home_id: str
    away_id: str
    venue: str | None = None
    neutral_site: bool = False
    status: str
    lineup_status: LineupStatus = "unknown"
    stage: str | None = None
    markets_discovered: int = 0
    markets_evaluated: int = 0


class RecommendationV1(_Base):
    recommendation_id: str
    sport: Sport
    league: str
    event_id: str
    event_name: str
    start_time: datetime
    market_ticker: str
    market_family: str
    market_description: str
    side: Literal["yes", "no"]
    current_price: Decimal
    available_size: Decimal | None = None
    fair_probability: float = Field(ge=0, le=1)
    fair_probability_low: float = Field(ge=0, le=1)
    fair_probability_high: float = Field(ge=0, le=1)
    probability_edge_positive: float = Field(ge=0, le=1)
    fee_adjusted_edge: float
    worst_case_edge: float
    bet_up_to_price: Decimal | None = None
    authority: AuthorityLevel
    confidence_label: str
    stake_units: float | None = Field(
        default=None, description="null until staking is externally supplied or authorised"
    )
    model_family: str
    model_version: str
    data_as_of: datetime
    market_as_of: datetime
    model_as_of: datetime
    lineup_status: LineupStatus
    coverage_status: CoverageStatus
    thesis: str
    risks: list[str]
    correlation_group: str
    fee_schedule_version: str
    prediction_record_id: str | None = None
    # --- V1.1 optional additions (backwards compatible) ---
    reference_probability: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="de-vigged reference-market probability for this side at prediction time",
    )
    reference_bookmaker: str | None = None
    reference_as_of: datetime | None = None
    divergence_from_reference: float | None = Field(
        default=None, description="fair_probability - reference_probability"
    )
    kalshi_mid_probability: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Kalshi midpoint for this side (diagnostic only; never the executable price)",
    )
    clv_probability_points: float | None = Field(
        default=None,
        description="filled after settlement: side-aware close minus entry, positive is good",
    )
    close_class: Literal["TRUE_CLOSE", "NEAR_CLOSE", "PRE_CLOSE", "NONE"] | None = None
    # --- v1.2 additive fields (remediation phases 9-10) ---
    model_posterior_edge_share: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="accurate name for probability_edge_positive (diagnostic only)",
    )
    selection_policy: str | None = None
    edge_v2_status: str | None = None
    edge_v2_expected_net_ev: float | None = None
    edge_v2_ev_lower: float | None = None
    edge_v2_reference_quality: str | None = None


class ModelHealthV1(_Base):
    sport: Sport
    model_family: str
    market_family: str
    horizon: str
    authority: AuthorityLevel
    n_settled: int
    brier: float | None = None
    log_loss: float | None = None
    market_log_loss: float | None = None
    ece: float | None = None
    interval_coverage_80: float | None = None
    clv_points_mean: float | None = None
    fee_adjusted_realised_ev: float | None = None
    last_evaluated_at: datetime | None = None
    notes: list[str] = Field(default_factory=list)


class PositionV1(_Base):
    position_id: str
    sport: Sport
    event_id: str
    market_ticker: str
    side: Literal["yes", "no"]
    contracts: Decimal
    average_price: Decimal
    fees_paid: Decimal
    opened_at: datetime
    source: str = Field(description="e.g. 'kalshi-router' import; this repo never places orders")
    recommendation_id: str | None = None
    status: Literal["open", "settled", "voided"] = "open"


class SettlementV1(_Base):
    settlement_id: str
    sport: Sport
    event_id: str
    market_ticker: str
    outcome: Literal["yes", "no", "void", "refused"]
    refusal_reason: str | None = None
    settled_at: datetime
    evidence: dict[str, Any]
    kalshi_result: str | None = None
    agrees_with_kalshi: bool | None = None
    position_id: str | None = None
    realised_pnl: Decimal | None = None
    # --- V1.1 optional additions ---
    close_class: Literal["TRUE_CLOSE", "NEAR_CLOSE", "PRE_CLOSE", "NONE"] | None = None
    clv_probability_points: float | None = None
    clv_price_points: float | None = None
    clv_fee_aware_points: float | None = None
    reference_close_probability: float | None = None


class CoverageReportV1(_Base):
    discovery_run_id: str
    discovery_complete: bool
    contracts_discovered: int
    contracts_evaluated: int
    contracts_excluded_mechanically: int
    contracts_unsupported: int
    unaccounted_contracts: int
    by_disposition: dict[str, int]
    contracts_by_family: dict[str, int]
    competitions_discovered: list[str]


class RunOutputV1(_Base):
    run_id: str
    sport: Sport
    generated_at: datetime
    run_date: str
    filters: dict[str, Any]
    no_bets: bool
    recommendations: list[RecommendationV1]
    shadow_recommendations: list[RecommendationV1] = Field(
        default_factory=list, description="RESEARCH_ONLY/SHADOW output; never actionable"
    )
    events: list[EventV1]
    coverage: CoverageReportV1
    model_health: list[ModelHealthV1] = Field(default_factory=list)
    freshness: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


def export_json_schemas(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for model in (
        EventV1,
        RecommendationV1,
        ModelHealthV1,
        PositionV1,
        SettlementV1,
        CoverageReportV1,
        RunOutputV1,
    ):
        path = out_dir / f"{model.__name__}.schema.json"
        path.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n")
        written.append(path)
    return written
