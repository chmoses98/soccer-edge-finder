"""International results dataset (remediation phase 16; audit §E, B7).

Source: `martj42/international_results` (GitHub), file `results.csv` — 49,547 men's full international
matches 1872-11-30 → 2026-08-26 with `date, home_team, away_team, home_score, away_score, tournament,
city, country, neutral`. Licence: CC0 1.0 Universal (the repository's LICENSE file is the CC0 legal
code). Pinned identity (2026-09-28): sha256
`df35268f8fc341ff7fb93d448b4e40356676ac35300a6b4461fd199a99ac1514`. The loader refuses a file whose hash
does not match the manifest unless `allow_unpinned=True` (research on a newer snapshot must say so).

This module builds the immutable normalised dataset (`soccer intl build-dataset`): one row per match with
team ids, date, tournament, competitive/friendly, neutral, home/away, confederation of each side, and a
point-in-time Elo for each side computed strictly from earlier rows of the same archive (never an external
rating snapshot). Only FIFA member associations (plus their historical predecessors) are modelled; the
CONIFA / regional sides present in the source are excluded and counted.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

SOURCE_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
SOURCE_LICENSE = "CC0 1.0 Universal (martj42/international_results LICENSE)"
PINNED_SHA256 = "df35268f8fc341ff7fb93d448b4e40356676ac35300a6b4461fd199a99ac1514"
DATASET_SCHEMA = "international_results_v1"

# FIFA member associations by confederation (2026), plus historical predecessors that appear in the
# source. Anything not listed is NON_FIFA (CONIFA / regional / island-games sides) and is excluded.
CONFEDERATIONS: dict[str, tuple[str, ...]] = {
    "UEFA": (
        "Albania",
        "Andorra",
        "Armenia",
        "Austria",
        "Azerbaijan",
        "Belarus",
        "Belgium",
        "Bosnia and Herzegovina",
        "Bulgaria",
        "Croatia",
        "Cyprus",
        "Czech Republic",
        "Denmark",
        "England",
        "Estonia",
        "Faroe Islands",
        "Finland",
        "France",
        "Georgia",
        "Germany",
        "Gibraltar",
        "Greece",
        "Hungary",
        "Iceland",
        "Israel",
        "Italy",
        "Kazakhstan",
        "Kosovo",
        "Latvia",
        "Liechtenstein",
        "Lithuania",
        "Luxembourg",
        "Malta",
        "Moldova",
        "Montenegro",
        "Netherlands",
        "North Macedonia",
        "Northern Ireland",
        "Norway",
        "Poland",
        "Portugal",
        "Republic of Ireland",
        "Romania",
        "Russia",
        "San Marino",
        "Scotland",
        "Serbia",
        "Slovakia",
        "Slovenia",
        "Spain",
        "Sweden",
        "Switzerland",
        "Turkey",
        "Ukraine",
        "Wales",
        # historical
        "Yugoslavia",
        "Czechoslovakia",
        "Soviet Union",
        "German DR",
        "Serbia and Montenegro",
        "Saarland",
        "Ireland",
        "Bohemia",
        "Russian Empire",
    ),
    "CONMEBOL": (
        "Argentina",
        "Bolivia",
        "Brazil",
        "Chile",
        "Colombia",
        "Ecuador",
        "Paraguay",
        "Peru",
        "Uruguay",
        "Venezuela",
    ),
    "CONCACAF": (
        "Anguilla",
        "Antigua and Barbuda",
        "Aruba",
        "Bahamas",
        "Barbados",
        "Belize",
        "Bermuda",
        "Bonaire",
        "British Virgin Islands",
        "Canada",
        "Cayman Islands",
        "Costa Rica",
        "Cuba",
        "Curaçao",
        "Dominica",
        "Dominican Republic",
        "El Salvador",
        "French Guiana",
        "Grenada",
        "Guadeloupe",
        "Guatemala",
        "Guyana",
        "Haiti",
        "Honduras",
        "Jamaica",
        "Martinique",
        "Mexico",
        "Montserrat",
        "Nicaragua",
        "Panama",
        "Puerto Rico",
        "Saint Kitts and Nevis",
        "Saint Lucia",
        "Saint Martin",
        "Saint Vincent and the Grenadines",
        "Sint Maarten",
        "Suriname",
        "Trinidad and Tobago",
        "Turks and Caicos Islands",
        "United States",
        "United States Virgin Islands",
        # historical / associate
        "Netherlands Antilles",
        "Saint Barthélemy",
    ),
    "CAF": (
        "Algeria",
        "Angola",
        "Benin",
        "Botswana",
        "Burkina Faso",
        "Burundi",
        "Cameroon",
        "Cape Verde",
        "Central African Republic",
        "Chad",
        "Comoros",
        "Congo",
        "DR Congo",
        "Djibouti",
        "Egypt",
        "Equatorial Guinea",
        "Eritrea",
        "Eswatini",
        "Ethiopia",
        "Gabon",
        "Gambia",
        "Ghana",
        "Guinea",
        "Guinea-Bissau",
        "Ivory Coast",
        "Kenya",
        "Lesotho",
        "Liberia",
        "Libya",
        "Madagascar",
        "Malawi",
        "Mali",
        "Mauritania",
        "Mauritius",
        "Morocco",
        "Mozambique",
        "Namibia",
        "Niger",
        "Nigeria",
        "Rwanda",
        "São Tomé and Príncipe",
        "Senegal",
        "Seychelles",
        "Sierra Leone",
        "Somalia",
        "South Africa",
        "South Sudan",
        "Sudan",
        "Tanzania",
        "Togo",
        "Tunisia",
        "Uganda",
        "Zambia",
        "Zimbabwe",
        # historical / associate
        "Zaire",
        "Rhodesia",
        "Réunion",
        "Mayotte",
        "Zanzibar",
        "Upper Volta",
        "Dahomey",
        "Swaziland",
    ),
    "AFC": (
        "Afghanistan",
        "Australia",
        "Bahrain",
        "Bangladesh",
        "Bhutan",
        "Brunei",
        "Cambodia",
        "China",
        "Guam",
        "Hong Kong",
        "India",
        "Indonesia",
        "Iran",
        "Iraq",
        "Japan",
        "Jordan",
        "Kuwait",
        "Kyrgyzstan",
        "Laos",
        "Lebanon",
        "Macau",
        "Malaysia",
        "Maldives",
        "Mongolia",
        "Myanmar",
        "Nepal",
        "North Korea",
        "Northern Mariana Islands",
        "Oman",
        "Pakistan",
        "Palestine",
        "Philippines",
        "Qatar",
        "Saudi Arabia",
        "Singapore",
        "South Korea",
        "Sri Lanka",
        "Syria",
        "Taiwan",
        "Tajikistan",
        "Thailand",
        "Timor-Leste",
        "Turkmenistan",
        "United Arab Emirates",
        "Uzbekistan",
        "Vietnam",
        "Yemen",
        # historical
        "Vietnam Republic",
        "Yemen DPR",
        "Burma",
        "Ceylon",
        "Malaya",
    ),
    "OFC": (
        "American Samoa",
        "Cook Islands",
        "Fiji",
        "New Caledonia",
        "New Zealand",
        "Papua New Guinea",
        "Samoa",
        "Solomon Islands",
        "Tahiti",
        "Tonga",
        "Vanuatu",
        "Tuvalu",
        "Kiribati",
        "Niue",
    ),
}
TEAM_TO_CONFEDERATION: dict[str, str] = {t: c for c, ts in CONFEDERATIONS.items() for t in ts}

# tournaments treated as friendlies (everything else is competitive)
FRIENDLY_TOURNAMENTS = {"Friendly"}
# Elo tournament weights (World Football Elo convention), used only for the point-in-time prior centre
_ELO_WEIGHT_RULES: tuple[tuple[str, float], ...] = (
    ("FIFA World Cup qualification", 40),
    ("FIFA World Cup", 60),
    ("UEFA Euro qualification", 40),
    ("UEFA Euro", 50),
    ("Copa América", 50),
    ("African Cup of Nations qualification", 40),
    ("African Cup of Nations", 50),
    ("AFC Asian Cup qualification", 40),
    ("AFC Asian Cup", 50),
    ("Gold Cup", 50),
    ("Confederations Cup", 50),
    ("Nations League", 40),
    ("qualification", 40),
    ("Friendly", 20),
)


def elo_weight(tournament: str) -> float:
    for key, w in _ELO_WEIGHT_RULES:
        if key.lower() in tournament.lower():
            return w
    return 30.0  # other continental / regional tournaments


def team_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"intl:{slug}"


@dataclass(frozen=True)
class IntlMatch:
    date: date
    home_team: str
    away_team: str
    home_id: str
    away_id: str
    home_goals: int
    away_goals: int
    tournament: str
    competitive: bool
    neutral: bool
    home_conf: str
    away_conf: str
    city: str
    country: str
    home_elo_pre: float
    away_elo_pre: float

    def to_row(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_id": self.home_id,
            "away_id": self.away_id,
            "home_goals": self.home_goals,
            "away_goals": self.away_goals,
            "tournament": self.tournament,
            "competitive": int(self.competitive),
            "neutral": int(self.neutral),
            "home_conf": self.home_conf,
            "away_conf": self.away_conf,
            "city": self.city,
            "country": self.country,
            "home_elo_pre": round(self.home_elo_pre, 2),
            "away_elo_pre": round(self.away_elo_pre, 2),
        }


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source(path: Path, *, allow_unpinned: bool = False) -> tuple[list[dict[str, str]], str]:
    digest = sha256_of(path)
    if digest != PINNED_SHA256 and not allow_unpinned:
        raise ValueError(
            f"international results file hash {digest[:12]}… does not match the pinned snapshot "
            f"{PINNED_SHA256[:12]}…; pass allow_unpinned=True to build from a newer snapshot"
        )
    with path.open(encoding="utf-8-sig") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("date")]
    return rows, digest


def compute_point_in_time_elo(
    rows: Iterable[dict[str, str]],
    *,
    k_base: float = 1.0,
    home_adv: float = 100.0,
    start: float = 1500.0,
) -> list[tuple[float, float]]:
    """World-Football-Elo-style ratings computed in date order from the archive itself; the returned
    pre-match ratings for each row use only strictly earlier rows (a match on the same day does not
    see the other's result)."""
    ratings: dict[str, float] = {}
    pending: list[tuple[str, float]] = []
    out: list[tuple[float, float]] = []
    last_date = None
    for r in rows:
        d = r["date"]
        if d != last_date:
            for team, new in pending:
                ratings[team] = new
            pending = []
            last_date = d
        h, a = r["home_team"], r["away_team"]
        rh, ra = ratings.get(h, start), ratings.get(a, start)
        out.append((rh, ra))
        try:
            hg, ag = int(float(r["home_score"])), int(float(r["away_score"]))
        except (ValueError, TypeError):
            continue
        neutral = str(r.get("neutral", "")).upper() == "TRUE"
        dr = rh - ra + (0.0 if neutral else home_adv)
        exp_h = 1.0 / (1.0 + 10 ** (-dr / 400.0))
        res = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
        margin = abs(hg - ag)
        gmult = 1.0 if margin <= 1 else 1.5 if margin == 2 else (11 + margin) / 8
        k = k_base * elo_weight(r.get("tournament", "")) * gmult
        delta = k * (res - exp_h)
        pending.append((h, rh + delta))
        pending.append((a, ra - delta))
    return out


def normalise(rows: list[dict[str, str]]) -> tuple[list[IntlMatch], dict[str, Any]]:
    rows = sorted(rows, key=lambda r: (r["date"], r["home_team"], r["away_team"]))
    elos = compute_point_in_time_elo(rows)
    out: list[IntlMatch] = []
    excluded: dict[str, int] = {}
    bad = 0
    for r, (eh, ea) in zip(rows, elos):
        h, a = r["home_team"], r["away_team"]
        ch, ca = TEAM_TO_CONFEDERATION.get(h), TEAM_TO_CONFEDERATION.get(a)
        if ch is None or ca is None:
            for t, c in ((h, ch), (a, ca)):
                if c is None:
                    excluded[t] = excluded.get(t, 0) + 1
            continue
        try:
            hg, ag = int(float(r["home_score"])), int(float(r["away_score"]))
            d = date.fromisoformat(r["date"])
        except (ValueError, TypeError):
            bad += 1
            continue
        out.append(
            IntlMatch(
                d,
                h,
                a,
                team_id(h),
                team_id(a),
                hg,
                ag,
                r.get("tournament", ""),
                r.get("tournament", "") not in FRIENDLY_TOURNAMENTS,
                str(r.get("neutral", "")).upper() == "TRUE",
                ch,
                ca,
                r.get("city", ""),
                r.get("country", ""),
                eh,
                ea,
            )
        )
    stats = {
        "source_rows": len(rows),
        "modelled_rows": len(out),
        "excluded_rows_non_fifa": len(rows) - len(out) - bad,
        "unparsable_rows": bad,
        "excluded_teams": dict(sorted(excluded.items(), key=lambda kv: -kv[1])),
        "teams_modelled": len({m.home_id for m in out} | {m.away_id for m in out}),
        "neutral_share": (sum(m.neutral for m in out) / len(out)) if out else None,
        "friendly_share": (sum(not m.competitive for m in out) / len(out)) if out else None,
        "by_confederation": _count(m.home_conf for m in out),
    }
    return out, stats


def _count(xs: Iterable[str]) -> dict[str, int]:
    c: dict[str, int] = {}
    for x in xs:
        c[x] = c.get(x, 0) + 1
    return dict(sorted(c.items()))


DATASET_COLUMNS = list(
    IntlMatch(
        date(2000, 1, 1), "", "", "", "", 0, 0, "", True, False, "", "", "", "", 0.0, 0.0
    ).to_row()
)


def write_dataset(
    matches: list[IntlMatch], out_dir: Path, *, source_sha256: str, stats: dict[str, Any]
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=DATASET_COLUMNS)
    w.writeheader()
    for m in matches:
        w.writerow(m.to_row())
    data = buf.getvalue().encode("utf-8")
    gz_path = out_dir / "results_v1.csv.gz"
    with (
        gz_path.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as fh,
    ):
        fh.write(data)  # mtime=0 + no filename: byte-identical rebuilds
    manifest = {
        "schema": DATASET_SCHEMA,
        "source_url": SOURCE_URL,
        "source_license": SOURCE_LICENSE,
        "source_sha256": source_sha256,
        "pinned_sha256": PINNED_SHA256,
        "dataset_file": gz_path.name,
        "dataset_sha256_uncompressed": hashlib.sha256(data).hexdigest(),
        "rows": len(matches),
        "date_min": matches[0].date.isoformat() if matches else None,
        "date_max": matches[-1].date.isoformat() if matches else None,
        "columns": DATASET_COLUMNS,
        "confederations": {c: len(ts) for c, ts in CONFEDERATIONS.items()},
        "elo": "World-Football-Elo-style, K by tournament class, home advantage 100 (0 on neutral), computed strictly from earlier rows of this archive",
        "stats": stats,
    }
    (out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "confederations.json").write_text(
        json.dumps(CONFEDERATIONS, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def read_dataset(out_dir: Path) -> list[dict[str, Any]]:
    gz_path = out_dir / "results_v1.csv.gz"
    with gzip.open(gz_path, "rt", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["home_goals"] = int(r["home_goals"])
        r["away_goals"] = int(r["away_goals"])
        r["competitive"] = r["competitive"] == "1"
        r["neutral"] = r["neutral"] == "1"
        r["home_elo_pre"] = float(r["home_elo_pre"])
        r["away_elo_pre"] = float(r["away_elo_pre"])
    return rows


def main(argv: list[str] | None = None) -> int:
    """Rebuild `data/international/` from a local copy of the source CSV (hash-pinned by default)."""
    import argparse

    ap = argparse.ArgumentParser(description="rebuild the international results dataset")
    ap.add_argument("source_csv", help="local copy of martj42/international_results results.csv")
    ap.add_argument(
        "--out-dir", default=str(Path(__file__).resolve().parents[3] / "data" / "international")
    )
    ap.add_argument(
        "--allow-unpinned", action="store_true", help="build from a newer source snapshot"
    )
    a = ap.parse_args(argv)
    rows, digest = load_source(Path(a.source_csv), allow_unpinned=a.allow_unpinned)
    matches, stats = normalise(rows)
    manifest = write_dataset(matches, Path(a.out_dir), source_sha256=digest, stats=stats)
    print(json.dumps({k: manifest[k] for k in ("rows", "date_min", "date_max", "pinned_sha256")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
