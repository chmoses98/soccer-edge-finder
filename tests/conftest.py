from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from soccer_edge.identity.models import Fixture
from soccer_edge.identity.registry import AliasRegistry
from soccer_edge.model.strength import DixonColesFitter, MatchRow

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _not_in_actions(monkeypatch):
    """Tests must behave the same locally and on the CI runner: the paid-call guard fails closed when
    GITHUB_ACTIONS=true and no claim store is given, so tests that exercise that guard set it explicitly."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


@pytest.fixture(scope="session")
def registry() -> AliasRegistry:
    return AliasRegistry.from_directory(REPO / "data" / "registry")


def synthetic_league(
    seed: int = 2, n_teams: int = 20, rounds: int = 38, start: date = date(2025, 8, 1)
):
    rng = np.random.default_rng(seed)
    teams = [f"t{i:02d}" for i in range(n_teams)]
    att = rng.normal(0, 0.25, n_teams)
    dfn = rng.normal(0, 0.25, n_teams)
    rows = []
    for rnd in range(rounds):
        order = list(range(n_teams))
        rng.shuffle(order)
        for i in range(0, n_teams, 2):
            h, a = order[i], order[i + 1]
            lam = np.exp(att[h] - dfn[a] + 0.25)
            mu = np.exp(att[a] - dfn[h])
            rows.append(
                MatchRow(
                    start + timedelta(days=7 * rnd),
                    teams[h],
                    teams[a],
                    int(rng.poisson(lam)),
                    int(rng.poisson(mu)),
                )
            )
    return teams, att, dfn, rows


@pytest.fixture(scope="session")
def synthetic_posterior():
    teams, att, dfn, rows = synthetic_league()
    post = DixonColesFitter().fit(rows, as_of=date(2026, 6, 1))
    return post, teams, att, dfn


@pytest.fixture
def epl_fixtures(registry) -> list[Fixture]:
    ko = datetime(2026, 10, 10, 14, 0, tzinfo=UTC)
    pairs = [
        ("eng.arsenal", "eng.leeds"),
        ("eng.chelsea", "eng.bournemouth"),
        ("eng.liverpool", "eng.man_city"),
    ]
    out = []
    for h, a in pairs:
        out.append(
            Fixture(
                fixture_id=Fixture.make_id(
                    "eng.premier_league", "2026-27", h, a, stage="Matchday 6"
                ),
                competition_id="eng.premier_league",
                season_id="2026-27",
                home_team_id=h,
                away_team_id=a,
                kickoff_utc=ko,
                kickoff_date="2026-10-10",
                stage="Matchday 6",
            )
        )
    return out
