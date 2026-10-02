"""
report_generator.py — توليد بطاقة الرد الموثّقة.
المالك: العنود (الرد).

التصحيح من الأدلة المسترجَعة فقط. needs_review -> امتناع. الخلافي -> إحالة لمختص.
"""
from __future__ import annotations

from ..schemas import Claim, ResponseCard, RiskScore, VerificationResult, STATUS_LABEL_AR


def build_card(claim: Claim, result: VerificationResult, risk: RiskScore) -> ResponseCard:
    """يرجّع ResponseCard نهائية."""
    sources = [e.url for e in result.evidence if e.url]

    if result.status == "needs_review":
        action = "امتناع"
        correction = "لا يوجد دليل كافٍ في المصادر المعتمدة؛ يُحال للمختص قبل أي حكم."
    elif result.status == "confirmed":
        action = "رد"
        correction = f"الادعاء مؤكد في المصادر المعتمدة. {result.note or ''}".strip()
    else:  # weak | fabricated
        action = "رد"
        top = result.evidence[0] if result.evidence else None
        ruling = top.ruling if top else ""
        correction = (
            f"الحكم: {ruling or STATUS_LABEL_AR[result.status]}. "
            "اعتمد التصحيح على المصدر المرفق؛ يُنصح بعرضه بلطف مع النص الصحيح."
        )

    # الخلافي الحسّاس يُحال حتى لو ورد حكم
    if claim.type in ("aqeedah",) and result.status == "needs_review":
        action = "إحالة لمختص"

    return ResponseCard(
        claim_id=claim.claim_id,
        verdict_label=STATUS_LABEL_AR.get(result.status, result.status),
        correction=correction,
        sources=sources,
        action=action,
        risk=risk.risk,
    )
