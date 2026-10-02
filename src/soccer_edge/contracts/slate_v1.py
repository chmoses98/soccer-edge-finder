"""ActionableSlateV1: the mutable, latest-state current-price board ChatGPT reads for RUN SOCCER.

Published as `runs/latest.actionable_slate.v1.json` on data-archive after every fresh Kalshi capture
(docs/ACTIONABLE_SLATE.md). It is a PRESENTATION of the latest state, never evidence: the immutable
prospective ledger (`predictions/`) is written only by model runs, never by a reprice.

Every input carries its own timestamp and freshness state (MODEL, KALSHI, REFERENCE, LINEUP, CONTEXT);
there is no single `as_of` implying everything is equally fresh. Freshness states are computed at publish
time AND given as absolute deadlines (`current_until`, `stale_after`) so a reader can recompute them at
read time: a price read after its `stale_after` is STALE_PRICE / NO ACTION whatever the file says.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from soccer_edge.contracts.v1 import AuthorityLevel, _Base

SLATE_CONTRACT_VERSION = "1.0.0"

FreshnessState = Literal["CURRENT", "AGING", "STALE", "UNAVAILABLE"]
ModelValidity = Literal["VALID", "INVALIDATED", "MISSING"]
# per contract side, computed at publish time (see docs/ACTIONABLE_SLATE.md §Actions)
SlateAction = Literal[
    "ACTIONABLE",  # authority LIMITED/TRUSTED + every gate passed (never today: all RESEARCH_ONLY)
    "RESEARCH_CANDIDATE",  # passes the production selection policy on a CURRENT price; authority forbids betting
    "NO_EDGE",  # current price, valid model, does not pass selection
    "STALE_PRICE",  # Kalshi price older than the live threshold: NO ACTION
    "NO_QUOTE",  # no executable ask on this side / market not open
    "MODEL_INVALIDATED",  # a material model input changed since the probability was computed: NO ACTION
    "MODEL_STALE",  # cached probability older than the model freshness limit: NO ACTION
    "FEE_UNVERIFIED",  # fee regime missing / not verified: NO ACTION
    "EXCLUDED_BY_GATE",  # e.g. international pool not validated (audit §E6)
]


class _SlateBase(_Base):
    schema_version: str = SLATE_CONTRACT_VERSION


class InputFreshnessV1(_SlateBase):
    """One input's timestamp and freshness. `current_until` / `stale_after` let a reader recompute the state
    at read time (state = CURRENT before current_until, AGING before stale_after, STALE after)."""

    observed_at: datetime | None = None
    age_minutes_at_publish: float | None = None
    status: FreshnessState
    current_until: datetime | None = None
    stale_after: datetime | None = None
    detail: str | None = None


class SlateFreshnessPolicyV1(_SlateBase):
    """Thresholds in minutes: CURRENT while age <= current_max, AGING while <= aging_max, else STALE."""

    kalshi_current_max: float
    kalshi_aging_max: float
    reference_current_max: float
    reference_aging_max: float
    lineup_current_max: float
    lineup_aging_max: float
    context_current_max: float
    context_aging_max: float
    model_current_max: float
    model_aging_max: float
    action_requires: list[str] = Field(
        description="inputs that must be CURRENT (model: VALID and not STALE) for any action"
    )


class SlateModelStateV1(_SlateBase):
    validity: ModelValidity
    invalidation_reasons: list[str] = Field(default_factory=list)
    model_family: str | None = None
    model_version: str | None = None
    engine_version: str | None = None
    worlds_version: str | None = None
    parameter_hash: str | None = None
    sim_key: str | None = None
    source_run_id: str | None = None
    freshness: InputFreshnessV1


class SlateLineupStateV1(_SlateBase):
    status: Literal["unknown", "unconfirmed", "confirmed", "post_hoc"]
    last_change_at: datetime | None = None
    freshness: InputFreshnessV1


class SlateReferenceStateV1(_SlateBase):
    bookmaker: str | None = None
    quality: str = "UNAVAILABLE"
    role: str | None = Field(
        default=None, description="entry | close | other (minutes before kickoff)"
    )
    quoted_at: datetime | None = Field(default=None, description="bookmaker's own last update")
    freshness: InputFreshnessV1


class SlateFixtureV1(_SlateBase):
    fixture_id: str
    event_name: str
    competition: str
    competition_name: str | None = None
    kickoff: datetime
    minutes_to_kickoff_at_publish: float
    model: SlateModelStateV1
    lineup: SlateLineupStateV1
    context: InputFreshnessV1
    reference: SlateReferenceStateV1
    contracts_priced: int = 0
    contracts_without_model: int = Field(
        default=0,
        description="open Kalshi contracts mapped to this fixture's events that the cached model did not price",
    )
    best_expressions: list[str] = Field(default_factory=list, description="'ticker|side'")


class SlateContractV1(_SlateBase):
    """One contract side. Prices are dollar strings; probabilities floats in [0, 1] for THIS side."""

    fixture_id: str
    event_name: str
    competition: str
    kickoff: datetime
    market_family: str
    market_description: str
    ticker: str
    event_ticker: str | None = None
    side: Literal["yes", "no"]

    model_probability: float
    model_probability_low: float
    model_probability_high: float
    model_family: str
    model_version: str
    model_generated_at: datetime

    kalshi_price: Decimal | None = Field(
        description="executable ask for this side (never a midpoint)"
    )
    kalshi_yes_bid: Decimal | None = None
    kalshi_yes_ask: Decimal | None = None
    kalshi_no_bid: Decimal | None = None
    kalshi_no_ask: Decimal | None = None
    kalshi_observed_at: datetime | None = None
    available_size: Decimal | None = None
    breakeven_price: Decimal | None = Field(
        default=None, description="executable price + fee per contract (probability units)"
    )
    fee_per_contract: Decimal | None = None

    reference_probability: float | None = None
    reference_quality: str = "UNAVAILABLE"
    reference_observed_at: datetime | None = None
    reference_freshness: FreshnessState = "UNAVAILABLE"

    fee_adjusted_ev: float | None = Field(
        default=None, description="model probability - break-even (per $1 contract)"
    )
    worst_case_edge: float | None = Field(
        default=None, description="q0.20 world probability - break-even (robust edge)"
    )
    model_posterior_edge_share: float | None = None
    reference_anchored_ev: float | None = Field(
        default=None, description="edge_v2 expected net EV against a CURRENT Pinnacle reference"
    )
    reference_anchored_ev_lower: float | None = None
    bet_up_to_price: Decimal | None = None

    lineup_status: str
    lineup_observed_at: datetime | None = None
    context_observed_at: datetime | None = None

    authority: AuthorityLevel
    research_status: str
    bet_permitted: bool = False
    action: SlateAction
    action_reasons: list[str] = Field(default_factory=list)
    action_valid_until: datetime | None = Field(
        default=None, description="after this instant the price is no longer CURRENT: re-read"
    )
    best_expression: bool = False
    freshness: dict[str, FreshnessState] = Field(
        description="model / kalshi / reference / lineup / context state at publish"
    )


class SlateComputeV1(_SlateBase):
    """What producing this slate cost. A reprice-only slate has simulations=0 and odds_api_calls=0."""

    mode: Literal["reprice_only", "model_refresh_and_reprice"]
    trigger: str
    simulations_run: int = 0
    fixtures_resimulated: list[str] = Field(default_factory=list)
    fixtures_reused_from_cache: list[str] = Field(default_factory=list)
    odds_api_calls: int = 0
    odds_api_credits: int = 0
    reprice_runtime_s: float
    model_refresh_runtime_s: float | None = None
    kalshi_capture_runtime_s: float | None = None


class ActionableSlateV1(_SlateBase):
    contract: Literal["actionable_slate.v1"] = "actionable_slate.v1"
    slate_id: str
    sport: Literal["soccer"] = "soccer"
    generated_at: datetime
    lookahead_hours: float
    consumer_rule: str
    freshness_policy: SlateFreshnessPolicyV1
    kalshi: InputFreshnessV1
    kalshi_discovery_run_id: str | None = None
    kalshi_discovery_complete: bool = False
    actionable_until: datetime | None = Field(
        default=None, description="the Kalshi prices stop being CURRENT at this instant"
    )
    model_board_generated_at: datetime | None = None
    authority_summary: str
    no_bets: bool = True
    compute: SlateComputeV1
    counts: dict[str, int] = Field(default_factory=dict)
    fixtures: list[SlateFixtureV1] = Field(default_factory=list)
    contracts: list[SlateContractV1] = Field(default_factory=list)
    removed_started: list[str] = Field(
        default_factory=list, description="fixtures dropped because they kicked off"
    )
    warnings: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
