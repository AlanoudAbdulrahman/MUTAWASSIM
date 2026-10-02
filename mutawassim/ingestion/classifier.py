"""
classifier.py — فلترة المحتوى الديني عن الضجيج.
المالك: سارة (البيانات).

MOCK: تصنيف بقواعد كلمات مفتاحية. لاحقًا: استبدلوه بمصنّف embeddings.
ملاحظة خصوصية: نصنّف المحتوى فقط، لا نصنّف سمات الناشر.
"""
from __future__ import annotations

from ..schemas import Post

# كلمات دالة على محتوى ديني قابل للتحقق (قابلة للتوسيع)
_RELIGIOUS_HINTS = (
    "حديث", "رسول", "النبي", "صلى الله", "قال الله", "آية", "سورة", "القرآن",
    "الصحابة", "روى", "أخرجه", "البخاري", "مسلم", "السنة", "الإسلام", "التوحيد",
    "العقيدة", "الفقه", "الشرع", "الدعاء", "الزكاة", "الصلاة",
)


def is_religious(text: str) -> bool:
    """هل المحتوى ذو طابع ديني قابل للتحقق؟ (MOCK بقواعد)."""
    t = text or ""
    return any(h in t for h in _RELIGIOUS_HINTS)


def filter_posts(posts: list[Post]) -> list[Post]:
    """يبقي المنشورات الدينية فقط."""
    return [p for p in posts if is_religious(p.text)]
