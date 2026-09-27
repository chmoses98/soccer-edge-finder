# Data source audit

Probed on 2026-09-27 from a GitHub-hosted `ubuntu-latest` runner by `.github/workflows/probe-sources.yml`
(`scripts/probe_sources.py`). Only sources that returned a usable payload are marked reachable.
The development container used for this build could reach GitHub and PyPI only, so everything
below was verified from the runner, which is also where production will run.

| Source | Data supplied | Cost | Auth | Rate limits | Historical depth | Coverage | Cloud reachability (runner) | Licensing / redistribution | Fallback | Production suitability |
|---|---|---|---|---|---|---|---|---|---|---|
| **openfootball/football.json** (GitHub raw) | fixtures, kickoff (local time), rounds, FT/HT scores | free | none | GitHub raw (generous) | 2010s→ current season | EPL, Championship, La Liga, Bundesliga, Serie A, Ligue 1 (2026-27 present for all five), Eredivisie, Primeira, Süper Lig, Austria; **no UEFA competitions** | ✅ 200 (30–110 ms) | public domain (CC0-style) | ESPN scoreboard | **Primary fixture/result provider (implemented)**; kickoff time zone assumed from country (flagged UNVERIFIED) |
| **Club-Football-Match-Data-2000-2025** (GitHub raw, xgabora) | 238,858 matches 2000→2026-09-03, FT/HT, shots, cards, corners, Bet365 pre-match 1X2 + O/U 2.5 + AH, max odds, ClubElo pre-match | free | none | GitHub raw | 26 seasons, 38 divisions | top-5 + 30 other leagues | ✅ 200 (45 MB, ~5 s) | redistribution of football-data.co.uk + ClubElo; research use; upstream terms apply | football-data.co.uk direct | **Primary research/history provider (implemented)**; odds are *not* closing lines |
| **football-data.co.uk** (direct CSV) | as above per season file, plus **closing** odds (B365C*, PSC*, AvgC*) from 2019-20 and **HxG/AxG** columns in current files; `fixtures.csv` = upcoming fixtures with current bookmaker odds | free | none | polite | 1993→ | 22 European divisions + extras | ✅ 200 (0.8 s) | free for personal/research use; attribution requested; no resale | GitHub redistribution | **Closing-line benchmark + live reference odds (adapter implemented; research-fetch workflow pending)** |
| **ESPN site API** (`site.api.espn.com`) | scoreboard per league incl. UCL/UEL, match status, lineups/rosters in summary endpoints, venue, odds snippets | free | none (undocumented) | unknown; be gentle | current season + limited past | broad incl. UEFA, MLS, internationals | ✅ 200 (EPL and UCL) | undocumented, unofficial; no redistribution | openfootball | **Best free candidate for UEFA fixtures + lineup provider**; adapter is on the roadmap, not implemented |
| **Open-Meteo** | hourly forecast by lat/lon | free (non-commercial) | none | 10k req/day | forecast + archive | global | ✅ 200 | CC-BY 4.0 | none | Weather provider candidate; effect size on goals is small and unvalidated → low priority |
| **Kalshi public API** (`api.elections.kalshi.com/trade-api/v2`) | series, events, markets, order books, milestones, settlement fields | free | none for reads | ~4 rps safe; 429 on tight loops | open markets; historical endpoint exists | all Kalshi soccer | ✅ 200 (`/series`, `/milestones?type=soccer_tournament_multi_leg`, `/markets?series_ticker=KXEPLTOTAL`) | Kalshi ToS; public data | none | **Primary market source (implemented)** |
| understat.com | team/player xG by match (embedded JSON in HTML) | free | none | scraping | 2014→ | top-5 + RFPL | ✅ 200 HTML | ToS grey area; scraping discouraged | football-data.co.uk xG columns | Not used; prefer football-data.co.uk xG once its coverage is verified |
| football-data.org v4 | fixtures, standings, lineups (paid tiers), 12 competitions free | free tier 10 req/min | **token required** | 10/min | 2018→ | top-5, UCL, WC, EC | ❌ 403 without token | attribution required | ESPN | Optional; adapter slot exists (`FOOTBALL_DATA_ORG_TOKEN` in `.env.example`), not implemented |
| ClubElo API | daily club Elo | free | none | polite | 1939→ | Europe | ❌ 502 during probe | free with attribution | Elo columns in the GitHub dataset | Retry later; Elo already available historically via the redistribution |
| FBref (Sports Reference) | detailed stats, xG, shots, lineups | free | none | Cloudflare bot check | deep | broad | ❌ 403 | scraping prohibited without permission | football-data.co.uk | **Do not use** from runners |
| FotMob internal API | lineups, xG, match events | free | undocumented | bot protection | current | broad | ❌ 404 (HTML shell) | unofficial | ESPN | Not usable |
| SofaScore internal API | lineups, events, ratings | free | undocumented | 403 for bots | current | broad | ❌ 403 | unofficial | ESPN | Not usable |
| The Odds API | multi-book odds incl. Pinnacle | 500 req/month free, then paid | **key required** | tiered | none (live only) | broad | ❌ 401 (no key) | commercial | football-data.co.uk `fixtures.csv` | Premium adapter slot; not implemented; **no paid services per mission** |
| StatsBomb / Opta / Wyscout | event data, lineups, xG | paid (StatsBomb open data is free but historical only) | key | n/a | varies | varies | not probed | commercial | — | Premium `EventDataProvider` slot; interface exists, adapter later |

## Provider interfaces vs implementations

| Interface | Implemented by | Status |
|---|---|---|
| `FixtureProvider` | `OpenFootballProvider` | working (fixtures + results, 5 leagues + more) |
| `TeamStatsProvider` | derived from results (`run/modeling.py`) | working (goals); xG/shots ingestion from football-data.co.uk pending |
| `OddsProvider` | `ClubFootballDataProvider` (historical), `FootballDataCoUkProvider` (closing + upcoming) | historical working; live `fixtures.csv` parsing pending |
| `LineupProvider`, `InjuryProvider` | none | **not wired** — player markets are dispositioned `UNSUPPORTED_FAMILY` with that reason |
| `PlayerStatsProvider`, `EventDataProvider` | none | premium/scrape sources only; interface reserved |
| `WeatherProvider` | none | Open-Meteo reachable; adapter deferred (unvalidated effect) |

## Freshness and provenance

Every observation carries `source`, `source_url`, `observed_at`, optional `effective_at`,
`content_hash`, `license` and quality flags (`OK, STALE, PARTIAL, CONFLICTING, UNVERIFIED, DERIVED,
SYNTHETIC`). `SYNTHETIC` observations (the offline Kalshi surface) can never be used for production.

## Gaps that matter

* **UEFA fixtures** are not in openfootball; ESPN is the reachable free option. Until an adapter
  exists, UCL/UEL/UECL contracts are dispositioned `UNMAPPED_EVENT`/`NO_FIXTURE`, counted, and
  reported — never silently dropped.
* **Lineups/injuries**: no free, reachable, licensed source was verified. The lineup layer exists in
  the model (`MatchContext.home_players`) and is exercised by tests, but production runs price
  with `lineup_state=unknown` and say so in every recommendation's risks.
* **Closing lines**: only football-data.co.uk direct files carry them; the runner can fetch them,
  the dev container cannot. The research in `data/research/` therefore benchmarks against Bet365
  *pre-match* odds and labels the result accordingly.
