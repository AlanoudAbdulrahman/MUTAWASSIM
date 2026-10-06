"""Limits and protections that keep the paid model from being drained."""
import pytest
from fastapi.testclient import TestClient

from mutawassim.api import main, security


@pytest.fixture
def client():
    return TestClient(main.app)


def _posts(n, text="حديث النظافة من الإيمان"):
    return {"posts": [{"post_id": f"p{i}", "text": text} for i in range(n)]}


def test_security_headers_on_site_and_api(client):
    for path in ("/", "/api/info"):
        h = client.get(path).headers
        assert h["X-Frame-Options"] == "DENY" and h["X-Content-Type-Options"] == "nosniff"
        assert "default-src 'self'" in h["Content-Security-Policy"]


@pytest.mark.parametrize("path", ["/api/analyze", "/verify"])
def test_batch_size_is_limited(client, path):
    assert client.post(path, json=_posts(security.MAX_POSTS + 1)).status_code == 413


def test_post_length_is_limited(client):
    body = _posts(1, "ح" * (security.MAX_POST_CHARS + 1))
    assert client.post("/api/analyze", json=body).status_code == 413


def test_empty_batch_is_rejected(client):
    assert client.post("/api/analyze", json={"posts": []}).status_code == 400


def test_upload_size_is_limited(client):
    big = "x" * (security.MAX_UPLOAD_CHARS + 1)
    assert client.post("/api/parse", json={"filename": "a.csv", "content": big}).status_code == 413


def test_evaluation_run_is_local_only_without_token():
    remote = TestClient(main.app, client=("203.0.113.9", 5000))
    assert remote.post("/api/evaluation", json={"kind": "extraction"}).status_code == 403
    assert remote.get("/api/evaluation").status_code == 200  # reading saved results stays public


def test_evaluation_run_requires_token_when_configured(client, monkeypatch):
    monkeypatch.setattr(security, "ADMIN_TOKEN", "s3cret")
    assert client.post("/api/evaluation", json={"kind": "extraction"}).status_code == 403
    ok = client.post("/api/evaluation", json={"kind": "extraction"}, headers={"X-Admin-Token": "s3cret"})
    assert ok.status_code == 200


def test_pipeline_errors_do_not_leak_details(client, monkeypatch):
    def boom(_):
        raise RuntimeError("secret internal detail sk-proj-123")

    monkeypatch.setattr(main, "process_batch", lambda *a, **k: boom(a))
    r = client.post("/api/analyze", json=_posts(1))
    assert r.status_code == 502 and "sk-proj" not in r.text and "secret" not in r.text


def test_unknown_report_theme_is_rejected(client):
    assert client.post("/api/report", json={"items": [], "theme": "../x"}).status_code == 400
