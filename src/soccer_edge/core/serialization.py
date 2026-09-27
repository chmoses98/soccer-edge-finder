"""Deterministic serialization and content hashing.

Everything archived is hashed with `content_hash`, which serialises via `canonical_json`.
Ordering is sorted, floats are repr'd, Decimals/Datetimes are stringified deterministically.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel

from soccer_edge.core.time import iso_utc


def _default(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="python")
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return iso_utc(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, set | frozenset):
        return sorted(obj)
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError(f"not serialisable: {type(obj).__name__}")


def canonical_json(obj: Any) -> str:
    """Sorted-key, compact JSON with deterministic scalar encodings."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_default, allow_nan=False)


def pretty_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, default=_default, allow_nan=False) + "\n"


def content_hash(obj: Any, *, prefix: str = "sha256") -> str:
    digest = hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def short_hash(obj: Any, n: int = 12) -> str:
    return content_hash(obj).split(":", 1)[1][:n]


def dump_model(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(pretty_json(obj), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(canonical_json(record) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
