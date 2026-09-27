"""Market taxonomy built from REAL observed Kalshi soccer tickers.

Ticker grammar (verified on 37 soccer series observed 2026-07..09, same grammar as NFL/CFB):
    KX<COMPCODE><FAMILYTOKEN>-<YYMONDD><AWAYCODE><HOMECODE>-<LEG>
e.g. KXMLSTOTAL-26AUG22SJMIN-9            (over 8.5 goals)
     KXUCLSPREAD-26SEP10MUNSBH-MUN4        (MUN wins by more than 3.5)
     KXUCLTEAMTOTAL-26SEP09SPOGAL-GAL4     (GAL scores over 3.5)
     KXEPLGOAL-26AUG22ARSCOV-ARSMZUBIM36-1 (player 1+ goals)

Classification happens AFTER discovery and never filters it. Anything that fails to parse or
whose family token is new lands in UNKNOWN with the raw ticker/title preserved.
Family tokens marked observed=False below are *expected* by analogy (NFL/CFB GAME/BTTS grammar)
and are classified only when the title/rules corroborate; they remain flagged `inferred`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from soccer_edge.kalshi.schemas import RawMarket


class MarketFamily(str, Enum):
    MATCH_RESULT_3WAY = "match_result_3way"  # home / draw / away legs of one event
    MATCH_WINNER_2WAY = "match_winner_2way"  # to advance / to win incl. ET+pens
    DRAW_NO_BET = "draw_no_bet"
    DOUBLE_CHANCE = "double_chance"
    HANDICAP = "handicap"  # "X wins by more than N.5 goals"
    TOTAL_GOALS = "total_goals"
    TEAM_TOTAL = "team_total"
    BTTS = "btts"
    EXACT_SCORE = "exact_score"
    WINNING_MARGIN = "winning_margin"
    FIRST_HALF_RESULT = "first_half_result"
    FIRST_HALF_TOTAL = "first_half_total"
    HT_FT = "ht_ft"
    CLEAN_SHEET = "clean_sheet"
    FIRST_TO_SCORE = "first_to_score"
    PLAYER_GOALS = "player_goals"  # "Name: K+ goals"
    PLAYER_ASSISTS = "player_assists"
    PLAYER_SHOTS = "player_shots"
    PLAYER_SHOTS_ON_TARGET = "player_shots_on_target"
    PLAYER_CARDS = "player_cards"
    COMPETITION_WINNER = "competition_winner"
    COMPETITION_TOP_N = "competition_top_n"
    COMPETITION_RELEGATION = "competition_relegation"
    COMPETITION_QUALIFICATION = "competition_qualification"
    TOURNAMENT_ADVANCEMENT = "tournament_advancement"
    PLAYER_AWARD = "player_award"
    SEASON_PLAYER_TOTAL = "season_player_total"
    COMBO = "combo"
    UNKNOWN = "unknown"


class Period(str, Enum):
    REGULATION = "regulation"  # 90' + stoppage
    FIRST_HALF = "first_half"
    SECOND_HALF = "second_half"
    INCLUDING_ET = "including_extra_time"
    INCLUDING_PENS = "including_penalties"  # qualification / advancement
    SEASON = "season"
    UNKNOWN = "unknown"


class Scope(str, Enum):
    MATCH = "match"
    PLAYER = "player"
    COMPETITION = "competition"
    UNKNOWN = "unknown"


# family token -> (family, scope, observed_live)
FAMILY_TOKENS: dict[str, tuple[MarketFamily, Scope, bool]] = {
    "TEAMTOTAL": (MarketFamily.TEAM_TOTAL, Scope.MATCH, True),
    "TOTAL": (MarketFamily.TOTAL_GOALS, Scope.MATCH, True),
    "SPREAD": (MarketFamily.HANDICAP, Scope.MATCH, True),
    "GOAL": (MarketFamily.PLAYER_GOALS, Scope.PLAYER, True),
    # inferred by grammar analogy; classified only with title corroboration
    "GAME": (MarketFamily.MATCH_RESULT_3WAY, Scope.MATCH, False),
    "WINNER": (MarketFamily.MATCH_WINNER_2WAY, Scope.MATCH, False),
    "BTTS": (MarketFamily.BTTS, Scope.MATCH, False),
    "1HTOTAL": (MarketFamily.FIRST_HALF_TOTAL, Scope.MATCH, False),
    "1HGAME": (MarketFamily.FIRST_HALF_RESULT, Scope.MATCH, False),
    "H1TOTAL": (MarketFamily.FIRST_HALF_TOTAL, Scope.MATCH, False),
    "H1": (MarketFamily.FIRST_HALF_RESULT, Scope.MATCH, False),
    "SCORE": (MarketFamily.EXACT_SCORE, Scope.MATCH, False),
    "CS": (MarketFamily.CLEAN_SHEET, Scope.MATCH, False),
    "ASSIST": (MarketFamily.PLAYER_ASSISTS, Scope.PLAYER, False),
    "SHOTS": (MarketFamily.PLAYER_SHOTS, Scope.PLAYER, False),
    "SOT": (MarketFamily.PLAYER_SHOTS_ON_TARGET, Scope.PLAYER, False),
    "CARD": (MarketFamily.PLAYER_CARDS, Scope.PLAYER, False),
    "CHAMP": (MarketFamily.COMPETITION_WINNER, Scope.COMPETITION, False),
    "CHAMPION": (MarketFamily.COMPETITION_WINNER, Scope.COMPETITION, False),
    "RELEGATION": (MarketFamily.COMPETITION_RELEGATION, Scope.COMPETITION, False),
    "TOP4": (MarketFamily.COMPETITION_TOP_N, Scope.COMPETITION, False),
    "TOP2": (MarketFamily.COMPETITION_TOP_N, Scope.COMPETITION, False),
    "TOP6": (MarketFamily.COMPETITION_TOP_N, Scope.COMPETITION, False),
    "GOLDENBOOT": (MarketFamily.PLAYER_AWARD, Scope.COMPETITION, False),
}

# Kalshi competition codes observed live (37 series, 2026-07..09) -> canonical competition ids.
# None means "known soccer competition without a canonical id yet" (kept as soccer, mapped later).
COMPETITION_CODES: dict[str, str | None] = {
    "EPL": "eng.premier_league",
    "EFLCHAMPIONSHIP": "eng.championship",
    "FACUP": "eng.fa_cup",
    "EFLCUP": "eng.efl_cup",
    "LALIGA": "esp.la_liga",
    "COPADELREY": "esp.copa_del_rey",
    "BUNDESLIGA": "ger.bundesliga",
    "BUNDESLIGA2": None,
    "DFBPOKAL": "ger.dfb_pokal",
    "SERIEA": "ita.serie_a",
    "SERIEB": None,
    "COPPAITALIA": "ita.coppa_italia",
    "LIGUE1": "fra.ligue_1",
    "LIGUE2": None,
    "EREDIVISIE": "ned.eredivisie",
    "KNVBCUP": None,
    "PRIMEIRALIGA": "por.primeira_liga",
    "LIGAPORTUGAL": "por.primeira_liga",
    "MLS": "usa.mls",
    "NWSL": "usa.nwsl",
    "USL": None,
    "LEAGUESCUP": None,
    "LIGAMX": "mex.liga_mx",
    "LIGAEXP": None,
    "TFF1LIG": None,
    "SUPERLIG": "tur.super_lig",
    "BELGIANPL": None,
    "ALLSVENSKAN": None,
    "SAUDIPL": "ksa.pro_league",
    "SPL": "sco.premiership",
    "UCL": "uefa.champions_league",
    "UCLW": None,
    "UEL": "uefa.europa_league",
    "UECL": "uefa.conference_league",
    "UEFANL": "uefa.nations_league",
    "EURO": "uefa.euro",
    "CONCACAFNL": None,
    "GOLDCUP": "concacaf.gold_cup",
    "CONMEBOLLIB": "conmebol.libertadores",
    "COPAAMERICA": "conmebol.copa_america",
    "COPADOBRASIL": None,
    "BRASILEIRO": "bra.serie_a",
    "WC": "fifa.world_cup",
    "WORLDCUP": "fifa.world_cup",
    "FIFAWC": "fifa.world_cup",
    "CWC": "fifa.club_world_cup",
    "WWC": "fifa.womens_world_cup",
}

_TICKER_RE = re.compile(r"^KX(?P<body>[A-Z0-9]+)-(?P<event>[A-Z0-9]+)(?:-(?P<leg>[A-Z0-9.\-]+))?$")
_EVENT_DATE_RE = re.compile(
    r"^(?P<yy>\d{2})(?P<mon>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(?P<dd>\d{2})(?P<teams>[A-Z0-9]*)$"
)
_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    )
}


@dataclass(frozen=True)
class ContractSpec:
    """What a YES contract pays on, in model terms. `family=UNKNOWN` is a valid, retained outcome."""

    ticker: str
    family: MarketFamily
    scope: Scope
    period: Period
    competition_code: str | None
    competition_id: str | None
    event_date: str | None  # YYYY-MM-DD from the ticker (Kalshi's event date, often US-local)
    team_codes: str | None  # raw AWAYHOME code string from the ticker
    side_team_code: str | None = (
        None  # team the contract references (spread/team total/player team)
    )
    line: Decimal | None = (
        None  # goals threshold: YES iff quantity > line (line ends in .5) unless exact
    )
    player_code: str | None = None
    player_name: str | None = None
    k: int | None = None  # "K+ goals"
    inferred: bool = False  # family classified from an unobserved token (needs live confirmation)
    rationale: str = ""

    @property
    def is_priceable_family(self) -> bool:
        return self.family in PRICEABLE_FAMILIES


PRICEABLE_FAMILIES = frozenset(
    {
        MarketFamily.MATCH_RESULT_3WAY,
        MarketFamily.HANDICAP,
        MarketFamily.TOTAL_GOALS,
        MarketFamily.TEAM_TOTAL,
        MarketFamily.BTTS,
        MarketFamily.EXACT_SCORE,
        MarketFamily.WINNING_MARGIN,
        MarketFamily.FIRST_HALF_RESULT,
        MarketFamily.FIRST_HALF_TOTAL,
        MarketFamily.CLEAN_SHEET,
        MarketFamily.DRAW_NO_BET,
        MarketFamily.DOUBLE_CHANCE,
        MarketFamily.FIRST_TO_SCORE,
        MarketFamily.MATCH_WINNER_2WAY,
        MarketFamily.PLAYER_GOALS,  # priced by the RESEARCH_ONLY player layer; authority gates it
    }
)


def split_competition_and_family(body: str) -> tuple[str | None, str | None]:
    """'MLSTEAMTOTAL' -> ('MLS', 'TEAMTOTAL'). Longest family token wins; competition must be known."""
    for tok in sorted(FAMILY_TOKENS, key=len, reverse=True):
        if body.endswith(tok):
            comp = body[: -len(tok)]
            if comp in COMPETITION_CODES:
                return comp, tok
    return None, None


def parse_event_code(event: str) -> tuple[str | None, str | None]:
    m = _EVENT_DATE_RE.match(event)
    if not m:
        return None, None
    yy, mon, dd = int(m["yy"]), _MONTHS[m["mon"]], int(m["dd"])
    return f"20{yy:02d}-{mon:02d}-{dd:02d}", m["teams"] or None


def _period_from_text(*texts: str) -> Period:
    blob = " ".join(texts).lower()
    if "first half" in blob or "1st half" in blob or "halftime" in blob:
        return Period.FIRST_HALF
    if (
        "including extra time" in blob
        or "extra time and penalt" in blob
        or "to advance" in blob
        or "to qualify" in blob
    ):
        return Period.INCLUDING_PENS
    if "extra time" in blob:
        return Period.INCLUDING_ET
    return Period.REGULATION


def classify(market: RawMarket) -> ContractSpec:
    t = market.ticker
    m = _TICKER_RE.match(t)
    if not m:
        return ContractSpec(
            t,
            MarketFamily.UNKNOWN,
            Scope.UNKNOWN,
            Period.UNKNOWN,
            None,
            None,
            None,
            None,
            rationale="ticker grammar not recognised",
        )
    comp, tok = split_competition_and_family(m["body"])
    event_date, team_codes = parse_event_code(m["event"])
    leg = m["leg"]
    if comp is None or tok is None:
        return ContractSpec(
            t,
            MarketFamily.UNKNOWN,
            Scope.UNKNOWN,
            Period.UNKNOWN,
            None,
            None,
            event_date,
            team_codes,
            rationale=f"unknown competition/family token in {m['body']!r}",
        )
    family, scope, observed = FAMILY_TOKENS[tok]
    comp_id = COMPETITION_CODES.get(comp)
    period = _period_from_text(
        market.title, market.subtitle, market.yes_sub_title, market.rules_primary
    )
    title = f"{market.title} {market.subtitle} {market.yes_sub_title}".lower()

    if family is MarketFamily.TOTAL_GOALS:
        line = _line_from(leg, market)
        return ContractSpec(
            t,
            family,
            scope,
            period,
            comp,
            comp_id,
            event_date,
            team_codes,
            line=line,
            inferred=not observed,
            rationale=f"token {tok}; leg {leg}",
        )
    if family is MarketFamily.TEAM_TOTAL:
        code, n = _split_team_and_number(leg)
        line = _line_from(n, market)
        return ContractSpec(
            t,
            family,
            scope,
            period,
            comp,
            comp_id,
            event_date,
            team_codes,
            side_team_code=code,
            line=line,
            inferred=not observed,
            rationale=f"token {tok}; leg {leg}",
        )
    if family is MarketFamily.HANDICAP:
        code, n = _split_team_and_number(leg)
        line = _line_from(n, market)
        return ContractSpec(
            t,
            family,
            scope,
            period,
            comp,
            comp_id,
            event_date,
            team_codes,
            side_team_code=code,
            line=line,
            inferred=not observed,
            rationale=f"token {tok}; leg {leg}",
        )
    if family is MarketFamily.PLAYER_GOALS:
        # leg like 'ARSMZUBIM36-1': <TEAM><INITIAL><SURNAME><JERSEY>-<K>
        tail = leg or ""
        pcode, k = tail.rsplit("-", 1) if "-" in tail else (tail, "1")
        team_code = pcode[:3] if pcode else None
        name = market.title.split(":")[0].strip() if ":" in market.title else None
        try:
            kk = int(k)
        except ValueError:
            kk = None
        return ContractSpec(
            t,
            family,
            scope,
            period,
            comp,
            comp_id,
            event_date,
            team_codes,
            side_team_code=team_code,
            player_code=pcode,
            player_name=name,
            k=kk,
            inferred=not observed,
            rationale=f"token {tok}; player tail {tail}",
        )
    if family is MarketFamily.MATCH_RESULT_3WAY:
        # inferred: corroborate with title ('win', 'draw', 'tie')
        if not any(w in title for w in ("win", "draw", "tie")):
            return ContractSpec(
                t,
                MarketFamily.UNKNOWN,
                scope,
                period,
                comp,
                comp_id,
                event_date,
                team_codes,
                rationale="GAME token without result wording",
            )
        side = (
            "DRAW" if ("draw" in title or "tie" in title) and leg in (None, "TIE", "DRAW") else leg
        )
        return ContractSpec(
            t,
            family,
            scope,
            period,
            comp,
            comp_id,
            event_date,
            team_codes,
            side_team_code=side,
            inferred=True,
            rationale=f"inferred token {tok}; leg {leg}",
        )
    if family is MarketFamily.BTTS:
        return ContractSpec(
            t,
            family,
            scope,
            period,
            comp,
            comp_id,
            event_date,
            team_codes,
            inferred=True,
            rationale=f"inferred token {tok}",
        )
    return ContractSpec(
        t,
        family,
        scope,
        period,
        comp,
        comp_id,
        event_date,
        team_codes,
        side_team_code=leg,
        inferred=not observed,
        rationale=f"token {tok}; leg {leg}",
    )


def _split_team_and_number(leg: str | None) -> tuple[str | None, str | None]:
    if not leg:
        return None, None
    mm = re.match(r"^([A-Z]+)(\d+(?:\.\d+)?)$", leg)
    if not mm:
        return leg, None
    return mm.group(1), mm.group(2)


def _line_from(n: str | None, market: RawMarket) -> Decimal | None:
    """Kalshi soccer totals: leg N with floor_strike N-0.5 ('over 8.5 goals' for -9).
    Prefer the API's floor_strike; fall back to the title; finally N - 0.5."""
    if market.floor_strike is not None:
        return Decimal(market.floor_strike)
    mm = re.search(
        r"(?:over|more than)\s+(\d+(?:\.\d+)?)", f"{market.title} {market.yes_sub_title}".lower()
    )
    if mm:
        return Decimal(mm.group(1))
    if n is not None:
        try:
            return Decimal(n) - Decimal("0.5")
        except ArithmeticError:
            return None
    return None
