"""Small cached HTTP fetcher used by public-data providers.

* Deterministic on-disk cache keyed by URL (sha256) so research runs are reproducible.
* Every fetch returns bytes + provenance; no provider parses directly from the network.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import httpx

from soccer_edge.core.errors import ProviderError
from soccer_edge.core.time import utc_now
from soccer_edge.providers.base import Provenance

DEFAULT_CACHE_DIR = Path(os.environ.get("SOCCER_EDGE_CACHE_DIR", "data/cache"))
USER_AGENT = "soccer-edge-finder/0.1 (+https://github.com/chmoses98/soccer-edge-finder; research)"


@dataclass(frozen=True)
class Fetched:
    content: bytes
    provenance: Provenance
    from_cache: bool


class CachedFetcher:
    def __init__(
        self,
        cache_dir: Path | None = None,
        *,
        max_age: timedelta | None = timedelta(hours=6),
        timeout: float = 60.0,
        offline: bool = False,
    ) -> None:
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.max_age = max_age
        self.timeout = timeout
        self.offline = offline

    def _cache_path(self, url: str) -> Path:
        h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
        return self.cache_dir / h[:2] / f"{h}.bin"

    def fetch(self, url: str, *, source: str, license_note: str | None = None) -> Fetched:
        path = self._cache_path(url)
        meta = path.with_suffix(".meta")
        now = utc_now()
        if path.exists() and meta.exists():
            observed = meta.read_text().strip()
            from soccer_edge.core.time import parse_iso_utc

            observed_at = parse_iso_utc(observed)
            fresh = self.max_age is None or (now - observed_at) <= self.max_age
            if fresh or self.offline:
                content = path.read_bytes()
                return Fetched(
                    content,
                    Provenance(
                        source=source,
                        source_url=url,
                        observed_at=observed_at,
                        content_hash="sha256:" + hashlib.sha256(content).hexdigest(),
                        license=license_note,
                    ),
                    from_cache=True,
                )
        if self.offline:
            raise ProviderError(f"offline and no cache for {url}")
        try:
            with httpx.Client(
                timeout=self.timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True
            ) as client:
                resp = client.get(url)
        except httpx.HTTPError as exc:  # network layer failure
            raise ProviderError(f"fetch failed for {url}: {exc}") from exc
        if resp.status_code != 200:
            raise ProviderError(f"fetch failed for {url}: HTTP {resp.status_code}")
        content = resp.content
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        from soccer_edge.core.time import iso_utc

        meta.write_text(iso_utc(now))
        return Fetched(
            content,
            Provenance(
                source=source,
                source_url=url,
                source_version=resp.headers.get("etag"),
                observed_at=now,
                content_hash="sha256:" + hashlib.sha256(content).hexdigest(),
                license=license_note,
            ),
            from_cache=False,
        )
