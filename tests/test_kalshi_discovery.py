from __future__ import annotations

import pytest

from soccer_edge.core.errors import CoverageInvariantError, DiscoveryIncompleteError
from soccer_edge.kalshi.client import KalshiPublicClient
from soccer_edge.kalshi.coverage import CoverageLedger, Disposition
from soccer_edge.kalshi.discovery import discover, require_complete
from soccer_edge.kalshi.fake import FakeKalshi
from soccer_edge.kalshi.ownership import classify_ownership
from soccer_edge.kalshi.schemas import Ownership, RawMarket, RawSeries
from soccer_edge.kalshi.taxonomy import MarketFamily, classify


def test_pagination_walks_all_pages(registry, epl_fixtures):
    fake = FakeKalshi(epl_fixtures, registry, page_size=7)
    client = KalshiPublicClient(transport=fake.transport)
    sw = client.markets(series_ticker="KXEPLTOTAL", status="open")
    assert sw.complete and sw.pages >= 3 and len(sw.items) == 15


def test_discovery_complete_and_unknown_family_preserved(registry, epl_fixtures):
    fake = FakeKalshi(epl_fixtures, registry)
    run = discover(KalshiPublicClient(transport=fake.transport))
    assert run.complete
    c = run.counters()
    assert c["contracts_unknown_family"] == 3  # KXEPLCORNERS per fixture
    assert c["contracts_discovered"] == 3 * 14
    assert "CORNERS" not in " ".join(f.value for f in MarketFamily)
    assert any(r.ownership is Ownership.AMBIGUOUS for r in run.series_records.values())


def test_failed_sweep_is_incomplete_never_zero(registry, epl_fixtures):
    fake = FakeKalshi(epl_fixtures, registry, fail_on={"/markets:KXEPLTOTAL"})
    run = discover(KalshiPublicClient(transport=fake.transport, max_retries=1))
    assert not run.complete
    assert run.counters()["contracts_discovered"] > 0  # other series still captured
    with pytest.raises(DiscoveryIncompleteError):
        require_complete(run)


def test_duplicates_are_counted_not_dropped_silently(registry, epl_fixtures):
    fake = FakeKalshi(epl_fixtures, registry)
    fake._markets["KXEPLTOTAL"].append(dict(fake._markets["KXEPLTOTAL"][0]))
    run = discover(KalshiPublicClient(transport=fake.transport))
    assert len(run.duplicates) == 1


def test_missing_key_in_response_fails_closed():
    def transport(path, params):
        return 200, {"nope": []}

    sw = KalshiPublicClient(transport=transport).series()
    assert not sw.complete and sw.failures


def test_http_error_after_retries_fails_closed():
    calls = {"n": 0}

    def transport(path, params):
        calls["n"] += 1
        return 429, {"error": "slow down"}

    sw = KalshiPublicClient(transport=transport, max_retries=2).series()
    assert not sw.complete and calls["n"] == 3


@pytest.mark.parametrize(
    ("ticker", "title", "floor", "family", "side", "line"),
    [
        (
            "KXMLSTOTAL-26AUG22SJMIN-9",
            "Will over 8.5 goals be scored?",
            "8.5",
            MarketFamily.TOTAL_GOALS,
            None,
            "8.5",
        ),
        (
            "KXUCLSPREAD-26SEP10MUNSBH-MUN4",
            "Bayern wins by more than 3.5 goals?",
            None,
            MarketFamily.HANDICAP,
            "MUN",
            "3.5",
        ),
        (
            "KXUCLTEAMTOTAL-26SEP09SPOGAL-GAL4",
            "Will Galatasaray score over 3.5 goals?",
            "3.5",
            MarketFamily.TEAM_TOTAL,
            "GAL",
            "3.5",
        ),
        (
            "KXEPLGOAL-26AUG22ARSCOV-ARSMZUBIM36-1",
            "Martin Zubimendi: 1+ goals",
            None,
            MarketFamily.PLAYER_GOALS,
            "ARS",
            None,
        ),
        ("KXWHATEVER-26AUG22ARSCOV-1", "?", None, MarketFamily.UNKNOWN, None, None),
        ("NOTATICKER", "?", None, MarketFamily.UNKNOWN, None, None),
    ],
)
def test_taxonomy_on_observed_tickers(ticker, title, floor, family, side, line):
    m = RawMarket.from_api(
        {
            "ticker": ticker,
            "event_ticker": ticker.rsplit("-", 1)[0],
            "title": title,
            "floor_strike": floor,
        }
    )
    s = classify(m)
    assert s.family is family
    assert s.side_team_code == side
    assert (str(s.line) if s.line is not None else None) == line


def test_game_family_observed_live_with_tie_leg():
    win = classify(
        RawMarket.from_api(
            {
                "ticker": "KXBRASILEIROGAME-26OCT02SPASAN-SAN",
                "event_ticker": "x",
                "title": "Santos wins",
                "rules_primary": "If Santos wins ... after 90 minutes plus stoppage time (does not include extra time or penalties)",
            }
        )
    )
    assert (
        win.family is MarketFamily.MATCH_RESULT_3WAY
        and not win.inferred
        and win.side_team_code == "SAN"
    )
    assert win.period.value == "regulation"  # negated 'extra time' clause must not flip the period
    draw = classify(
        RawMarket.from_api(
            {"ticker": "KXAPFDDHGAME-26SEP28LIBOLI-TIE", "event_ticker": "x", "title": "Draw"}
        )
    )
    assert (
        draw.side_team_code == "DRAW"
        and draw.competition_code == "APFDDH"
        and draw.competition_id is None
    )


@pytest.mark.parametrize(
    ("ticker", "title", "rules", "family", "period", "side"),
    [
        (
            "KXLIGAMXSCORE-26SEP27LEOJUA-LEO0JUA0",
            "Final score Draw 0-0?",
            "(does not include extra time or penalties)",
            MarketFamily.EXACT_SCORE,
            "regulation",
            "LEO",
        ),
        (
            "KXUEFANLFTTS-26SEP28ARMMNE-ARM",
            "Will Armenia record the first goal of the game?",
            "first goal during the entire game (regulation, stoppage and any extra time periods)",
            MarketFamily.FIRST_TO_SCORE,
            "including_extra_time",
            "ARM",
        ),
        (
            "KXUEFANL1HSPREAD-26SEP28ARMMNE-ARM2",
            "Armenia wins by more than 1.5 goals in the 1st Half",
            "",
            MarketFamily.FIRST_HALF_HANDICAP,
            "first_half",
            "ARM",
        ),
        (
            "KXCONCACAFNL1H-26SEP27CUWNIC-CUW",
            "Curacao wins 1st Half",
            "",
            MarketFamily.FIRST_HALF_RESULT,
            "first_half",
            "CUW",
        ),
        (
            "KXCONCACAFNL1HBTTS-26SEP27CUWNIC-BTTS",
            "Both teams score in the 1st Half?",
            "",
            MarketFamily.FIRST_HALF_BTTS,
            "first_half",
            None,
        ),
        (
            "KXWC-30-ALB",
            "Will Albania win the 2030 FIFA Men's World Cup?",
            "",
            MarketFamily.COMPETITION_WINNER,
            "season",
            "ALB",
        ),
        (
            "KXBUNDESLIGATEAMPOINTS-27-BMG30",
            "Will M´gladbach finish with 30+ points?",
            "",
            MarketFamily.COMPETITION_TEAM_POINTS,
            "season",
            "BMG30",
        ),
        (
            "KXEPLLEADER-27AST-AGARNA49",
            "Will Alejandro Garnacho lead EPL in assists?",
            "",
            MarketFamily.PLAYER_SEASON_LEADER,
            "season",
            "AGARNA49",
        ),
        (
            "KXJOINCLUB-26OCT02CPULISIC-ACM",
            "Where will Christian Pulisic go next?",
            "",
            MarketFamily.SOCCER_SPECIAL,
            "season",
            "ACM",
        ),
        (
            "KXUCLROUND-27FINAL-AEK",
            "Will AEK Athens qualify for the Final?",
            "",
            MarketFamily.TOURNAMENT_ADVANCEMENT,
            "season",
            "AEK",
        ),
        (
            "KXBALLONDORRANK-26T10-AHAK",
            "Achraf Hakimi: Top 10?",
            "",
            MarketFamily.PLAYER_AWARD,
            "season",
            "AHAK",
        ),
        ("KXWEIRDNEW-26SEP28ABCDEF-1", "Something", "", MarketFamily.UNKNOWN, "unknown", None),
    ],
)
def test_taxonomy_v2_on_live_observed_tickers(ticker, title, rules, family, period, side):
    s = classify(
        RawMarket.from_api(
            {
                "ticker": ticker,
                "event_ticker": ticker.rsplit("-", 1)[0],
                "title": title,
                "rules_primary": rules,
            }
        )
    )
    assert s.family is family and s.period.value == period
    assert s.side_team_code == side
    if s.family is not MarketFamily.UNKNOWN:
        assert not s.inferred


def test_ownership_fail_closed_on_bare_football():
    s = RawSeries.from_api(
        {
            "ticker": "KXFOOTBALLX",
            "title": "Football thing",
            "category": "Sports",
            "tags": ["Football"],
        }
    )
    assert classify_ownership(s)[0] is Ownership.AMBIGUOUS
    s2 = RawSeries.from_api(
        {"ticker": "KXNFLGAME", "title": "NFL", "category": "Sports", "tags": ["Football", "NFL"]}
    )
    assert classify_ownership(s2)[0] is Ownership.NOT_SOCCER
    s3 = RawSeries.from_api(
        {"ticker": "KXEPLTOTAL", "title": "Premier League totals", "category": "Sports", "tags": []}
    )
    assert classify_ownership(s3)[0] is Ownership.SOCCER


def test_price_units_parse_dollars_and_legacy_cents():
    m = RawMarket.from_api(
        {
            "ticker": "T-1-1",
            "event_ticker": "T-1",
            "yes_bid_dollars": "0.4200",
            "yes_ask": 45,
            "no_ask_size_fp": "12.5",
        }
    )
    assert (
        str(m.yes_bid) == "0.4200" and str(m.yes_ask) == "0.4500" and str(m.no_ask_size) == "12.5"
    )


def test_coverage_invariant():
    led = CoverageLedger()
    led.discover(["A", "B", "C"])
    led.set("A", Disposition.PRICED)
    led.set("B", Disposition.UNKNOWN_FAMILY, "x")
    with pytest.raises(CoverageInvariantError):
        led.assert_invariant()
    led.set("C", Disposition.CLOSED)
    led.assert_invariant()
    assert led.summary()["unaccounted_contracts"] == 0
    with pytest.raises(CoverageInvariantError):
        led.set("A", Disposition.CLOSED)  # one terminal state per contract
    with pytest.raises(CoverageInvariantError):
        led.set("Z", Disposition.CLOSED)  # never disposition an undiscovered contract


def test_bare_football_series_are_retained_but_not_swept(registry, epl_fixtures):
    fake = FakeKalshi(epl_fixtures, registry)
    run = discover(KalshiPublicClient(transport=fake.transport))
    c = run.counters()
    recs = run.series_records
    assert recs["KXAFCCHAMP"].ownership is Ownership.NOT_SOCCER  # american-football wording
    assert (
        recs["KXFOOTBALLMYSTERY"].ownership is Ownership.AMBIGUOUS
        and not recs["KXFOOTBALLMYSTERY"].swept
    )
    assert (
        recs["KXMYSTERYCUP"].ownership is Ownership.SOCCER and recs["KXMYSTERYCUP"].swept
    )  # soccer wording wins
    assert c["series_ambiguous_unswept"] == 1 and c["series_ambiguous_unswept_tickers"] == [
        "KXFOOTBALLMYSTERY"
    ]
    assert run.complete


def test_nfl_prefix_with_soccer_mistag_is_ambiguous():
    s = RawSeries.from_api(
        {
            "ticker": "KXFIRSTSUPERBOWLSONG",
            "title": "What will be the first Super Bowl song?",
            "category": "Entertainment",
            "tags": ["Soccer", "Music"],
        }
    )
    assert classify_ownership(s)[0] is Ownership.AMBIGUOUS
    s2 = RawSeries.from_api(
        {
            "ticker": "KXNFLGAME",
            "title": "Pro football game",
            "category": "Sports",
            "tags": ["Football"],
        }
    )
    assert classify_ownership(s2)[0] is Ownership.NOT_SOCCER


def test_fast_capture_sweeps_known_market_series_and_new_series(registry, epl_fixtures):
    fake = FakeKalshi(epl_fixtures, registry)
    fake._series.append(
        {
            "ticker": "KXEPLNEWFAMILY",
            "title": "EPL new thing",
            "category": "Sports",
            "tags": ["Soccer"],
            "fee_type": "quadratic",
        }
    )
    fake._markets["KXEPLNEWFAMILY"] = [
        dict(
            fake._markets["KXEPLTOTAL"][0],
            ticker="KXEPLNEWFAMILY-26OCT10LEEARS-1",
            event_ticker="KXEPLNEWFAMILY-26OCT10LEEARS",
            series_ticker="KXEPLNEWFAMILY",
        )
    ]
    fake._events["KXEPLNEWFAMILY"] = []
    client = KalshiPublicClient(transport=fake.transport)
    known = {
        "KXEPLTOTAL",
        "KXEPLGAME",
        "KXEPLSPREAD",
        "KXEPLTEAMTOTAL",
        "KXEPLGOAL",
        "KXEPLCORNERS",
        "KXMYSTERYCUP",
    }
    run = discover(client, sweep_series={"KXEPLTOTAL", "KXEPLGAME"}, known_series=known)
    c = run.counters()
    swept = {r.series.ticker for r in run.swept_series()}
    assert {"KXEPLTOTAL", "KXEPLGAME", "KXEPLNEWFAMILY"} <= swept  # known-with-markets + NEW
    assert "KXEPLSPREAD" not in swept and c["series_skipped_fast_mode"] >= 4
    assert "KXEPLNEWFAMILY-26OCT10LEEARS-1" in run.markets and run.complete


@pytest.mark.parametrize(
    ("minutes", "label"),
    [(2964, "T-24h"), (1440, "T-24h"), (1439, "T-12h"), (400, "T-6h"), (130, "T-2h"), (95, "T-90m"), (61, "T-60m"), (40, "T-30m"), (16, "T-15m"), (12, "T-10m"), (5, "close"), (0, "close"), (-10, "close")],
)
def test_label_horizon_is_largest_horizon_not_yet_passed(minutes, label):
    from soccer_edge.kalshi.capture import label_horizon

    assert label_horizon(minutes).value == label
