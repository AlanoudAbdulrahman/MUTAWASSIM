"""Lexical matching must not treat a claim as identical to its negation."""
import pytest

from mutawassim import config
from mutawassim.retrieval.arabic import coverage


@pytest.mark.parametrize("query, doc", [
    ("يجوز الكذب في المزاح", "لا يجوز الكذب في المزاح"),
    ("يؤمن أحدكم حتى يحب لأخيه", "لا يؤمن أحدكم حتى يحب لأخيه ما يحب لنفسه"),
    ("لا صلاة لجار المسجد", "صلاة لجار المسجد في المسجد"),
])
def test_negation_mismatch_is_not_an_exact_match(query, doc):
    assert coverage(query, doc) < config.MIN_COVERAGE


@pytest.mark.parametrize("query, doc", [
    ("لا يؤمن أحدكم حتى يحب لأخيه", "لا يؤمن أحدكم حتى يحب لأخيه ما يحب لنفسه"),
    ("من لم يهتم بأمر المسلمين", "من لم يهتم بأمر المسلمين فليس منهم"),
    ("إنما الأعمال بالنيات", "إنما الأعمال بالنيات، وإنما لكل امرئ ما نوى"),
])
def test_matching_negation_still_matches(query, doc):
    assert coverage(query, doc) >= config.MIN_COVERAGE
