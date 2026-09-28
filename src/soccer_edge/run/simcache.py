"""Simulation cache: separates MARKET REFRESH from MODEL REFRESH.

Key = hash(posterior params, world config, sim config, match context, contract semantics set).
If only quotes changed, the cached per-contract world-probability summaries are reused and
repriced. If the key changes (new results, lineup state, new contracts), we re-simulate.
World probabilities are stored as compact quantile summaries + mean (never raw draws).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from soccer_edge.core.serialization import content_hash
from soccer_edge.pricing.pricer import PricedProbability

QUANTILES = np.array([0.02, 0.05, 0.10, 0.20, 0.25, 0.50, 0.75, 0.80, 0.90, 0.95, 0.98])


def sim_key(
    *,
    posterior_hash: str,
    world_cfg: dict[str, Any],
    sim_cfg: dict[str, Any],
    context: dict[str, Any],
    seed: int,
) -> str:
    return content_hash(
        {"p": posterior_hash, "w": world_cfg, "s": sim_cfg, "c": context, "seed": seed}
    )


@dataclass
class CachedFixtureSim:
    sim_key: str
    fixture_id: str
    outcome_hash: str
    summary: dict[str, Any]
    contracts: dict[str, dict[str, Any]]  # ticker -> compact priced probability

    def has(self, tickers: list[str]) -> bool:
        return all(t in self.contracts for t in tickers)


def compact(p: PricedProbability) -> dict[str, Any]:
    q = np.quantile(p.world_probs, QUANTILES)
    return {
        **p.to_json(),
        "world_quantiles": {str(k): round(float(v), 6) for k, v in zip(QUANTILES, q)},
        # coarse histogram of world probabilities (20 bins); kept for older readers
        "world_hist": np.histogram(p.world_probs, bins=20, range=(0, 1))[0].tolist(),
        # exact per-world probabilities so repricing recomputes P(edge>0) / worst case without binning
        "world_probs": [round(float(v), 6) for v in p.world_probs],
    }


def expand_world_probs(c: dict[str, Any]) -> np.ndarray:
    """Per-world probabilities from the cache: exact when stored, else approximated from the histogram."""
    if c.get("world_probs"):
        return np.asarray(c["world_probs"], dtype=float)
    hist = np.array(c["world_hist"], dtype=float)
    edges = np.linspace(0, 1, 21)
    mids = (edges[:-1] + edges[1:]) / 2
    n = int(hist.sum())
    if n == 0:
        return np.array([c["fair_probability_mean"]])
    return np.repeat(mids, hist.astype(int))


class SimCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, fixture_id: str) -> Path:
        safe = fixture_id.replace(":", "_").replace("/", "_")
        return self.root / f"{safe}.json"

    def load(self, fixture_id: str) -> CachedFixtureSim | None:
        p = self._path(fixture_id)
        if not p.exists():
            return None
        d = json.loads(p.read_text())
        return CachedFixtureSim(
            d["sim_key"], d["fixture_id"], d["outcome_hash"], d["summary"], d["contracts"]
        )

    def save(self, c: CachedFixtureSim) -> None:
        self._path(c.fixture_id).write_text(
            json.dumps(c.__dict__, sort_keys=True, indent=1, default=str) + "\n"
        )
