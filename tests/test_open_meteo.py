from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from soccer_edge.providers.open_meteo import (
    Geo,
    capture_weather,
    geocode_key,
    parse_geocode,
    pick_kickoff_hour,
)


def test_geocode_and_hour_pick():
    assert geocode_key(" Bournemouth ", "England") == "bournemouth|england"
    assert parse_geocode({"results": []}) is None
    g = parse_geocode(
        {
            "results": [
                {
                    "latitude": 50.72,
                    "longitude": -1.88,
                    "name": "Bournemouth",
                    "country": "United Kingdom",
                }
            ]
        }
    )
    assert g == Geo(50.72, -1.88, "Bournemouth", "United Kingdom")
    body = {
        "hourly": {
            "time": [f"2026-09-20T{h:02d}:00" for h in range(24)],
            "temperature_2m": list(range(24)),
            "precipitation": [0.0] * 24,
            "wind_speed_10m": [5.0] * 24,
        }
    }
    fc = pick_kickoff_hour(body, datetime(2026, 9, 20, 13, 30, tzinfo=UTC))
    assert (
        fc["forecast_time_utc"] == "2026-09-20T13:00"
        and fc["temperature_2m"] == 13
        and fc["weather_code"] is None
    )
    assert pick_kickoff_hour({"hourly": {}}, datetime(2026, 9, 20, 13, tzinfo=UTC)) is None
    assert (
        pick_kickoff_hour(body, datetime(2026, 9, 21, 13, tzinfo=UTC)) is None
    )  # >3h from any available hour


def test_capture_weather_context_only(tmp_path):
    class P:
        def geocode(self, city, country):
            return Geo(50.72, -1.88, city, country) if city != "Nowhere" else None

        def forecast_at(self, geo, ko):
            return {
                "forecast_time_utc": ko.strftime("%Y-%m-%dT%H:00"),
                "temperature_2m": 12.5,
                "precipitation": 0.2,
                "wind_speed_10m": 20.0,
            }, datetime(2026, 9, 19, 12, tzinfo=UTC)

    as_of = datetime(2026, 9, 19, 12, tzinfo=UTC)
    evs = [
        SimpleNamespace(
            espn_event_id="1",
            league="eng.1",
            kickoff_utc=datetime(2026, 9, 20, 13, tzinfo=UTC),
            venue="Vitality Stadium",
            venue_city="Bournemouth",
            venue_country="England",
        ),
        SimpleNamespace(
            espn_event_id="2",
            league="eng.1",
            kickoff_utc=datetime(2026, 9, 20, 15, tzinfo=UTC),
            venue=None,
            venue_city=None,
            venue_country=None,
        ),
        SimpleNamespace(
            espn_event_id="3",
            league="eng.1",
            kickoff_utc=datetime(2026, 9, 20, 15, tzinfo=UTC),
            venue="X",
            venue_city="Nowhere",
            venue_country="England",
        ),
        SimpleNamespace(
            espn_event_id="4",
            league="eng.1",
            kickoff_utc=datetime(2026, 9, 30, 15, tzinfo=UTC),
            venue="X",
            venue_city="Bournemouth",
            venue_country="England",
        ),  # outside 72h
    ]
    st = capture_weather(P(), evs, tmp_path, as_of=as_of)
    assert st == {
        "events": 3,
        "captured": 1,
        "no_venue": 1,
        "geocode_miss": 1,
        "forecast_miss": 0,
        "failures": [],
    }
    import json

    rows = [json.loads(x) for x in (tmp_path / "2026-09-19.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["hours_before_kickoff"] == 25.0 and rows[0]["schema"] == "weather_snapshot_v1"
