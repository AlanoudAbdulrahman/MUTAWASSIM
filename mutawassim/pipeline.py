"""
pipeline.py — ربط المراحل الأربع في مسار واحد.
المالك: غيداء (التكامل).

run_pipeline(raw_posts) -> list[ResponseCard] مرتّبة تنازليًا بالخطورة.
الترتيب: تنظيف -> فلترة -> استخراج -> تحقق -> خطورة -> بطاقة.
"""
from __future__ import annotations

from collections import Counter

from .schemas import ResponseCard
from .ingestion.cleaner import clean_posts
from .ingestion.classifier import filter_posts
from .extraction.claim_extractor import extract_claims
from .verification.verifier import verify
from .scoring.risk_score import score
from .reporting.report_generator import build_card


def run_pipeline(raw_posts: list[dict]) -> list[ResponseCard]:
    posts = filter_posts(clean_posts(raw_posts))

    # استخراج كل الادعاءات
    claims = []
    for p in posts:
        claims.extend(extract_claims(p))

    # حساب الانتشار: تكرار صيغة البحث داخل الدفعة (0..1)
    freq = Counter(c.normalized_query for c in claims)
    max_freq = max(freq.values()) if freq else 1

    cards: list[ResponseCard] = []
    for c in claims:
        result = verify(c)
        spread = freq[c.normalized_query] / max_freq
        risk = score(c, result, spread=spread)
        cards.append(build_card(c, result, risk))

    cards.sort(key=lambda x: x.risk, reverse=True)
    return cards


if __name__ == "__main__":
    import json
    from . import config

    raw = json.loads((config.DATA_DIR / "raw" / "posts.sample.json").read_text(encoding="utf-8"))
    for card in run_pipeline(raw):
        print(f"[{card.risk:.3f}] {card.verdict_label} | {card.action} | {card.correction[:60]}")
