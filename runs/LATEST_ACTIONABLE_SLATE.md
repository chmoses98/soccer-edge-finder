# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261116T221232Z-ac60c3` · generated 2026-11-16T22:12:32.766968Z · trigger `kalshi_capture:slate_refresh` · mode `reprice_only`

**Kalshi prices observed 2026-11-16T22:09:13.603436Z (CURRENT at publish; CURRENT until 2026-11-16T22:29:13.603436Z, STALE after 2026-11-16T22:39:13.603436Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated 2026-11-16T17:15:51.165310Z · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.56s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|
| 2026-11-17T00:00:00Z | Martinique vs Aruba (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-17T00:00:00Z | Trinidad and Tobago vs Antigua and Barbuda (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-17T01:00:00Z | Canada vs Guatemala (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 25 | 0 |
| 2026-11-17T13:10:00Z | Japan vs Paraguay (fifa.friendly) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 23 | 0 |
| 2026-11-17T15:30:00Z | Saudi Arabia vs Uzbekistan (fifa.friendly) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 23 | 0 |
| 2026-11-17T16:00:00Z | Jordan vs Australia (fifa.friendly) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 23 | 0 |
| 2026-11-17T19:00:00Z | Belize vs Sint Maarten (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-17T19:00:00Z | Dominica vs Cayman Islands (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-17T19:00:00Z | St. Lucia vs Barbados (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-17T19:00:00Z | St. Kitts and Nevis vs Bonaire (concacaf.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-17T19:45:00Z | Bosnia and Herzegovina vs Romania (uefa.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-17T19:45:00Z | Denmark vs Norway (uefa.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-17T19:45:00Z | Hungary vs Northern Ireland (uefa.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-17T19:45:00Z | Republic of Ireland vs Kosovo (uefa.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-17T19:45:00Z | Israel vs Austria (uefa.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-17T19:45:00Z | Poland vs Sweden (uefa.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-17T19:45:00Z | Ukraine vs Georgia (uefa.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-17T19:45:00Z | Wales vs Portugal (uefa.nations_league) | VALID (CURRENT) | unconfirmed (CURRENT) | UNAVAILABLE | CURRENT | 61 | 1 |
| 2026-11-17T23:00:00Z | Argentina vs Costa Rica (fifa.friendly) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-17T23:30:00Z | Uruguay vs Dominican Republic (fifa.friendly) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 14 | 0 |
| 2026-11-18T00:00:00Z | United States vs Haiti (concacaf.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 16 | 0 |
| 2026-11-18T01:00:00Z | El Salvador vs St. Martin (concacaf.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 16 | 0 |
| 2026-11-18T02:30:00Z | Mexico vs Jamaica (concacaf.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 16 | 0 |
| 2026-11-18T03:00:00Z | Nicaragua vs Montserrat (concacaf.nations_league) | VALID (CURRENT) | unknown (UNAVAILABLE) | UNAVAILABLE | CURRENT | 16 | 0 |

## Candidates on CURRENT prices (0; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|

## Counts

```
action_EXCLUDED_BY_GATE: 142
action_NO_EDGE: 1267
action_NO_QUOTE: 151
contract_sides: 1560
fixtures: 24
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
