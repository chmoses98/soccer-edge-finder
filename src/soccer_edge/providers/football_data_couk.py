"""football-data.co.uk direct CSV provider (free; blocked from some corporate egress, fine from Actions).

Supplies the same columns as the GitHub redistribution plus *closing* odds columns
(B365CH/B365CD/B365CA, PSCH/PSCD/PSCA, and AvgC*) for seasons from 2019-20 onward.
Used by the research-fetch workflow to build a genuine closing-line benchmark.
"""

from __future__ import annotations

import csv
import io

from soccer_edge.providers.base import Observation, QualityFlag
from soccer_edge.providers.http import CachedFetcher

BASE = "https://www.football-data.co.uk/mmz4281"
LICENSE = "football-data.co.uk free data; attribution requested"

CLOSING_COLUMNS = {
    "bet365": ("B365CH", "B365CD", "B365CA"),
    "pinnacle": ("PSCH", "PSCD", "PSCA"),
    "average": ("AvgCH", "AvgCD", "AvgCA"),
}


def season_code(season_id: str) -> str:
    # '2026-27' -> '2627'
    start, end = season_id.split("-")
    return start[2:] + end


class FootballDataCoUkProvider:
    provider_id = "football_data_couk"

    def __init__(self, fetcher: CachedFetcher | None = None) -> None:
        self.fetcher = fetcher or CachedFetcher()

    def raw_rows(self, division: str, season_id: str) -> Observation[list[dict[str, str]]]:
        url = f"{BASE}/{season_code(season_id)}/{division}.csv"
        fetched = self.fetcher.fetch(url, source=self.provider_id, license_note=LICENSE)
        text = fetched.content.decode("utf-8", errors="replace")
        rows = [r for r in csv.DictReader(io.StringIO(text)) if r.get("Date")]
        has_closing = bool(rows) and any(
            c in rows[0] for cols in CLOSING_COLUMNS.values() for c in cols
        )
        flags = (QualityFlag.OK,) if has_closing else (QualityFlag.PARTIAL,)
        notes = () if has_closing else ("no closing-odds columns in this season file",)
        return Observation(payload=rows, provenance=fetched.provenance, flags=flags, notes=notes)
