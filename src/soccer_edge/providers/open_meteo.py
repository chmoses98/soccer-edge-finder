"""Open-Meteo weather capture (Phase 15) — CONTEXT ONLY.

Free, keyless: geocoding (https://geocoding-api.open-meteo.com/v1/search) and forecast
(https://api.open-meteo.com/v1/forecast). Venue coordinates come from the ESPN event's venue city/country,
geocoded once and cached (append-only JSON keyed by "city|country"). For each fixture within the capture window
we store the forecast for the kickoff hour: temperature, precipitation, wind, weather code, plus the forecast
issue time (=captured_at), so later research can compare forecast horizons. Nothing here feeds pricing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from soccer_edge.core.serialization import append_jsonl, read_json, write_json
from soccer_edge.core.time import ensure_utc, utc_now
from soccer_edge.providers.http import CachedFetcher

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
PROVIDER_ID = "open_meteo"
HOURLY = "temperature_2m,precipitation,precipitation_probability,wind_speed_10m,wind_gusts_10m,weather_code,relative_humidity_2m"


@dataclass(frozen=True)
class Geo:
    latitude: float
    longitude: float
    name: str
    country: str | None


def geocode_key(city: str | None, country: str | None) -> str:
    return f"{(city or '').strip().lower()}|{(country or '').strip().lower()}"


def parse_geocode(body: dict[str, Any]) -> Geo | None:
    res = body.get("results") or []
    if not res:
        return None
    r = res[0]
    return Geo(float(r["latitude"]), float(r["longitude"]), r.get("name") or "", r.get("country"))


def pick_kickoff_hour(body: dict[str, Any], kickoff_utc: datetime) -> dict[str, Any] | None:
    hourly = body.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return None
    target = ensure_utc(kickoff_utc).replace(minute=0, second=0, microsecond=0)
    key = target.strftime("%Y-%m-%dT%H:%M")
    try:
        i = times.index(key)
    except ValueError:
        # nearest hour available
        diffs = [
            abs((datetime.fromisoformat(t).replace(tzinfo=target.tzinfo) - target).total_seconds())
            for t in times
        ]
        i = min(range(len(times)), key=lambda k: diffs[k])
        if diffs[i] > 3 * 3600:
            return None
    out = {"forecast_time_utc": times[i]}
    for var in HOURLY.split(","):
        vals = hourly.get(var)
        out[var] = vals[i] if vals and i < len(vals) else None
    return out


class OpenMeteoProvider:
    provider_id = PROVIDER_ID

    def __init__(
        self, fetcher: CachedFetcher | None = None, cache_path: Path | None = None
    ) -> None:
        self.fetcher = fetcher or CachedFetcher(max_age=timedelta(hours=1))
        self.cache_path = cache_path
        self._geo: dict[str, dict[str, Any]] = (
            read_json(cache_path) if cache_path and cache_path.exists() else {}
        )

    def geocode(self, city: str | None, country: str | None) -> Geo | None:
        key = geocode_key(city, country)
        if not city:
            return None
        if key in self._geo:
            g = self._geo[key]
            return Geo(g["latitude"], g["longitude"], g["name"], g.get("country")) if g else None
        url = f"{GEOCODE_URL}?name={city.split(',')[0].strip().replace(' ', '%20')}&count=5&language=en&format=json"
        body = json.loads(
            self.fetcher.fetch(url, source=PROVIDER_ID, license_note="Open-Meteo CC BY 4.0").content
        )
        geo = None
        res = body.get("results") or []
        if country:
            match = [
                r
                for r in res
                if (r.get("country") or "").lower() == country.lower()
                or (r.get("country_code") or "").lower() == country.lower()
            ]
            res = match or res
        geo = parse_geocode({"results": res})
        self._geo[key] = (
            {
                "latitude": geo.latitude,
                "longitude": geo.longitude,
                "name": geo.name,
                "country": geo.country,
            }
            if geo
            else None
        )
        if self.cache_path:
            write_json(self.cache_path, self._geo)
        return geo

    def forecast_at(
        self, geo: Geo, kickoff_utc: datetime
    ) -> tuple[dict[str, Any] | None, datetime]:
        d = ensure_utc(kickoff_utc).date()
        url = f"{FORECAST_URL}?latitude={geo.latitude:.4f}&longitude={geo.longitude:.4f}&hourly={HOURLY}&timezone=UTC&start_date={d}&end_date={d}"
        f = self.fetcher.fetch(url, source=PROVIDER_ID, license_note="Open-Meteo CC BY 4.0")
        return pick_kickoff_hour(json.loads(f.content), kickoff_utc), f.provenance.observed_at


def capture_weather(
    provider: OpenMeteoProvider,
    events: list[Any],
    out_dir: Path,
    *,
    as_of: datetime | None = None,
    horizon_hours: float = 72.0,
    max_events: int = 200,
) -> dict[str, Any]:
    """events: EspnEvent-like objects with kickoff_utc, venue, venue_city, venue_country, espn_event_id, league.
    Appends one row per (event, capture) to weather/<date>.jsonl; every capture is kept (forecasts change)."""
    as_of = as_of or utc_now()
    stats = {
        "events": 0,
        "captured": 0,
        "no_venue": 0,
        "geocode_miss": 0,
        "forecast_miss": 0,
        "failures": [],
    }
    for ev in events[:max_events]:
        if not (
            as_of - timedelta(hours=3) <= ev.kickoff_utc <= as_of + timedelta(hours=horizon_hours)
        ):
            continue
        stats["events"] += 1
        city, country = getattr(ev, "venue_city", None), getattr(ev, "venue_country", None)
        if not city:
            stats["no_venue"] += 1
            continue
        try:
            geo = provider.geocode(city, country)
            if geo is None:
                stats["geocode_miss"] += 1
                continue
            fc, observed = provider.forecast_at(geo, ev.kickoff_utc)
        except Exception as exc:
            stats["failures"].append(f"{ev.espn_event_id}: {str(exc)[:100]}")
            continue
        if fc is None:
            stats["forecast_miss"] += 1
            continue
        row = {
            "schema": "weather_snapshot_v1",
            "provider": PROVIDER_ID,
            "espn_event_id": ev.espn_event_id,
            "league": ev.league,
            "kickoff_utc": ev.kickoff_utc.isoformat(),
            "captured_at": ensure_utc(observed).isoformat(),
            "hours_before_kickoff": round(
                (ev.kickoff_utc - ensure_utc(observed)).total_seconds() / 3600, 2
            ),
            "venue": getattr(ev, "venue", None),
            "venue_city": city,
            "venue_country": country,
            "latitude": geo.latitude,
            "longitude": geo.longitude,
            **fc,
        }
        append_jsonl(out_dir / f"{as_of:%Y-%m-%d}.jsonl", row)
        stats["captured"] += 1
    return stats
