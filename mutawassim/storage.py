"""
storage.py — حفظ عمليات التحقق (SQLite مدمجة في بايثون، بلا خادم).

كل دفعة مربوطة بمالكها (owner): هوية مجهولة لكل متصفح يصدرها الموقع
(api/security.py). كل استعلام هنا مقيّد بالمالك، فلا يرى زائرٌ سجلّ غيره:
- السجل وإحصائيات الاستخدام: لكل مالك على حدة.
- الانتشار عبر الزمن: من دفعات المالك نفسه.

ملف القاعدة: config.DB_FILE (غير مرفوع إلى git). تُنشأ الجداول وتُرقّى تلقائيًا.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    posts_in INTEGER NOT NULL,
    total_claims INTEGER NOT NULL,
    errors INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES batches(id) ON DELETE CASCADE,
    owner TEXT NOT NULL DEFAULT '',
    post_key TEXT NOT NULL,           -- batch_id:post_id (فريد عبر الدفعات)
    query_key TEXT NOT NULL,          -- صيغة البحث المطبّعة (لحساب الانتشار)
    status TEXT NOT NULL,
    action TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    risk REAL NOT NULL,
    data TEXT NOT NULL                -- عنصر العرض كاملًا (JSON)
);
"""
_INDEXES = """
CREATE INDEX IF NOT EXISTS ix_batches_owner ON batches(owner, id);
CREATE INDEX IF NOT EXISTS ix_claims_owner_query ON claims(owner, query_key);
CREATE INDEX IF NOT EXISTS ix_claims_batch ON claims(batch_id);
"""


def query_key(q: str) -> str:
    return " ".join((q or "").split())


def _connect() -> sqlite3.Connection:
    config.DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA)
    for table in ("batches", "claims"):  # ترقية قاعدة أُنشئت قبل إضافة المالك
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if "owner" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN owner TEXT NOT NULL DEFAULT ''")
    conn.executescript(_INDEXES)
    return conn


def history_post_counts(keys: set[str], owner: str) -> dict[str, int]:
    """لكل صيغة بحث: عدد المنشورات المختلفة التي ذكرتها في دفعات هذا المالك."""
    if not keys:
        return {}
    marks = ",".join("?" * len(keys))
    with closing(_connect()) as conn:
        rows = conn.execute(
            f"SELECT query_key, COUNT(DISTINCT post_key) AS n FROM claims "
            f"WHERE owner = ? AND query_key IN ({marks}) GROUP BY query_key",
            (owner, *keys)).fetchall()
    return {r["query_key"]: r["n"] for r in rows}


def save_batch(items: list[dict], posts_in: int, mode: str, owner: str, errors: int = 0) -> int:
    """يحفظ دفعة؛ items بصيغة العرض (serialize.item_to_json)."""
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "INSERT INTO batches (owner, created_at, mode, posts_in, total_claims, errors) VALUES (?,?,?,?,?,?)",
            (owner, datetime.now().isoformat(timespec="seconds"), mode, posts_in, len(items), errors))
        batch_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO claims (batch_id, owner, post_key, query_key, status, action, claim_type, risk, data) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            [(batch_id, owner, f"{batch_id}:{i['post_id']}", i["query_key"], i["status"], i["action"],
              i["claim_type"], i["risk"], json.dumps(i, ensure_ascii=False)) for i in items])
    return batch_id


def list_batches(owner: str, limit: int = 50) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT b.id, b.created_at, b.mode, b.posts_in, b.total_claims, b.errors, "
            " SUM(c.status IN ('fabricated','weak')) AS misleading, "
            " SUM(c.action = 'إحالة لمختص') AS referrals, MAX(c.risk) AS max_risk "
            "FROM batches b LEFT JOIN claims c ON c.batch_id = b.id "
            "WHERE b.owner = ? GROUP BY b.id ORDER BY b.id DESC LIMIT ?", (owner, limit)).fetchall()
    return [{k: r[k] for k in r.keys()} | {"misleading": r["misleading"] or 0,
                                           "referrals": r["referrals"] or 0,
                                           "max_risk": r["max_risk"] or 0.0} for r in rows]


def get_batch(batch_id: int, owner: str) -> dict | None:
    with closing(_connect()) as conn:
        b = conn.execute("SELECT id, created_at, mode, posts_in, total_claims, errors FROM batches "
                         "WHERE id = ? AND owner = ?", (batch_id, owner)).fetchone()
        if not b:
            return None
        rows = conn.execute("SELECT data FROM claims WHERE batch_id = ? ORDER BY risk DESC, id",
                            (batch_id,)).fetchall()
    return {"batch": dict(b), "items": [json.loads(r["data"]) for r in rows]}


def delete_batch(batch_id: int, owner: str) -> bool:
    with closing(_connect()) as conn, conn:
        return conn.execute("DELETE FROM batches WHERE id = ? AND owner = ?",
                            (batch_id, owner)).rowcount > 0


def usage_stats(owner: str, top: int = 8) -> dict:
    """إحصائيات كل ما فحصه هذا المالك."""
    with closing(_connect()) as conn:
        totals = conn.execute(
            "SELECT COUNT(*) AS batches, COALESCE(SUM(posts_in),0) AS posts, "
            "COALESCE(SUM(total_claims),0) AS claims FROM batches WHERE owner = ?", (owner,)).fetchone()
        by_status = Counter({r["status"]: r["n"] for r in conn.execute(
            "SELECT status, COUNT(*) AS n FROM claims WHERE owner = ? GROUP BY status", (owner,))})
        referrals = conn.execute("SELECT COUNT(*) FROM claims WHERE owner = ? AND action = 'إحالة لمختص'",
                                 (owner,)).fetchone()[0]
        recurring = conn.execute(
            "SELECT query_key, COUNT(DISTINCT post_key) AS posts, MAX(data) AS data FROM claims "
            "WHERE owner = ? AND status IN ('fabricated','weak') GROUP BY query_key "
            "ORDER BY posts DESC, MAX(risk) DESC LIMIT ?", (owner, top)).fetchall()
    return {
        "batches": totals["batches"], "posts": totals["posts"], "claims": totals["claims"],
        "by_status": dict(by_status), "referrals": referrals,
        "top_misleading": [
            {"posts": r["posts"], "claim_text": json.loads(r["data"])["claim_text"],
             "status": json.loads(r["data"])["status"]} for r in recurring],
    }


def claim_legacy(owner: str) -> int:
    """يُسند الدفعات المحفوظة قبل إضافة الهويات (بلا مالك) إلى هذا المالك. للجهاز المحلي فقط."""
    with closing(_connect()) as conn, conn:
        n = conn.execute("UPDATE batches SET owner = ? WHERE owner = ''", (owner,)).rowcount
        conn.execute("UPDATE claims SET owner = ? WHERE owner = ''", (owner,))
    return n
