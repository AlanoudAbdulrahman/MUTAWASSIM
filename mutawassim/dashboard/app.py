# app.py — لوحة متوسّم
# واجهة فقط؛ لا يوجد منطق تحقق هنا.

from __future__ import annotations

import html
from urllib.parse import urlparse

import streamlit as st

import pipeline_client as pc


st.set_page_config(
    page_title="متوسّم — التحقق من المحتوى الديني",
    page_icon="🔎",
    layout="centered",
)


# ============================================================
# تنسيق الحالات
# ============================================================

STYLES = {
    "fabricated": {
        "label": "موضوع",
        "bg": "#FEF2F2",
        "bar": "#DC2626",
        "icon": "⛔",
    },
    "weak": {
        "label": "ضعيف",
        "bg": "#FFF7ED",
        "bar": "#EA580C",
        "icon": "⚠️",
    },
    "confirmed": {
        "label": "صحيح",
        "bg": "#F0FDF4",
        "bar": "#16A34A",
        "icon": "✅",
    },
    "needs_review": {
        "label": "يحتاج مراجعة",
        "bg": "#F1F5F9",
        "bar": "#64748B",
        "icon": "🔍",
    },
    "referral": {
        "label": "إحالة لمختص",
        "bg": "#EFF6FF",
        "bar": "#2563EB",
        "icon": "🧭",
    },
}


EXAMPLES = {
    "مثال ١": "منشور تجريبي يحتوي ادعاءً دينيًا للتجربة.",
    "مثال ٢": "منشور تجريبي آخر يحتوي أكثر من ادعاء.",
    "مثال ٣": "سؤال شخصي تجريبي لاختبار الإحالة لمختص.",
}


# ============================================================
# تحديد شكل البطاقة من ResponseCard
# ============================================================

def style_key(card: dict) -> str:
    """
    تحديد لون البطاقة اعتمادًا على verdict_label و action فقط.

    لا نستخدم status أو risk هنا لأنهما ليسا جزءًا
    من ResponseCard النهائي.
    """

    label = str(card.get("verdict_label", "")).strip()

    if "موضوع" in label or "مختلق" in label:
        return "fabricated"

    if "ضعيف" in label:
        return "weak"

    if "صحيح" in label or "مؤكد" in label:
        return "confirmed"

    if card.get("action") == "إحالة لمختص":
        return "referral"

    return "needs_review"


def card_style(card: dict) -> dict:
    return STYLES[style_key(card)]


def safe_url(url: str) -> bool:
    """
    السماح فقط بروابط HTTP/HTTPS.
    """
    try:
        return urlparse(str(url)).scheme in ("http", "https")
    except Exception:
        return False


# ============================================================
# عرض بطاقة ResponseCard
# ============================================================

def render_card(card: dict) -> None:
    esc = html.escape
    style = card_style(card)

    sources = card.get("sources", [])

    links = "".join(
        f'<li><a href="{esc(str(url))}" target="_blank" rel="noopener">'
        f"{esc(str(url))}</a></li>"
        for url in sources
        if safe_url(url)
    )

    if not links:
        links = "<li class='none'>لا يوجد مصدر</li>"

    st.markdown(
        f"""
        <div class="card"
             style="
                background:{style['bg']};
                border-right:6px solid {style['bar']};
             ">

            <div class="head">

                <span class="verdict"
                      style="color:{style['bar']}">
                    {style['icon']}
                    {esc(str(card.get('verdict_label', style['label'])))}
                </span>

                <span class="chip">
                    الإجراء:
                    {esc(str(card.get('action', '—')))}
                </span>

                <span class="cid">
                    {esc(str(card.get('claim_id', '')))}
                </span>

            </div>

            <div class="body">
                {esc(str(card.get('correction', '')))}
            </div>

            <div class="src">
                <b>المصادر</b>
                <ul>
                    {links}
                </ul>
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

      @import url(
        'https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap'
      );

      html,
      body,
      .stApp,
      .stMarkdown,
      textarea,
      button,
      label {
        font-family: 'Tajawal', sans-serif !important;
      }

      .stApp {
        direction: rtl;
        text-align: right;
      }

      textarea {
        direction: rtl;
        text-align: right;
        font-size: 1.05rem !important;
      }

      .hero {
        background: linear-gradient(
          135deg,
          #0F766E,
          #115E59 60%,
          #134E4A
        );

        color: #fff;
        padding: 26px 28px;
        border-radius: 18px;
        margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(15,118,110,.25);
      }

      .hero h1 {
        margin: 0;
        font-size: 2.1rem;
        font-weight: 800;
        color: #fff;
      }

      .hero p {
        margin: 6px 0 0;
        opacity: .92;
        font-size: 1.05rem;
      }

      .badge {
        display: inline-block;
        margin-top: 12px;
        padding: 3px 12px;
        border-radius: 20px;
        background: #ffffff26;
        font-size: .85rem;
      }

      .card {
        padding: 16px 20px;
        border-radius: 14px;
        margin: 14px 0;
        box-shadow: 0 2px 10px rgba(0,0,0,.06);
      }

      .head {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 8px;
      }

      .verdict {
        font-size: 1.3rem;
        font-weight: 800;
      }

      .chip {
        background: #ffffffcc;
        border-radius: 14px;
        padding: 2px 12px;
        font-size: .85rem;
      }

      .cid {
        margin-right: auto;
        color: #94A3B8;
        font-size: .8rem;
        direction: ltr;
      }

      .body {
        line-height: 2;
        margin: 4px 0 10px;
        font-size: 1.05rem;
      }

      .src ul {
        margin: 4px 0 0;
        padding-right: 22px;
      }

      .src a {
        direction: ltr;
        unicode-bidi: plaintext;
        word-break: break-all;
        color: #0F766E;
      }

      .none {
        color: #94A3B8;
        list-style: none;
        margin-right: -22px;
      }

      .foot {
        text-align: center;
        color: #64748B;
        font-size: .85rem;
        margin-top: 26px;
      }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# رأس الصفحة
# ============================================================

mode = (
    "متصل بالـ pipeline الحقيقي"
    if pc.REAL_PIPELINE
    else "وضع تجريبي (بيانات وهمية)"
)

st.markdown(
    f"""
    <div class="hero">

        <h1>🔎 متوسّم</h1>

        <p>
            نرصد المحتوى الديني المغلوط، ونتحقق منه من مصادر معتمدة،
            ونرتّبه بحسب الخطورة.
        </p>

        <span class="badge">
            {mode}
        </span>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# التبويبات
# ============================================================

tab_text, tab_file = st.tabs(
    ["✍️ لصق نص", "📁 رفع ملف"]
)


# ============================================================
# تبويب النص
# ============================================================

with tab_text:

    st.caption("جرّبي مثالًا جاهزًا:")

    cols = st.columns(len(EXAMPLES))

    for col, (name, sample) in zip(cols, EXAMPLES.items()):

        if col.button(
            name,
            use_container_width=True,
        ):
            st.session_state["text_input"] = sample

    text = st.text_area(
        "منشور واحد في كل سطر",
        key="text_input",
        height=160,
        placeholder="الصقي نص المنشور هنا ثم اضغطي «تحقّق»",
    )

    if st.button(
        "تحقّق",
        type="primary",
        use_container_width=True,
        key="go_text",
    ):

        if not text.strip():

            st.warning("الرجاء لصق نص أولًا.")

        else:

            with st.spinner("جارٍ التحقق..."):

                try:

                    st.session_state["cards"] = pc.verify_batch(text)

                except Exception as e:

                    st.session_state["cards"] = None

                    st.error(
                        f"تعذّر التحقق: {e}"
                    )


# ============================================================
# تبويب الملف
# ============================================================

with tab_file:

    st.caption(
        "ملف CSV (عمود text، وpost_id اختياري) "
        "أو JSON ([{post_id, text}])."
    )

    up = st.file_uploader(
        "اختاري ملف المنشورات",
        type=["csv", "json"],
    )

    if st.button(
        "تحقّق من الملف",
        type="primary",
        use_container_width=True,
        key="go_file",
    ):

        if up is None:

            st.warning(
                "الرجاء رفع ملف أولًا."
            )

        else:

            try:

                posts = pc.parse_posts(
                    up.name,
                    up.getvalue(),
                )

                with st.spinner(
                    f"جارٍ التحقق من {len(posts)} منشور..."
                ):

                    st.session_state["cards"] = pc.verify_posts(
                        posts
                    )

            except Exception as e:

                st.session_state["cards"] = None

                st.error(
                    f"تعذّر قراءة الملف أو تشغيل التحقق: {e}"
                )


# ============================================================
# النتائج
# ============================================================

cards = st.session_state.get("cards")


if cards is not None:

    # مهم:
    # لا نرتب هنا حسب risk.
    # الـ pipeline مسؤول عن حساب الخطورة والترتيب قبل ResponseCard.

    st.divider()

    st.subheader(
        f"النتائج ({len(cards)})"
    )

    if not cards:

        st.info(
            "لم يتم العثور على ادعاءات قابلة للتحقق."
        )

    else:

        counts = {
            key: 0
            for key in STYLES
        }

        for card in cards:

            counts[style_key(card)] += 1

        metrics = st.columns(4)

        metrics[0].metric(
            "موضوع",
            counts["fabricated"],
        )

        metrics[1].metric(
            "ضعيف",
            counts["weak"],
        )

        metrics[2].metric(
            "صحيح",
            counts["confirmed"],
        )

        metrics[3].metric(
            "امتناع/إحالة",
            counts["needs_review"] + counts["referral"],
        )

        for card in cards:

            render_card(card)

    if not pc.REAL_PIPELINE:

        st.caption(
            "⚠️ القيم تجريبية حاليًا ولا تمثّل أحكامًا شرعية."
        )


# ============================================================
# التذييل
# ============================================================

st.markdown(
    """
    <div class="foot">
        متوسّم — التحقق من المحتوى الديني النصي من مصادر معتمدة
    </div>
    """,
    unsafe_allow_html=True,
)