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
    assert "حكمه في الدرر السنية: موضوع." in c
    assert "«حب الوطن من الإيمان»" in c
    assert "dorar.net" not in c  # the link is listed under sources, not in the text


def test_confirmed_correction_quotes_evidence():
    ev = EV.model_copy(update={"ruling": "صحيح", "snippet": "إنما الأعمال بالنيات"})
    c = _card("confirmed", evidence=[ev]).correction
    assert c == "ورد في الدرر السنية بنصّه: «إنما الأعمال بالنيات»."


@pytest.mark.parametrize("status", get_args(Status))
def test_internal_note_never_reaches_the_user(status):
    note = "MOCK: مشتقّ من حكم أقرب مصدر"
    assert note not in _card(status, note=note).correction


def test_missing_ruling_falls_back_to_status_label():
    ev = EV.model_copy(update={"ruling": None})
    assert _card("weak", evidence=[ev]).correction.startswith("الحكم: ضعيف.")


def test_needs_review_with_evidence_does_not_claim_no_evidence():
    ev = EV.model_copy(update={"ruling": None, "source": "quranpedia.net",
                               "snippet": "إن الله وملائكته يصلون على النبي"})
    c = _card("needs_review", evidence=[ev]).correction
    assert "لا يوجد دليل" not in c
    assert "يُحال للمختص" in c and "قرآنبيديا" in c


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


def _question_card(evidence=None):
    claim = Claim(claim_id="q1", source_post_id="p1", type="other",
                  text="سؤال عن حكم الاستثمار في البيتكوين")
    result = VerificationResult(claim_id="q1", status="needs_review",
                                evidence=[] if evidence is None else evidence)
    return rg.build_card(claim, result, RiskScore(claim_id="q1", risk=0.2))


def test_question_gets_its_own_label_and_is_referred():
    card = _question_card()
    assert card.verdict_label == "يحتاج تحقق"
    assert card.action == "إحالة لمختص"
    assert "لا يُصدر فتاوى" in card.correction
    assert "لا يوجد دليل" not in card.correction


def test_question_shows_related_source_as_help_for_the_expert():
    c = _question_card(evidence=[EV]).correction
    assert "قد تفيد المختص، في الدرر السنية" in c
    assert "لا يكفي لإصدار حكم" not in c


def test_unknown_source_name_is_shown_as_is():
    ev = EV.model_copy(update={"source": "example.org/x"})
    assert "example.org/x" in _card(evidence=[ev]).correction


def test_no_boilerplate_advice_on_ordinary_cards():
    assert "يُنصح" not in _card("fabricated").correction


def test_card_quotes_the_evidence_that_matches_the_verdict():
    # The LLM may judge from a lower-ranked source; the text must not contradict the badge.
    sahih = EV.model_copy(update={"ruling": "صحيح", "snippet": "نص صحيح قريب", "url": "u1"})
    daif = EV.model_copy(update={"ruling": "ضعيف", "snippet": "النص الضعيف المطابق", "url": "u2"})
    card = _card("weak", evidence=[sahih, daif])
    assert card.verdict_label == "ضعيف"
    assert "حكمه في الدرر السنية: ضعيف." in card.correction
    assert "«النص الضعيف المطابق»" in card.correction
    assert "صحيح" not in card.correction


def test_verdict_not_backed_by_any_source_is_not_attributed_to_it():
    ev = EV.model_copy(update={"ruling": "صحيح"})
    c = _card("fabricated", evidence=[ev]).correction
    assert c.startswith("الحكم: موضوع.")
    assert "وأقرب نص في الدرر السنية" in c
    assert "صحيح" not in c
