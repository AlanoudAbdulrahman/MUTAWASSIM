"""
embeddings.py — توليد المتجهات.
المالك: غيداء (التحقق/الاسترجاع).

MOCK: متجه حتمي بسيط (hashing) يعمل بلا تنزيل نماذج.
الحقيقي: مزوّدان قابلان للتبديل عبر EMBED_PROVIDER:
  - openai: text-embedding-3-small عبر الـAPI (بلا torch) — الأنسب على ويندوز.
  - local : sentence-transformers/e5 محليًا (يتطلب torch). e5 يحتاج بادئة
            "query: " للاستعلام و"passage: " للمصدر — تُضاف تلقائيًا.
"""
from __future__ import annotations

import hashlib

from .. import config, llm

_DIM = 256
_model = None   # نموذج محلي (local)


def _mock_embed(text: str) -> list[float]:
    vec = [0.0] * _DIM
    for tok in (text or "").split():
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        vec[h % _DIM] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def _normalize(v: list[float]) -> list[float]:
    n = sum(x * x for x in v) ** 0.5 or 1.0
    return [x / n for x in v]


def _openai_embed(texts: list[str]) -> list[list[float]]:
    """متجهات عبر OpenAI (بلا torch) بمفتاح الطلب الحالي (مفتاح الزائر أو LLM_API_KEY)."""
    # OpenAI يرفض النص الفارغ -> نستبدله بمسافة
    inputs = [t if (t and t.strip()) else " " for t in texts]
    resp = llm.openai_client().embeddings.create(model=config.OPENAI_EMBED_MODEL, input=inputs)
    return [_normalize(d.embedding) for d in resp.data]


def _is_e5() -> bool:
    return "e5" in config.EMBEDDING_MODEL.lower()


def _local_embed(texts: list[str], kind: str) -> list[list[float]]:
    """متجهات محلية عبر sentence-transformers (e5). يتطلب torch."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    inputs = texts
    if _is_e5():
        prefix = "query: " if kind == "query" else "passage: "
        inputs = [prefix + (t or "") for t in texts]
    return _model.encode(inputs, normalize_embeddings=True).tolist()


def embed(texts: list[str], kind: str = "passage") -> list[list[float]]:
    """يرجّع متجهًا لكل نص. kind: "passage" للمصادر، "query" للاستعلام (مهم لـ e5)."""
    if config.MOCK_MODE:
        return [_mock_embed(t) for t in texts]
    if config.EMBED_PROVIDER == "openai":
        return _openai_embed(texts)   # openai لا يحتاج بادئات
    return _local_embed(texts, kind)
