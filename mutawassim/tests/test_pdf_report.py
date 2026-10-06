"""Smoke tests for the PDF export; layout itself is checked by eye."""
import json
import re

from mutawassim import config
from mutawassim.reporting import pdf_report
from mutawassim.schemas import Claim, ResponseCard


def _pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page\b", pdf))


def _card(i, label="موضوع", action="رد", sources=("https://dorar.net/hadith/search?q=x",)):
    return ResponseCard(claim_id=f"p{i}_c00", verdict_label=label, action=action,
                        correction="الحكم: موضوع. المصدر: dorar.net/hadith.",
                        sources=list(sources), risk=0.5)


def _claim(i):
    return Claim(claim_id=f"p{i}_c00", source_post_id=f"p{i}", text="حب الوطن من الإيمان")


def test_renders_valid_pdf_with_and_without_claims():
    cards = [_card(1), _card(2, "مؤكد", sources=())]
    for claims in (None, [_claim(1)]):
        pdf = pdf_report.render_pdf(cards, claims)
        assert pdf.startswith(b"%PDF") and _pages(pdf) == 1


def test_empty_batch_still_renders():
    assert _pages(pdf_report.render_pdf([])) == 1


def test_many_cards_flow_onto_new_pages():
    cards = [_card(i) for i in range(30)]
    assert _pages(pdf_report.render_pdf(cards, [_claim(i) for i in range(30)])) > 3


def test_every_verdict_and_action_renders():
    cards = [_card(i, label, action)
             for i, (label, action) in enumerate([("موضوع", "رد"), ("ضعيف", "إحالة لمختص"),
                                                  ("يحتاج تحقق", "امتناع"), ("مؤكد", "رد")])]
    assert pdf_report.render_pdf(cards).startswith(b"%PDF")


def test_short_url_hides_query_string():
    assert pdf_report._short_url("https://dorar.net/hadith/search?q=%D8%AD") == "dorar.net/hadith/search"
    assert len(pdf_report._short_url("https://a.com/" + "x" * 200)) == 80


def test_cli_writes_report(tmp_path):
    out = tmp_path / "report.pdf"
    posts = config.DATA_DIR / "raw" / "posts.sample.json"
    assert json.loads(posts.read_text(encoding="utf-8"))
    pdf_report.main([str(posts), "-o", str(out)])
    assert out.read_bytes().startswith(b"%PDF")


def test_display_strips_emoji_but_keeps_arabic_symbols():
    assert pdf_report._display("الدين المعاملة 👌 ❤️🙏  #ترند") == "الدين المعاملة #ترند"
    assert pdf_report._display("قال النبي ﷺ") == "قال النبي ﷺ"


def test_load_posts_reads_sarah_formats(tmp_path):
    md = tmp_path / "demo.md"
    md.write_text('# عنوان\n1. "منشور أول"\n2. "منشور ثان"\n', encoding="utf-8")
    assert [p["text"] for p in pdf_report.load_posts(md)] == ["منشور أول", "منشور ثان"]

    test_set = tmp_path / "test_set.json"
    test_set.write_text('[{"claim_text": "ادعاء", "expected_status": "weak"}]', encoding="utf-8")
    assert pdf_report.load_posts(test_set) == [{"post_id": "test_set_001", "text": "ادعاء"}]

    posts = tmp_path / "posts.json"
    posts.write_text('[{"post_id": "p1", "text": "نص"}]', encoding="utf-8")
    assert pdf_report.load_posts(posts) == [{"post_id": "p1", "text": "نص"}]


def test_display_can_drop_diacritics_for_tajawal_text():
    assert pdf_report._display("يُحال للمختص، موضوع حسّاس", keep_marks=False) == "يحال للمختص، موضوع حساس"
    assert pdf_report._display("إِنَّ اللَّهَ") == "إِنَّ اللَّهَ"


def test_every_theme_renders():
    for theme in pdf_report._THEMES:
        assert pdf_report.render_pdf([_card(1)], [_claim(1)], theme=theme).startswith(b"%PDF")


def test_unknown_theme_is_rejected():
    import pytest
    with pytest.raises(KeyError):
        pdf_report.render_pdf([], theme="neon")
