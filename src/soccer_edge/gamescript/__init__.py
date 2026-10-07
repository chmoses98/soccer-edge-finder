"""Soccer game-script engine (`soccer_scripts_v1`): simulation-derived match archetypes over the joint model
distribution, script-conditional pricing of every supported contract, and price-time script survivability.

Design (docs/GAME_SCRIPTS.md):

* MODEL TIME (`conditional.py`, inside a model run): the per-world Dixon-Coles score matrices of world_sim_v2 and
  an exact, world-independent timing kernel (`kernel.py`) define a joint distribution over
  (full-time score, half-time score, first scorer). Every script (`taxonomy.py`) is a deterministic function of
  (full-time score, first scorer), so script shares, P(contract | script) and per-script outcome profiles are
  exact sums - no extra simulation, no Monte Carlo noise, and P(M) = sum_S P(S) P(M|S) holds to rounding.
* PRICE TIME (`survivability.py`, `expressions.py`, inside a reprice): cached conditionals x the current
  executable ask and verified fee -> per-script conditional edge, support/oppose, survivability label,
  counter-case, robust/script-specific ranking and same-thesis groups. Zero simulations.

Scripts are market-blind: nothing here reads a Kalshi price before the price-time layer.
"""
