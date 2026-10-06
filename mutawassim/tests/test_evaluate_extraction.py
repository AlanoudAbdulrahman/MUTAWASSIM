"""Tests for the extraction metric itself, using fake extractors."""
import json

from mutawassim.evaluation import evaluate_extraction as ev
from mutawassim.schemas import Claim

GOLD = json.loads(ev.EXTRACTION_TEST_FILE.read_text(encoding="utf-8"))
_BY_ID = {row["post_id"]: row for row in GOLD}


def _gold_extractor(post):
    """Returns exactly the gold claims, as a perfect extractor would."""
    return [
        Claim(claim_id=f"{post.post_id}_c{i:02d}", source_post_id=post.post_id,
              original_text=post.text, **c)
        for i, c in enumerate(_BY_ID[post.post_id]["expected_claims"])
    ]


def test_gold_file_loads_as_utf8():
    assert GOLD and all("expected_claims" in row for row in GOLD)


def test_perfect_extractor_scores_one(monkeypatch):
    monkeypatch.setattr(ev, "extract_claims", _gold_extractor)
    m = ev.evaluate_extraction()
    assert m["claim_precision"] == m["claim_recall"] == m["claim_f1"] == 1.0
    assert m["type_accuracy"] == m["no_claim_accuracy"] == 1.0
    assert m["errors"] == 0 and m["failures"] == []


def test_wrong_type_lowers_type_accuracy_only(monkeypatch):
    def wrong_type(post):
        # "history" is not the expected type of any gold claim
        return [c.model_copy(update={"type": "history"}) for c in _gold_extractor(post)]

    monkeypatch.setattr(ev, "extract_claims", wrong_type)
    m = ev.evaluate_extraction()
    assert m["claim_f1"] == 1.0
    assert m["type_accuracy"] == 0.0


def test_extra_claim_on_empty_post_is_false_positive(monkeypatch):
    def noisy(post):
        claims = _gold_extractor(post)
        if not claims:
            claims = [Claim(claim_id="x", source_post_id=post.post_id, text=post.text)]
        return claims

    monkeypatch.setattr(ev, "extract_claims", noisy)
    m = ev.evaluate_extraction()
    assert m["claim_recall"] == 1.0
    assert m["claim_precision"] < 1.0
    assert m["no_claim_accuracy"] == 0.0


def test_provider_errors_count_as_missed_claims(monkeypatch):
    def broken(post):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(ev, "extract_claims", broken)
    m = ev.evaluate_extraction()
    assert m["errors"] == len(GOLD)
    assert m["claim_recall"] == 0.0


def test_overlap_tolerates_punctuation_and_diacritics():
    assert ev._overlap("قال النبيُّ: إنما الأعمالُ بالنيات.", "قال النبي إنما الأعمال بالنيات") == 1.0
    assert ev._overlap("سورة الفاتحة سبع آيات", "سورة الإخلاص أربع آيات") < ev.MATCH_THRESHOLD
