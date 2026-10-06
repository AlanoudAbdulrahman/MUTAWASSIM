"""
llm.py — غلاف بسيط للنموذج اللغوي.

في MOCK_MODE لا يُستدعى مزود خارجي. عند التفعيل الحقيقي، عبّوا الدالة
_real_chat حسب مزودكم (OpenAI/غيره). الباقي من الكود لا يتغيّر.

المفتاح: لكل طلب مفتاحه. الموقع العام يمرّر مفتاح الزائر نفسه عبر using_key()
فلا يُستهلك رصيد صاحب الخادم؛ وخارج الطلبات (سطر الأوامر، القياس) يُستخدم
LLM_API_KEY من الإعدادات. المفتاح لا يُحفظ ولا يُكتب في أي سجل.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from . import config

_request_key: ContextVar[str | None] = ContextVar("llm_request_key", default=None)


@contextmanager
def using_key(key: str | None):
    """يجعل كل استدعاءات النموذج داخل الكتلة بهذا المفتاح (مفتاح الزائر)."""
    token = _request_key.set(key or "")
    try:
        yield
    finally:
        _request_key.reset(token)


def current_key() -> str:
    """مفتاح الطلب الحالي إن ضُبط (حتى لو فارغًا = لا مفتاح)، وإلا مفتاح الإعدادات."""
    key = _request_key.get()
    return config.LLM_API_KEY if key is None else key


def has_key() -> bool:
    return bool(current_key())


_clients: dict[str, Any] = {}
_MAX_CLIENTS = 64


def openai_client():
    """عميل OpenAI لمفتاح الطلب الحالي (مخزّن ببصمة المفتاح لا بالمفتاح نفسه)."""
    key = current_key()
    if not key:
        raise RuntimeError("لا يوجد مفتاح للنموذج")
    fp = hashlib.sha256(key.encode()).hexdigest()
    client = _clients.get(fp)
    if client is None:
        from openai import OpenAI
        if len(_clients) >= _MAX_CLIENTS:
            _clients.pop(next(iter(_clients)))
        client = _clients[fp] = OpenAI(api_key=key)
    return client


def chat_json(system: str, user: str) -> dict[str, Any]:
    """يرجّع ناتجًا بصيغة JSON (dict). في MOCK يرجّع {} فيعتمد النداء منطقه البديل."""
    if config.MOCK_MODE:
        return {}
    text = _real_chat(system, user)
    try:
        return json.loads(text)
    except Exception:
        # محاولة انتزاع كتلة JSON من النص
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start : end + 1])
        raise


def _real_chat(system: str, user: str) -> str:
    """تنفيذ OpenAI (الافتراضي). لمزود آخر: غيّروا هذه الدالة فقط.
    يتطلب: pip install openai + مفتاح (من الزائر أو LLM_API_KEY) + MOCK_MODE=0."""
    if config.LLM_PROVIDER != "openai":
        raise NotImplementedError(
            f"المزود {config.LLM_PROVIDER} غير مُفعّل — عدّلوا _real_chat في llm.py"
        )
    resp = openai_client().chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return resp.choices[0].message.content or "{}"
