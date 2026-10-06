"""Integrated pipeline: saved history, spread across batches, fault tolerance, auto benchmark."""
import time

import pytest
from fastapi.testclient import TestClient

from mutawassim import benchmark, config, pipeline, storage
from mutawassim.api import main

ME, OTHER = "owner-me", "owner-other"
POSTS = [{"post_id": "p1", "text": "حديث حب الوطن من الإيمان"},
         {"post_id": "p2", "text": "قال النبي إنما الأعمال بالنيات"}]


def _risk_of(batch, text):
    return next(i.card.risk for i in batch.items if text in i.claim.text)


# ---------- الحفظ والانتشار عبر الزمن ----------
def test_batches_are_saved_and_listed():
    b1 = pipeline.process_batch(POSTS, owner=ME)
    b2 = pipeline.process_batch(POSTS[:1], owner=ME)
    listed = storage.list_batches(ME)
    assert [b["id"] for b in listed] == [b2.batch_id, b1.batch_id]
    assert listed[1]["posts_in"] == 2 and listed[1]["total_claims"] == len(b1.items)
    assert storage.get_batch(b1.batch_id, ME)["items"][0]["claim_text"]


def test_spread_grows_when_the_same_claim_returns_in_later_batches():
    first = _risk_of(pipeline.process_batch(POSTS[:1], owner=ME), "حب الوطن")
    second = _risk_of(pipeline.process_batch([{"post_id": "x9", "text": "حديث حب الوطن من الإيمان"}], owner=ME), "حب الوطن")
    assert second > first > 0


def test_run_pipeline_does_not_read_or_write_history():
    pipeline.process_batch(POSTS, owner=ME)
    before = storage.list_batches(ME)
    pipeline.run_pipeline(POSTS)
    assert storage.list_batches(ME) == before


def test_delete_batch_and_usage_stats():
    b = pipeline.process_batch(POSTS, owner=ME)
    u = storage.usage_stats(ME)
    assert u["batches"] == 1 and u["posts"] == 2 and u["claims"] == len(b.items)
    assert storage.delete_batch(b.batch_id, ME) and storage.usage_stats(ME)["claims"] == 0
    assert not storage.delete_batch(b.batch_id, ME)


# ---------- المتانة ----------
def test_one_failing_post_does_not_stop_the_batch(monkeypatch):
    real = pipeline.extract_claims

    def flaky(post):
        if post.post_id == "p1":
            raise RuntimeError("provider down")
        return real(post)

    monkeypatch.setattr(pipeline, "extract_claims", flaky)
    batch = pipeline.process_batch(POSTS, owner=ME)
    assert {i.post.post_id for i in batch.items} == {"p2"}
    assert batch.errors == [{"post_id": "p1", "stage": "extraction", "message": "RuntimeError"}]


def test_failed_verification_is_referred_not_dropped(monkeypatch):
    def broken(claim):
        raise TimeoutError()

    monkeypatch.setattr(pipeline, "verify", broken)
    batch = pipeline.process_batch(POSTS[:1], owner=ME)
    assert batch.items and all(i.card.action == "إحالة لمختص" for i in batch.items)
    assert batch.errors[0]["stage"] == "verification"


# ---------- الخصوصية: كل زائر يرى بياناته فقط ----------
def test_spread_history_is_per_owner():
    pipeline.process_batch(POSTS[:1], owner=OTHER)
    pipeline.process_batch(POSTS[:1], owner=OTHER)
    mine = _risk_of(pipeline.process_batch(POSTS[:1], owner=ME), "حب الوطن")
    fresh = _risk_of(pipeline.process_batch(POSTS[:1], owner="someone-new"), "حب الوطن")
    assert mine == fresh  # other people's posts do not raise my spread


def test_each_browser_sees_only_its_own_history():
    alice, bob = TestClient(main.app), TestClient(main.app)
    r = alice.post("/api/analyze", json={"posts": POSTS}).json()
    assert r["batch_id"] and r["errors"] == []
    assert [b["id"] for b in alice.get("/api/history").json()] == [r["batch_id"]]
    assert alice.get("/api/usage").json()["posts"] == 2

    assert bob.get("/api/history").json() == []
    assert bob.get("/api/usage").json()["posts"] == 0
    assert bob.get(f"/api/history/{r['batch_id']}").status_code == 404
    assert bob.delete(f"/api/history/{r['batch_id']}").status_code == 404

    detail = alice.get(f"/api/history/{r['batch_id']}").json()
    assert detail["summary"]["total_claims"] == len(r["items"])
    assert alice.delete(f"/api/history/{r['batch_id']}").json() == {"deleted": r["batch_id"]}
    assert alice.get("/api/history").json() == []


def test_identity_cookie_is_httponly_and_not_stored_raw():
    c = TestClient(main.app)
    set_cookie = c.get("/api/info").headers["set-cookie"]
    assert "mw_id=" in set_cookie and "HttpOnly" in set_cookie and "SameSite=lax" in set_cookie
    token = c.cookies.get("mw_id")
    c.post("/api/analyze", json={"posts": POSTS})
    assert token not in config.DB_FILE.read_bytes().decode("utf-8", "ignore")
    assert "set-cookie" not in c.get("/api/info").headers  # issued once, then reused


def test_forged_cookie_gets_a_fresh_identity():
    c = TestClient(main.app, cookies={"mw_id": "short"})
    assert "mw_id=" in c.get("/api/info").headers["set-cookie"]


def test_legacy_batches_are_claimed_only_from_the_local_machine():
    storage.save_batch([], posts_in=1, mode="mock", owner="")
    remote = TestClient(main.app, client=("203.0.113.9", 5000))
    assert remote.get("/api/history").json() == []
    local = TestClient(main.app)
    assert len(local.get("/api/history").json()) == 1
    assert remote.get("/api/history").json() == []


# ---------- القياس التلقائي ----------
def test_fingerprint_changes_with_settings(monkeypatch):
    fp = benchmark.fingerprint()
    monkeypatch.setattr(config, "MIN_COVERAGE", 0.7)
    assert benchmark.fingerprint() != fp


def test_results_go_stale_when_code_or_settings_change(monkeypatch):
    assert benchmark.status()["stale"] == list(benchmark.KINDS)
    benchmark.run("extraction")
    assert benchmark.status()["stale"] == ["verification"]
    monkeypatch.setattr(config, "RETRIEVE_K", 7)
    assert set(benchmark.status()["stale"]) == set(benchmark.KINDS)


def _wait_idle():
    for _ in range(200):
        if not benchmark._state["running"]:
            return
        time.sleep(0.02)


def test_auto_evaluation_runs_in_background_when_stale(monkeypatch):
    calls = []
    monkeypatch.setattr(config, "AUTO_EVALUATE", True)
    monkeypatch.setattr(benchmark, "run", lambda kind: calls.append(kind))
    monkeypatch.setitem(benchmark._state, "failed_fp", None)
    assert benchmark.ensure_fresh() is True
    _wait_idle()
    assert calls == list(benchmark.KINDS)


def test_failed_auto_evaluation_is_not_retried_for_the_same_code(monkeypatch):
    calls = []

    def boom(kind):
        calls.append(kind)
        raise RuntimeError("bad key")

    monkeypatch.setattr(config, "AUTO_EVALUATE", True)
    monkeypatch.setattr(benchmark, "run", boom)
    monkeypatch.setitem(benchmark._state, "failed_fp", None)
    benchmark.ensure_fresh(); _wait_idle()
    assert benchmark.ensure_fresh() is False and calls == ["verification"]
    assert benchmark.status()["error"] == "RuntimeError"
    monkeypatch.setitem(benchmark._state, "error", None)


@pytest.mark.parametrize("auto", [False])
def test_auto_evaluation_can_be_disabled(monkeypatch, auto):
    monkeypatch.setattr(config, "AUTO_EVALUATE", auto)
    assert benchmark.ensure_fresh() is False
