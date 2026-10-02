"""اختبار دخان سريع: يتأكد أن المسار كاملًا يعمل في وضع MOCK."""
import json

from mutawassim import config
from mutawassim.pipeline import run_pipeline
from mutawassim.evaluation.evaluate import evaluate


def _load_sample_posts():
    return json.loads((config.DATA_DIR / "raw" / "posts.sample.json").read_text(encoding="utf-8"))


def test_pipeline_runs_and_filters_noise():
    cards = run_pipeline(_load_sample_posts())
    assert len(cards) >= 1
    # المنشور غير الديني (الطقس) يجب أن يُفلتر فلا يُنتج بطاقة
    assert all("الطقس" not in c.correction for c in cards)


def test_cards_are_sorted_by_risk():
    cards = run_pipeline(_load_sample_posts())
    risks = [c.risk for c in cards]
    assert risks == sorted(risks, reverse=True)


def test_evaluate_returns_metrics():
    m = evaluate()
    for key in ("detection_precision", "detection_recall", "status_accuracy", "citation_rate"):
        assert key in m
