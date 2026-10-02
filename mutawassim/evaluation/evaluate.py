"""
evaluate.py — قياس الدقة على مجموعة الاختبار.
المالك: سارة / غيداء.

يقيس: دقة/استرجاع كشف المغلوط، تطابق الحالة، ونسبة الإحالة للمصدر.
تشغيل:  python -m mutawassim.evaluation.evaluate
"""
from __future__ import annotations

import json

from .. import config
from ..schemas import Post
from ..extraction.claim_extractor import extract_claims
from ..verification.verifier import verify

# نعتبر "مغلوطًا" الحالات التالية
_MISLEADING = {"fabricated", "weak"}


def _is_misleading(status: str) -> bool:
    return status in _MISLEADING


def evaluate(test_set_path=None) -> dict:
    path = test_set_path or config.TEST_SET_FILE
    rows = json.loads(open(path, encoding="utf-8").read())

    tp = fp = fn = tn = 0
    status_match = 0
    cited = 0
    total = 0

    for i, row in enumerate(rows):
        total += 1
        claim_text = row["claim_text"]
        expected = row["expected_status"]

        # نحوّل نص الاختبار إلى منشور ونأخذ أول ادعاء
        post = Post(post_id=f"t{i:03d}", text=claim_text)
        claims = extract_claims(post)
        if not claims:
            fn += 1 if _is_misleading(expected) else 0
            continue
        result = verify(claims[0])

        if result.status == expected:
            status_match += 1
        if result.evidence and any(e.url for e in result.evidence):
            cited += 1

        pred_mis = _is_misleading(result.status)
        exp_mis = _is_misleading(expected)
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
        "total": total,
        "detection_precision": round(precision, 3),
        "detection_recall": round(recall, 3),
        "detection_f1": round(f1, 3),
        "status_accuracy": round(status_match / total, 3) if total else 0.0,
        "citation_rate": round(cited / total, 3) if total else 0.0,
    }
    return metrics


if __name__ == "__main__":
    m = evaluate()
    print("=== نتائج القياس ===")
    for k, v in m.items():
        print(f"{k}: {v}")
