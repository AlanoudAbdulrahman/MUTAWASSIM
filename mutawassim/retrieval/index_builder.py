"""
index_builder.py — بناء فهرس Chroma من المصادر (المسار الحقيقي، اختياري).
المالك: غيداء / سارة.

للتشغيل الفوري نكتفي بالفهرس الداخلي في retriever.build_index().
عند التوسّع: شغّلوا هذا الملف لبناء فهرس Chroma مستديم.
"""
from __future__ import annotations

import json

from .. import config
from .embeddings import embed


def build_chroma_index() -> int:
    """يبني فهرس Chroma من SOURCES_FILE. يرجّع عدد الوثائق."""
    import chromadb

    docs = json.loads(config.SOURCES_FILE.read_text(encoding="utf-8"))
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    coll = client.get_or_create_collection("sources")
    ids = [str(d.get("id", i)) for i, d in enumerate(docs)]
    texts = [d.get("text", "") for d in docs]
    metas = [
        {"source": d.get("source", ""), "url": d.get("url", ""), "ruling": d.get("ruling", "")}
        for d in docs
    ]
    coll.upsert(ids=ids, embeddings=embed(texts), documents=texts, metadatas=metas)
    return len(docs)


if __name__ == "__main__":
    n = build_chroma_index()
    print(f"فُهرِس {n} مصدرًا في Chroma -> {config.CHROMA_DIR}")
