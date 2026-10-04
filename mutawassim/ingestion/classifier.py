"""
classifier.py — فلترة المحتوى الديني (فلتر هجين).
المالك: سارة (البيانات) — مدموج داخل الباكج.

الطبقة 1 (كلمات مفتاحية): سريعة وبلا مكتبات، تلتقط الحالات الواضحة.
الطبقة 2 (SBERT دلالي): اختيارية (lazy)، تلتقط السياق الخفي — تعمل خارج وضع MOCK فقط.
ملاحظة خصوصية: نصنّف المحتوى فقط، لا نصنّف سمات الناشر.
"""
from __future__ import annotations

from ..schemas import Post
from .. import config

RELIGIOUS_KEYWORDS = [
    "حديث", "رسول الله", "صلى الله عليه وسلم", "قال الله", "قرآن", "آية",
    "سورة", "صحابي", "الصحابة", "فقه", "سنة", "فتاوى", "فتوى", "حكم الشرع",
    "حلال", "حرام", "يجوز", "لا يجوز", "رواه", "أخرجه", "أخرج", "إسناد",
    "بدعة", "وضوء", "عذاب القبر", "يوم القيامة", "صيام", "زكاة", "الصلاة",
    "التوحيد", "النبي", "الإسلام",
]

_model = None
_label_emb = None


def _semantic_religious(text: str) -> bool:
    """الطبقة الدلالية (lazy، آمنة عند غياب المكتبات)."""
    global _model, _label_emb
    try:
        import torch.nn.functional as F
        from sentence_transformers import SentenceTransformer
        if _model is None:
            _model = SentenceTransformer(config.EMBEDDING_MODEL)
            labels = [
                "محتوى ديني، أحاديث، فقه، فتاوى إسلامية، قرآن",
                "محتوى عام، ترفيه، طبخ، أخبار، يوميات",
            ]
            _label_emb = _model.encode(labels, convert_to_tensor=True)
        emb = _model.encode(text, convert_to_tensor=True)
        scores = F.cosine_similarity(emb.unsqueeze(0), _label_emb)
        return scores[0].item() > scores[1].item()
    except Exception:
        return False  # الهبوط الآمن: نكتفي بالكلمات المفتاحية


def is_religious(text: str) -> bool:
    """هل المحتوى ذو طابع ديني قابل للتحقق؟ (هجين)."""
    t = text or ""
    for w in RELIGIOUS_KEYWORDS:  # الطبقة 1 (substring آمن للعربية)
        if w in t:
            return True
    if not config.MOCK_MODE:      # الطبقة 2 خارج وضع MOCK فقط
        return _semantic_religious(t)
    return False


def filter_posts(posts: list[Post]) -> list[Post]:
    """يبقي المنشورات الدينية فقط."""
    return [p for p in posts if is_religious(p.text)]
