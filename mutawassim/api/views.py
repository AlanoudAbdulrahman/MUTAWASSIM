"""
api/views.py — بيانات العرض الخاصة بالموقع (الوضع، الديمو، المصادر، الاستخدام).
تحويل نتائج المسار في serialize.py، والقياس التلقائي في benchmark.py.
"""
from __future__ import annotations

import json
from collections import Counter

from .. import config, storage
from ..reporting.report_generator import _source_name
from ..schemas import STATUS_LABEL_AR, Evidence
from ..serialize import STATUS_ORDER, TYPE_LABEL_AR, status_rows
from ..verification.verifier import _status_from_ruling

DEMO_SETS = {
    "formal": ("منشورات الديمو الرسمية", config.DATA_DIR / "Demo Posts" / "demo_posts1.md"),
    "colloquial": ("منشورات الديمو العامية", config.DATA_DIR / "Demo Posts" / "demo_posts2.md"),
}


def mode_info(request=None) -> dict:
    """وضع التشغيل كما يراه هذا الزائر: هل يحتاج مفتاحه، وما النموذج."""
    from . import security
    real = not config.MOCK_MODE
    server_key = bool(request is not None and security.server_key_allowed(request))
    return {
        "mock_mode": config.MOCK_MODE,
        "needs_user_key": real and not server_key,
        "server_key": real and server_key,
        "llm_extract": real and config.USE_LLM_EXTRACT,
        "model": config.LLM_MODEL if real else None,
        "embeddings": config.EMBED_PROVIDER if real else "lexical",
    }


def mode_label() -> str:
    return "mock" if config.MOCK_MODE else f"real:{config.LLM_MODEL}"


def sources_overview() -> dict:
    """ملخص قاعدة المعرفة كما يقرؤها المحقق."""
    docs = json.loads(config.SOURCES_FILE.read_text(encoding="utf-8"))
    rows = []
    for d in docs:
        status = _status_from_ruling(d.get("ruling")) or "needs_review"
        rows.append({
            "id": d.get("id"), "text": d.get("text", ""), "ruling": d.get("ruling"),
            "status": status, "label": STATUS_LABEL_AR[status],
            "type": d.get("type"), "type_ar": TYPE_LABEL_AR.get(d.get("type"), d.get("type")),
            "source_name": _source_name(Evidence(source=d.get("source", ""), url="")),
            "url": d.get("url", ""),
        })
    by_status = Counter(r["status"] for r in rows)
    return {
        "total": len(rows),
        "by_status": status_rows(by_status),
        "by_type": [{"type": t, "label": TYPE_LABEL_AR.get(t, t), "count": n}
                    for t, n in Counter(r["type"] for r in rows).most_common()],
        "by_source": [{"label": s, "count": n}
                      for s, n in Counter(r["source_name"] for r in rows).most_common()],
        "items": rows,
    }


def usage(owner: str) -> dict:
    stats = storage.usage_stats(owner)
    stats["by_status"] = status_rows(stats["by_status"])
    stats["misleading"] = sum(r["count"] for r in stats["by_status"] if r["status"] in ("fabricated", "weak"))
    return stats


__all__ = ["DEMO_SETS", "STATUS_ORDER", "mode_info", "mode_label", "sources_overview", "usage"]
