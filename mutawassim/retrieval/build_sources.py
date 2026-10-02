"""
build_sources.py — يبني data/sources/sources.json من ملف CSV منسّق يدويًا.
المالك: سارة (البيانات).

الخطوات:
1. املؤوا data/sources/sources_seed.csv بالأعمدة: id,text,url,ruling,source,type
   (انسخوا النص والحكم والرابط الدقيق من دُرر السنية لكل حديث/أثر).
2. شغّلوا:  python -m mutawassim.retrieval.build_sources
3. يُنشأ data/sources/sources.json ويستخدمه النظام تلقائيًا.

ملاحظة: الأحكام والروابط يجب أن تكون صحيحة ومن المصادر المعتمدة فقط.
"""
from __future__ import annotations

import csv
import json
import pathlib

from .. import config

SEED_CSV = config.DATA_DIR / "sources" / "sources_seed.csv"
OUT_JSON = config.SOURCES_FILE  # data/sources/sources.json

_REQUIRED = ("id", "text", "url", "ruling", "source", "type")


def build_sources(seed_csv: pathlib.Path | None = None) -> int:
    """يحوّل CSV البذرة إلى sources.json. يرجّع عدد السجلات."""
    seed_csv = seed_csv or SEED_CSV
    if not seed_csv.exists():
        raise FileNotFoundError(f"لم يوجد ملف البذرة: {seed_csv}")

    rows: list[dict] = []
    with open(seed_csv, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in _REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"أعمدة ناقصة في CSV: {missing}")
        for i, r in enumerate(reader):
            text = (r.get("text") or "").strip()
            if not text:
                continue  # تجاهل الصفوف الفارغة
            rows.append({
                "id": (r.get("id") or f"s{i:04d}").strip(),
                "text": text,
                "url": (r.get("url") or "").strip(),
                "ruling": (r.get("ruling") or "").strip() or None,
                "source": (r.get("source") or "").strip(),
                "type": (r.get("type") or "hadith").strip(),
            })

    OUT_JSON.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return len(rows)


if __name__ == "__main__":
    n = build_sources()
    print(f"تم بناء {n} مصدرًا -> {OUT_JSON}")
