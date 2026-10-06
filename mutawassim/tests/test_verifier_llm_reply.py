"""The LLM verdict path must survive malformed model replies."""
import pytest

from mutawassim.schemas import Claim, Evidence
from mutawassim.verification import verifier

EV = Evidence(source="dorar.net/hadith", url="u", ruling="ضعيف", snippet="نص بعيد تماما")


@pytest.fixture
def llm_path(monkeypatch):
    # force the ambiguous path: real mode, a key, evidence that is not an exact match
    monkeypatch.setattr(verifier.config, "MOCK_MODE", False)
    monkeypatch.setattr(verifier.config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(verifier, "retrieve", lambda *_: [EV])


def _verify(monkeypatch, reply):
    monkeypatch.setattr(verifier, "chat_json", lambda *_: reply)
    return verifier.verify(Claim(claim_id="c", source_post_id="p", text="ادعاء مختلف"))


@pytest.mark.parametrize("reply, status", [
    ({"status": "Confirmed", "confidence": 0.9}, "confirmed"),
    ({"status": " weak ", "confidence": "0.8"}, "weak"),
    ({"status": "صحيح", "confidence": 0.9}, "needs_review"),
    ({"status": None, "confidence": 0.9}, "needs_review"),
    ({"status": "fabricated", "confidence": "high"}, "needs_review"),
    ({"status": "fabricated", "confidence": 0.1}, "needs_review"),
    ({}, "needs_review"),
    (None, "needs_review"),
])
def test_malformed_replies_never_crash(llm_path, monkeypatch, reply, status):
    result = _verify(monkeypatch, reply)
    assert result.status == status
    assert 0.0 <= result.confidence <= 1.0


def test_non_string_note_is_dropped(llm_path, monkeypatch):
    result = _verify(monkeypatch, {"status": "weak", "confidence": 0.9, "note": ["x"]})
    assert result.note is None
