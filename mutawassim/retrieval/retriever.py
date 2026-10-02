"""
retriever.py — الاسترجاع الدلالي من المصادر المعتمدة.
المالك: غيداء (التحقق/الاسترجاع).

يعمل فورًا بفهرس داخلي (cosine على متجهات embeddings). المصادر تُحمّل من
SOURCES_FILE. لاحقًا يمكن استبدال الفهرس الداخلي بـ Chroma (index_builder.py).
"""
from __future__ import annotations

import json

from .. import config
from ..schemas import Evidence
from .embeddings import embed

_INDEX: list[dict] | None = None   # [{doc, vec}]


def _load_sources() -> list[dict]:
    path = config.SOURCES_FILE
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def build_index() -> int:
    """يبني الفهرس الداخلي من ملف المصادر. يرجّع عدد المصادر المفهرسة."""
    global _INDEX
    docs = _load_sources()
    vecs = embed([d.get("text", "") for d in docs]) if docs else []
    _INDEX = [{"doc": d, "vec": v} for d, v in zip(docs, vecs)]
    return len(_INDEX)


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def retrieve(normalized_query: str, k: int | None = None) -> list[Evidence]:
    """يرجّع أقرب k مصادر كـ Evidence مرتّبة تنازليًا بالتشابه."""
    global _INDEX
    if _INDEX is None:
        build_index()
    if not _INDEX:
        return []
    k = k or config.RETRIEVE_K
    qv = embed([normalized_query])[0]
    ranked = sorted(
        ((e, _cosine(qv, e["vec"])) for e in _INDEX),
        key=lambda t: t[1], reverse=True,
    )
    # استبعاد ما كان تشابهه أدنى من العتبة (يمنع إسناد ادعاء لمصدر غير ذي صلة)
    ranked = [(e, s) for e, s in ranked if s >= config.MIN_SIM][:k]
    out: list[Evidence] = []
    for e, _s in ranked:
        d = e["doc"]
        out.append(
            Evidence(
                source=d.get("source", ""),
                url=d.get("url", ""),
                ruling=d.get("ruling"),
                snippet=d.get("text", "")[:300],
            )
        )
    return out
