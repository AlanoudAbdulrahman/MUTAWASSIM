"""Tests for the transparent risk score: risk = spread * severity * sensitivity."""
from typing import get_args

import pytest

from mutawassim.scoring import risk_score as rs
from mutawassim.schemas import Claim, ClaimType, Status, VerificationResult


def _claim(claim_type="hadith", claim_id="c1", post_id="p1", query="ادعاء"):
    return Claim(claim_id=claim_id, source_post_id=post_id, text="ادعاء",
                 type=claim_type, normalized_query=query)


def _result(status="fabricated"):
    return VerificationResult(claim_id="c1", status=status)


def test_every_status_and_type_has_a_weight():
    # Guards the shared contract: a new status/type in schemas.py needs a weight here.
    assert set(get_args(Status)) <= set(rs._SEVERITY)
    assert set(get_args(ClaimType)) <= set(rs._SENSITIVITY)


def test_risk_is_product_of_factors():
    r = rs.score(_claim("hadith"), _result("weak"), spread=0.5)
    assert r.claim_id == "c1"
    assert r.factors.spread == 0.5
    assert r.factors.severity == rs._SEVERITY["weak"]
    assert r.factors.sensitivity == rs._SENSITIVITY["hadith"]
    assert r.risk == round(0.5 * 0.6 * 0.8, 4)


def test_confirmed_claim_has_zero_risk():
    assert rs.score(_claim("aqeedah"), _result("confirmed"), spread=1.0).risk == 0.0


@pytest.mark.parametrize("spread, expected", [(-0.5, 0.0), (0.0, 0.0), (1.7, 1.0)])
def test_spread_is_clamped(spread, expected):
    r = rs.score(_claim(), _result(), spread=spread)
    assert r.factors.spread == expected
    assert 0.0 <= r.risk <= 1.0


def test_default_spread_is_single_post():
    r = rs.score(_claim("quran"), _result("fabricated"))
    assert r.factors.spread == rs._spread_from_count(1) == 0.2
    assert r.risk == 0.2


@pytest.mark.parametrize("posts, expected", [(0, 0.0), (1, 0.2), (5, 0.6723), (20, 0.9885)])
def test_spread_from_count(posts, expected):
    assert rs._spread_from_count(posts) == expected


def test_compute_spread_counts_distinct_posts():
    claims = [
        _claim(claim_id="a", post_id="p1", query="حب الوطن من الإيمان"),
        _claim(claim_id="b", post_id="p2", query="حب  الوطن من الإيمان "),
        _claim(claim_id="c", post_id="p3", query="حب الوطن من الإيمان"),
        _claim(claim_id="d", post_id="p3", query="النظافة من الإيمان"),
    ]
    spread = rs.compute_spread(claims)
    assert spread["a"] == spread["b"] == spread["c"] == rs._spread_from_count(3)
    assert spread["d"] == rs._spread_from_count(1)


def test_compute_spread_does_not_depend_on_batch_size():
    alone = rs.compute_spread([_claim(claim_id="x", query="ادعاء نادر")])
    with_popular = rs.compute_spread(
        [_claim(claim_id="x", query="ادعاء نادر")]
        + [_claim(claim_id=f"p{i}", post_id=f"p{i}", query="ادعاء منتشر") for i in range(10)]
    )
    assert alone["x"] == with_popular["x"] == rs._spread_from_count(1)


def test_same_post_repeating_claim_counts_once():
    claims = [_claim(claim_id=f"c{i}", post_id="p1", query="ادعاء") for i in range(3)]
    assert set(rs.compute_spread(claims).values()) == {rs._spread_from_count(1)}


def test_compute_spread_empty():
    assert rs.compute_spread([]) == {}


def test_risk_stays_in_unit_range_for_all_combinations():
    for status in get_args(Status):
        for claim_type in get_args(ClaimType):
            risk = rs.score(_claim(claim_type), _result(status), spread=1.0).risk
            assert 0.0 <= risk <= 1.0


def test_severity_orders_statuses():
    risks = {
        s: rs.score(_claim(), _result(s), spread=1.0).risk
        for s in ("fabricated", "weak", "needs_review", "confirmed")
    }
    assert risks["fabricated"] > risks["weak"] > risks["needs_review"] > risks["confirmed"]
