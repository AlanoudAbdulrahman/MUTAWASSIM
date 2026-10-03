"""
config.py — الإعدادات المركزية.

MOCK_MODE=1 (الافتراضي) يشغّل النظام كاملًا بدون أي مفتاح API، بمنطق بديل
حتمي (deterministic) للتحقق والاستخراج — مثالي لليوم الأول والتكامل.
عند جاهزية النماذج الحقيقية: اضبطوا MOCK_MODE=0 وعبّوا المفاتيح في .env
"""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass  # python-dotenv اختياري

# وضع التشغيل
MOCK_MODE: bool = os.getenv("MOCK_MODE", "1") == "1"

# مزود النموذج اللغوي (عند MOCK_MODE=0)
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

# نموذج الـ embeddings العربي (sentence-transformers)
EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "intfloat/multilingual-e5-base"
)

# مسارات البيانات
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SOURCES_FILE = DATA_DIR / "sources" / "sources.json"          # المصادر الحقيقية (تُبنى من build_sources.py)
SOURCES_SAMPLE_FILE = DATA_DIR / "sources" / "sources.sample.json"  # عيّنة احتياطية
TEST_SET_FILE = DATA_DIR / "test_set" / "test_set.sample.json"
CHROMA_DIR = DATA_DIR / "chroma_index"

# إعدادات الاسترجاع والعتبات
RETRIEVE_K: int = int(os.getenv("RETRIEVE_K", "5"))
MIN_CONFIDENCE: float = float(os.getenv("MIN_CONFIDENCE", "0.35"))
MIN_SIM: float = float(os.getenv("MIN_SIM", "0.15"))  # أدنى تشابه لقبول دليل
