"""
report_generator.py — توليد بطاقة الرد الموثّقة.
المالك: العنود (الرد).

التصحيح من الأدلة المسترجَعة فقط: يعرض حكم المصدر ونصه واسمه، ولا يعرض
ملاحظات التحقق الداخلية (note) لأنها تقنية وليست موجّهة للمستخدم.

الإجراء:
- confirmed                                  -> رد
- needs_review (لا دليل كافٍ)                 -> إحالة لمختص
- weak/fabricated في موضوع حسّاس (عقيدة/شبهة) -> إحالة لمختص
- weak/fabricated في غيره                    -> رد
"""
from __future__ import annotations

from ..schemas import (
    Action, Claim, Evidence, ResponseCard, RiskScore, VerificationResult, STATUS_LABEL_AR,
)

# أنواع لا يُرد عليها آليًا إلا إذا ثبتت صحتها؛ غير ذلك يراجعه مختص
_SENSITIVE_TYPES = frozenset({"aqeedah", "shubha"})

_SNIPPET_MAX = 200


def _quote(e: Evidence) -> str:
    """نص الدليل مختصرًا بين علامتي تنصيص."""
    text = " ".join(e.snippet.split())
    if len(text) > _SNIPPET_MAX:
        text = text[:_SNIPPET_MAX].rsplit(" ", 1)[0] + "…"
    return f"«{text}»"


def _action(claim: Claim, result: VerificationResult) -> Action:
    if result.status == "confirmed":
        return "رد"
    if result.status == "needs_review" or claim.type in _SENSITIVE_TYPES:
        return "إحالة لمختص"
    return "رد"


def _correction(result: VerificationResult, action: Action) -> str:
    top = result.evidence[0] if result.evidence else None

    if top is None:
        return "لا يوجد دليل كافٍ في المصادر المعتمدة؛ يُحال للمختص قبل أي حكم."

    source = f"المصدر: {top.source}." if top.source else ""
    quote = f"النص في المصدر: {_quote(top)}." if top.snippet.strip() else ""

    if result.status == "needs_review":
        # وُجد مصدر قريب لكنه لا يكفي للحكم (مثل آية بلا درجة)؛ نعرضه للمختص
        parts = ["وُجد مصدر ذو صلة لكنه لا يكفي لإصدار حكم؛ يُحال للمختص.", source, quote]
        return " ".join(p for p in parts if p)

    if result.status == "confirmed":
        parts = ["الادعاء ثابت في المصادر المعتمدة.", source, quote]
    else:  # weak | fabricated
        ruling = top.ruling or STATUS_LABEL_AR[result.status]
        parts = [f"الحكم: {ruling}.", source, quote]
        if action == "إحالة لمختص":
            parts.append("موضوع حسّاس؛ يراجعه مختص قبل نشر الرد.")
        else:
            parts.append("يُنصح بعرض التصحيح بلطف مع إرفاق المصدر.")
    return " ".join(p for p in parts if p)


def build_card(claim: Claim, result: VerificationResult, risk: RiskScore) -> ResponseCard:
    """يرجّع ResponseCard نهائية."""
    action = _action(claim, result)
    return ResponseCard(
        claim_id=claim.claim_id,
        verdict_label=STATUS_LABEL_AR.get(result.status, result.status),
        correction=_correction(result, action),
        # روابط فريدة بترتيب قوة الدليل
        sources=list(dict.fromkeys(e.url for e in result.evidence if e.url)),
        action=action,
        risk=risk.risk,
    )
