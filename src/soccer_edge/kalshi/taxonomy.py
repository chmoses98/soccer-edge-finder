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
    PLAYER_SEASON_LEADER = "player_season_leader"
    SECOND_HALF_RESULT = "second_half_result"
    FIRST_HALF_EXACT_SCORE = "first_half_exact_score"
    FIRST_HALF_BTTS = "first_half_btts"
    FIRST_HALF_HANDICAP = "first_half_handicap"
    FIRST_HALF_TEAM_TOTAL = "first_half_team_total"
    COMPETITION_TEAM_POINTS = "competition_team_points"
    COMPETITION_POINTS_MARGIN = "competition_points_margin"
    COMPETITION_LAST_PLACE = "competition_last_place"
    COMPETITION_HEAD_TO_HEAD = "competition_head_to_head"
    COMPETITION_PROMOTION = "competition_promotion"
    COMPETITION_HOST = "competition_host"
    COMPETITION_TROPHIES = "competition_trophies"
    SOCCER_SPECIAL = "soccer_special"  # transfers, manager exits, retirements, bans ...
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


# family token -> (family, scope, observed_live). Observed = seen in a complete runner-side discovery
# (2026-09-27, 6,694 contracts) or in sibling-repo archives. Longest token wins when splitting.
FAMILY_TOKENS: dict[str, tuple[MarketFamily, Scope, bool]] = {
    "1HTEAMTOTAL": (MarketFamily.FIRST_HALF_TEAM_TOTAL, Scope.MATCH, False),
    "1HSCORE": (MarketFamily.FIRST_HALF_EXACT_SCORE, Scope.MATCH, True),
    "2H": (MarketFamily.SECOND_HALF_RESULT, Scope.MATCH, True),
    "ADVANCE": (MarketFamily.MATCH_WINNER_2WAY, Scope.MATCH, True),
    "H2H": (MarketFamily.COMPETITION_HEAD_TO_HEAD, Scope.COMPETITION, True),
    "TREBLE": (MarketFamily.COMPETITION_TROPHIES, Scope.COMPETITION, True),
    "1HSPREAD": (MarketFamily.FIRST_HALF_HANDICAP, Scope.MATCH, True),
    "1HTOTAL": (MarketFamily.FIRST_HALF_TOTAL, Scope.MATCH, True),
    "1HBTTS": (MarketFamily.FIRST_HALF_BTTS, Scope.MATCH, True),
    "1HGAME": (MarketFamily.FIRST_HALF_RESULT, Scope.MATCH, False),
    "1H": (MarketFamily.FIRST_HALF_RESULT, Scope.MATCH, True),
    "TEAMTOTAL": (MarketFamily.TEAM_TOTAL, Scope.MATCH, True),
    "TOTAL": (MarketFamily.TOTAL_GOALS, Scope.MATCH, True),
    "SPREAD": (MarketFamily.HANDICAP, Scope.MATCH, True),
    "GAME": (MarketFamily.MATCH_RESULT_3WAY, Scope.MATCH, True),
    "BTTS": (MarketFamily.BTTS, Scope.MATCH, True),
    "FTTS": (MarketFamily.FIRST_TO_SCORE, Scope.MATCH, True),
    "SCORE": (MarketFamily.EXACT_SCORE, Scope.MATCH, True),
    "ANYGOAL": (MarketFamily.PLAYER_GOALS, Scope.PLAYER, True),
    "GOAL": (MarketFamily.PLAYER_GOALS, Scope.PLAYER, True),
    "BRACE": (MarketFamily.PLAYER_GOALS, Scope.PLAYER, True),
    "WINNER": (MarketFamily.MATCH_WINNER_2WAY, Scope.MATCH, False),
    "CS": (MarketFamily.CLEAN_SHEET, Scope.MATCH, False),
    "ASSIST": (MarketFamily.PLAYER_ASSISTS, Scope.PLAYER, False),
    "SHOTS": (MarketFamily.PLAYER_SHOTS, Scope.PLAYER, False),
    "SOT": (MarketFamily.PLAYER_SHOTS_ON_TARGET, Scope.PLAYER, False),
    "CARD": (MarketFamily.PLAYER_CARDS, Scope.PLAYER, False),
    # competition / season scope (observed 2026-09-27)
    "RELEGATION": (MarketFamily.COMPETITION_RELEGATION, Scope.COMPETITION, True),
    "TEAMPOINTS": (MarketFamily.COMPETITION_TEAM_POINTS, Scope.COMPETITION, True),
    "POINTMARGIN": (MarketFamily.COMPETITION_POINTS_MARGIN, Scope.COMPETITION, True),
    "SEASONSTAT": (MarketFamily.SEASON_PLAYER_TOTAL, Scope.COMPETITION, True),
    "H2HFINISH": (MarketFamily.COMPETITION_HEAD_TO_HEAD, Scope.COMPETITION, True),
    "GROUPWIN": (MarketFamily.COMPETITION_QUALIFICATION, Scope.COMPETITION, True),
    "LEADER": (MarketFamily.PLAYER_SEASON_LEADER, Scope.COMPETITION, True),
    "TOPX": (MarketFamily.COMPETITION_TOP_N, Scope.COMPETITION, True),
    "TOP8": (MarketFamily.COMPETITION_TOP_N, Scope.COMPETITION, True),
    "TOP4": (MarketFamily.COMPETITION_TOP_N, Scope.COMPETITION, False),
    "TOP2": (MarketFamily.COMPETITION_TOP_N, Scope.COMPETITION, False),
    "TOP6": (MarketFamily.COMPETITION_TOP_N, Scope.COMPETITION, False),
    "TOP": (MarketFamily.COMPETITION_TOP_N, Scope.COMPETITION, True),
    "BOTTOM": (MarketFamily.COMPETITION_LAST_PLACE, Scope.COMPETITION, True),
    "LAST": (MarketFamily.COMPETITION_LAST_PLACE, Scope.COMPETITION, True),
    "QUAL": (MarketFamily.COMPETITION_QUALIFICATION, Scope.COMPETITION, True),
    "ROUND": (MarketFamily.TOURNAMENT_ADVANCEMENT, Scope.COMPETITION, True),
    "PROMO": (MarketFamily.COMPETITION_PROMOTION, Scope.COMPETITION, True),
    "HOST": (MarketFamily.COMPETITION_HOST, Scope.COMPETITION, True),
    "AWARD": (MarketFamily.PLAYER_AWARD, Scope.COMPETITION, True),
    "RANK": (MarketFamily.PLAYER_AWARD, Scope.COMPETITION, True),
    "GOLDENBOOT": (MarketFamily.PLAYER_SEASON_LEADER, Scope.COMPETITION, False),
    "CHAMPION": (MarketFamily.COMPETITION_WINNER, Scope.COMPETITION, False),
    "CHAMP": (MarketFamily.COMPETITION_WINNER, Scope.COMPETITION, False),
    "CUP": (MarketFamily.COMPETITION_WINNER, Scope.COMPETITION, True),
    "TROPHIES": (MarketFamily.COMPETITION_TROPHIES, Scope.COMPETITION, True),
}

# bodies that are whole-series specials (no competition split); observed 2026-09-27
SPECIAL_BODIES: dict[str, MarketFamily] = {
    "JOINCLUB": MarketFamily.SOCCER_SPECIAL,
    "MANAGERSOUT": MarketFamily.SOCCER_SPECIAL,
    "SOCCERRETIRE": MarketFamily.SOCCER_SPECIAL,
    "SOCCERLEAVE": MarketFamily.SOCCER_SPECIAL,
    "FIFALEAVE": MarketFamily.SOCCER_SPECIAL,
    "UEFAISRAELBAN": MarketFamily.SOCCER_SPECIAL,
    "WCDELAY": MarketFamily.SOCCER_SPECIAL,
    "CLUBWCHOST": MarketFamily.COMPETITION_HOST,
    "BALLONDOR": MarketFamily.PLAYER_AWARD,
    "BALLONDORAWARD": MarketFamily.PLAYER_AWARD,
    "BALLONDORRANK": MarketFamily.PLAYER_AWARD,
    "SOCCERTROPHIES": MarketFamily.COMPETITION_TROPHIES,
    "SUPERBALLONDOR": MarketFamily.PLAYER_AWARD,
    "WCCAREERGOALS": MarketFamily.SEASON_PLAYER_TOTAL,
    "WCTEAMS": MarketFamily.SOCCER_SPECIAL,
    "HKANEKNIGHT": MarketFamily.SOCCER_SPECIAL,
    "LAMINEYAMAL": MarketFamily.SOCCER_SPECIAL,
    "POCHETTINOOUT": MarketFamily.SOCCER_SPECIAL,
    "MANAGEROUTDATE": MarketFamily.SOCCER_SPECIAL,
}
_SPECIAL_PREFIXES = (
    "CLUBCHANGE",
    "JOINCLUB",
    "JOINLEAGUE",
    "JOINRONALDO",
    "MANAGERSOUT",
    "MANAGEROUT",
    "BALLONDOR",
    "WINSTREAK",
)

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
    "WCW": "fifa.womens_world_cup",
    "FIFAW": None,
    "INTLFRIENDLY": None,
    "CONMEBOLSUD": None,
    "DENSUPERLIGA": None,
    "KLEAGUE": None,
    "DIMAYOR": None,
    "EFLL1": None,
    "EFLL2": None,
    "EFL": None,
    "ISRNL": None,
    "ENGNL": None,
    "SVKCUP": None,
    "USLCUP": None,
    "PREMIERLEAGUE": "eng.premier_league",
    "UEFAEURO": "uefa.euro",
    "UEFASUPERCUP": None,
    "UEFASC": None,
    "ENGCS": None,
    "UCLLEAGUE": "uefa.champions_league",
    "MLSCUP": "usa.mls",
    "MLSEAST": "usa.mls",
    "MLSWEST": "usa.mls",
    # observed 2026-09-27 (not yet modelled)
    "APFDDH": None,
    "ARGNACB": None,
    "ARGPREMDIV": "arg.primera",
    "BRASILEIROB": None,
    "BRASILEIROC": None,
    "CANPL": None,
    "CHNL1": None,
    "CHNSL": None,
    "CHLLDP": None,
    "ECULP": None,
    "EKSTRAKLASA": None,
    "PERLIGA1": None,
    "TACAPORT": None,
    "THAIL1": None,
    "URYPD": None,
    "VENFUTVE": None,
    "CONCACAFGC": "concacaf.gold_cup",
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
        MarketFamily.FIRST_HALF_BTTS,
        MarketFamily.FIRST_HALF_HANDICAP,
        MarketFamily.FIRST_HALF_TEAM_TOTAL,
        MarketFamily.FIRST_HALF_EXACT_SCORE,
        MarketFamily.SECOND_HALF_RESULT,
        MarketFamily.PLAYER_GOALS,  # priced by the RESEARCH_ONLY player layer; authority gates it
    }
)


def split_competition_and_family(body: str) -> tuple[str | None, str | None]:
    """'MLSTEAMTOTAL' -> ('MLS', 'TEAMTOTAL'); 'APFDDHGAME' -> ('APFDDH', 'GAME') even though APFDDH is
    an unregistered competition (the competition_id is then None). Longest token wins. A bare
    competition body ('KXWC', 'KXPREMIERLEAGUE') returns (body, None) when the body is a known code."""
    if body in SPECIAL_BODIES or body.startswith(_SPECIAL_PREFIXES):
        return None, None
    for tok in sorted(FAMILY_TOKENS, key=len, reverse=True):
        if body.endswith(tok):
            comp = body[: -len(tok)]
            if comp and (comp in COMPETITION_CODES or len(comp) >= 2):
                return comp, tok
    if body in COMPETITION_CODES:
        return body, None
    return None, None


def parse_event_code(event: str) -> tuple[str | None, str | None]:
    m = _EVENT_DATE_RE.match(event)
    if not m:
        return None, None
    yy, mon, dd = int(m["yy"]), _MONTHS[m["mon"]], int(m["dd"])
    return f"20{yy:02d}-{mon:02d}-{dd:02d}", m["teams"] or None


def _period_from_text(*texts: str) -> Period:
    blob = " ".join(texts).lower()
    if "first half" in blob or "1st half" in blob or "halftime" in blob or " 1h " in f" {blob} ":
        return Period.FIRST_HALF
    # Kalshi's standard soccer clause: "after 90 minutes plus stoppage time (does not include extra
    # time or penalties)" -> regulation. The negation must be checked BEFORE 'extra time'.
    if (
        "does not include extra time" in blob
        or "not include extra time" in blob
        or "excluding extra time" in blob
    ):
        return Period.REGULATION
    if (
        "including extra time" in blob
        or "extra time and penalt" in blob
        or "to advance" in blob
        or "to qualify" in blob
        or "penalty shootout" in blob
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
    body = m["body"]
    event_date, team_codes = parse_event_code(m["event"])
    leg = m["leg"]
    title = f"{market.title} {market.subtitle} {market.yes_sub_title}".lower()
    special = SPECIAL_BODIES.get(body) or (
        MarketFamily.SOCCER_SPECIAL if body.startswith(_SPECIAL_PREFIXES) else None
    )
    if special is not None:
        return ContractSpec(
            t,
            special,
            Scope.COMPETITION,
            Period.SEASON,
            None,
            None,
            event_date,
            team_codes,
            side_team_code=leg,
            rationale=f"special body {body}",
        )
    comp, tok = split_competition_and_family(body)
    if comp is not None and tok is None:
        # bare competition body: outright winner ("Will Albania win the 2030 FIFA Men's World Cup?")
        if re.search(r"\bwin(s|ner)?\b|champion", title):
            return ContractSpec(
                t,
                MarketFamily.COMPETITION_WINNER,
                Scope.COMPETITION,
                Period.SEASON,
                comp,
                COMPETITION_CODES.get(comp),
                event_date,
                team_codes,
                side_team_code=leg,
                rationale=f"bare competition body {comp} with winner wording",
            )
        return ContractSpec(
            t,
            MarketFamily.UNKNOWN,
            Scope.COMPETITION,
            Period.SEASON,
            comp,
            COMPETITION_CODES.get(comp),
            event_date,
            team_codes,
            rationale=f"bare competition body {comp} without winner wording",
        )
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
            rationale=f"unknown competition/family token in {body!r}",
        )
    family, scope, observed = FAMILY_TOKENS[tok]
    comp_id = COMPETITION_CODES.get(comp)
    period = _period_from_text(
        market.title, market.subtitle, market.yes_sub_title, market.rules_primary
    )
    if family in (
        MarketFamily.FIRST_HALF_RESULT,
        MarketFamily.FIRST_HALF_TOTAL,
        MarketFamily.FIRST_HALF_BTTS,
        MarketFamily.FIRST_HALF_HANDICAP,
        MarketFamily.FIRST_HALF_TEAM_TOTAL,
        MarketFamily.FIRST_HALF_EXACT_SCORE,
    ):
        period = Period.FIRST_HALF
    if family is MarketFamily.SECOND_HALF_RESULT:
        period = Period.SECOND_HALF
    if family is MarketFamily.MATCH_WINNER_2WAY:
        period = Period.INCLUDING_PENS
    if scope is Scope.COMPETITION:
        period = Period.SEASON

    if family in (MarketFamily.EXACT_SCORE, MarketFamily.FIRST_HALF_EXACT_SCORE):
        # leg like LEO0JUA0 = <first team code><goals><second team code><goals>, codes in event order
        mm = re.match(r"^([A-Z]+?)(\d+)([A-Z]+?)(\d+)$", leg or "")
        if mm and team_codes:
            first_code, g1, second_code, g2 = (
                mm.group(1),
                int(mm.group(2)),
                mm.group(3),
                int(mm.group(4)),
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
                side_team_code=first_code,
                line=None,
                k=None,
                inferred=not observed,
                rationale=f"token {tok}; exact score {first_code} {g1}-{g2} {second_code}",
                player_code=f"{g1}-{g2}",
            )
        return ContractSpec(
            t,
            MarketFamily.UNKNOWN,
            scope,
            period,
            comp,
            comp_id,
            event_date,
            team_codes,
            rationale=f"SCORE leg {leg!r} not parseable",
        )
    if family is MarketFamily.TOTAL_GOALS or family is MarketFamily.FIRST_HALF_TOTAL:
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
    if family in (MarketFamily.TEAM_TOTAL, MarketFamily.FIRST_HALF_TEAM_TOTAL):
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
    if family in (MarketFamily.HANDICAP, MarketFamily.FIRST_HALF_HANDICAP):
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
    if family in (
        MarketFamily.MATCH_RESULT_3WAY,
        MarketFamily.FIRST_HALF_RESULT,
        MarketFamily.SECOND_HALF_RESULT,
    ):
        # observed live: legs <TEAM> for wins and TIE for the draw ("Santos wins", "Draw")
        side = "DRAW" if leg in ("TIE", "DRAW") or ("draw" in title and "win" not in title) else leg
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
            inferred=not observed,
            rationale=f"token {tok}; leg {leg}",
        )
    if family in (MarketFamily.BTTS, MarketFamily.FIRST_HALF_BTTS):
        return ContractSpec(
            t,
            family,
            scope,
            period,
            comp,
            comp_id,
            event_date,
            team_codes,
            inferred=not observed,
            rationale=f"token {tok}",
        )
    if family is MarketFamily.FIRST_TO_SCORE:
        # observed rules: "records the first goal during the entire game (regulation, stoppage and any extra time periods)"
        per = (
            Period.INCLUDING_ET
            if "extra time" in market.rules_primary.lower()
            and "not include extra time" not in market.rules_primary.lower()
            else period
        )
        return ContractSpec(
            t,
            family,
            scope,
            per,
            comp,
            comp_id,
            event_date,
            team_codes,
            side_team_code=leg,
            inferred=not observed,
            rationale=f"token {tok}; leg {leg}",
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
