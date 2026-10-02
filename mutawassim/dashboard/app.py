"""
dashboard/app.py — لوحة التحكم (Streamlit).
المالك: لجين (الواجهة).

تشغيل:  streamlit run mutawassim/dashboard/app.py
"""
from __future__ import annotations

import json
import sys
import pathlib

# السماح بالاستيراد عند التشغيل المباشر
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import streamlit as st
from mutawassim.pipeline import run_pipeline

_COLORS = {"موضوع": "#C0392B", "ضعيف": "#E67E22", "يحتاج تحقق": "#7F8C8D", "مؤكد": "#2E8B57"}

st.set_page_config(page_title="متوسّم", page_icon="🛡️", layout="wide")
st.title("مُتوسّم — الإنذار المبكر للمحتوى الديني")
st.caption("ألصق دفعة منشورات أو ارفع ملفًا، ثم تحقّق.")

tab_text, tab_file = st.tabs(["لصق نص", "رفع ملف"])
raw_posts: list[dict] = []

with tab_text:
    txt = st.text_area("منشور واحد في كل سطر:", height=160)
    if st.button("تحقّق", key="btn_text") and txt.strip():
        raw_posts = [{"post_id": f"p{i}", "text": line} for i, line in enumerate(txt.splitlines()) if line.strip()]

with tab_file:
    up = st.file_uploader("ملف JSON [{post_id, text}] أو CSV بعمود text", type=["json", "csv"])
    if up and st.button("تحقّق", key="btn_file"):
        if up.name.endswith(".json"):
            raw_posts = json.load(up)
        else:
            import csv, io
            reader = csv.DictReader(io.StringIO(up.getvalue().decode("utf-8")))
            raw_posts = [{"post_id": f"p{i}", "text": r.get("text", "")} for i, r in enumerate(reader)]

if raw_posts:
    cards = run_pipeline(raw_posts)
    st.subheader(f"النتائج ({len(cards)}) — مرتّبة بالخطورة")
    for c in cards:
        color = _COLORS.get(c.verdict_label, "#555")
        with st.container(border=True):
            st.markdown(
                f"<span style='background:{color};color:#fff;padding:2px 10px;border-radius:12px'>"
                f"{c.verdict_label}</span> &nbsp; <b>خطورة:</b> {c.risk:.3f} &nbsp; "
                f"<b>الإجراء:</b> {c.action}",
                unsafe_allow_html=True,
            )
            st.write(c.correction)
            for s in c.sources:
                st.markdown(f"- [{s}]({s})")
