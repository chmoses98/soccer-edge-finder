"""Script taxonomy `soccer_scripts_v1`: six primary match archetypes that partition every modelled realisation.

Every regulation realisation (full-time score h-a, first scorer) belongs to exactly one script:

1. TIGHT_LOW_EVENT   at most one goal in the match                         (0-0, 1-0, 0-1)
2. OPEN_END_TO_END   both sides score at least twice                       (2-2, 3-2, 2-3, 3-3, ...)
3. HOME_CONTROL      home scores first and wins                            (2-0, 2-1, 3-0, 3-1, ...)
4. HOME_CHASE        away scores first; home recovers at least a draw      (1-1, 2-1 / 3-1 comebacks)
5. AWAY_CHASE        home scores first; away recovers at least a draw      (1-1, 1-2 / 1-3 comebacks)
6. AWAY_CONTROL      away scores first and wins                            (0-2, 1-2, 0-3, 1-3, ...)

Proof of partition: (1) and (2) are disjoint (total <= 1 vs total >= 4). Outside them the match has >= 2 goals,
hence a first scorer, and at least one side has <= 1 goal. If home scored first, home either wins (3) or does not
(5: draw or away win); symmetrically for an away first goal (6 / 4). The only draw outside (1)/(2) is 1-1, a chase.

Choice (docs/GAME_SCRIPTS.md section 2): the production engine world_sim_v2 draws the full-time score from the fitted
Dixon-Coles matrix and goal times i.i.d. given the count; it has NO game-state dynamics. The facts a match shape can
carry are therefore the score and the order of goals, and the first goal is the one ordering fact every market
family can be conditioned on exactly. Candidates compared on the 32 fixtures of the 2026-10-03 production board
(mean largest share / scripts at or above the materiality floor / mean between-script R^2 over 10 key markets):

  score-band taxonomy (tight = each side <= 1)            0.43 / 3.4 / 0.52
  tight = level 0-0 or 1-1, comeback wins only           0.42 / 3.6 / 0.55
  first scorer x result (5 scripts)                      0.45 / 3.9 / 0.56
  soccer_scripts_v1 (this taxonomy)                      0.36 / 4.9 / 0.58
  v1 + margin split of the control scripts (8 scripts)   0.33 / 5.4 / 0.64  (rejected: 8 scripts)

A CHAOTIC/VOLATILE primary script (lead changed hands) was rejected: those worlds are the comeback wins inside the
CHASE scripts and part of OPEN_END_TO_END; a separate script would only re-slice them by a timing assumption that
is not fitted. Volatility is published per script instead (temporal profile: P(lead changed hands), minutes led).

Order of the published arrays: the canonical order below runs from home-dominant to away-dominant so a
script x market matrix reads left (home) to right (away).
"""

from __future__ import annotations

from dataclasses import dataclass

TAXONOMY_VERSION = "soccer_scripts_v1"


@dataclass(frozen=True)
class ScriptDef:
    script_id: str
    title: str
    definition: str  # exact rule, for display and audit
    lean: str  # HOME | AWAY | NONE
    tempo: str  # LOW | HIGH | MIXED


SCRIPTS: tuple[ScriptDef, ...] = (
    ScriptDef(
        "HOME_CONTROL",
        "Home control",
        "Home side scores first and wins; not both sides score twice.",
        "HOME",
        "MIXED",
    ),
    ScriptDef(
        "HOME_CHASE",
        "Home chase",
        "Away side scores first; home side recovers at least a draw (1-1, or a comeback win while the away side "
        "scores once).",
        "HOME",
        "MIXED",
    ),
    ScriptDef(
        "TIGHT_LOW_EVENT",
        "Tight, low event",
        "At most one goal in the match (0-0, 1-0 or 0-1).",
        "NONE",
        "LOW",
    ),
    ScriptDef(
        "OPEN_END_TO_END",
        "Open, end to end",
        "Both sides score at least twice (2-2, 3-2, 2-3 and higher).",
        "NONE",
        "HIGH",
    ),
    ScriptDef(
        "AWAY_CHASE",
        "Away chase",
        "Home side scores first; away side recovers at least a draw (1-1, or a comeback win while the home side "
        "scores once).",
        "AWAY",
        "MIXED",
    ),
    ScriptDef(
        "AWAY_CONTROL",
        "Away control",
        "Away side scores first and wins; not both sides score twice.",
        "AWAY",
        "MIXED",
    ),
)
SCRIPT_IDS: tuple[str, ...] = tuple(s.script_id for s in SCRIPTS)
K = len(SCRIPTS)
INDEX = {s: i for i, s in enumerate(SCRIPT_IDS)}

# first-scorer codes (as JointOutcome.first_goal_team): 0 none, 1 home, 2 away
FT_NONE, FT_HOME, FT_AWAY = 0, 1, 2


def script_of(h: int, a: int, first: int) -> str:
    """The one primary script of a regulation realisation (h-a, first scorer). Raises on an impossible state."""
    if (h + a == 0) != (first == FT_NONE):
        raise ValueError(f"inconsistent realisation {h}-{a} first={first}")
    if (first == FT_HOME and h == 0) or (first == FT_AWAY and a == 0):
        raise ValueError(f"first scorer without a goal: {h}-{a} first={first}")
    if h + a <= 1:
        return "TIGHT_LOW_EVENT"
    if h >= 2 and a >= 2:
        return "OPEN_END_TO_END"
    if first == FT_HOME:
        return "HOME_CONTROL" if h > a else "AWAY_CHASE"
    return "AWAY_CONTROL" if a > h else "HOME_CHASE"


# --------------------------------------------------------------------------------- materiality (section 10)
# A script is MATERIAL for survivability when its simulation share is at least half of the uniform share
# 1/K (K = 6 -> 1/12 = 8.33 %). Scale-free (it moves with the taxonomy size), deterministic, and it keeps a
# 3-5 % minority script from making a position look fragile while every script still has a published share.
MATERIAL_SHARE_RULE = "simulation_share >= 1 / (2 * K)"
MATERIAL_SHARE_MIN = 1.0 / (2 * K)


def is_material(share: float) -> bool:
    return share >= MATERIAL_SHARE_MIN - 1e-12
