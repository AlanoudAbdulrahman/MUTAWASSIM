"""
cleaner.py — تنظيف وتطبيع المنشورات الخام.
المالك: سارة (البيانات).
"""
from __future__ import annotations

import re

from ..schemas import Post

_WS = re.compile(r"\s+")
_TATWEEL = re.compile("ـ")  # ـ


def normalize_text(text: str) -> str:
    """تطبيع عربي خفيف: إزالة التطويل وتوحيد المسافات."""
    text = _TATWEEL.sub("", text)
    text = _WS.sub(" ", text)
    return text.strip()


def clean_posts(raw: list[dict]) -> list[Post]:
    """يحوّل سجلات خام [{post_id, text}] إلى list[Post] نظيفة بلا تكرار/فراغ."""
    seen: set[str] = set()
    used_ids: set[str] = set()
    out: list[Post] = []
    for i, r in enumerate(raw):
        text = normalize_text(str(r.get("text", "")))
        if not text:
            continue
        if text in seen:  # إزالة التكرار
            continue
        seen.add(text)
        # معرّف فريد: معرّفان متطابقان يجعلان معرّفات الادعاءات تتصادم
        post_id = base = str(r.get("post_id") or f"p{i:04d}")
        n = 2
        while post_id in used_ids:
            post_id, n = f"{base}_{n}", n + 1
        used_ids.add(post_id)
        out.append(
            Post(
                post_id=post_id,
                text=text,
                meta=r.get("meta", {}) or {},
            )
        )
    return out
