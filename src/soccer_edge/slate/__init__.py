"""Live-slate layer: cached model distributions (model board) repriced against fresh Kalshi captures.

MODEL COMPUTATION (`soccer run`, full or fast) writes the board; MARKET REPRICING (`slate.reprice`) reads
it with the latest Kalshi sweep and publishes `runs/latest.actionable_slate.v1.json`. See
docs/ACTIONABLE_SLATE.md.
"""
