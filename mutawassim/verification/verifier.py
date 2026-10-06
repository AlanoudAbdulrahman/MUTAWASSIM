"""
verifier.py — الحكم على الادعاء بناءً على الأدلة المسترجَعة فقط (grounded).
المالك: غيداء (التحقق).

قاعدة صارمة: لا حكم من معرفة النموذج. عند غياب دليل كافٍ -> needs_review.
MOCK: يشتق الحالة من حكم أقرب دليل (موضوع->fabricated، ضعيف->weak، صحيح->confirmed).
الحقيقي:
  - مع مفتاح LLM: نموذج لغوي مقيّد بالأدلة يعيد الحالة + التبرير.
  - بلا مفتاح: استرجاع e5 دلالي + حكم من درجة المصدر (هبوط آمن).
"""
from __future__ import annotations

from typing import get_args

from ..schemas import Claim, Evidence, Status, VerificationResult
from .. import config
from ..retrieval.retriever import retrieve
from ..retrieval.arabic import coverage
from ..llm import chat_json

_SYSTEM = (
    "أنت محقّق يصدر الحكم من الأدلة المرفقة فقط. أعد JSON: "
    '{"status":"confirmed|weak|fabricated|needs_review","confidence":0..1,"note":"..."}. '
    "لا تستخدم معرفتك الخاصة. إن لم تكفِ الأدلة أعد needs_review."
)

_VALID_STATUSES = frozenset(get_args(Status))

_RULING_TO_STATUS = {
    "موضوع": "fabricated",
    "باطل": "fabricated",
    "لا أصل له": "fabricated",
    "ليس بحديث": "fabricated",   # مقولة نُسبت للنبي ﷺ وليست من كلامه
    "ضعيف": "weak",
    "صحيح": "confirmed",
    "حسن": "confirmed",
    "نص قرآني": "confirmed",     # آية مطابقة لمصدر قرآني (لا درجة للآيات)
}


def _status_from_ruling(ruling: str | None) -> str | None:
    if not ruling:
        return None
    for key, status in _RULING_TO_STATUS.items():
        if key in ruling:
            return status
    return None


def verify(claim: Claim) -> VerificationResult:
    """يرجّع VerificationResult مسنَدًا بالمصدر."""
    evidence: list[Evidence] = retrieve(claim.normalized_query or claim.text)

    # لا أدلة -> امتناع
    if not evidence:
        return VerificationResult(
            claim_id=claim.claim_id, status="needs_review", evidence=[],
            confidence=0.0, note="لا توجد أدلة كافية في الفهرس",
        )

    if config.MOCK_MODE:
        top = evidence[0]
        status = _status_from_ruling(top.ruling) or "needs_review"
        conf = 0.8 if status != "needs_review" else 0.3
        return VerificationResult(
            claim_id=claim.claim_id, status=status, evidence=evidence[:3],
            confidence=conf, note="MOCK: مشتقّ من حكم أقرب مصدر",
        )

    top = evidence[0]
    q = claim.normalized_query or claim.text
    exact = coverage(q, top.snippet) >= config.MIN_COVERAGE

    # تطابق لفظي دقيق، أو غياب مفتاح LLM -> حكم حتمي من درجة المصدر
    # (دقيق وسريع؛ نحتفظ بالـLLM للحالات الدلالية الغامضة فقط)
    if exact or not config.LLM_API_KEY:
        status = _status_from_ruling(top.ruling) or "needs_review"
        conf = 0.85 if status != "needs_review" else 0.3
        note = (
            "تطابق لفظي دقيق: حكم من درجة المصدر" if exact
            else "استرجاع دلالي + حكم من درجة المصدر (بلا LLM)"
        )
        return VerificationResult(
            claim_id=claim.claim_id, status=status, evidence=evidence[:3],
            confidence=conf, note=note,
        )

    # المسار الحقيقي الكامل (حالة دلالية غامضة): LLM مقيّد بالأدلة
    ev_text = "\n".join(f"- [{e.ruling}] {e.snippet} ({e.url})" for e in evidence)
    data = chat_json(_SYSTEM, f"الادعاء: {claim.text}\n\nالأدلة:\n{ev_text}")
    if not isinstance(data, dict):
        data = {}
    # رد النموذج غير موثوق الصيغة: حالة غير معروفة أو ثقة غير رقمية -> needs_review
    status = str(data.get("status") or "").strip().lower()
    if status not in _VALID_STATUSES:
        status = "needs_review"
    try:
        conf = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
    except (TypeError, ValueError):
        conf = 0.0
    if conf < config.MIN_CONFIDENCE:
        status = "needs_review"
    note = data.get("note")
    if not isinstance(note, str):
        note = None
    return VerificationResult(
        claim_id=claim.claim_id, status=status, evidence=evidence[:3],
        confidence=conf, note=note,
    )
