"""
evaluate.py — قياس الدقة على مجموعة الاختبار.
المالك: سارة / غيداء.

يقيس: دقة/استرجاع كشف المغلوط، تطابق الحالة، والاستشهاد بالمصادر.
- citation_rate: من الأحكام (مؤكد/ضعيف/موضوع)، كم منها مسند برابط مصدر.
- citation_accuracy: من الأحكام، كم منها مسند بمصدر درجته توافق الحكم نفسه.
  (needs_review لا يُحتسب فيهما؛ لا يُتوقع له مصدر.)
تشغيل:  python -m mutawassim.evaluation.evaluate
"""
from __future__ import annotations

import json

from .. import config
from ..schemas import Post
from ..extraction.claim_extractor import extract_claims
from ..verification.verifier import _status_from_ruling, verify

# نعتبر "مغلوطًا" الحالات التالية
_MISLEADING = {"fabricated", "weak"}


def _is_misleading(status: str) -> bool:
    return status in _MISLEADING


def evaluate(test_set_path=None) -> dict:
    path = test_set_path or config.TEST_SET_FILE
    rows = json.loads(open(path, encoding="utf-8").read())

    tp = fp = fn = tn = 0
    status_match = 0
    verdicts = cited = backed = 0
    no_claim = errors = 0
    failures: list[dict] = []
    total = 0

    for i, row in enumerate(rows):
        total += 1
        claim_text = row["claim_text"]
        expected = row["expected_status"]
        exp_mis = _is_misleading(expected)

        # نحوّل نص الاختبار إلى منشور ونأخذ أول ادعاء
        post = Post(post_id=f"t{i:03d}", text=claim_text)
        try:
            claims = extract_claims(post)
            result = verify(claims[0]) if claims else None
        except Exception as e:
            # فشل المزود في حالة واحدة لا يُسقط القياس كله
            errors += 1
            fn += exp_mis
            failures.append({"i": i, "claim": claim_text, "expected": expected, "got": f"error: {e}"})
            continue

        if result is None:
            no_claim += 1
            fn += exp_mis
            failures.append({"i": i, "claim": claim_text, "expected": expected, "got": "no_claim"})
            continue

        if result.status == expected:
            status_match += 1
        else:
            failures.append({"i": i, "claim": claim_text, "expected": expected, "got": result.status})

        if result.status != "needs_review":
            verdicts += 1
            linked = [e for e in result.evidence if e.url]
            cited += bool(linked)
            backed += any(_status_from_ruling(e.ruling) == result.status for e in linked)

        pred_mis = _is_misleading(result.status)
        if pred_mis and exp_mis:
            tp += 1
        elif pred_mis and not exp_mis:
            fp += 1
        elif not pred_mis and exp_mis:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    metrics = {
        "mock_mode": config.MOCK_MODE,
        "total": total,
        "detection_precision": round(precision, 3),
        "detection_recall": round(recall, 3),
        "detection_f1": round(f1, 3),
        "status_accuracy": round(status_match / total, 3) if total else 0.0,
        "citation_rate": round(cited / verdicts, 3) if verdicts else 0.0,
        "citation_accuracy": round(backed / verdicts, 3) if verdicts else 0.0,
        "no_claim": no_claim,
        "errors": errors,
        "failures": failures,
    }
    return metrics


if __name__ == "__main__":
    m = evaluate()
    failures = m.pop("failures")
    print("=== نتائج القياس ===")
    if m["mock_mode"]:
        print("تنبيه: MOCK_MODE مفعّل — الاستخراج تقسيم جمل والتحقق لفظي فقط.")
    for k, v in m.items():
        print(f"{k}: {v}")
    if failures:
        print("\n=== حالات للمراجعة ===")
        for f in failures:
            print(json.dumps(f, ensure_ascii=False))
