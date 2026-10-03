"""Contract tests; mocked model replies do not measure extraction quality."""
import json

import pytest

from mutawassim.extraction import claim_extractor as extractor
from mutawassim.schemas import Post


@pytest.fixture
def real_mode(monkeypatch):
    monkeypatch.setattr(extractor.config, "MOCK_MODE", False)


def test_prompt_roles_and_source_linkage(real_mode, monkeypatch):
    post = Post(post_id="p1", text="لم يقل الباحث سالم إن الحدث وقع عام ١٢٠٠.")
    reply = {
        "claims": [{
            "text": post.text,
            "type": "attribution",
            "normalized_query": "لم يقل الباحث سالم الحدث وقع عام ١٢٠٠",
        }]
    }
    calls = []

    def fake_chat(system, user):
        calls.append((system, user))
        return reply

    monkeypatch.setattr(extractor, "chat_json", fake_chat)
    claims = extractor.extract_claims(post)
    assert len(calls) == 1
    assert calls[0][0] == extractor._SYSTEM_PROMPT
    assert calls[0][1] == extractor._USER_PROMPT.format(
        post_json=json.dumps({"post_text": post.text}, ensure_ascii=False)
    )
    assert claims[0].model_dump() == {
        "claim_id": "p1_c00",
        "source_post_id": "p1",
        "text": post.text,
        "original_text": post.text,
        "type": "attribution",
        "normalized_query": reply["claims"][0]["normalized_query"],
    }


def test_multiple_claims_and_exact_duplicates(real_mode, monkeypatch):
    item = {"text": "سورة الفاتحة سبع آيات", "type": "quran",
            "normalized_query": "الفاتحة سبع آيات"}
    second = {"text": "قال الباحث سالم إن الحدث وقع عام ١٢٠٠",
              "type": "attribution"}
    monkeypatch.setattr(extractor, "chat_json",
                        lambda *_: {"claims": [item, dict(item), second]})
    post = Post(post_id="batch", text="منشور تجريبي")
    claims = extractor.extract_claims(post)
    assert [c.claim_id for c in claims] == ["batch_c00", "batch_c01"]
    assert claims[1].normalized_query == second["text"]


def test_same_text_with_different_types_is_one_claim(real_mode, monkeypatch):
    text = "قال النبي: إنما الأعمال بالنيات"
    monkeypatch.setattr(extractor, "chat_json", lambda *_: {"claims": [
        {"text": text, "type": "hadith"},
        {"text": f"  {text} ", "type": "attribution"},
    ]})
    claims = extractor.extract_claims(Post(post_id="p", text=text))
    assert [(c.claim_id, c.type) for c in claims] == [("p_c00", "hadith")]


@pytest.mark.parametrize("raw_type, expected", [
    ("Hadith", "hadith"), (" QURAN ", "quran"),
    ("fiqh", "other"), ("invalid", "other"), (None, "other"), ("", "other"),
])
def test_type_is_normalized_not_rejected(real_mode, monkeypatch, raw_type, expected):
    item = {"text": "ادعاء قابل للتحقق"}
    if raw_type is not None:
        item["type"] = raw_type
    monkeypatch.setattr(extractor, "chat_json", lambda *_: {"claims": [item]})
    claims = extractor.extract_claims(Post(post_id="p", text="منشور تجريبي"))
    assert [c.type for c in claims] == [expected]


def test_no_claims_is_valid(real_mode, monkeypatch):
    monkeypatch.setattr(extractor, "chat_json", lambda *_: {"claims": []})
    assert extractor.extract_claims(Post(post_id="p", text="اللهم ارزقنا الطمأنينة")) == []


@pytest.mark.parametrize("reply", [
    None, {}, {"claims": None}, {"claims": {}}, {"claims": [None]},
    {"claims": [{"text": " ", "type": "hadith"}]},
    {"claims": [{"text": "ادعاء", "type": ["hadith"]}]},
    {"claims": [{"text": 123, "type": "hadith"}]},
    {"claims": [{"text": "ادعاء", "type": "hadith", "normalized_query": 123}]},
    {"claims": [{"text": "ادعاء", "type": "hadith"}, {"text": ""}]},
])
def test_malformed_response_raises(real_mode, monkeypatch, reply):
    monkeypatch.setattr(extractor, "chat_json", lambda *_: reply)
    with pytest.raises(ValueError):
        extractor.extract_claims(Post(post_id="p", text="منشور تجريبي"))


def test_provider_failure_is_not_no_claims(real_mode, monkeypatch):
    def unavailable(*_):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(extractor, "chat_json", unavailable)
    with pytest.raises(RuntimeError, match="provider unavailable"):
        extractor.extract_claims(Post(post_id="p", text="منشور تجريبي"))


def test_empty_post_does_not_call_provider(real_mode, monkeypatch):
    def unexpected(*_):
        pytest.fail("Empty posts must not call the provider")

    monkeypatch.setattr(extractor, "chat_json", unexpected)
    assert extractor.extract_claims(Post(post_id="p", text="  ")) == []


def test_mock_does_not_call_provider(monkeypatch):
    monkeypatch.setattr(extractor.config, "MOCK_MODE", True)

    def unexpected(*_):
        pytest.fail("MOCK must not call the provider")

    monkeypatch.setattr(extractor, "chat_json", unexpected)
    claims = extractor.extract_claims(
        Post(post_id="p", text="قال النبي إنما الأعمال بالنيات؟سورة الفاتحة سبع آيات")
    )
    assert [c.type for c in claims] == ["hadith", "quran"]
