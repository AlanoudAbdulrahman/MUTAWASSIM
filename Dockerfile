FROM python:3.11-slim

# إعداد المتغيرات البيئية لمنع بايثون من كتابة ملفات .pyc وإرسال المخرجات مباشرة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# تعيين مجلد العمل داخل الحاوية
WORKDIR /app

# الموقع يحتاج الأساسية فقط (المكتبات الثقيلة في requirements-full.txt اختيارية)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع إلى الحاوية (.env وقاعدة السجل مستبعدة في .dockerignore)
COPY . .

# إعدادات الموقع العام — لا مفتاح هنا: كل زائر يدخل مفتاحه
ENV MOCK_MODE=0 \
    USE_LLM_EXTRACT=1 \
    EMBED_PROVIDER=openai \
    SERVER_KEY_FOR=none \
    TRUST_LOCALHOST=0 \
    EXPOSE_DOCS=0 \
    AUTO_EVALUATE=0 \
    PORT=8000

# سجل التحقق يُحفظ هنا؛ اربطوه بـ volume حتى لا يُمسح عند إعادة تشغيل الحاوية
VOLUME ["/app/mutawassim/data/history"]
ENV DB_FILE=/app/mutawassim/data/history/mutawassim.db

EXPOSE 8000

# --proxy-headers: خلف HTTPS الاستضافة يرى الخادم الاتصال آمنًا فيقبل مفاتيح الزوار
CMD uvicorn mutawassim.api.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips="*"
