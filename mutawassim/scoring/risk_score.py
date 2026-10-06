"""
risk_score.py — مؤشر الخطورة الشفّاف.
المالك: العنود (الخطورة).

risk = spread * severity * sensitivity   (كلها بين 0 و 1)
"""
from __future__ import annotations

from collections import defaultdict

from ..schemas import Claim, RiskFactors, RiskScore, VerificationResult

# درجة البطلان حسب الحالة
_SEVERITY = {
    "fabricated": 1.0,     # موضوع/باطل: نسبة كلام مكذوب للدين، أعلى ضرر
    "weak": 0.6,           # ضعيف: له أصل لكن لا يصح الاحتجاج به
    "needs_review": 0.4,   # لا دليل كافٍ: خطره مجهول، فيُرفع للمختص دون تقديمه على الثابت ضعفه
    "confirmed": 0.0,      # مؤكد: لا يحتاج تصحيحًا
}

# حساسية الموضوع حسب النوع
_SENSITIVITY = {
    "aqeedah": 1.0,        # العقيدة: الخطأ فيها يمس أصل الدين
    "quran": 1.0,          # القرآن: نص قطعي، أي تحريف فيه خطير
    "shubha": 0.9,         # الشبهة: تستهدف التشكيك مباشرة
    "hadith": 0.8,         # الحديث: نسبة قول للنبي صلى الله عليه وسلم
    "attribution": 0.7,    # قول منسوب لعالم أو جهة: أقل من النسبة للنبي
    "history": 0.6,        # واقعة تاريخية: أثرها على الدين غير مباشر غالبًا
    "other": 0.5,          # غير مصنّف: قيمة وسطى محايدة
}

# كل منشور إضافي يذكر الادعاء يغطي 20% مما تبقى للوصول إلى 1:
# منشور واحد ≈ 0.2، خمسة ≈ 0.67، عشرون ≈ 0.99. مطلق لا يعتمد على حجم الدفعة.
_SPREAD_DECAY = 0.8


def _spread_from_count(posts: int) -> float:
    return round(1 - _SPREAD_DECAY ** max(0, posts), 4)


spread_from_count = _spread_from_count


def compute_spread(claims: list[Claim]) -> dict[str, float]:
    """يرجّع {claim_id: spread} حسب عدد المنشورات المختلفة التي ذكرت نفس صيغة البحث."""
    posts_by_query: dict[str, set[str]] = defaultdict(set)
    for c in claims:
        posts_by_query[" ".join(c.normalized_query.split())].add(c.source_post_id)
    return {
        c.claim_id: _spread_from_count(len(posts_by_query[" ".join(c.normalized_query.split())]))
        for c in claims
    }


def score(
    claim: Claim, result: VerificationResult, spread: float = _spread_from_count(1)
) -> RiskScore:
    """يحسب الخطورة. spread = مدى انتشار الادعاء (0..1)، الافتراضي: منشور واحد."""
    severity = _SEVERITY.get(result.status, 0.4)
    sensitivity = _SENSITIVITY.get(claim.type, 0.5)
    spread = max(0.0, min(1.0, spread))
    factors = RiskFactors(spread=spread, severity=severity, sensitivity=sensitivity)
    return RiskScore(
        claim_id=claim.claim_id,
        risk=round(spread * severity * sensitivity, 4),
        factors=factors,
    )
