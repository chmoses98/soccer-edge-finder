from __future__ import annotations

from datetime import date

import numpy as np

from soccer_edge.model.xg_family import FAMILY_ID, fit_xg_family, rows_from_results_xg
from soccer_edge.providers.football_data_couk import FootballDataCoUkProvider
from soccer_edge.providers.interfaces import MatchResult

CSV_XG = """\ufeffDiv,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HTHG,HTAG,HTR,Referee,HxG,AxG,HS,AS,B365H,B365D,B365A
E0,15/08/2026,20:00,Liverpool,Bournemouth,4,2,H,1,0,H,X,2.85,1.10,18,9,1.25,6.0,11.0
E0,16/08/2026,15:00,Arsenal,Leeds,1,0,H,0,0,D,X,,,14,6,1.30,5.5,9.0
"""


def _results(n=80, xg=True):
    rng = np.random.default_rng(1)
    teams = [f"t{i}" for i in range(8)]
    out = []
    k = 0
    for i, h in enumerate(teams):
        for j, a in enumerate(teams):
            if h == a:
                continue
            k += 1
            hg, ag = int(rng.poisson(1.4 + 0.1 * i)), int(rng.poisson(1.1 + 0.1 * j))
            out.append(
                MatchResult(
                    fixture_id=f"f{k}",
                    competition_id="c",
                    season_id="2026-27",
                    match_date=f"2026-0{1 + k % 8}-{1 + k % 27:02d}",
                    home_team_id=h,
                    away_team_id=a,
                    home_goals=hg,
                    away_goals=ag,
                    home_xg=(hg * 0.8 + 0.3) if xg and k % 3 else None,
                    away_xg=(ag * 0.9 + 0.2) if xg and k % 3 else None,
                )
            )
    return out


def test_rows_blend_xg_where_present_and_fit_runs():
    res = _results()
    rows, n_xg = rows_from_results_xg(res, weight=0.7)
    assert n_xg == sum(1 for r in res if r.home_xg is not None) and 0 < n_xg < len(res)
    r0 = next(r for r in res if r.home_xg is not None)
    row0 = rows[res.index(r0)]
    assert abs(row0.home_goals - (0.7 * r0.home_xg + 0.3 * r0.home_goals)) < 1e-12
    r1 = next(r for r in res if r.home_xg is None)
    assert rows[res.index(r1)].home_goals == float(r1.home_goals)
    post, rep = fit_xg_family(res, as_of=date(2026, 12, 31))
    assert rep.family == FAMILY_ID and rep.rows_with_xg == n_xg and "NOT_EVALUATED" in rep.evidence
    assert np.isfinite(post.mean).all()
    post_goals, _ = fit_xg_family(_results(xg=False), as_of=date(2026, 12, 31))
    assert post.mean.shape == post_goals.mean.shape


def test_football_data_couk_results_with_xg(registry, monkeypatch):
    prov = FootballDataCoUkProvider(registry=registry)

    class Obs:
        def __init__(self, rows):
            import csv
            import io
            from datetime import UTC, datetime

            from soccer_edge.providers.base import Provenance, QualityFlag

            self.payload = list(csv.DictReader(io.StringIO(CSV_XG.lstrip("\ufeff"))))
            self.provenance = Provenance(
                source="football_data_couk", observed_at=datetime(2026, 9, 28, tzinfo=UTC)
            )
            self.flags = (QualityFlag.OK,)
            self.notes = ()

    monkeypatch.setattr(prov, "raw_rows", lambda division, season_id: Obs(None))
    obs = prov.results_with_xg("E0", "2026-27")
    assert len(obs.payload) == 2
    liv = next(r for r in obs.payload if r.home_team_id == "eng.liverpool")
    assert (
        liv.home_xg == 2.85 and liv.away_xg == 1.10 and liv.home_goals == 4 and liv.home_shots == 18
    )
    ars = next(r for r in obs.payload if r.home_team_id == "eng.arsenal")
    assert ars.home_xg is None and ars.away_goals == 0
    assert any("xg_columns=present" in n for n in obs.notes)
