"""
llm.py — غلاف بسيط للنموذج اللغوي.

في MOCK_MODE لا يُستدعى مزود خارجي. عند التفعيل الحقيقي، عبّوا الدالة
_real_chat حسب مزودكم (OpenAI/غيره). الباقي من الكود لا يتغيّر.
"""
from __future__ import annotations

import json
from typing import Any

from . import config


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
    """TODO: صِلوها بمزودكم. مثال OpenAI:

    from openai import OpenAI
    client = OpenAI(api_key=config.LLM_API_KEY)
    resp = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return resp.choices[0].message.content
    """
    raise NotImplementedError(
        "فعّلوا _real_chat في llm.py واضبطوا MOCK_MODE=0 في .env"
    )
