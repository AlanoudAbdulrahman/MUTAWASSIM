"""
benchmark.py — قياس الأداء التلقائي على مجموعات الاختبار.

بصمة (fingerprint) لكل ما يؤثر في النتائج: كود المسار، والمصادر، ومجموعات
الاختبار، والإعدادات (الوضع والنموذج والعتبات). إذا تغيّرت البصمة عن آخر قياس
محفوظ يُعاد القياس تلقائيًا في الخلفية، فتبقى الأرقام مطابقة لآخر نسخة من الكود.
النتائج تُحفظ لكل وضع على حدة (حقيقي/تجريبي) حتى لا يمسح أحدهما الآخر.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime

from . import config

log = logging.getLogger("mutawassim.benchmark")

KINDS = ("verification", "extraction")
CACHE = config.DATA_DIR / "cleaned" / "last_evaluation.json"

# ما يغيّر الأرقام إذا تغيّر (الموقع والـ API والاختبارات لا تغيّرها)
_CODE_DIRS = ("extraction", "ingestion", "retrieval", "verification", "scoring", "reporting", "evaluation")
_CODE_FILES = ("pipeline.py", "llm.py", "schemas.py", "config.py")
_DATA_FILES = ("sources/sources.json", "test_set/test_set.json", "test_set/extraction.sample.json")

_state = {"running": False, "error": None, "failed_fp": None}
_lock = threading.Lock()


def mode_key() -> str:
    return "mock" if config.MOCK_MODE or not config.LLM_API_KEY else "real"


def fingerprint() -> str:
    h = hashlib.sha256()
    root = config.ROOT
    files = [root / f for f in _CODE_FILES]
    for d in _CODE_DIRS:
        files += sorted((root / d).rglob("*.py"))
    files += [config.DATA_DIR / f for f in _DATA_FILES]
    for f in files:
        if f.exists():
            h.update(str(f.relative_to(root)).encode())
            h.update(f.read_bytes())
    settings = {k: getattr(config, k, None) for k in (
        "MOCK_MODE", "LLM_MODEL", "USE_LLM_EXTRACT", "EMBED_PROVIDER", "OPENAI_EMBED_MODEL",
        "RETRIEVE_K", "MIN_CONFIDENCE", "MIN_SIM", "MIN_SIM_OPENAI", "MIN_COVERAGE")}
    settings["has_key"] = bool(config.LLM_API_KEY)
    h.update(json.dumps(settings, sort_keys=True).encode())
    return h.hexdigest()[:16]


def _load() -> dict:
    if not CACHE.exists():
        return {}
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    if any(k in data for k in KINDS):  # صيغة قديمة بلا بصمة: تُعاد القياس
        return {}
    return data


def _save(kind: str, metrics: dict, fp: str) -> dict:
    data = _load()
    entry = {**metrics, "ran_at": datetime.now().isoformat(timespec="minutes"), "fingerprint": fp,
             "model": config.LLM_MODEL if mode_key() == "real" else None}
    data.setdefault(mode_key(), {})[kind] = entry
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry


def run(kind: str) -> dict:
    """قياس واحد الآن (متزامن) وحفظه."""
    if kind == "verification":
        from .evaluation.evaluate import evaluate as fn
    elif kind == "extraction":
        from .evaluation.evaluate_extraction import evaluate_extraction as fn
    else:
        raise ValueError(kind)
    return _save(kind, fn(), fingerprint())


def status() -> dict:
    fp = fingerprint()
    results = _load().get(mode_key(), {})
    stale = [k for k in KINDS if results.get(k, {}).get("fingerprint") != fp]
    return {"mode": mode_key(), "results": results, "stale": stale,
            "running": _state["running"], "error": _state["error"], "auto": config.AUTO_EVALUATE}


def _worker(kinds: list[str], fp: str) -> None:
    try:
        for k in kinds:
            run(k)
        _state["error"] = _state["failed_fp"] = None
    except Exception as e:
        log.exception("auto evaluation failed")
        # لا إعادة محاولة تلقائية لنفس البصمة (تفاديًا لاستهلاك متكرر)، حتى يتغيّر الكود
        _state["error"], _state["failed_fp"] = type(e).__name__, fp
    finally:
        _state["running"] = False


def ensure_fresh() -> bool:
    """يبدأ قياسًا في الخلفية إذا تغيّرت البصمة. يرجّع True إذا بدأ (أو كان يعمل)."""
    if not config.AUTO_EVALUATE:
        return _state["running"]
    with _lock:
        if _state["running"]:
            return True
        fp = fingerprint()
        stale = status()["stale"]
        if not stale or _state["failed_fp"] == fp:
            return False
        _state["running"] = True
    threading.Thread(target=_worker, args=(stale, fp), daemon=True, name="auto-evaluate").start()
    return True
