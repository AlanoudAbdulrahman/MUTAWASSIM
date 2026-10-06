"""
pipeline.py — ربط المراحل في مسار واحد متكامل.
المالك: العنود (التكامل).

الترتيب: تنظيف -> فلترة -> استخراج -> تحقق -> خطورة -> بطاقة [-> حفظ].

لا يُشغَّل وحده: الموقع (python -m mutawassim) يستدعيه عند كل تحقق.

- run_pipeline(raw_posts) -> list[ResponseCard]        (العقد الأصلي، بلا حفظ)
- run_pipeline_detailed(raw_posts) -> list[PipelineItem] (البطاقة مع الادعاء والتحقق والخطورة)
- process_batch(raw_posts, save=True) -> BatchResult     (للموقع: انتشار عبر الزمن + حفظ في السجل)

متانة: فشل استخراج منشور لا يوقف الدفعة (يُسجَّل في errors)، وفشل التحقق من ادعاء
يجعله needs_review فيُحال لمختص بدل إسقاطه.
الانتشار: عدد المنشورات المختلفة التي ذكرت الادعاء (risk_score.spread_from_count)،
ومع history=True يشمل دفعات المالك نفسه المحفوظة سابقًا (لكل زائر سجله).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from .schemas import Claim, Post, ResponseCard, RiskScore, VerificationResult
from .ingestion.cleaner import clean_posts
from .ingestion.classifier import filter_posts
from .extraction.claim_extractor import extract_claims
from .verification.verifier import verify
from .scoring.risk_score import score, spread_from_count
from .reporting.report_generator import build_card
from . import storage
from .serialize import item_to_json

log = logging.getLogger("mutawassim.pipeline")


@dataclass
class PipelineItem:
    """كل مخرجات المسار لادعاء واحد (للوحة والتقرير)."""
    post: Post
    claim: Claim
    result: VerificationResult
    risk: RiskScore
    card: ResponseCard


@dataclass
class BatchResult:
    items: list[PipelineItem]
    posts_in: int
    errors: list[dict] = field(default_factory=list)  # {post_id, stage, message}
    batch_id: int | None = None


# أخطاء المفتاح نفسه (خاطئ/بلا رصيد): لا معنى لإكمال الدفعة، نُبلغ المستخدم مباشرة
KEY_ERRORS = ("AuthenticationError", "PermissionDeniedError", "RateLimitError")


def is_key_error(e: Exception) -> bool:
    return type(e).__name__ in KEY_ERRORS


def _verify_safely(claim: Claim, errors: list[dict], post_id: str) -> VerificationResult:
    try:
        return verify(claim)
    except Exception as e:
        if is_key_error(e):
            raise
        log.exception("verification failed for %s", claim.claim_id)
        errors.append({"post_id": post_id, "stage": "verification", "message": type(e).__name__})
        return VerificationResult(claim_id=claim.claim_id, status="needs_review",
                                  note="تعذّر التحقق آليًا؛ يُحال للمختص")


def _run(raw_posts: list[dict], history: bool, owner: str = "") -> tuple[list[PipelineItem], list[dict]]:
    errors: list[dict] = []
    posts = filter_posts(clean_posts(raw_posts))

    # الاستخراج: منشور يفشل لا يوقف البقية
    pairs: list[tuple[Post, Claim]] = []
    for p in posts:
        try:
            pairs.extend((p, c) for c in extract_claims(p))
        except Exception as e:
            if is_key_error(e):
                raise
            log.exception("extraction failed for %s", p.post_id)
            errors.append({"post_id": p.post_id, "stage": "extraction", "message": type(e).__name__})

    # الانتشار: منشورات مختلفة ذكرت نفس صيغة البحث (+ الدفعات السابقة عند history)
    posts_by_key: dict[str, set[str]] = defaultdict(set)
    for p, c in pairs:
        posts_by_key[storage.query_key(c.normalized_query or c.text)].add(p.post_id)
    past = storage.history_post_counts(set(posts_by_key), owner) if history else {}

    items: list[PipelineItem] = []
    for p, c in pairs:
        key = storage.query_key(c.normalized_query or c.text)
        result = _verify_safely(c, errors, p.post_id)
        spread = spread_from_count(len(posts_by_key[key]) + past.get(key, 0))
        risk = score(c, result, spread=spread)
        items.append(PipelineItem(p, c, result, risk, build_card(c, result, risk)))

    items.sort(key=lambda x: x.card.risk, reverse=True)
    return items, errors


def run_pipeline_detailed(raw_posts: list[dict]) -> list[PipelineItem]:
    """مثل run_pipeline لكن يُبقي الادعاء والتحقق والخطورة مع كل بطاقة."""
    return _run(raw_posts, history=False)[0]


def run_pipeline(raw_posts: list[dict]) -> list[ResponseCard]:
    return [item.card for item in run_pipeline_detailed(raw_posts)]


def process_batch(raw_posts: list[dict], owner: str, save: bool = True, mode: str = "") -> BatchResult:
    """المسار الكامل للموقع: انتشار عبر الزمن من سجل المالك، ثم حفظ الدفعة فيه."""
    items, errors = _run(raw_posts, history=True, owner=owner)
    batch = BatchResult(items=items, posts_in=len(raw_posts), errors=errors)
    if save:
        batch.batch_id = storage.save_batch([item_to_json(i) for i in items],
                                            posts_in=len(raw_posts), mode=mode, owner=owner, errors=len(errors))
    return batch
