"""
embeddings.py — توليد المتجهات.
المالك: غيداء (التحقق/الاسترجاع).

MOCK: متجه حتمي بسيط (hashing) يعمل بلا تنزيل نماذج.
الحقيقي: sentence-transformers بنموذج عربي.
"""
from __future__ import annotations

import hashlib

from .. import config

_DIM = 256
_model = None


def _mock_embed(text: str) -> list[float]:
    vec = [0.0] * _DIM
    for tok in (text or "").split():
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        vec[h % _DIM] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def embed(texts: list[str]) -> list[list[float]]:
    """يرجّع متجهًا لكل نص."""
    if config.MOCK_MODE:
        return [_mock_embed(t) for t in texts]
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model.encode(texts, normalize_embeddings=True).tolist()
