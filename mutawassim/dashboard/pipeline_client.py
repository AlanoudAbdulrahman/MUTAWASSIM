"""
pipeline_client.py — نقطة الاتصال الوحيدة بين لوحة Streamlit و Pipeline غيداء.

العقد المشترك للـ ResponseCard لا يتغير:
{
    "claim_id": "...",
    "verdict_label": "...",
    "correction": "...",
    "sources": ["https://..."],
    "action": "رد | إحالة لمختص | امتناع"
}

إذا وُجدت run_pipeline من mutawassim.pipeline تُستخدم تلقائيًا.
وإلا تعمل اللوحة في وضع تجريبي حتى لا تتعطل الواجهة.
"""

from __future__ import annotations

import csv
import importlib
import io
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List


# ============================================================
# العقد النهائي — لا نضيف إليه risk أو status
# ============================================================

ResponseCard = Dict[str, Any]

_CARD_FIELDS = (
    "claim_id",
    "verdict_label",
    "correction",
    "sources",
    "action",
)


# ============================================================
# محاولة الاتصال بالـ Pipeline الحقيقي
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


try:
    from mutawassim.pipeline import run_pipeline

    REAL_PIPELINE = True

except Exception:
    run_pipeline = None
    REAL_PIPELINE = False


# ============================================================
# تحويل ResponseCard إلى dict بدون تغيير العقد
# ============================================================

def _to_dict(card: Any) -> ResponseCard:
    """
    يحول ResponseCard القادم من pipeline إلى dict.

    مهم:
    لا نسمح بإضافة حقول جديدة إلى العقد النهائي.
    """

    if isinstance(card, dict):
        data = card

    elif hasattr(card, "model_dump"):
        # Pydantic
        data = card.model_dump()

    elif is_dataclass(card):
        data = asdict(card)

    else:
        data = {
            field: getattr(card, field)
            for field in _CARD_FIELDS
            if hasattr(card, field)
        }

    # نحتفظ فقط بالحقول المتفق عليها بين الوحدات.
    return {
        field: data.get(field)
        for field in _CARD_FIELDS
    }


# ============================================================
# Demo فقط — لا يمثل حكمًا حقيقيًا
# ============================================================

def _demo_cards() -> List[ResponseCard]:
    """
    بيانات تجريبية لاختبار الواجهة فقط.

    لا تستخدم هذه القيم كأحكام شرعية حقيقية.
    """

    return [
        {
            "claim_id": "demo-c001",
            "verdict_label": "موضوع",
            "correction": "[تجريبي] نتيجة تجريبية لاختبار بطاقة الواجهة.",
            "sources": ["https://example.org/demo/source-1"],
            "action": "رد",
        },
        {
            "claim_id": "demo-c002",
            "verdict_label": "ضعيف",
            "correction": "[تجريبي] نتيجة تجريبية لاختبار بطاقة الواجهة.",
            "sources": ["https://example.org/demo/source-2"],
            "action": "رد",
        },
        {
            "claim_id": "demo-c003",
            "verdict_label": "يحتاج مراجعة",
            "correction": "لا يوجد دليل كافٍ في الوضع التجريبي.",
            "sources": [],
            "action": "امتناع",
        },
        {
            "claim_id": "demo-c004",
            "verdict_label": "مسألة خلافية",
            "correction": "مثال تجريبي للإحالة إلى مختص.",
            "sources": [],
            "action": "إحالة لمختص",
        },
        {
            "claim_id": "demo-c005",
            "verdict_label": "صحيح",
            "correction": "[تجريبي] نتيجة تجريبية لاختبار بطاقة الواجهة.",
            "sources": ["https://example.org/demo/source-3"],
            "action": "رد",
        },
    ]


# ============================================================
# قراءة الملفات
# ============================================================

def parse_posts(filename: str, raw: bytes) -> List[Dict[str, str]]:
    """
    يحول CSV/JSON إلى:

    [
        {
            "post_id": "p001",
            "text": "..."
        }
    ]
    """

    content = raw.decode("utf-8-sig")

    posts: List[Dict[str, str]] = []

    if filename.lower().endswith(".json"):

        data = json.loads(content)

        if not isinstance(data, list):
            raise ValueError("ملف JSON يجب أن يحتوي على قائمة منشورات.")

        for i, item in enumerate(data, 1):

            if isinstance(item, str):
                posts.append(
                    {
                        "post_id": f"p{i:03d}",
                        "text": item,
                    }
                )

            elif isinstance(item, dict):

                if "text" not in item:
                    raise ValueError(
                        f"المنشور رقم {i} لا يحتوي على الحقل text."
                    )

                posts.append(
                    {
                        "post_id": str(
                            item.get("post_id")
                            or item.get("id")
                            or f"p{i:03d}"
                        ),
                        "text": str(item["text"]),
                    }
                )

            else:
                raise ValueError(
                    f"صيغة المنشور رقم {i} غير مدعومة."
                )

    else:

        reader = csv.DictReader(io.StringIO(content))

        if not reader.fieldnames or "text" not in reader.fieldnames:
            raise ValueError(
                "ملف CSV يجب أن يحتوي على عمود text."
            )

        for i, row in enumerate(reader, 1):

            posts.append(
                {
                    "post_id": row.get("post_id")
                    or row.get("id")
                    or f"p{i:03d}",
                    "text": row["text"],
                }
            )

    return [
        post
        for post in posts
        if post["text"].strip()
    ]


# ============================================================
# تشغيل Pipeline
# ============================================================

def verify_posts(posts: List[Dict[str, str]]) -> List[ResponseCard]:
    """
    نقطة الاتصال بين الواجهة والـ Pipeline.

    Pipeline الحقيقي:
        posts
        → Claim
        → VerificationResult
        → RiskScore
        → ResponseCard

    الواجهة تستقبل فقط ResponseCard النهائي.
    """

    if not posts:
        return []

    if REAL_PIPELINE:

        cards = run_pipeline(posts)

        if cards is None:
            return []

        return [
            _to_dict(card)
            for card in cards
        ]

    # وضع تجريبي فقط أثناء عدم توفر pipeline.py
    return _demo_cards()


# ============================================================
# Adapter خاص بالواجهة النصية
# ============================================================
def verify_batch(
    text: str,
) -> List[ResponseCard]:
    """
    Adapter لواجهة Streamlit.

    يحوّل النص إلى منشورات ثم يمرره إلى الـ pipeline.
    إذا لم ينتج الـ pipeline أي بطاقة، نرجع بطاقة مراجعة
    محايدة بدون حكم أو مصدر مخترع.
    """

    if not text or not text.strip():
        return []

    posts = [
        {
            "post_id": f"p{i}",
            "text": line.strip(),
        }
        for i, line in enumerate(
            text.splitlines(),
            1,
        )
        if line.strip()
    ]

    cards = verify_posts(posts)

    # لا يوجد حكم ولا دليل مسترجع:
    # نعرض حالة مراجعة فقط بدل اختراع نتيجة.
    if not cards and posts:
        return [
            {
                "claim_id": posts[0]["post_id"],
                "verdict_label": "يحتاج مراجعة",
                "correction": (
                    "لم يُستخرج ادعاء قابل للتحقق من النص "
                    "ضمن نتائج الـ pipeline الحالية."
                ),
                "sources": [],
                "action": "امتناع",
            }
        ]

    return cards