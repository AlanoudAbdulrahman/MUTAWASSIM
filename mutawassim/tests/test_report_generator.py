"""Tests for the response card: action rules and evidence-grounded correction."""
from typing import get_args

import pytest

from mutawassim.reporting import report_generator as rg
from mutawassim.schemas import (
    Claim, ClaimType, Evidence, RiskScore, Status, VerificationResult, STATUS_LABEL_AR,
)

EV = Evidence(source="dorar.net/hadith", url="https://dorar.net/h/1",
              ruling="موضوع", snippet="حب الوطن من الإيمان")


def _card(status="fabricated", claim_type="hadith", evidence=None, note="ملاحظة داخلية", risk=0.5):
    claim = Claim(claim_id="c1", source_post_id="p1", text="ادعاء", type=claim_type)
    result = VerificationResult(
        claim_id="c1", status=status, note=note,
        evidence=[EV] if evidence is None else evidence,
    )
    return rg.build_card(claim, result, RiskScore(claim_id="c1", risk=risk))


@pytest.mark.parametrize("status, claim_type, action", [
    ("confirmed", "aqeedah", "رد"),
    ("confirmed", "hadith", "رد"),
    ("fabricated", "hadith", "رد"),
    ("weak", "history", "رد"),
    ("fabricated", "aqeedah", "إحالة لمختص"),
    ("weak", "shubha", "إحالة لمختص"),
    ("needs_review", "hadith", "إحالة لمختص"),
    ("needs_review", "other", "إحالة لمختص"),
])
def test_action_rules(status, claim_type, action):
    assert _card(status, claim_type).action == action


def test_every_status_and_type_builds_a_card():
    for status in get_args(Status):
        for claim_type in get_args(ClaimType):
            card = _card(status, claim_type)
            assert card.verdict_label == STATUS_LABEL_AR[status]
            assert card.correction


def test_fabricated_correction_shows_ruling_source_and_quote():
    c = _card("fabricated").correction
    assert "الحكم: موضوع." in c
    assert "dorar.net/hadith" in c
    assert "«حب الوطن من الإيمان»" in c


def test_confirmed_correction_quotes_evidence():
    ev = EV.model_copy(update={"ruling": "صحيح", "snippet": "إنما الأعمال بالنيات"})
    c = _card("confirmed", evidence=[ev]).correction
    assert "ثابت" in c and "«إنما الأعمال بالنيات»" in c


@pytest.mark.parametrize("status", get_args(Status))
def test_internal_note_never_reaches_the_user(status):
    note = "MOCK: مشتقّ من حكم أقرب مصدر"
    assert note not in _card(status, note=note).correction


def test_missing_ruling_falls_back_to_status_label():
    ev = EV.model_copy(update={"ruling": None})
    assert "الحكم: ضعيف." in _card("weak", evidence=[ev]).correction


def test_needs_review_with_evidence_does_not_claim_no_evidence():
    ev = EV.model_copy(update={"ruling": None, "source": "quranpedia.net",
                               "snippet": "إن الله وملائكته يصلون على النبي"})
    c = _card("needs_review", evidence=[ev]).correction
    assert "لا يوجد دليل" not in c
    assert "يُحال للمختص" in c and "quranpedia.net" in c


def test_empty_evidence_is_treated_as_insufficient():
    card = _card("fabricated", evidence=[])
    assert "لا يوجد دليل كافٍ" in card.correction
    assert card.sources == []


def test_long_snippet_is_shortened():
    ev = EV.model_copy(update={"snippet": "كلمة " * 100})
    c = _card(evidence=[ev]).correction
    assert "…»" in c
    assert len(c) < 400


def test_sources_are_unique_urls_in_order():
    evidence = [EV, EV.model_copy(update={"url": ""}),
                EV.model_copy(update={"url": "https://dorar.net/h/2"}), EV]
    assert _card(evidence=evidence).sources == ["https://dorar.net/h/1", "https://dorar.net/h/2"]


def test_card_carries_risk_and_claim_id():
    card = _card(risk=0.42)
    assert card.claim_id == "c1"
    assert card.risk == 0.42
