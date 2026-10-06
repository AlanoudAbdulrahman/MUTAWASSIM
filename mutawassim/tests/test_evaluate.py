"""Metric definitions of evaluate.py, using fake extraction/verification."""
import json

import pytest

from mutawassim.evaluation import evaluate as ev
from mutawassim.schemas import Claim, Evidence, VerificationResult

DAIF = Evidence(source="dorar.net/hadith", url="u1", ruling="ضعيف", snippet="x")
SAHIH = Evidence(source="dorar.net/hadith", url="u2", ruling="صحيح", snippet="y")

# claim text -> (status the fake verifier returns, evidence)
OUTCOMES = {
    "ضعيف مسند": ("weak", [DAIF]),
    "ضعيف بدليل مخالف": ("weak", [SAHIH]),
    "ضعيف بلا رابط": ("weak", [DAIF.model_copy(update={"url": ""})]),
    "يحتاج تحقق": ("needs_review", []),
}


@pytest.fixture
def run(tmp_path, monkeypatch):
    def _run(rows, fail_on=None):
        def extract(post):
            if post.text == fail_on:
                raise RuntimeError("provider unavailable")
            if post.text == "بلا ادعاء":
                return []
            return [Claim(claim_id=post.post_id, source_post_id=post.post_id, text=post.text)]

        def verify(claim):
            status, evidence = OUTCOMES[claim.text]
            return VerificationResult(claim_id=claim.claim_id, status=status, evidence=evidence)

        monkeypatch.setattr(ev, "extract_claims", extract)
        monkeypatch.setattr(ev, "verify", verify)
        path = tmp_path / "set.json"
        path.write_text(json.dumps([{"claim_text": t, "expected_status": s} for t, s in rows],
                                   ensure_ascii=False), encoding="utf-8")
        return ev.evaluate(path)
    return _run


def test_citation_metrics_ignore_needs_review(run):
    m = run([("ضعيف مسند", "weak"), ("يحتاج تحقق", "needs_review")])
    assert m["citation_rate"] == 1.0          # the only verdict has a link
    assert m["citation_accuracy"] == 1.0
    assert m["status_accuracy"] == 1.0


def test_citation_accuracy_requires_a_source_that_backs_the_verdict(run):
    m = run([("ضعيف مسند", "weak"), ("ضعيف بدليل مخالف", "weak"), ("ضعيف بلا رابط", "weak")])
    assert m["citation_rate"] == round(2 / 3, 3)
    assert m["citation_accuracy"] == round(1 / 3, 3)


def test_errors_and_missing_claims_are_counted_not_fatal(run):
    m = run([("ضعيف مسند", "weak"), ("بلا ادعاء", "weak"), ("ضعيف بلا رابط", "weak")],
            fail_on="ضعيف بلا رابط")
    assert m["total"] == 3 and m["errors"] == 1 and m["no_claim"] == 1
    assert m["detection_recall"] == round(1 / 3, 3)
    assert {f["got"] for f in m["failures"]} == {"no_claim", "error: provider unavailable"}


def test_mismatches_are_listed(run):
    m = run([("يحتاج تحقق", "weak")])
    assert m["failures"] == [{"i": 0, "claim": "يحتاج تحقق", "expected": "weak", "got": "needs_review"}]
