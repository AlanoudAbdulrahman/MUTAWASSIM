"""
serialize.py — تحويل مخرجات المسار إلى JSON (للموقع والسجل) وإحصائيات الدفعة.
مكان واحد للتحويل يستخدمه المسار عند الحفظ والـ API عند العرض.
"""
from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .reporting.report_generator import _source_name
from .schemas import STATUS_LABEL_AR
from . import storage

if TYPE_CHECKING:
    from .pipeline import PipelineItem

STATUS_ORDER = ("fabricated", "weak", "needs_review", "confirmed")

TYPE_LABEL_AR = {
    "hadith": "حديث", "quran": "قرآن", "aqeedah": "عقيدة", "history": "تاريخ",
    "attribution": "نسبة قول", "shubha": "شبهة", "other": "أخرى",
}


def item_to_json(item: "PipelineItem") -> dict:
    c, r, k = item.claim, item.result, item.risk
    return {
        "claim_id": c.claim_id,
        "post_id": item.post.post_id,
        "post_text": item.post.text,
        "claim_text": c.text,
        "claim_type": c.type,
        "claim_type_ar": TYPE_LABEL_AR.get(c.type, c.type),
        "query_key": storage.query_key(c.normalized_query or c.text),
        "status": r.status,
        "verdict_label": item.card.verdict_label,
        "action": item.card.action,
        "correction": item.card.correction,
        "sources": item.card.sources,
        "risk": item.card.risk,
        "factors": k.factors.model_dump(),
        "confidence": r.confidence,
        "evidence": [
            {"source_name": _source_name(e), "url": e.url, "ruling": e.ruling, "snippet": e.snippet}
            for e in r.evidence
        ],
    }


def status_rows(counts: dict) -> list[dict]:
    return [{"status": s, "label": STATUS_LABEL_AR[s], "count": counts.get(s, 0)} for s in STATUS_ORDER]


def summarize(items: list[dict], posts_in: int) -> dict:
    """إحصائيات دفعة من عناصر العرض (تعمل للنتيجة الجديدة ولدفعة من السجل)."""
    by_status = Counter(i["status"] for i in items)
    by_type = Counter(i["claim_type"] for i in items)
    risks = [i["risk"] for i in items]
    return {
        "posts_in": posts_in,
        "posts_with_claims": len({i["post_id"] for i in items}),
        "total_claims": len(items),
        "by_status": status_rows(by_status),
        "misleading": by_status.get("fabricated", 0) + by_status.get("weak", 0),
        "referrals": sum(i["action"] == "إحالة لمختص" for i in items),
        "by_type": [{"type": t, "label": TYPE_LABEL_AR.get(t, t), "count": n}
                    for t, n in by_type.most_common()],
        "max_risk": max(risks, default=0.0),
        "avg_risk": round(sum(risks) / len(risks), 3) if risks else 0.0,
    }
