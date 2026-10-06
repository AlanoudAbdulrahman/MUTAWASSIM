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
`run_pipeline(raw_posts) -> list[ResponseCard]` (بلا حفظ)
الترتيب: تنظيف ← فلترة ← استخراج ← تحقق ← خطورة ← بطاقة. كل مرحلة تستقبل مخرج السابقة بنفس الصيغة.
- `run_pipeline_detailed(raw_posts)`: البطاقات مع الادعاء والتحقق والخطورة (للتقارير).
- `process_batch(raw_posts)`: مسار الموقع؛ يحسب الانتشار عبر كل الدفعات المحفوظة ثم يحفظ الدفعة في السجل.
- **المتانة:** فشل استخراج منشور لا يوقف الدفعة (يُسجَّل في `errors`)، وفشل التحقق من ادعاء يجعله needs_review.
- **الانتشار:** `1 − 0.8^n` حيث n عدد المنشورات المختلفة التي ذكرت نفس صيغة البحث (مع السجل في الموقع).

## الحفظ والقياس التلقائي
- `storage.py`: قاعدة SQLite محلية `data/mutawassim.db` (غير مرفوعة) لسجل التحقق وإحصائيات الاستخدام.
  **كل متصفح سجله الخاص:** هوية مجهولة في كوكي HttpOnly (القاعدة تحفظ بصمتها لا الرمز)،
  والسجل والإحصائيات والانتشار عبر الزمن مقيّدة بها. المشترك بين الكل: أداء النظام والمصادر.
- **كل زائر بمفتاحه (BYOK):** زائر الإنترنت يدخل مفتاح OpenAI الخاص به؛ يبقى في متصفحه ويُرسل
  مع طلب التحقق فقط (ترويسة `X-LLM-Key`، عبر HTTPS)، ولا يُحفظ ولا يُسجَّل في الخادم.
  مفتاح الخادم لا يُستخدم للزوار إلا حسب `SERVER_KEY_FOR` (الافتراضي: جهاز الخادم فقط)،
  والقياس التلقائي لا يطلقه إلا جهاز الخادم.
- `benchmark.py`: بصمة للكود والمصادر ومجموعات الاختبار والإعدادات؛ عند تغيّرها يُعاد قياس الأداء
  تلقائيًا في الخلفية (`AUTO_EVALUATE=0` لإيقافه). شغّلوا الخادم بـ `--reload` ليطابق الكودُ المحمَّل البصمةَ.

## قواعد مشتركة
- **الاستخراج:** يستخرج الادعاءات القابلة للتحقق دون الحكم عليها. والأسئلة الدينية:
  سؤال عن صحة نص (هل صح هذا الحديث؟) ← يُستخرج النص ويُتحقق منه ·
  سؤال يطلب حكمًا شرعيًا (حلال؟ يجوز؟) ← «سؤال عن حكم …» نوعه `other`، وبطاقته
  «يحتاج تحقق» ← إحالة لمختص مع تنبيه أن النظام لا يُفتي · سؤال معلومات (متى؟ كم؟) أو طلب تفسير رؤيا ← يُتجاهل.
- **درجة المصدر ← الحالة** (`verifier._RULING_TO_STATUS`، بالاحتواء):
  `صحيح`/`حسن`/`نص قرآني` ← confirmed · `ضعيف` ← weak ·
  `موضوع`/`باطل`/`لا أصل له`/`ليس بحديث` ← fabricated. أي درجة في `sources.json`
  خارج هذه الكلمات يُفشل اختبار `test_verifier_rulings.py`.
- **الخطورة:** `risk = spread × severity × sensitivity` (الأوزان موثقة في `scoring/risk_score.py`).
- **إجراء البطاقة:** confirmed ← رد · needs_review ← إحالة لمختص ·
  weak/fabricated في العقيدة أو الشبهة ← إحالة لمختص · غير ذلك ← رد.
  التصحيح يقتبس الدليل (الحكم والمصدر والنص) ولا يعرض ملاحظات التحقق الداخلية.
- **الإسناد إلزامي:** حكم النموذج في الحالات الغامضة يجب أن توافقه درجة أحد الأدلة المسترجعة،
  وإلا يصبح needs_review (يمنع الهلوسة والتعليمات المدسوسة في المنشورات).

---

# التشغيل السريع

```bash
python -m venv .venv && source .venv/bin/activate   # (ويندوز: .venv\Scripts\activate)
pip install -r requirements.txt

# التشغيل: أمر واحد يشغّل النظام كاملًا (الموقع + الـ API + المسار + النموذج) ويفتح المتصفح.
# (run.bat اختصار له بالنقر المزدوج على ويندوز)
python -m mutawassim

# القياس:
python -m mutawassim.evaluation.evaluate               # التحقق على test_set
python -m mutawassim.evaluation.evaluate_extraction    # جودة استخراج الادعاءات

# تقرير PDF (يقبل JSON أو test_set.json أو ملف ديمو .md):
python -m mutawassim.reporting.pdf_report [posts.json] -o report.pdf [--theme navy|mauve|beige|green]

# الحماية: حدود الدفعة، وتشغيل القياس من جهاز الخادم فقط (أو ADMIN_TOKEN)، وترويسات أمان — api/security.py

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
