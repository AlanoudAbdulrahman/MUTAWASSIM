"""
arabic.py — تطبيع عربي وتقطيع بسيط للمطابقة اللفظية.
المالك: غيداء (الاسترجاع).

الهدف: مطابقة الحديث حتى مع اختلاف الإملاء (أ/ا، ى/ي، ة/ه، الهمزات)
وتجاهل الكلمات الشائعة التي تضخّم التشابه زورًا (من، في، الـ...).
"""
from __future__ import annotations

import re

# الحركات والتطويل
_DIACRITICS = re.compile(r"[ً-ْٰـ]")
_NON_LETTER = re.compile(r"[^ء-ي\s]")

# كلمات شائعة لا تميّز المعنى
_STOPWORDS = {
    "من", "في", "على", "عن", "الى", "إلى", "و", "او", "أو", "ف", "ب", "ك", "ل",
    "ما", "لا", "ان", "إن", "أن", "انه", "الذي", "التي", "هذا", "هذه", "ذلك",
    "هو", "هي", "قد", "كان", "مع", "عند", "كل", "بعض", "غير", "بين", "لكن",
    "اذا", "اذ", "اي", "يا", "ثم", "حتى", "كما", "به", "بها", "فيه", "فيها",
    "هم", "هن", "انا", "نحن", "انت", "انتم",
}


def normalize(text: str) -> str:
    """تطبيع: إزالة الحركات والتطويل وتوحيد الألف/الياء/التاء المربوطة/الهمزات."""
    t = _DIACRITICS.sub("", text or "")
    t = (t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا")
           .replace("ى", "ي").replace("ة", "ه")
           .replace("ؤ", "و").replace("ئ", "ي").replace("ء", ""))
    return t


def tokens(text: str) -> set[str]:
    """كلمات دالّة: مطبّعة، بلا شائعة، وبإزالة 'ال' التعريف."""
    t = _NON_LETTER.sub(" ", normalize(text))
    out: set[str] = set()
    for w in t.split():
        if w.startswith("ال") and len(w) > 3:
            w = w[2:]
        if len(w) >= 2 and w not in _STOPWORDS:
            out.add(w)
    return out


# أدوات النفي: «لا» ضمن الكلمات الشائعة فتُحذف من المقارنة، فبدون هذا الفحص
# يطابق «يجوز الكذب» نص «لا يجوز الكذب» تطابقًا كاملًا وهو عكسه.
_NEGATIONS = {"لا", "لم", "لن", "ليس", "ليست"}


def _negated(text: str) -> set[str]:
    """الكلمات الواقعة بعد أداة نفي مباشرة (بنفس تطبيع tokens)."""
    words = _NON_LETTER.sub(" ", normalize(text)).split()
    out: set[str] = set()
    for neg, w in zip(words, words[1:]):
        if neg in _NEGATIONS:
            out.add(w[2:] if w.startswith("ال") and len(w) > 3 else w)
    return out


def coverage(query: str, doc: str) -> float:
    """نسبة كلمات الاستعلام المميّزة الموجودة في المصدر (0..1).
    إن نُفيت في أحد النصين كلمةٌ مشتركة دون الآخر تُنصّف النتيجة فلا تُعدّ تطابقًا
    دقيقًا. النفي في جزء من المصدر لا يمس الادعاء (مثل «فإن لم يستطع») لا يؤثر."""
    q, d = tokens(query), tokens(doc)
    if not q:
        return 0.0
    score = len(q & d) / len(q)
    shared = q & d
    if (_negated(query) ^ _negated(doc)) & shared:
        score /= 2
    return score
