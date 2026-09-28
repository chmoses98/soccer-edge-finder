# Weather capture (Phase 15) — context only

Source: Open-Meteo (free, keyless, CC BY 4.0): geocoding API for venue coordinates and the forecast API for the
kickoff hour. Implemented in `src/soccer_edge/providers/open_meteo.py`; captured by `soccer espn-sync`
(`.github/workflows/espn-lineups.yml`, every 2 h) for every ESPN event kicking off within the next 72 h.

What is stored (`weather/<capture-date>.jsonl` on `data-archive`, schema `weather_snapshot_v1`): ESPN event id,
league, kickoff, `captured_at` (forecast issue time), hours before kickoff, venue name/city/country, coordinates,
and the kickoff-hour values of temperature, precipitation, precipitation probability, wind speed and gusts,
humidity and WMO weather code. **Every capture is kept** — the point is to have forecast revisions at different
horizons, not a single "the weather was" value. Venue coordinates come from the ESPN venue address geocoded once
and cached (`weather/geocode_cache.json`, append-only); a venue without a city is counted, not guessed.

What it is not: no model reads it. Weather is not a feature of any priced family, and no research result exists
yet that says it should be. When at least a season of snapshots exists, the pre-registered question is: does
wind/precipitation at kickoff shift realised total goals after conditioning on the benchmark's expected total?
(Effect sizes in the literature are small and mostly on totals; the burden of proof is on the feature.)
