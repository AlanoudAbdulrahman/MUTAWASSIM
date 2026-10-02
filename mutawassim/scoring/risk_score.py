"""
risk_score.py — مؤشر الخطورة الشفّاف.
المالك: العنود (الخطورة).

risk = spread * severity * sensitivity   (كلها بين 0 و 1)
"""
from __future__ import annotations

from ..schemas import Claim, RiskFactors, RiskScore, VerificationResult

# درجة البطلان حسب الحالة
_SEVERITY = {
    "fabricated": 1.0,
    "weak": 0.6,
    "needs_review": 0.4,
    "confirmed": 0.0,
}

# حساسية الموضوع حسب النوع
_SENSITIVITY = {
    "aqeedah": 1.0,
    "quran": 1.0,
    "hadith": 0.8,
    "attribution": 0.7,
    "history": 0.6,
    "shubha": 0.9,
    "other": 0.5,
}


def score(claim: Claim, result: VerificationResult, spread: float = 0.3) -> RiskScore:
    """يحسب الخطورة. spread = مدى انتشار الادعاء في الدفعة (0..1)."""
    severity = _SEVERITY.get(result.status, 0.4)
    sensitivity = _SENSITIVITY.get(claim.type, 0.5)
    spread = max(0.0, min(1.0, spread))
    factors = RiskFactors(spread=spread, severity=severity, sensitivity=sensitivity)
    return RiskScore(
        claim_id=claim.claim_id,
        risk=round(spread * severity * sensitivity, 4),
        factors=factors,
    )
