"""Keyword layer of the religious filter (MOCK mode: no semantic layer)."""
import pytest

from mutawassim.ingestion import classifier


@pytest.fixture(autouse=True)
def keywords_only(monkeypatch):
    monkeypatch.setattr(classifier.config, "MOCK_MODE", True)


@pytest.mark.parametrize("text", [
    "البيتكوين حلال ولا حرام؟",
    "هل يجوز دفع الرشوة؟",
    "هل تجوز الرشوة لتخليص معاملة؟",
    "وش حكم الرشوة؟",
    "ما حكم الاستثمار في الأسهم؟",
    "هل الموسيقى محرمة؟",
    "هل يحرم الأكل واقفًا؟",
    "كم ركعة صلاة الفجر؟",
    "ينفع أصوم وأنا مسافر؟",
])
def test_religious_questions_pass(text):
    assert classifier.is_religious(text)


@pytest.mark.parametrize("text", [
    "الطقس اليوم جميل",
    "خصومات كبيرة على الملابس",
    "زرت المحكمة اليوم",
    "هذي حكمة جميلة",
    "محرمات الطبخ الصحي",
    "يحرم علي النوم من التعب",
])
def test_everyday_text_is_filtered(text):
    assert not classifier.is_religious(text)
