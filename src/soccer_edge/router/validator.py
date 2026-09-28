"""Whole-ledger validator the router runs instead of CI.

GitHub runs a `pull_request` workflow only if the file exists on the pull request's BASE
branch; `data-archive` is an orphan branch with no `.github/`, so a delivery there gets no
check run. This is the verdict that replaces it: THIS repository's schemas and identity rule,
run over the tree THIS repository's importer just produced.

Checks, all of them fail-closed:
* every file under the ledger root is `wagers/<YYYY>.jsonl` or `settlements/<YYYY>.jsonl`;
* every line parses as a JSON object with the expected record `schema`;
* `position` / `settlement` validate against the pydantic app contracts;
* `position_id == mint(source_bet_key)` and `settlement_id == mint(source_bet_key)`;
* ids and source keys are unique; a wager sits in the file of its `game_date` year;
* every settlement references a filed position whose id it names.

Output is counts only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from soccer_edge.contracts.v1 import PositionV1, SettlementV1
from soccer_edge.router.identity import mint_position_id, mint_settlement_id
from soccer_edge.router.importer import SETTLEMENT_RECORD_SCHEMA, WAGER_RECORD_SCHEMA
from soccer_edge.router.ledger import LedgerPaths, iter_records, year_of_file


@dataclass
class ValidationResult:
    wager_rows: int = 0
    settlement_rows: int = 0
    files: int = 0
    violations: dict[str, int] = field(default_factory=dict)

    def flag(self, kind: str) -> None:
        self.violations[kind] = self.violations.get(kind, 0) + 1

    @property
    def passed(self) -> bool:
        return not self.violations

    @property
    def exit_code(self) -> int:
        return 0 if self.passed else 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "files": self.files,
            "wager_rows": self.wager_rows,
            "settlement_rows": self.settlement_rows,
            "violations": dict(sorted(self.violations.items())),
        }

    def summary_lines(self) -> list[str]:
        lines = [
            f"validate-positions-ledger: files={self.files} wager_rows={self.wager_rows} "
            f"settlement_rows={self.settlement_rows} violations={sum(self.violations.values())} "
            f"passed={str(self.passed).lower()}"
        ]
        lines.extend(f"  {kind}: {n}" for kind, n in sorted(self.violations.items()))
        return lines


def _unexpected_files(paths: LedgerPaths, result: ValidationResult) -> None:
    root = paths.root
    if not root.exists():
        return
    allowed = set(paths.year_files(paths.wagers)) | set(paths.year_files(paths.settlements))
    for path in root.rglob("*"):
        if path.is_file() and path not in allowed:
            result.flag("unexpected_file")


def validate_ledger(ledger_root: Path) -> ValidationResult:
    paths = LedgerPaths(Path(ledger_root))
    result = ValidationResult()
    _unexpected_files(paths, result)

    positions: dict[str, str] = {}  # source_bet_key -> position_id
    seen_position_ids: set[str] = set()
    for path in paths.year_files(paths.wagers):
        result.files += 1
        year = year_of_file(path)
        try:
            for _, record in iter_records(path):
                result.wager_rows += 1
                if record.get("schema") != WAGER_RECORD_SCHEMA:
                    result.flag("wager_schema_tag")
                    continue
                key = record.get("source_bet_key")
                imported = record.get("imported")
                if not isinstance(key, str) or not key or not isinstance(imported, dict):
                    result.flag("wager_shape")
                    continue
                try:
                    position = PositionV1.model_validate(record.get("position"))
                except ValidationError:
                    result.flag("position_contract")
                    continue
                if position.position_id != mint_position_id(key):
                    result.flag("position_id_not_minted_from_key")
                if position.position_id in seen_position_ids or key in positions:
                    result.flag("duplicate_position")
                seen_position_ids.add(position.position_id)
                positions.setdefault(key, position.position_id)
                if position.source != "kalshi-router" or position.sport != "soccer":
                    result.flag("position_provenance")
                if (
                    imported.get("source_bet_key") != key
                    or imported.get("market_ticker") != position.market_ticker
                ):
                    result.flag("imported_disagrees_with_position")
                if str(imported.get("game_date", ""))[:4] != str(year):
                    result.flag("wager_in_wrong_year_file")
        except ValueError:
            result.flag("wager_file_unparseable")

    seen_settlement_ids: set[str] = set()
    for path in paths.year_files(paths.settlements):
        result.files += 1
        try:
            for _, record in iter_records(path):
                result.settlement_rows += 1
                if record.get("schema") != SETTLEMENT_RECORD_SCHEMA:
                    result.flag("settlement_schema_tag")
                    continue
                key = record.get("source_bet_key")
                if (
                    not isinstance(key, str)
                    or not key
                    or not isinstance(record.get("imported"), dict)
                ):
                    result.flag("settlement_shape")
                    continue
                try:
                    settlement = SettlementV1.model_validate(record.get("settlement"))
                except ValidationError:
                    result.flag("settlement_contract")
                    continue
                if settlement.settlement_id != mint_settlement_id(key):
                    result.flag("settlement_id_not_minted_from_key")
                if settlement.settlement_id in seen_settlement_ids:
                    result.flag("duplicate_settlement")
                seen_settlement_ids.add(settlement.settlement_id)
                if positions.get(key) != settlement.position_id:
                    result.flag("settlement_orphan")
        except ValueError:
            result.flag("settlement_file_unparseable")
    return result
