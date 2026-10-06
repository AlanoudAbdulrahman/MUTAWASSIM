"""
api/security.py — حدود الاستخدام وحماية الواجهات المكلفة.

كل تحقق يستدعي نموذجًا مدفوعًا، فالحدود تمنع استنزاف الرصيد:
- MAX_POSTS / MAX_POST_CHARS: حجم الدفعة الواحدة.
- MAX_UPLOAD_CHARS: حجم الملف المرفوع.
- ADMIN_TOKEN: إن ضُبط، تشغيل القياس (100+ استدعاء) يتطلب الترويسة X-Admin-Token؛
  وإن لم يُضبط، يُسمح به من الجهاز نفسه فقط (localhost).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

from fastapi import HTTPException, Request

from .. import config

MAX_POSTS = int(os.getenv("MAX_POSTS", "50"))
MAX_POST_CHARS = int(os.getenv("MAX_POST_CHARS", "4000"))
MAX_UPLOAD_CHARS = int(os.getenv("MAX_UPLOAD_CHARS", "500000"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
EXPOSE_DOCS = os.getenv("EXPOSE_DOCS", "1") == "1"

_LOCAL = {"127.0.0.1", "::1", "localhost", "testclient"}
# امتيازات «جهاز الخادم» (مفتاح الخادم، القياس، السجل القديم). عند النشر خلف وسيط عكسي
# (reverse proxy) يظهر كل الزوار كـ 127.0.0.1، فيجب إيقافها: TRUST_LOCALHOST=0
TRUST_LOCALHOST = os.getenv("TRUST_LOCALHOST", "1") == "1"

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # لا سكربتات مضمّنة ولا مصادر خارجية: كل الملفات من نفس الخادم
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
        "frame-ancestors 'none'; form-action 'self'"
    ),
}
# صفحة /docs تحتاج سكربتات Swagger الخارجية
DOCS_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; "
            "frame-ancestors 'none'")


def check_batch(posts: list) -> None:
    if not posts:
        raise HTTPException(400, "لا توجد منشورات للتحقق.")
    if len(posts) > MAX_POSTS:
        raise HTTPException(413, f"الحد الأقصى {MAX_POSTS} منشورًا في الدفعة الواحدة.")
    if any(len(p.text) > MAX_POST_CHARS for p in posts):
        raise HTTPException(413, f"الحد الأقصى لطول المنشور {MAX_POST_CHARS} حرف.")


def check_upload(content: str) -> None:
    if len(content) > MAX_UPLOAD_CHARS:
        raise HTTPException(413, "الملف أكبر من المسموح.")


def is_local(request: Request) -> bool:
    return TRUST_LOCALHOST and (request.client.host if request.client else "") in _LOCAL


def require_admin(request: Request) -> None:
    """تشغيل القياس مكلف: بالرمز إن ضُبط، وإلا من الجهاز نفسه فقط."""
    if ADMIN_TOKEN:
        sent = request.headers.get("X-Admin-Token", "")
        if not hmac.compare_digest(sent, ADMIN_TOKEN):
            raise HTTPException(403, "تشغيل القياس متاح للمشرف فقط.")
    elif not is_local(request):
        raise HTTPException(403, "تشغيل القياس متاح من جهاز الخادم فقط.")


# ---------- هوية مجهولة لكل متصفح (بلا تسجيل دخول) ----------
# رمز عشوائي في كوكي HttpOnly؛ القاعدة تحفظ بصمته (sha256) لا الرمز نفسه.
COOKIE_NAME = "mw_id"
COOKIE_MAX_AGE = 365 * 24 * 3600
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "auto")  # auto = Secure عند HTTPS
_TOKEN_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def new_token() -> str:
    return secrets.token_urlsafe(32)


def valid_token(token: str | None) -> bool:
    return bool(token) and 32 <= len(token) <= 64 and set(token) <= _TOKEN_CHARS


def owner_of(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def cookie_secure(request: Request) -> bool:
    if COOKIE_SECURE in ("0", "1"):
        return COOKIE_SECURE == "1"
    return request.url.scheme == "https"


# ---------- مفتاح النموذج: كل زائر بمفتاحه ----------
# مفتاح الزائر يصل في ترويسة لكل طلب، ويُستخدم لذلك الطلب فقط: لا يُحفظ ولا يُسجَّل.
# مفتاح الخادم (LLM_API_KEY) لا يُستخدم للزوار إلا حسب SERVER_KEY_FOR:
#   local (الافتراضي) = لجهاز الخادم فقط · all = للجميع · none = لا أحد
KEY_HEADER = "X-LLM-Key"
SERVER_KEY_FOR = os.getenv("SERVER_KEY_FOR", "local")


def user_key(request: Request) -> str | None:
    key = request.headers.get(KEY_HEADER, "").strip()
    if not key:
        return None
    if not (key.startswith("sk-") and 20 <= len(key) <= 300 and key.isascii() and " " not in key):
        raise HTTPException(400, "صيغة مفتاح OpenAI غير صحيحة.")
    if not (request.url.scheme == "https" or is_local(request)):
        raise HTTPException(400, "لحماية مفتاحك، يُقبل عبر اتصال آمن (HTTPS) فقط.")
    return key


def server_key_allowed(request: Request) -> bool:
    if not config.LLM_API_KEY:
        return False
    return SERVER_KEY_FOR == "all" or (SERVER_KEY_FOR == "local" and is_local(request))


def resolve_key(request: Request) -> tuple[str | None, bool]:
    """(المفتاح المستخدم لهذا الطلب، هل هو مفتاح الخادم)."""
    key = user_key(request)
    if key:
        return key, False
    if server_key_allowed(request):
        return config.LLM_API_KEY, True
    return None, False
