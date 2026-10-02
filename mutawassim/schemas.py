"""
schemas.py — العقد الموحّد لبيانات متوسّم (source of truth).

كل الوحدات تستورد نماذجها من هنا ولا تعرّف صيغًا خاصة بها.
أي تغيير في الحقول يُناقَش مع قائدة التكامل أولًا.
Pydantic v2.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

# الحالات الأربع المعتمدة (موحّدة) — لا تُضف حالات جديدة دون اتفاق الفريق.
Status = Literal["confirmed", "weak", "fabricated", "needs_review"]
# confirmed=مؤكد · weak=ضعيف · fabricated=موضوع/باطل · needs_review=يحتاج مختصًّا/دليل غير كافٍ

ClaimType = Literal[
    "hadith", "quran", "aqeedah", "history", "attribution", "shubha", "other"
]

Action = Literal["رد", "إحالة لمختص", "امتناع"]


class Post(BaseModel):
    """منشور خام واحد (مدخل النظام)."""
    post_id: str
    text: str
    meta: dict = Field(default_factory=dict)


class Claim(BaseModel):
    """ادعاء قابل للتحقق مستخرَج من منشور."""
    claim_id: str
    source_post_id: str
    text: str                      # نص الادعاء كما يُفهم
    original_text: Optional[str] = None  # النص الأصلي الذي ورد فيه
    type: ClaimType = "other"
    normalized_query: str = ""     # صيغة بحث مختصرة للاسترجاع


class Evidence(BaseModel):
    """دليل مسترجَع من المصادر المعتمدة."""
    source: str                    # مثل: dorar.net/hadith
    url: str
    ruling: Optional[str] = None   # صحيح | ضعيف | موضوع | None
    snippet: str = ""


class VerificationResult(BaseModel):
    """نتيجة التحقق من ادعاء واحد."""
    claim_id: str
    status: Status
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = 0.0        # 0..1
    note: Optional[str] = None


class RiskFactors(BaseModel):
    spread: float = 0.0            # 0..1 تكرار/انتشار الادعاء
    severity: float = 0.0          # 0..1 درجة البطلان
    sensitivity: float = 0.0       # 0..1 حساسية الموضوع


class RiskScore(BaseModel):
    claim_id: str
    risk: float = 0.0              # 0..1 = spread * severity * sensitivity
    factors: RiskFactors = Field(default_factory=RiskFactors)


class ResponseCard(BaseModel):
    """المخرج النهائي: بطاقة ردّ موثّقة لكل ادعاء."""
    claim_id: str
    verdict_label: str             # الحكم بالعربية: مؤكد/ضعيف/موضوع/يحتاج تحقق
    correction: str                # التصحيح/التوضيح المُسنَد (من الأدلة فقط)
    sources: list[str] = Field(default_factory=list)  # روابط المصادر
    action: Action = "امتناع"
    risk: float = 0.0


# خريطة عرض الحالة بالعربية (للوحة والبطاقة)
STATUS_LABEL_AR: dict[str, str] = {
    "confirmed": "مؤكد",
    "weak": "ضعيف",
    "fabricated": "موضوع",
    "needs_review": "يحتاج تحقق",
}
