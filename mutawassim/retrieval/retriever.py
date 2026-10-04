"""
retriever.py — الاسترجاع من المصادر المعتمدة.
المالك: غيداء (التحقق/الاسترجاع).

MOCK (بلا مفاتيح): مطابقة لفظية عربية (coverage) — دقيقة للأحاديث القصيرة.

الحقيقي = استرجاع هجين:
  1) لفظي أولاً (coverage): يمسك الحديث نفسه بدرجته الصحيحة بدقة عالية.
  2) دلالي احتياطيًا (embeddings + cosine): فقط عند غياب تطابق لفظي،
     لالتقاط الصياغات المعاد صياغتها.
الهجين يجمع دقة اللفظي مع تغطية الدلالي.
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


def _sim_threshold() -> float:
    if config.EMBED_PROVIDER == "openai":
        return config.MIN_SIM_OPENAI
    return config.MIN_SIM


def _to_evidence(d: dict) -> Evidence:
    return Evidence(
        source=d.get("source", ""),
        url=d.get("url", ""),
        ruling=d.get("ruling"),
        snippet=d.get("text", "")[:300],
    )


def _lexical(query: str) -> list[tuple[dict, float]]:
    scored = [(d, coverage(query, d.get("text", ""))) for d in _DOCS or []]
    return [(d, s) for d, s in scored if s >= config.MIN_COVERAGE]


def _semantic(query: str) -> list[tuple[dict, float]]:
    qv = embed([query], kind="query")[0]
    thr = _sim_threshold()
    scored = [(d, _cosine(qv, v)) for d, v in zip(_DOCS or [], _VECS or [])]
    return [(d, s) for d, s in scored if s >= thr]


def retrieve(normalized_query: str, k: int | None = None) -> list[Evidence]:
    """يرجّع المصادر الأكثر صلة فقط (فوق العتبة)، مرتّبة تنازليًا."""
    global _DOCS, _VECS
    if _DOCS is None:
        build_index()
    if not _DOCS:
        return []
    k = k or config.RETRIEVE_K

    if config.MOCK_MODE:
        # وضع MOCK: لفظي فقط
        scored = _lexical(normalized_query)
    else:
        # هجين: لفظي أولاً (دقيق)، ثم دلالي احتياطيًا (للصياغات المختلفة)
        scored = _lexical(normalized_query)
        if not scored:
            scored = _semantic(normalized_query)

    scored.sort(key=lambda t: t[1], reverse=True)
    return [_to_evidence(d) for d, _s in scored[:k]]
