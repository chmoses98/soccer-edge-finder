# soccer-edge-finder — accounting-data (routed-wager ledger)

**ACCOUNTING ONLY.** This branch records SOCCER bets the owner placed **manually** on Kalshi, as observed (read-only)
and delivered by `chmoses98/kalshi-bet-router`, and what the exchange later paid on them. It holds nothing else: no
model predictions, research snapshots or slate outputs. A row here says "the owner placed this bet", never "a model
recommended it". The SOCCER models' authority is unchanged by anything on this branch.

| file | contents |
|---|---|
| `data/accounting/wagers.jsonl` | one line per order (`soccer_accounted_wager.v1`), append-only |
| `data/accounting/settlements.jsonl` | one line per settled wager (`soccer_wager_settlement.v1`, `router-settlement-economics.v2`), append-only |

Identity is minted by the destination from the router's `source_bet_key`: `socw-` / `socs-` +
sha256(key)[:24]. The importers and validator live on `main` (`scripts/accounting/`, thin wrappers over the vendored
Edge Finder contract's shared `routed_ledger`). This orphan branch carries no `.github/`, so pull requests into it get
no CI; the router runs the destination's own validator and merges only when its gate passes. Existing lines are never
rewritten or removed.
