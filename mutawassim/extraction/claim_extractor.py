"""
claim_extractor.py — استخراج الادعاءات القابلة للتحقق من منشور.
المالك: العنود (الاستخراج).

MOCK (أو بلا مفتاح LLM): تقسيم النص إلى جمل واعتبار كل جملة ادعاءً مبدئيًا.
الحقيقي الكامل: LLM بموجّه يستخرج الادعاءات ويصنّف النوع ويكتب normalized_query.
"""
from __future__ import annotations

import re

from ..schemas import Claim, ClaimType, Post
from .. import config
from ..llm import chat_json

_SENT_SPLIT = re.compile(r"[.!؟\n]+")

_SYSTEM = (
    "أنت مستخرِج ادعاءات دينية قابلة للتحقق. أعد JSON بالشكل: "
    '{"claims":[{"text":"...","type":"hadith|quran|aqeedah|history|attribution|shubha|other",'
    '"normalized_query":"..."}]}. '
    "استخرج فقط ما يمكن التحقق منه (حديث/آية/نسبة قول/معلومة عقدية أو تاريخية). "
    "لا تصدر أحكامًا. تجاهل الكلام غير القابل للتحقق."
)


def _guess_type(text: str) -> ClaimType:
    if any(w in text for w in ("حديث", "روى", "أخرجه", "البخاري", "مسلم", "النبي")):
        return "hadith"
    if any(w in text for w in ("آية", "سورة", "قال الله", "القرآن")):
        return "quran"
    if any(w in text for w in ("التوحيد", "العقيدة", "الإيمان")):
        return "aqeedah"
    return "other"


def _split_extract(post: Post) -> list[Claim]:
    """استخراج حتمي بتقسيم الجمل (بلا LLM)."""
    claims: list[Claim] = []
    for j, sent in enumerate(_SENT_SPLIT.split(post.text)):
        s = sent.strip()
        if len(s) < 10:
            continue
        claims.append(
            Claim(
                claim_id=f"{post.post_id}_c{j:02d}",
                source_post_id=post.post_id,
                text=s,
                original_text=post.text,
                type=_guess_type(s),
                normalized_query=s,
            )
        )
    return claims


def extract_claims(post: Post) -> list[Claim]:
    """يرجّع list[Claim] من منشور واحد."""
    # الاستخراج الحتمي هو الافتراضي: يحفظ النص الأصلي فتبقى المطابقة دقيقة.
    # الـLLM يُستخدم فقط إذا فُعّل صراحةً (USE_LLM_EXTRACT=1) ومتاح.
    if config.MOCK_MODE or not config.LLM_API_KEY or not config.USE_LLM_EXTRACT:
        return _split_extract(post)

    data = chat_json(_SYSTEM, post.text)
    out: list[Claim] = []
    for j, c in enumerate(data.get("claims", [])):
        out.append(
            Claim(
                claim_id=f"{post.post_id}_c{j:02d}",
                source_post_id=post.post_id,
                text=c.get("text", ""),
                original_text=post.text,
                type=c.get("type", "other"),
                normalized_query=c.get("normalized_query") or c.get("text", ""),
            )
        )
    return out
