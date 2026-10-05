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

## قواعد مشتركة
- **الاستخراج:** يستخرج الادعاءات القابلة للتحقق دون الحكم عليها. السؤال عن حكم شرعي
  (حلال/حرام/يجوز) يُستخرج بصيغة «سؤال عن حكم …» ونوعه `other` ليُحال لمختص.
- **درجة المصدر ← الحالة** (`verifier._RULING_TO_STATUS`، بالاحتواء):
  `صحيح`/`حسن`/`نص قرآني` ← confirmed · `ضعيف` ← weak ·
  `موضوع`/`باطل`/`لا أصل له`/`ليس بحديث` ← fabricated. أي درجة في `sources.json`
  خارج هذه الكلمات يُفشل اختبار `test_verifier_rulings.py`.
- **الخطورة:** `risk = spread × severity × sensitivity` (الأوزان موثقة في `scoring/risk_score.py`).
- **إجراء البطاقة:** confirmed ← رد · needs_review ← إحالة لمختص ·
  weak/fabricated في العقيدة أو الشبهة ← إحالة لمختص · غير ذلك ← رد.
  التصحيح يقتبس الدليل (الحكم والمصدر والنص) ولا يعرض ملاحظات التحقق الداخلية.

---

# التشغيل السريع

```bash
python -m venv .venv && source .venv/bin/activate   # (ويندوز: .venv\Scripts\activate)
pip install -r requirements.txt

# المسار كاملًا على العيّنة (وضع MOCK بلا مفاتيح):
python -m mutawassim.pipeline

# القياس:
python -m mutawassim.evaluation.evaluate               # التحقق على test_set
python -m mutawassim.evaluation.evaluate_extraction    # جودة استخراج الادعاءات

# تقرير PDF (يقبل JSON أو test_set.json أو ملف ديمو .md):
python -m mutawassim.reporting.pdf_report [posts.json] -o report.pdf [--theme navy|mauve|beige|green]

# اللوحة:
streamlit run mutawassim/dashboard/app.py

# الـ API:
uvicorn mutawassim.api.main:app --reload

# الاختبارات:
pytest -q
```

## الانتقال للوضع الحقيقي
1. `pip install -r requirements.txt` ثم `pip install openai` (أو `requirements-full.txt` للمزوّد المحلي `local` والفلتر الدلالي).
2. انسخوا `.env.example` إلى `.env` واضبطوا `MOCK_MODE=0`. ضعوا `LLM_API_KEY` في `.env`
   أو في متغيرات بيئة النظام (الأخيرة تتقدّم على `.env`). لا يُكتب المفتاح في الكود أبدًا.
3. لاستخراج الادعاءات بالنموذج: `USE_LLM_EXTRACT=1` (الافتراضي تقسيم الجمل).
4. OpenAI مفعّل افتراضيًا في `mutawassim/llm.py`؛ لمزوّد آخر عدّلوا `_real_chat`.
5. (اختياري) ابنوا فهرس Chroma: `python -m mutawassim.retrieval.index_builder`.

## من يملك ماذا
- **سارة:** `ingestion/`, `data/`, `test_set`.
- **العنود:** `extraction/`, `scoring/`, `reporting/`.
- **غيداء:** `retrieval/`, `verification/`, `pipeline.py` (التكامل).
- **لجين:** `api/`, `dashboard/`, النشر والتوثيق.
