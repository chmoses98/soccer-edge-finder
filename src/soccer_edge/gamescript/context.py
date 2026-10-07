"""Structured, provenance-aware competition / match context. DISPLAY ONLY.

Every field is {value, status, source}: status KNOWN (read from a feed or registry), DERIVED (a deterministic rule
over KNOWN fields, rule named in `source`) or UNAVAILABLE (no trustworthy input; value null). Nothing here is
inferred from narrative, and nothing here changes a production probability except the two inputs the model already
consumed before this layer existed: `neutral_site` (no home advantage) and `requires_winner` (extra time /
penalties for to-advance contracts). `must_win`, `draw_utility` and standings implications are UNAVAILABLE: no
standings / qualification-scenario input exists in this repository, and they are never guessed.

A separately versioned RESEARCH_ONLY context family would be the only route for context to move probabilities
(docs/GAME_SCRIPTS.md section 9); none is enabled.
"""

from __future__ import annotations

import re
from typing import Any

CONTEXT_VERSION = "match_context_v1"
CONFEDERATIONS = {"UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC", "FIFA"}


def _f(value: Any, status: str, source: str) -> dict[str, Any]:
    return {"value": value, "status": status, "source": source}


def _unavailable(why: str) -> dict[str, Any]:
    return _f(None, "UNAVAILABLE", why)


def competition_type(comp: Any, *, national: bool | None) -> tuple[str, str]:
    """(type, rule). Types: LEAGUE, DOMESTIC_CUP, CONTINENTAL_CLUB, INTERNATIONAL_COMPETITIVE,
    INTERNATIONAL_FRIENDLY, CLUB_FRIENDLY, UNKNOWN."""
    if comp is None:
        return "UNKNOWN", "competition not in the registry"
    fmt = getattr(comp.format, "value", str(comp.format))
    if fmt == "friendly":
        if national is False:
            return "CLUB_FRIENDLY", "registry format friendly; teams are clubs"
        return "INTERNATIONAL_FRIENDLY", "registry format friendly; teams are national sides"
    if fmt == "league":
        return "LEAGUE", "registry format league"
    if national:
        return "INTERNATIONAL_COMPETITIVE", f"registry format {fmt}; teams are national sides"
    if str(comp.country).upper() in CONFEDERATIONS:
        return (
            "CONTINENTAL_CLUB",
            f"registry format {fmt}; confederation competition ({comp.country})",
        )
    return (
        "DOMESTIC_CUP",
        f"registry format {fmt}; national association competition ({comp.country})",
    )


def _stage_kind(stage: str | None) -> str | None:
    if not stage:
        return None
    s = stage.lower()
    if re.search(r"\bsemi", s):
        return "SEMI_FINAL"
    if re.search(r"\bquarter", s):
        return "QUARTER_FINAL"
    if re.search(r"\bfinal\b", s):
        return "FINAL"
    if re.search(r"round of|knockout|play-?off|\bround\b", s):
        return "KNOCKOUT_ROUND"
    if re.search(r"group|league phase|matchday|regular", s):
        return "ROUND_ROBIN"
    return None


def match_context(
    *,
    competition: Any,
    competition_id: str,
    stage: str | None,
    leg_number: int | None,
    requires_winner: bool,
    neutral_site: bool,
    national: bool | None,
    rest_days_home: int | None,
    rest_days_away: int | None,
    two_leg_second_leg: bool = False,
    first_leg: tuple[int, int] | None = None,
) -> dict[str, Any]:
    ctype, ctype_rule = competition_type(competition, national=national)
    stage_kind = _stage_kind(stage)
    fmt = getattr(getattr(competition, "format", None), "value", None)
    if requires_winner:
        knockout = _f(True, "KNOWN", "fixture feed: penalties possible (a winner is required)")
    elif fmt == "league":
        knockout = _f(False, "DERIVED", "registry format league (round robin)")
    elif stage_kind == "ROUND_ROBIN":
        knockout = _f(False, "DERIVED", f"stage '{stage}' is a group / league phase")
    elif ctype in ("INTERNATIONAL_FRIENDLY", "CLUB_FRIENDLY"):
        knockout = _f(False, "DERIVED", "friendly")
    else:
        knockout = _f(
            False, "DERIVED", "fixture feed: no winner required (no extra time / penalties)"
        )
    if leg_number is not None:
        leg = _f(leg_number, "KNOWN", "fixture feed")
    elif requires_winner or stage_kind in ("KNOCKOUT_ROUND", "QUARTER_FINAL", "SEMI_FINAL"):
        leg = _unavailable("tie / leg structure not supplied by the fixture feed")
    else:
        leg = _f(None, "DERIVED", "single match (not a two-legged tie)")
    aggregate = (
        _f({"home": first_leg[0], "away": first_leg[1]}, "KNOWN", "first-leg result")
        if two_leg_second_leg and first_leg is not None
        else (
            _unavailable("first-leg result not joined to this fixture")
            if leg_number == 2
            else _f(None, "DERIVED", "no aggregate (not a second leg)")
        )
    )
    friendly = ctype in ("INTERNATIONAL_FRIENDLY", "CLUB_FRIENDLY")
    flags = []
    if friendly:
        flags.append("FRIENDLY")
    if knockout["value"]:
        flags.append("KNOCKOUT")
    if leg_number == 2:
        flags.append("SECOND_LEG")
    if stage_kind == "FINAL":
        flags.append("FINAL")
    if neutral_site:
        flags.append("NEUTRAL_SITE")
    if ctype == "INTERNATIONAL_COMPETITIVE":
        flags.append("INTERNATIONAL_COMPETITIVE")
    rot = (
        _f(
            "ELEVATED_UNQUANTIFIED",
            "DERIVED",
            "friendly: selection, rotation and substitution norms differ from competitive matches; the size of "
            "the effect is not measured in this repository",
        )
        if friendly
        else _unavailable(
            "no rotation / availability provider; XI publication is the only availability input"
        )
    )
    return {
        "version": CONTEXT_VERSION,
        "competition_id": competition_id,
        "competition_name": _f(
            getattr(competition, "name", None),
            "KNOWN" if competition else "UNAVAILABLE",
            "registry",
        ),
        "competition_type": _f(ctype, "DERIVED" if competition else "UNAVAILABLE", ctype_rule),
        "competition_format": _f(fmt, "KNOWN" if fmt else "UNAVAILABLE", "registry"),
        "stage": _f(stage, "KNOWN", "fixture feed")
        if stage
        else _unavailable("stage not supplied by the fixture feed"),
        "stage_kind": _f(stage_kind, "DERIVED", "pattern over the stage label")
        if stage_kind
        else _unavailable("no stage label"),
        "knockout": knockout,
        "requires_winner": _f(bool(requires_winner), "KNOWN", "fixture feed (penalties possible)"),
        "leg_number": leg,
        "aggregate": aggregate,
        "neutral_site": _f(
            bool(neutral_site), "KNOWN", "ESPN neutralSite / international venue-country rule"
        ),
        "rest_days_home": _f(rest_days_home, "DERIVED", "days since the previous archived match")
        if rest_days_home is not None
        else _unavailable("no previous match in the archive"),
        "rest_days_away": _f(rest_days_away, "DERIVED", "days since the previous archived match")
        if rest_days_away is not None
        else _unavailable("no previous match in the archive"),
        "rotation_uncertainty": rot,
        "standings_implications": _unavailable("no standings / qualification-scenario input"),
        "must_win": _unavailable("not objectively derivable without standings and scenario inputs"),
        "draw_utility": _unavailable(
            "not objectively derivable without standings and scenario inputs"
        ),
        "flags": flags,
        "model_effect": (
            "DISPLAY_ONLY. Production probabilities use only neutral_site (no home advantage) and requires_winner "
            "(extra time / penalties for to-advance contracts); no motivation adjustment is applied."
        ),
    }
