# ACTIONABLE SOCCER SLATE (latest state, not evidence)

slate `slate-20261110T165035Z-65785f` · generated 2026-11-10T16:50:35.823217Z · trigger `kalshi_capture` · mode `reprice_only`

**Kalshi prices observed 2026-11-10T16:47:29.647454Z (CURRENT at publish; CURRENT until 2026-11-10T17:07:29.647454Z, STALE after 2026-11-10T17:17:29.647454Z).** After that instant every price below is STALE_PRICE / NO ACTION: run REFRESH SOCCER SLATE.

model board generated - · simulations this update: 0 · Odds API calls this update: 0 (credits 0) · reprice 0.03s

**NO BETS** — every model family x market family x horizon is RESEARCH_ONLY: no contract side is bet_permitted; RESEARCH_CANDIDATE rows are shadow analysis only

## Fixtures

| kickoff | fixture | model | lineup | reference | context | priced | no model |
|---|---|---|---|---|---|---|---|

## Candidates on CURRENT prices (0; RESEARCH_ONLY = analysis, never a bet)

| fixture | contract | side | price | model p [80%] | fee-adj EV | worst case | bet up to | ref p | best | action |
|---|---|---|---|---|---|---|---|---|---|---|

## Counts

```
contract_sides: 0
fixtures: 0
fixtures_model_invalidated: 0
fixtures_model_missing: 0
```

Each input has its own timestamp and freshness (model, kalshi, reference, lineup, context). Recompute at READ time: a price is CURRENT only before its `action_valid_until` (= kalshi.current_until); after that treat it as STALE_PRICE / NO ACTION and run REFRESH SOCCER SLATE. Only action == ACTIONABLE permits a bet (bet_permitted). Every model family is RESEARCH_ONLY, so RESEARCH_CANDIDATE is analysis only. Never pair a probability from this file with a price from another file or another time.
