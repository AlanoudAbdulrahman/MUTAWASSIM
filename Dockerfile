FROM python:3.11-slim

# إعداد المتغيرات البيئية لمنع بايثون من كتابة ملفات .pyc وإرسال المخرجات مباشرة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# تعيين مجلد العمل داخل الحاوية
WORKDIR /app

# تحديث النظام وتثبيت المتطلبات الأساسية
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملفات الاعتماديات أولاً (للاستفادة من طبقات الكاش في دوكر)
COPY requirements.txt requirements-full.txt ./

# تثبيت الاعتماديات
# نستخدم requirements-full.txt لأنه يحتوي على كل المكتبات المطلوبة للنظام
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-full.txt

# نسخ باقي ملفات المشروع إلى الحاوية
COPY . .

# الأمر الافتراضي (يمكن تغييره لاحقاً لتشغيل لوحة Streamlit أو الخادم)
CMD ["python", "mutawassim/pipeline.py"]
