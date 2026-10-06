"""
pdf_report.py — تصدير بطاقات الرد إلى تقرير PDF عربي.
المالك: العنود (الرد).

render_pdf(cards, claims=None) -> bytes
- cards: مخرج run_pipeline (مرتّبة بالخطورة).
- claims: اختياري؛ إن مُرّرت يعرض التقرير نص الادعاء ورقم المنشور لكل بطاقة.

تشغيل:  python -m mutawassim.reporting.pdf_report [posts.json] [-o report.pdf] [--theme navy|mauve|beige|green]
الخطوط: Tajawal للواجهة و Amiri للنصوص المقتبسة (رخصة OFL، في fonts/).
"""
from __future__ import annotations

import datetime as _dt
import pathlib
import re
from collections import Counter
from typing import Iterable
from urllib.parse import urlsplit

from fpdf import FPDF
from fpdf.enums import MethodReturnValue, XPos, YPos

from ..schemas import Claim, ResponseCard

_FONTS = pathlib.Path(__file__).resolve().parent / "fonts"
_LOGO = pathlib.Path(__file__).resolve().parents[1] / "web" / "logo.png"  # نفس شعار الموقع (أبيض لهيدر غامق)

# ألوان الحالات (نفس ألوان اللوحة dashboard/app.py)
_VERDICT_COLORS = {
    "موضوع": (192, 57, 43),
    "ضعيف": (230, 126, 34),
    "يحتاج تحقق": (127, 140, 141),
    "مؤكد": (46, 139, 87),
}
_VERDICT_ORDER = ("موضوع", "ضعيف", "يحتاج تحقق", "مؤكد")

_INK = (33, 37, 41)
_MUTED = (108, 117, 125)
# ثيمات التقرير: band خلفية الترويسة، pattern لون الزخرفة، primary العناوين والإجراء،
# accent الخطوط الذهبية، surface خلفية البطاقات، track مسار شريط الخطورة
_THEMES = {
    "mauve": {
        "band": (62, 38, 84), "pattern": (84, 58, 108), "title": (255, 255, 255),
        "subtitle": (228, 216, 238), "date": (214, 180, 92), "accent": (201, 162, 39),
        "primary": (74, 44, 100), "surface": (247, 245, 249), "track": (226, 220, 232),
        "link": (98, 64, 132),
    },
    "beige": {
        "band": (112, 84, 54), "pattern": (134, 104, 72), "title": (255, 255, 255),
        "subtitle": (240, 228, 210), "date": (226, 194, 120), "accent": (201, 162, 39),
        "primary": (104, 76, 46), "surface": (248, 245, 239), "track": (230, 222, 208),
        "link": (128, 90, 40),
    },
    "navy": {
        "band": (24, 34, 74), "pattern": (66, 64, 118), "title": (255, 255, 255),
        "subtitle": (214, 208, 236), "date": (190, 168, 226), "accent": (168, 140, 206),
        "primary": (32, 44, 92), "surface": (246, 245, 250), "track": (224, 220, 236),
        "link": (84, 70, 150),
    },
    "green": {
        "band": (15, 61, 62), "pattern": (32, 86, 87), "title": (255, 255, 255),
        "subtitle": (222, 232, 228), "date": (201, 162, 39), "accent": (201, 162, 39), "primary": (15, 61, 62),
        "surface": (247, 245, 239), "track": (226, 223, 214), "link": (17, 103, 105),
    },
}
DEFAULT_THEME = "navy"

_MARGIN = 16
_PAD = 6
_ACCENT = 2.5
_GAP = 5


# الإيموجي غير موجود في الخطوط؛ يُحذف من النص المعروض فقط
_EMOJI = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]")


# خط Tajawal لا يركّب الحركات (خاصة الشدة مع الكسرة) فتنقطع الحروف؛
# تُحذف من نصوصه فقط، ونص الادعاء بخط Amiri يبقى مشكولًا
_TASHKEEL = re.compile(r"[\u064B-\u0652\u0670]")


def _display(text: str, keep_marks: bool = True) -> str:
    text = _EMOJI.sub("", text)
    if not keep_marks:
        text = _TASHKEEL.sub("", text)
    return " ".join(text.split())


def _short_url(url: str) -> str:
    """اسم الموقع والمسار فقط؛ الرابط الكامل يبقى قابلًا للنقر."""
    parts = urlsplit(url)
    shown = f"{parts.netloc}{parts.path}".rstrip("/") or url
    return shown if len(shown) <= 80 else shown[:77] + "..."


def _risk_color(risk: float) -> tuple[int, int, int]:
    if risk >= 0.6:
        return _VERDICT_COLORS["موضوع"]
    if risk >= 0.3:
        return _VERDICT_COLORS["ضعيف"]
    return _VERDICT_COLORS["مؤكد"]


class _ReportPDF(FPDF):
    def __init__(self, theme: str = DEFAULT_THEME) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.t = _THEMES[theme]
        self.add_font("Tajawal", "", str(_FONTS / "Tajawal-Regular.ttf"))
        self.add_font("Tajawal", "B", str(_FONTS / "Tajawal-Bold.ttf"))
        self.add_font("Amiri", "", str(_FONTS / "Amiri-Regular.ttf"))
        self.set_text_shaping(use_shaping_engine=True, direction="rtl", script="arab", language="ara")
        self.set_margins(_MARGIN, _MARGIN, _MARGIN)
        self.set_auto_page_break(auto=False)
        self.content_w = self.w - 2 * _MARGIN

    def footer(self) -> None:
        self.set_y(-13)
        self.set_draw_color(*self.t["accent"])
        self.set_line_width(0.3)
        self.line(_MARGIN, self.get_y() - 2, self.w - _MARGIN, self.get_y() - 2)
        self.set_font("Tajawal", "", 8)
        self.set_text_color(*_MUTED)
        self.cell(self.content_w, 5, "يعتمد هذا التقرير على المصادر المعتمدة فقط، ولا يعد فتوى.", align="R")
        self.set_x(_MARGIN)
        self.set_text_shaping(use_shaping_engine=True, direction="ltr")
        self.cell(self.content_w, 5, f"{self.page_no()} / {{nb}}", align="L")
        self.set_text_shaping(use_shaping_engine=True, direction="rtl", script="arab", language="ara")

    # ---- أدوات مساعدة ----
    def text_height(self, w: float, h: float, text: str) -> float:
        return self.multi_cell(w, h, text, align="R", dry_run=True, output=MethodReturnValue.HEIGHT)

    def pill(self, x_right: float, y: float, text: str, fill, color=(255, 255, 255),
             outline: bool = False, size: float = 9) -> float:
        """يرسم شارة تنتهي عند x_right، ويرجّع موضعها الأيسر."""
        self.set_font("Tajawal", "B", size)
        w = self.get_string_width(text) + 7
        h = 6.2
        x = x_right - w
        if outline:
            self.set_draw_color(*fill)
            self.set_line_width(0.35)
            self.rect(x, y, w, h, style="D", round_corners=True, corner_radius=3)
            self.set_text_color(*fill)
        else:
            self.set_fill_color(*fill)
            self.rect(x, y, w, h, style="F", round_corners=True, corner_radius=3)
            self.set_text_color(*color)
        self.set_xy(x, y + 0.4)
        self.cell(w, h - 0.8, text, align="C")
        return x

    def ensure_space(self, h: float) -> None:
        if self.get_y() + h > self.h - 20:
            self.add_page()
            self.set_y(_MARGIN)


def _star(pdf: _ReportPDF, cx: float, cy: float, r: float) -> None:
    """نجمة ثمانية (مربع + مربع مدوّر 45°) مع دائرة صغيرة في المركز."""
    a = r / 1.4142
    pdf.polygon([(cx - a, cy - a), (cx + a, cy - a), (cx + a, cy + a), (cx - a, cy + a)], style="D")
    pdf.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], style="D")
    pdf.circle(x=cx, y=cy, radius=r * 0.28, style="D")


def _draw_pattern(pdf: _ReportPDF, x: float, y: float, w: float, h: float) -> None:
    """شبكة نجوم ثمانية متداخلة، مقصوصة على حدود الترويسة."""
    step, r = 13.0, 5.2
    pdf.set_draw_color(*pdf.t["pattern"])
    pdf.set_line_width(0.3)
    fade_start, fade_end = x + w * 0.3, x + w * 0.62
    with pdf.rect_clip(x, y, w, h):
        row = 0
        cy = y - step / 2
        while cy < y + h + step:
            cx = x - step + (step / 2 if row % 2 else 0)
            while cx < fade_end + step:
                # تتلاشى الزخرفة تدريجيًا قبل منطقة العنوان
                opacity = min(1.0, max(0.0, (fade_end - cx) / (fade_end - fade_start)))
                if opacity > 0:
                    with pdf.local_context(stroke_opacity=opacity):
                        _star(pdf, cx, cy, r)
                cx += step
            cy += step / 2
            row += 1


def _draw_header(pdf: _ReportPDF, title: str, generated_at: _dt.datetime) -> None:
    band_h = 46
    pdf.set_fill_color(*pdf.t["band"])
    pdf.rect(0, 0, pdf.w, band_h, style="F")
    _draw_pattern(pdf, 0, 0, pdf.w, band_h)
    pdf.set_fill_color(*pdf.t["accent"])
    pdf.rect(0, band_h, pdf.w, 1.2, style="F")
    pdf.rect(0, band_h + 2, pdf.w, 0.4, style="F")

    if _LOGO.exists():
        logo_h = 20
        pdf.image(str(_LOGO), x=pdf.w - _MARGIN - logo_h * 376 / 186, y=3.5, h=logo_h)
    else:  # احتياط إن لم يوجد الشعار
        pdf.set_text_color(*pdf.t["title"])
        pdf.set_font("Tajawal", "B", 30)
        pdf.set_xy(_MARGIN, 9)
        # بلا تشكيل: الشدة مع الكسرة تقطع وصل الحروف في خط Tajawal العريض
        pdf.cell(pdf.content_w, 14, "متوسم", align="R")

    pdf.set_font("Tajawal", "", 12)
    pdf.set_text_color(*pdf.t["subtitle"])
    pdf.set_xy(_MARGIN, 24)
    pdf.cell(pdf.content_w, 7, title, align="R")

    pdf.set_font("Tajawal", "", 9)
    pdf.set_text_color(*pdf.t["date"])
    pdf.set_xy(_MARGIN, 33)
    pdf.cell(pdf.content_w, 6, f"تاريخ الإصدار: {generated_at:%Y-%m-%d %H:%M}", align="R")
    pdf.set_y(58)


def _draw_summary(pdf: _ReportPDF, cards: list[ResponseCard]) -> None:
    counts = Counter(c.verdict_label for c in cards)
    gap = 4
    tile_w = (pdf.content_w - gap * (len(_VERDICT_ORDER) - 1)) / len(_VERDICT_ORDER)
    tile_h = 24
    y = pdf.get_y()
    for i, label in enumerate(_VERDICT_ORDER):
        x = pdf.w - _MARGIN - (i + 1) * tile_w - i * gap   # من اليمين لليسار
        color = _VERDICT_COLORS[label]
        pdf.set_fill_color(*pdf.t["surface"])
        pdf.rect(x, y, tile_w, tile_h, style="F", round_corners=True, corner_radius=2.5)
        pdf.set_fill_color(*color)
        pdf.rect(x, y, tile_w, 1.6, style="F")
        pdf.set_text_color(*color)
        pdf.set_font("Tajawal", "B", 20)
        pdf.set_xy(x, y + 4)
        pdf.cell(tile_w, 10, str(counts.get(label, 0)), align="C")
        pdf.set_font("Tajawal", "", 9.5)
        pdf.set_text_color(*_INK)
        pdf.set_xy(x, y + 15)
        pdf.cell(tile_w, 6, label, align="C")

    referrals = sum(c.action == "إحالة لمختص" for c in cards)
    top = max((c.risk for c in cards), default=0.0)
    pdf.set_xy(_MARGIN, y + tile_h + 4)
    pdf.set_font("Tajawal", "", 10)
    pdf.set_text_color(*_MUTED)
    pdf.cell(
        pdf.content_w, 6,
        f"إجمالي الادعاءات: {len(cards)}   ·   إحالات للمختص: {referrals}   ·   أعلى خطورة: {top:.2f}",
        align="R",
    )
    pdf.set_y(y + tile_h + 15)


def _section_title(pdf: _ReportPDF, text: str) -> None:
    pdf.ensure_space(14)
    pdf.set_font("Tajawal", "B", 13)
    pdf.set_text_color(*pdf.t["primary"])
    pdf.set_x(_MARGIN)
    pdf.cell(pdf.content_w, 8, text, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_fill_color(*pdf.t["accent"])
    pdf.rect(pdf.w - _MARGIN - 18, pdf.get_y(), 18, 0.8, style="F")
    pdf.ln(5)


def _draw_card(pdf: _ReportPDF, index: int, card: ResponseCard, claim: Claim | None) -> None:
    inner_w = pdf.content_w - 2 * _PAD - _ACCENT
    inner_x = _MARGIN + _PAD

    # قياس الارتفاع قبل الرسم لتفادي انقسام البطاقة بين صفحتين
    h = _PAD + 7 + 3
    if claim:
        pdf.set_font("Amiri", "", 13)
        claim_text = f"«{_display(claim.text)}»"
        claim_h = pdf.text_height(inner_w, 7, claim_text)
        h += 5 + claim_h + 2
    pdf.set_font("Tajawal", "", 10.5)
    correction = _display(card.correction, keep_marks=False)
    corr_h = pdf.text_height(inner_w, 6, correction)
    h += corr_h + 2
    if card.sources:
        h += 4 + 5 * len(card.sources)
    h += _PAD - 2
    pdf.ensure_space(h + _GAP)

    x0, y0 = _MARGIN, pdf.get_y()
    color = _VERDICT_COLORS.get(card.verdict_label, _MUTED)
    pdf.set_fill_color(*pdf.t["surface"])
    pdf.rect(x0, y0, pdf.content_w, h, style="F", round_corners=True, corner_radius=3)
    pdf.set_fill_color(*color)
    pdf.rect(x0 + pdf.content_w - _ACCENT, y0 + 2, _ACCENT, h - 4, style="F")

    # الصف الأول: الرقم، الحكم، الإجراء، الخطورة
    y = y0 + _PAD
    right = x0 + pdf.content_w - _ACCENT - _PAD
    pdf.set_font("Tajawal", "B", 11)
    pdf.set_text_color(*_MUTED)
    num = str(index)
    num_w = pdf.get_string_width(num) + 2
    pdf.set_xy(right - num_w, y)
    pdf.cell(num_w, 6.2, num, align="R")
    left = pdf.pill(right - num_w - 2, y, card.verdict_label, color)
    pdf.pill(left - 2.5, y, card.action, pdf.t["primary"], outline=True, size=8.5)

    bar_w = 34
    pdf.set_fill_color(*pdf.t["track"])
    pdf.rect(inner_x, y + 4.2, bar_w, 2, style="F", round_corners=True, corner_radius=1)
    if card.risk > 0:
        pdf.set_fill_color(*_risk_color(card.risk))
        pdf.rect(inner_x, y + 4.2, max(2.0, bar_w * min(card.risk, 1.0)), 2,
                 style="F", round_corners=True, corner_radius=1)
    pdf.set_font("Tajawal", "B", 8.5)
    pdf.set_text_color(*_INK)
    pdf.set_xy(inner_x, y - 0.6)
    pdf.cell(bar_w, 4.5, f"الخطورة {card.risk:.2f}", align="R")
    y += 7 + 3

    if claim:
        pdf.set_font("Tajawal", "", 8.5)
        pdf.set_text_color(*_MUTED)
        pdf.set_xy(inner_x, y)
        pdf.cell(inner_w, 5, f"الادعاء — من المنشور {claim.source_post_id}", align="R")
        y += 5
        pdf.set_font("Amiri", "", 13)
        pdf.set_text_color(*_INK)
        pdf.set_xy(inner_x, y)
        pdf.multi_cell(inner_w, 7, claim_text, align="R")
        y += claim_h + 2

    pdf.set_font("Tajawal", "", 10.5)
    pdf.set_text_color(*_INK)
    pdf.set_xy(inner_x, y)
    pdf.multi_cell(inner_w, 6, correction, align="R")
    y += corr_h + 2

    if card.sources:
        pdf.set_draw_color(*pdf.t["track"])
        pdf.set_line_width(0.2)
        pdf.line(inner_x, y + 1, inner_x + inner_w, y + 1)
        y += 3
        pdf.set_font("Tajawal", "", 8.5)
        pdf.set_text_color(*pdf.t["link"])
        pdf.set_text_shaping(use_shaping_engine=True, direction="ltr")
        for n, url in enumerate(card.sources, start=1):
            pdf.set_xy(inner_x, y)
            pdf.cell(inner_w, 5, f"[{n}]  {_short_url(url)}", align="L", link=url)
            y += 5
        pdf.set_text_shaping(use_shaping_engine=True, direction="rtl", script="arab", language="ara")

    pdf.set_y(y0 + h + _GAP)


def render_pdf(
    cards: list[ResponseCard],
    claims: Iterable[Claim] | None = None,
    title: str = "تقرير التحقق من المحتوى الديني",
    generated_at: _dt.datetime | None = None,
    theme: str = DEFAULT_THEME,
) -> bytes:
    """يرجّع ملف PDF كبايتات (للحفظ أو للتنزيل من اللوحة/الـAPI)."""
    by_id = {c.claim_id: c for c in claims or []}
    pdf = _ReportPDF(theme)
    pdf.set_title(title)
    pdf.set_creator("MUTAWASSIM")
    pdf.add_page()
    _draw_header(pdf, title, generated_at or _dt.datetime.now())
    _draw_summary(pdf, cards)
    _section_title(pdf, "تفاصيل الادعاءات (مرتبة حسب الخطورة)")

    if not cards:
        pdf.set_font("Tajawal", "", 11)
        pdf.set_text_color(*_MUTED)
        pdf.cell(pdf.content_w, 10, "لا توجد ادعاءات قابلة للتحقق في هذه الدفعة.", align="R")
    for i, card in enumerate(cards, start=1):
        _draw_card(pdf, i, card, by_id.get(card.claim_id))
    return bytes(pdf.output())


def load_posts(path: str | pathlib.Path) -> list[dict]:
    """يقرأ المنشورات من:
    - JSON بصيغة [{post_id, text}]
    - JSON مجموعة الاختبار [{claim_text, ...}]
    - Markdown منشورات الديمو: أسطر مرقّمة بين علامتي تنصيص  1. "نص المنشور"
    """
    path = pathlib.Path(path)
    return parse_posts(path.name, path.read_text(encoding="utf-8-sig"))


def parse_posts(filename: str, content: str) -> list[dict]:
    """مثل load_posts لكن من نص الملف مباشرة (للرفع من الموقع). يدعم أيضًا CSV بعمود text."""
    import csv
    import io
    import json
    import re

    stem, _, suffix = filename.rpartition(".")
    stem, suffix = (stem or filename), suffix.lower()
    content = content.lstrip("﻿")
    if suffix == "md":
        texts = re.findall(r'^\s*\d+\.\s*"(.+)"\s*$', content, re.M)
        return [{"post_id": f"{stem}_{i:02d}", "text": t} for i, t in enumerate(texts, 1)]
    if suffix == "csv":
        rows = list(csv.DictReader(io.StringIO(content)))
    else:
        rows = json.loads(content)
    return [
        {"post_id": r.get("post_id") or f"{stem}_{i:03d}", "text": r.get("text") or r.get("claim_text", "")}
        for i, r in enumerate(rows, 1)
    ]


def main(argv: list[str] | None = None) -> pathlib.Path:
    import argparse

    from .. import config
    from ..pipeline import run_pipeline_detailed

    parser = argparse.ArgumentParser(description="تصدير تقرير متوسّم إلى PDF")
    parser.add_argument("posts", nargs="?", default=str(config.DATA_DIR / "raw" / "posts.sample.json"),
                        help="JSON [{post_id, text}] أو test_set.json أو ملف ديمو .md")
    parser.add_argument("-o", "--output", default="mutawassim_report.pdf")
    parser.add_argument("--theme", choices=sorted(_THEMES), default=DEFAULT_THEME)
    args = parser.parse_args(argv)

    raw = load_posts(args.posts)
    items = run_pipeline_detailed(raw)
    cards = [i.card for i in items]
    claims = [i.claim for i in items]

    out = pathlib.Path(args.output)
    out.write_bytes(render_pdf(cards, claims, theme=args.theme))
    print(f"تم إنشاء التقرير: {out.resolve()}")
    return out


if __name__ == "__main__":
    main()
