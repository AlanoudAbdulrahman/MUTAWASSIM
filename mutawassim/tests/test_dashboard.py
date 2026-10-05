import sys
from pathlib import Path

# الصعود خطوة لأعلى (.parent.parent) للوصول للجذر ثم مجلد dashboard
DASH = Path(__file__).resolve().parent.parent / "dashboard"
if str(DASH) not in sys.path:
    sys.path.insert(0, str(DASH))

from streamlit.testing.v1 import AppTest  # noqa: E402
import pipeline_client as pc  # noqa: E402
from app import card_style, STYLES  # noqa: E402


def test_styles():
    """اختبار تحديد النمط والتصميم حسب الحكم الشرعي/الحالة."""
    assert card_style({"verdict_label": "موضوع"}) is STYLES["fabricated"]
    assert card_style({"verdict_label": "غير معروف"}) is STYLES["needs_review"]


def test_parse_posts():
    """اختبار تحويل قراءة ملفات CSV و JSON إلى منشورات."""
    content = "post_id,text\np1,hello\n".encode("utf-8")
    parsed = pc.parse_posts("a.csv", content)
    assert parsed[0]["text"] == "hello"


def test_text_flow():
    """اختبار سريان الواجهة المباشر عبر Streamlit AppTest."""
    at = AppTest.from_file(str(DASH / "app.py")).run()

    # 1. إدخال النص في حقل النص مع مفتاحه الخاص مباشرة
    at.text_area(key="text_input").input("منشور تجريبي").run()

    # 2. النقر على زر "تحقّق"
    at.button(key="go_text").click().run()

    # 3. التأكد من عدم وجود أخطاء وأن البطاقات أُضيفت للـ session_state وتصييرها بالواجهة
    assert not at.exception
    assert at.session_state["cards"] is not None
    assert len(at.session_state["cards"]) >= 1


def test_real_pipeline_objects_are_normalized(monkeypatch):
    """اختبار تطبيع الكائنات الناتجة من Pipeline غيداء عند تفعيل الوضع الحقيقي."""
    class Card:  # كائن محاكاة لمخرجات run_pipeline
        claim_id = "c1"
        verdict_label = "صحيح"
        correction = "موافق للمصدر"
        sources = ["https://example.org/x"]
        action = "رد"
        risk = 0.0

    monkeypatch.setattr(pc, "REAL_PIPELINE", True)
    monkeypatch.setattr(pc, "run_pipeline", lambda posts: [Card()], raising=False)
    
    out = pc.verify_batch("سطر 1\nسطر 2")
    assert len(out) > 0
    assert out[0]["verdict_label"] == "صحيح"
    assert card_style(out[0]) is STYLES["confirmed"]
    