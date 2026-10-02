# عقود البيانات — المرجع الموحّد (Source of Truth)

كل الوحدات تلتزم بهذه الصيغ، ومصدرها الرسمي هو `mutawassim/schemas.py`.
أي تغيير يُناقَش مع قائدة التكامل (غيداء) أولًا، ويُحدَّث هنا وفي `schemas.py` معًا.

## الحالات المعتمدة (status)
`confirmed` مؤكد · `weak` ضعيف · `fabricated` موضوع/باطل · `needs_review` يحتاج مختصًّا/دليل غير كافٍ

## النماذج
- **Post**: `{post_id, text, meta}`
- **Claim**: `{claim_id, source_post_id, text, original_text, type, normalized_query}`
- **Evidence**: `{source, url, ruling, snippet}`
- **VerificationResult**: `{claim_id, status, evidence[], confidence, note}`
- **RiskScore**: `{claim_id, risk, factors:{spread, severity, sensitivity}}`
- **ResponseCard**: `{claim_id, verdict_label, correction, sources[], action, risk}`

## عقد الـ pipeline
`run_pipeline(raw_posts) -> list[ResponseCard]`
الترتيب: تنظيف ← فلترة ← استخراج ← تحقق ← خطورة ← بطاقة. كل مرحلة تستقبل مخرج السابقة بنفس الصيغة.

---

# التشغيل السريع

```bash
python -m venv .venv && source .venv/bin/activate   # (ويندوز: .venv\Scripts\activate)
pip install -r requirements.txt

# المسار كاملًا على العيّنة (وضع MOCK بلا مفاتيح):
python -m mutawassim.pipeline

# القياس:
python -m mutawassim.evaluation.evaluate

# اللوحة:
streamlit run mutawassim/dashboard/app.py

# الـ API:
uvicorn mutawassim.api.main:app --reload

# الاختبارات:
pytest -q
```

## الانتقال للوضع الحقيقي
1. `pip install -r requirements-full.txt`
2. انسخوا `.env.example` إلى `.env`، اضبطوا `MOCK_MODE=0` واملؤوا `LLM_API_KEY`.
3. فعّلوا `_real_chat` في `mutawassim/llm.py` حسب مزودكم.
4. (اختياري) ابنوا فهرس Chroma: `python -m mutawassim.retrieval.index_builder`.

## من يملك ماذا
- **سارة:** `ingestion/`, `data/`, `test_set`.
- **العنود:** `extraction/`, `scoring/`, `reporting/`.
- **غيداء:** `retrieval/`, `verification/`, `pipeline.py` (التكامل).
- **لجين:** `api/`, `dashboard/`, النشر والتوثيق.
