"""
evaluate_extraction.py — قياس جودة استخراج الادعاءات على مجموعة ذهبية.
المالك: العنود (الاستخراج).

يقيس: دقة/استرجاع الادعاءات المستخرَجة، دقة النوع، وصحة إرجاع "لا ادعاءات".
المطابقة بين الادعاء المتوقع والمستخرَج بتداخل الكلمات بعد تطبيع عربي خفيف،
لأن النموذج قد يعيد صياغة الادعاء قليلًا دون أن يكون خاطئًا.
في وضع MOCK تقيس النتائج البديل المؤقت (تقسيم الجمل) وليس النموذج الحقيقي.

تشغيل:  python -m mutawassim.evaluation.evaluate_extraction
"""
from __future__ import annotations

import json
import re

from .. import config
from ..schemas import Post
from ..extraction.claim_extractor import extract_claims

EXTRACTION_TEST_FILE = config.DATA_DIR / "test_set" / "extraction.sample.json"

# أدنى تداخل كلمات لاعتبار الادعاء المستخرَج هو نفسه المتوقع
MATCH_THRESHOLD = 0.6

_TASHKEEL = re.compile(r"[ً-ْٰـ]")  # الحركات والتطويل
_PUNCT = re.compile(r"[^\w\s]")


def _normalize(text: str) -> list[str]:
    """تطبيع للمقارنة فقط: حذف التشكيل وعلامات الترقيم وتوحيد الألف والياء والتاء."""
    text = _TASHKEEL.sub("", text)
    text = re.sub("[أإآ]", "ا", text).replace("ى", "ي").replace("ة", "ه")
    return _PUNCT.sub(" ", text).split()


def _overlap(a: str, b: str) -> float:
    """F1 على مستوى الكلمات بين نصين (0..1)."""
    ta, tb = _normalize(a), _normalize(b)
    if not ta or not tb:
        return 0.0
    common = sum(min(ta.count(t), tb.count(t)) for t in set(ta))
    if not common:
        return 0.0
    p, r = common / len(ta), common / len(tb)
    return 2 * p * r / (p + r)


def _match(predicted: list[dict], expected: list[dict]) -> list[tuple[dict, dict]]:
    """مطابقة واحد-لواحد، الأعلى تداخلًا أولًا."""
    pairs = sorted(
        ((_overlap(p["text"], e["text"]), i, j)
         for i, p in enumerate(predicted) for j, e in enumerate(expected)),
        reverse=True,
    )
    used_p: set[int] = set()
    used_e: set[int] = set()
    out = []
    for s, i, j in pairs:
        if s < MATCH_THRESHOLD:
            break
        if i in used_p or j in used_e:
            continue
        used_p.add(i)
        used_e.add(j)
        out.append((predicted[i], expected[j]))
    return out


def evaluate_extraction(test_set_path=None) -> dict:
    path = test_set_path or EXTRACTION_TEST_FILE
    rows = json.loads(open(path, encoding="utf-8").read())

    n_pred = n_exp = n_matched = type_ok = 0
    empty_posts = empty_ok = 0
    errors = 0
    failures: list[dict] = []

    for row in rows:
        expected = row["expected_claims"]
        post = Post(post_id=row["post_id"], text=row["text"])
        try:
            predicted = [c.model_dump() for c in extract_claims(post)]
        except Exception as e:
            # فشل المزود أو رد غير صالح: الادعاءات المتوقعة تُحسب مفقودة
            errors += 1
            predicted = []
            failures.append({"post_id": post.post_id, "error": str(e)})

        matches = _match(predicted, expected)
        n_pred += len(predicted)
        n_exp += len(expected)
        n_matched += len(matches)
        type_ok += sum(p["type"] == e["type"] for p, e in matches)
        if not expected:
            empty_posts += 1
            empty_ok += not predicted

        if len(matches) != len(predicted) or len(matches) != len(expected):
            failures.append({
                "post_id": post.post_id,
                "predicted": [p["text"] for p in predicted],
                "expected": [e["text"] for e in expected],
            })

    precision = n_matched / n_pred if n_pred else (1.0 if not n_exp else 0.0)
    recall = n_matched / n_exp if n_exp else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "mock_mode": config.MOCK_MODE,
        "posts": len(rows),
        "expected_claims": n_exp,
        "predicted_claims": n_pred,
        "matched_claims": n_matched,
        "claim_precision": round(precision, 3),
        "claim_recall": round(recall, 3),
        "claim_f1": round(f1, 3),
        "type_accuracy": round(type_ok / n_matched, 3) if n_matched else 0.0,
        "no_claim_accuracy": round(empty_ok / empty_posts, 3) if empty_posts else 0.0,
        "errors": errors,
        "failures": failures,
    }


if __name__ == "__main__":
    m = evaluate_extraction()
    failures = m.pop("failures")
    print("=== نتائج قياس الاستخراج ===")
    if m["mock_mode"]:
        print("تنبيه: MOCK_MODE مفعّل — النتائج تقيس البديل المؤقت لا النموذج.")
    for k, v in m.items():
        print(f"{k}: {v}")
    if failures:
        print("\n=== حالات للمراجعة ===")
        for f in failures:
            print(json.dumps(f, ensure_ascii=False))
