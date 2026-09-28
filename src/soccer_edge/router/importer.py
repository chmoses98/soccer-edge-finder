"""Wager and settlement importers for `kalshi-bet-router` payloads.

*** THE CONTRACT THE ROUTER HOLDS THIS FILE TO ***
(`kalshi_router.destinations.DestinationProfile`, verified against router main `2322bd7`)

* payload `{"importBatchId": "kalshi-router-v1", "rows": [...]}`; one receipt PER ROW to
  `--receipts-out`, in a shape `kalshi_router.receipts.normalise` reads
  (`source_bet_key`, `wager_id`/`settlement_id`, `status`, `conflicting_fields`, `reason`);
* identity minted from `source_bet_key` alone; a second identical import is all
  `DUPLICATE_NOOP` and changes no byte of the ledger;
* a re-delivery that disagrees with a filed record on an economic field is `CONFLICT` and the
  filed record is never rewritten;
* an unknown field, and any field that would claim MODEL PROVENANCE, refuses the row; a refused
  row does not block the others; exit status is non-zero when any row was refused or conflicts;
* the importer writes only under the ledger root and leaves no residue.

*** WHAT A ROW MAY SAY ***
`SOCCER_WAGER_FIELDS` is the whole vocabulary. A Kalshi execution proves the owner placed a
bet; it proves nothing about what recommended it, so `recommendation_id`, `model_*`, `fair_*`,
`edge_*`, `probability*` and friends are refused outright rather than ignored -- ignoring one
would let a later router version quietly assert model backing for a position.

*** PRIVACY ***
Every value in a row is private (this repository's logs are public). Functions here return
counts and field names; the only place a value goes is the ledger file and the receipts file,
both of which the router keeps off its logs.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal

from soccer_edge.contracts.v1 import PositionV1, SettlementV1
from soccer_edge.core.time import iso_utc, parse_iso_utc
from soccer_edge.router.identity import event_ticker_for, mint_position_id, mint_settlement_id
from soccer_edge.router.ledger import LedgerPaths, append_lines, iter_records

ROUTER_IMPORT_BATCH_ID = "kalshi-router-v1"
WAGER_RECORD_SCHEMA = "soccer_routed_wager.v1"
SETTLEMENT_RECORD_SCHEMA = "soccer_routed_settlement.v1"

Status = Literal["NEW", "DUPLICATE_NOOP", "CONFLICT", "REFUSED"]

# ------------------------------------------------------------------ vocabularies

#: Exactly what a routed soccer wager row may carry (snake_case, the NFL/CFB dialect).
#: `actual_price` (NFL's name) and `execution_price` (CFB's name) are the same quantity-weighted
#: price; a row carries exactly one of them. `fee_state` and `execution_action` are evidence
#: the NFL builder also emits; accepted, stored, not part of a row's economic identity.
SOCCER_WAGER_FIELDS: frozenset[str] = frozenset(
    {
        "source_bet_key",
        "import_batch_id",
        "entry_method",
        "game_date",
        "market_ticker",
        "side",
        "executed_at",
        "contracts",
        "actual_price",
        "execution_price",
        "stake",
        "fees_paid",
        "fees_are_estimated",
        "venue",
        "fee_state",
        "execution_action",
    }
)
_WAGER_REQUIRED: frozenset[str] = frozenset(
    {
        "source_bet_key",
        "import_batch_id",
        "entry_method",
        "game_date",
        "market_ticker",
        "side",
        "executed_at",
        "contracts",
        "stake",
        "fees_paid",
        "fees_are_estimated",
        "venue",
    }
)
_PRICE_FIELDS = ("actual_price", "execution_price")

#: Fields whose disagreement on re-delivery is a CONFLICT (`price` is the canonical name for
#: whichever price field the row used). Batch id, entry method and the evidence fields are not
#: economic and are not compared.
WAGER_COMPARED_FIELDS: tuple[str, ...] = (
    "game_date",
    "market_ticker",
    "side",
    "executed_at",
    "contracts",
    "price",
    "stake",
    "fees_paid",
    "fees_are_estimated",
    "venue",
)

#: The router's per-order settlement row (`kalshi_router.destination._settlement_row`).
#: `economics_version` is present only for a v2 destination.
SOCCER_SETTLEMENT_FIELDS: frozenset[str] = frozenset(
    {
        "source_bet_key",
        "market_ticker",
        "side",
        "settlement_status",
        "settled_at",
        "result",
        "gross_return",
        "net_profit_loss",
        "refusals",
        "venue",
        "economics_version",
    }
)
_SETTLEMENT_REQUIRED: frozenset[str] = frozenset(
    {
        "source_bet_key",
        "market_ticker",
        "side",
        "settlement_status",
        "settled_at",
        "result",
        "gross_return",
        "net_profit_loss",
        "refusals",
        "venue",
    }
)
SETTLEMENT_COMPARED_FIELDS: tuple[str, ...] = (
    "market_ticker",
    "side",
    "settlement_status",
    "settled_at",
    "result",
    "gross_return",
    "net_profit_loss",
    "economics_version",
)

#: A field NAME matching this is a claim of model provenance and refuses the row.
_MODEL_PROVENANCE_RE = re.compile(
    r"^(model_|fair_|edge_|probabilit|recommendation|prediction_|thesis|authority|confidence)"
)

_SIDES = ("YES", "NO")
_ENTRY_METHOD = "IMPORTED_RECEIPT"
_VENUE = "kalshi"
_RESULTS = ("WON", "LOST")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def canonical_line(record: dict[str, Any]) -> str:
    """One ledger line: sorted keys, compact separators, ASCII only. Deliberately stdlib-only so the
    router can run this importer with nothing but pydantic installed; every Decimal and datetime
    has already been rendered to a string by the time a record reaches here."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)


# ---------------------------------------------------------------------- results


@dataclass(frozen=True)
class Receipt:
    source_bet_key: str | None
    identity: str | None
    status: Status
    conflicting_fields: tuple[str, ...] = ()
    reason: str | None = None

    @property
    def success(self) -> bool:
        return self.status in ("NEW", "DUPLICATE_NOOP")

    def as_dict(self, identity_field: str) -> dict[str, Any]:
        return {
            "source_bet_key": self.source_bet_key,
            identity_field: self.identity,
            "status": self.status,
            "success": self.success,
            "conflicting_fields": list(self.conflicting_fields),
            "reason": self.reason,
        }


@dataclass
class ImportOutcome:
    """Counts and field names only: safe to print anywhere."""

    kind: str
    receipts: list[Receipt] = field(default_factory=list)
    files_written: int = 0
    payload_error: str | None = None

    @property
    def counts(self) -> dict[str, int]:
        out = {"NEW": 0, "DUPLICATE_NOOP": 0, "CONFLICT": 0, "REFUSED": 0}
        for r in self.receipts:
            out[r.status] += 1
        return out

    @property
    def exit_code(self) -> int:
        if self.payload_error:
            return 2
        c = self.counts
        return 1 if (c["REFUSED"] or c["CONFLICT"]) else 0

    def summary_lines(self) -> list[str]:
        c = self.counts
        lines = [
            f"{self.kind}: rows={len(self.receipts)} NEW={c['NEW']} "
            f"DUPLICATE_NOOP={c['DUPLICATE_NOOP']} CONFLICT={c['CONFLICT']} REFUSED={c['REFUSED']} "
            f"files_written={self.files_written}"
        ]
        if self.payload_error:
            lines.append(f"  payload refused: {self.payload_error}")
        reasons = sorted({r.reason for r in self.receipts if r.reason})
        if reasons:
            lines.append("  refusal reasons (shape names only): " + "; ".join(reasons))
        names = sorted({f for r in self.receipts for f in r.conflicting_fields})
        if names:
            lines.append("  conflicting fields (names only): " + ", ".join(names))
        return lines


class RowRefused(Exception):
    """Carries a reason made of field/shape names only -- never a value."""


# ------------------------------------------------------------------- parsing


def _decimal(
    value: Any, name: str, *, minimum: Decimal | None = None, maximum: Decimal | None = None
) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise RowRefused(f"invalid_value:{name}")
    try:
        parsed = Decimal(str(value)) if isinstance(value, int | float) else Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise RowRefused(f"invalid_value:{name}") from exc
    if not parsed.is_finite():
        raise RowRefused(f"invalid_value:{name}")
    if minimum is not None and parsed < minimum:
        raise RowRefused(f"invalid_value:{name}")
    if maximum is not None and parsed > maximum:
        raise RowRefused(f"invalid_value:{name}")
    return parsed


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RowRefused(f"invalid_value:{name}")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    try:
        return parse_iso_utc(_string(value, name))
    except ValueError as exc:
        raise RowRefused(f"invalid_value:{name}") from exc


def _screen_fields(row: Any, vocabulary: frozenset[str], required: frozenset[str]) -> None:
    if not isinstance(row, dict):
        raise RowRefused("row_not_an_object")
    provenance = sorted(k for k in row if isinstance(k, str) and _MODEL_PROVENANCE_RE.match(k))
    if provenance:
        raise RowRefused("model_provenance_field:" + ",".join(provenance))
    unknown = sorted(str(k) for k in row if k not in vocabulary)
    if unknown:
        raise RowRefused("unknown_field:" + ",".join(unknown))
    missing = sorted(required - set(row))
    if missing:
        raise RowRefused("missing_field:" + ",".join(missing))


def _normalise_wager(row: Any, batch_id: str) -> dict[str, Any]:
    """Validate one wager row; return the `imported` record (Decimals kept as Decimal)."""
    _screen_fields(row, SOCCER_WAGER_FIELDS, _WAGER_REQUIRED)
    present_prices = [f for f in _PRICE_FIELDS if f in row]
    if len(present_prices) != 1:
        raise RowRefused("price_field:exactly_one_of:" + ",".join(_PRICE_FIELDS))
    price_field = present_prices[0]

    out: dict[str, Any] = {}
    out["source_bet_key"] = _string(row["source_bet_key"], "source_bet_key")
    if _string(row["import_batch_id"], "import_batch_id") != batch_id:
        raise RowRefused("import_batch_id:disagrees_with_envelope")
    out["import_batch_id"] = row["import_batch_id"]
    if _string(row["entry_method"], "entry_method") != _ENTRY_METHOD:
        raise RowRefused("invalid_value:entry_method")
    out["entry_method"] = row["entry_method"]
    game_date = _string(row["game_date"], "game_date")
    try:
        if not _DATE_RE.match(game_date):
            raise ValueError
        date.fromisoformat(game_date)
    except ValueError as exc:
        raise RowRefused("invalid_value:game_date") from exc
    out["game_date"] = game_date
    out["market_ticker"] = _string(row["market_ticker"], "market_ticker")
    if row["side"] not in _SIDES:
        raise RowRefused("invalid_value:side")
    out["side"] = row["side"]
    out["executed_at"] = iso_utc(_timestamp(row["executed_at"], "executed_at"))
    out["contracts"] = _decimal(row["contracts"], "contracts", minimum=Decimal("0"))
    if out["contracts"] == 0:
        raise RowRefused("invalid_value:contracts")
    out[price_field] = _decimal(
        row[price_field], price_field, minimum=Decimal("0"), maximum=Decimal("1")
    )
    out["stake"] = _decimal(row["stake"], "stake", minimum=Decimal("0"))
    out["fees_paid"] = _decimal(row["fees_paid"], "fees_paid", minimum=Decimal("0"))
    if not isinstance(row["fees_are_estimated"], bool):
        raise RowRefused("invalid_value:fees_are_estimated")
    out["fees_are_estimated"] = row["fees_are_estimated"]
    if _string(row["venue"], "venue") != _VENUE:
        raise RowRefused("invalid_value:venue")
    out["venue"] = row["venue"]
    for optional in ("fee_state", "execution_action"):
        if optional in row:
            out[optional] = _string(row[optional], optional)
    return out


def _wager_price(imported: dict[str, Any]) -> Decimal:
    for f in _PRICE_FIELDS:
        if f in imported:
            return Decimal(str(imported[f]))
    raise RowRefused("price_field:missing")


def _wager_comparable(imported: dict[str, Any]) -> dict[str, Any]:
    """The economic identity of a wager, with money as Decimal so `0.53 == 0.530`."""
    return {
        "game_date": str(imported["game_date"]),
        "market_ticker": str(imported["market_ticker"]),
        "side": str(imported["side"]),
        "executed_at": str(imported["executed_at"]),
        "contracts": Decimal(str(imported["contracts"])),
        "price": _wager_price(imported),
        "stake": Decimal(str(imported["stake"])),
        "fees_paid": Decimal(str(imported["fees_paid"])),
        "fees_are_estimated": bool(imported["fees_are_estimated"]),
        "venue": str(imported["venue"]),
    }


def _differing(
    existing: dict[str, Any], incoming: dict[str, Any], fields: tuple[str, ...]
) -> tuple[str, ...]:
    return tuple(f for f in fields if existing.get(f) != incoming.get(f))


def _position_for(imported: dict[str, Any]) -> PositionV1:
    return PositionV1(
        position_id=mint_position_id(imported["source_bet_key"]),
        sport="soccer",
        event_id=event_ticker_for(imported["market_ticker"]),
        market_ticker=imported["market_ticker"],
        side="yes" if imported["side"] == "YES" else "no",
        contracts=imported["contracts"],
        average_price=_wager_price(imported),
        fees_paid=imported["fees_paid"],
        opened_at=parse_iso_utc(imported["executed_at"]),
        source="kalshi-router",
        recommendation_id=None,
        status="open",
    )


def _wager_record(imported: dict[str, Any]) -> dict[str, Any]:
    position = _position_for(imported)
    return {
        "schema": WAGER_RECORD_SCHEMA,
        "source_bet_key": imported["source_bet_key"],
        "position": position.model_dump(mode="json"),
        "imported": {k: (str(v) if isinstance(v, Decimal) else v) for k, v in imported.items()},
    }


# ------------------------------------------------------------------ the ledger index


def _load_index(
    paths: LedgerPaths, directory: Path, key: str = "source_bet_key"
) -> dict[str, dict[str, Any]]:
    """`{source_bet_key: record}` across every year file. A corrupt ledger raises."""
    index: dict[str, dict[str, Any]] = {}
    for path in paths.year_files(directory):
        for _, record in iter_records(path):
            k = record.get(key)
            if isinstance(k, str):
                index.setdefault(k, record)
    return index


def _read_payload(
    payload_path: Path, rows_key: str
) -> tuple[str | None, list[Any] | None, str | None]:
    """`(batch_id, rows, error)`; the error names a shape, never a value."""
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, None, f"payload_unreadable:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, None, "payload_not_an_object"
    rows = payload.get(rows_key)
    if not isinstance(rows, list):
        return None, None, f"payload_missing:{rows_key}"
    batch_id = payload.get("importBatchId")
    if rows_key == "rows" and not (isinstance(batch_id, str) and batch_id):
        return None, None, "payload_missing:importBatchId"
    return batch_id, rows, None


def _write_receipts(
    path: Path | None, outcome: ImportOutcome, identity_field: str, batch_id: str | None
) -> None:
    if path is None:
        return
    c = outcome.counts
    body = {
        "importBatchId": batch_id,
        "kind": outcome.kind,
        "written": c["NEW"],
        "alreadyPresent": c["DUPLICATE_NOOP"],
        "conflicts": c["CONFLICT"],
        "refused": c["REFUSED"],
        "payloadError": outcome.payload_error,
        "rows": [r.as_dict(identity_field) for r in outcome.receipts],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ------------------------------------------------------------------ wager import


def import_wagers(
    payload_path: Path, ledger_root: Path, receipts_out: Path | None = None
) -> ImportOutcome:
    """Import a router wager payload into `<ledger_root>/wagers/<YYYY>.jsonl` (year of `game_date`)."""
    paths = LedgerPaths(Path(ledger_root))
    outcome = ImportOutcome(kind="import-wagers")
    batch_id, rows, error = _read_payload(Path(payload_path), "rows")
    if error or rows is None:
        outcome.payload_error = error
        _write_receipts(receipts_out, outcome, "wager_id", batch_id)
        return outcome

    index = _load_index(paths, paths.wagers)
    pending: dict[int, list[str]] = {}
    for row in rows:
        key = row.get("source_bet_key") if isinstance(row, dict) else None
        key = key if isinstance(key, str) and key else None
        identity = mint_position_id(key) if key else None
        try:
            imported = _normalise_wager(row, str(batch_id))
        except RowRefused as exc:
            outcome.receipts.append(Receipt(key, identity, "REFUSED", reason=str(exc)))
            continue
        key = imported["source_bet_key"]
        identity = mint_position_id(key)
        filed = index.get(key)
        if filed is not None:
            try:
                existing = _wager_comparable(filed.get("imported") or {})
            except (KeyError, RowRefused, InvalidOperation, TypeError):
                outcome.receipts.append(
                    Receipt(key, identity, "CONFLICT", ("imported",), "filed_record_unreadable")
                )
                continue
            diff = _differing(existing, _wager_comparable(imported), WAGER_COMPARED_FIELDS)
            if diff:
                outcome.receipts.append(
                    Receipt(key, identity, "CONFLICT", diff, "economic_fields_disagree")
                )
            else:
                outcome.receipts.append(Receipt(key, identity, "DUPLICATE_NOOP"))
            continue
        record = _wager_record(imported)
        index[key] = record
        pending.setdefault(int(imported["game_date"][:4]), []).append(canonical_line(record))
        outcome.receipts.append(Receipt(key, identity, "NEW"))

    for year, lines in sorted(pending.items()):
        append_lines(paths.wager_file(year), lines)
        outcome.files_written += 1
    _write_receipts(receipts_out, outcome, "wager_id", batch_id)
    return outcome


# ------------------------------------------------------------- settlement import


def _normalise_settlement(row: Any) -> dict[str, Any]:
    _screen_fields(row, SOCCER_SETTLEMENT_FIELDS, _SETTLEMENT_REQUIRED)
    out: dict[str, Any] = {}
    out["source_bet_key"] = _string(row["source_bet_key"], "source_bet_key")
    out["market_ticker"] = _string(row["market_ticker"], "market_ticker")
    if row["side"] not in _SIDES:
        raise RowRefused("invalid_value:side")
    out["side"] = row["side"]
    out["settlement_status"] = _string(row["settlement_status"], "settlement_status")
    out["settled_at"] = iso_utc(_timestamp(row["settled_at"], "settled_at"))
    if row["result"] is not None and row["result"] not in _RESULTS:
        raise RowRefused("invalid_value:result")
    out["result"] = row["result"]
    for money in ("gross_return", "net_profit_loss"):
        out[money] = None if row[money] is None else _decimal(row[money], money)
    refusals = row["refusals"]
    if not isinstance(refusals, list) or not all(isinstance(r, str) for r in refusals):
        raise RowRefused("invalid_value:refusals")
    out["refusals"] = list(refusals)
    if _string(row["venue"], "venue") != _VENUE:
        raise RowRefused("invalid_value:venue")
    out["venue"] = row["venue"]
    if "economics_version" in row:
        out["economics_version"] = _string(row["economics_version"], "economics_version")
    return out


def _settlement_comparable(imported: dict[str, Any]) -> dict[str, Any]:
    def money(v: Any) -> Decimal | None:
        return None if v is None else Decimal(str(v))

    return {
        "market_ticker": str(imported["market_ticker"]),
        "side": str(imported["side"]),
        "settlement_status": str(imported["settlement_status"]),
        "settled_at": str(imported["settled_at"]),
        "result": imported.get("result"),
        "gross_return": money(imported.get("gross_return")),
        "net_profit_loss": money(imported.get("net_profit_loss")),
        "economics_version": imported.get("economics_version"),
    }


def _settlement_for(imported: dict[str, Any], position: dict[str, Any]) -> SettlementV1:
    side = "yes" if imported["side"] == "YES" else "no"
    other = "no" if side == "yes" else "yes"
    result = imported["result"]
    if result == "WON":
        outcome: str = side
    elif result == "LOST":
        outcome = other
    else:
        outcome = "void"
    refusals = imported["refusals"]
    evidence = {
        "source": "kalshi-router",
        "settlement_status": imported["settlement_status"],
        "result": result,
        "gross_return": None if imported["gross_return"] is None else str(imported["gross_return"]),
        "net_profit_loss": (
            None if imported["net_profit_loss"] is None else str(imported["net_profit_loss"])
        ),
        "refusals": list(refusals),
        "venue": imported["venue"],
        "economics_version": imported.get("economics_version"),
    }
    return SettlementV1(
        settlement_id=mint_settlement_id(imported["source_bet_key"]),
        sport="soccer",
        event_id=str(position["event_id"]),
        market_ticker=imported["market_ticker"],
        outcome=outcome,  # type: ignore[arg-type]
        refusal_reason=",".join(refusals) if refusals else None,
        settled_at=parse_iso_utc(imported["settled_at"]),
        evidence=evidence,
        kalshi_result=None if outcome == "void" else outcome,
        agrees_with_kalshi=None,
        position_id=str(position["position_id"]),
        realised_pnl=imported["net_profit_loss"],
    )


def _settlement_record(imported: dict[str, Any], position: dict[str, Any]) -> dict[str, Any]:
    settlement = _settlement_for(imported, position)
    return {
        "schema": SETTLEMENT_RECORD_SCHEMA,
        "source_bet_key": imported["source_bet_key"],
        "settlement": settlement.model_dump(mode="json"),
        "imported": {k: (str(v) if isinstance(v, Decimal) else v) for k, v in imported.items()},
    }


def import_settlements(
    payload_path: Path, ledger_root: Path, receipts_out: Path | None = None
) -> ImportOutcome:
    """Import router settlement rows (`{"settlements": [...]}`) into `<ledger_root>/settlements/<YYYY>.jsonl`.

    The year is the POSITION's `game_date` year, so a fixture's wager and its settlement shard
    together. An orphan (no filed position for the key) is refused per row.
    """
    paths = LedgerPaths(Path(ledger_root))
    outcome = ImportOutcome(kind="import-settlements")
    batch_id, rows, error = _read_payload(Path(payload_path), "settlements")
    if error or rows is None:
        outcome.payload_error = error
        _write_receipts(receipts_out, outcome, "settlement_id", batch_id)
        return outcome

    positions = _load_index(paths, paths.wagers)
    index = _load_index(paths, paths.settlements)
    pending: dict[int, list[str]] = {}
    for row in rows:
        key = row.get("source_bet_key") if isinstance(row, dict) else None
        key = key if isinstance(key, str) and key else None
        identity = mint_settlement_id(key) if key else None
        try:
            imported = _normalise_settlement(row)
        except RowRefused as exc:
            outcome.receipts.append(Receipt(key, identity, "REFUSED", reason=str(exc)))
            continue
        key = imported["source_bet_key"]
        identity = mint_settlement_id(key)
        wager = positions.get(key)
        if wager is None:
            outcome.receipts.append(
                Receipt(key, identity, "REFUSED", reason="orphan:source_bet_key")
            )
            continue
        position = wager.get("position") or {}
        wager_imported = wager.get("imported") or {}
        mismatched = tuple(
            f for f in ("market_ticker", "side") if wager_imported.get(f) != imported[f]
        )
        if mismatched:
            outcome.receipts.append(
                Receipt(
                    key,
                    identity,
                    "REFUSED",
                    mismatched,
                    "position_disagrees:" + ",".join(mismatched),
                )
            )
            continue
        filed = index.get(key)
        if filed is not None:
            try:
                existing = _settlement_comparable(filed.get("imported") or {})
            except (KeyError, InvalidOperation, TypeError):
                outcome.receipts.append(
                    Receipt(key, identity, "CONFLICT", ("imported",), "filed_record_unreadable")
                )
                continue
            diff = _differing(
                existing, _settlement_comparable(imported), SETTLEMENT_COMPARED_FIELDS
            )
            if diff:
                outcome.receipts.append(
                    Receipt(key, identity, "CONFLICT", diff, "settlement_fields_disagree")
                )
            else:
                outcome.receipts.append(Receipt(key, identity, "DUPLICATE_NOOP"))
            continue
        record = _settlement_record(imported, position)
        index[key] = record
        year = int(str(wager_imported.get("game_date", imported["settled_at"]))[:4])
        pending.setdefault(year, []).append(canonical_line(record))
        outcome.receipts.append(Receipt(key, identity, "NEW"))

    for year, lines in sorted(pending.items()):
        append_lines(paths.settlement_file(year), lines)
        outcome.files_written += 1
    _write_receipts(receipts_out, outcome, "settlement_id", batch_id)
    return outcome
