"""
retriever.py — الاسترجاع من المصادر المعتمدة.
المالك: غيداء (التحقق/الاسترجاع).

وضعان:
- MOCK (بلا مفاتيح): مطابقة لفظية عربية ذكية (تطبيع + تجاهل الكلمات الشائعة)
  عبر coverage — دقيقة للأحاديث القصيرة وتعيد المصدر المطابق فقط.
- الحقيقي: embeddings دلالية + cosine (يمسك الصياغات المختلفة).
المصادر تُحمّل من SOURCES_FILE ثم العيّنة الاحتياطية.
"""
from __future__ import annotations

import json

from .. import config
from ..schemas import Evidence
from .embeddings import embed
from .arabic import coverage

_DOCS: list[dict] | None = None     # قائمة المصادر
_VECS: list[list[float]] | None = None  # متجهاتها (للوضع الحقيقي فقط)


def _load_sources() -> list[dict]:
    for path in (config.SOURCES_FILE, config.SOURCES_SAMPLE_FILE):
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return []


def build_index() -> int:
    """يحمّل المصادر (ويبني المتجهات في الوضع الحقيقي). يرجّع عددها."""
    global _DOCS, _VECS
    _DOCS = _load_sources()
    _VECS = None
    if not config.MOCK_MODE and _DOCS:
        _VECS = embed([d.get("text", "") for d in _DOCS], kind="passage")
    return len(_DOCS)


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _to_evidence(d: dict) -> Evidence:
    return Evidence(
        source=d.get("source", ""),
        url=d.get("url", ""),
        ruling=d.get("ruling"),
        snippet=d.get("text", "")[:300],
    )


def retrieve(normalized_query: str, k: int | None = None) -> list[Evidence]:
    """يرجّع المصادر الأكثر صلة فقط (فوق العتبة)، مرتّبة تنازليًا."""
    global _DOCS, _VECS
    if _DOCS is None:
        build_index()
    if not _DOCS:
        return []
    k = k or config.RETRIEVE_K

    if config.MOCK_MODE:
        # مطابقة لفظية عربية: coverage
        scored = [(d, coverage(normalized_query, d.get("text", ""))) for d in _DOCS]
        scored = [(d, s) for d, s in scored if s >= config.MIN_COVERAGE]
    else:
        # مطابقة دلالية: cosine على المتجهات (بادئة query لـ e5)
        qv = embed([normalized_query], kind="query")[0]
        scored = [(d, _cosine(qv, v)) for d, v in zip(_DOCS, _VECS or [])]
        scored = [(d, s) for d, s in scored if s >= config.MIN_SIM]

    scored.sort(key=lambda t: t[1], reverse=True)
    return [_to_evidence(d) for d, _s in scored[:k]]
