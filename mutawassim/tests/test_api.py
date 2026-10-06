"""Website API: every number shown on the site comes from these endpoints."""
import pytest
from fastapi.testclient import TestClient

from mutawassim.api import main


@pytest.fixture
def client():
    return TestClient(main.app)


def test_site_and_legacy_endpoints_are_served(client):
    assert "<div id=\"root\">" in client.get("/").text
    assert client.get("/fonts/Tajawal-Regular.ttf").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}


def test_info_reports_mock_mode(client):
    info = client.get("/api/info").json()
    assert info["mode"]["mock_mode"] is True
    assert {d["key"] for d in info["demos"]} == {"formal", "colloquial"}


def test_unknown_demo_is_404(client):
    assert client.get("/api/demo/nope").status_code == 404


def test_analyze_summary_matches_items(client):
    posts = client.get("/api/demo/formal").json()
    data = client.post("/api/analyze", json={"posts": posts}).json()
    items, summary = data["items"], data["summary"]
    assert summary["posts_in"] == len(posts)
    assert summary["total_claims"] == len(items)
    assert sum(s["count"] for s in summary["by_status"]) == len(items)
    assert summary["referrals"] == sum(i["action"] == "إحالة لمختص" for i in items)
    assert [i["risk"] for i in items] == sorted((i["risk"] for i in items), reverse=True)
    for i in items:
        f = i["factors"]
        assert round(f["spread"] * f["severity"] * f["sensitivity"], 4) == i["risk"]


def test_report_returns_pdf(client):
    posts = client.get("/api/demo/colloquial").json()
    items = client.post("/api/analyze", json={"posts": posts}).json()["items"]
    r = client.post("/api/report", json={"items": items})
    assert r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF")


@pytest.mark.parametrize("filename, content, texts", [
    ("a.json", '[{"post_id": "p1", "text": "حديث"}]', ["حديث"]),
    ("a.csv", "text\nحديث أول\n\nحديث ثان\n", ["حديث أول", "حديث ثان"]),
    ("a.md", '1. "منشور"\n', ["منشور"]),
])
def test_parse_upload_formats(client, filename, content, texts):
    posts = client.post("/api/parse", json={"filename": filename, "content": content}).json()
    assert [p["text"] for p in posts] == texts


def test_parse_rejects_broken_file(client):
    assert client.post("/api/parse", json={"filename": "a.json", "content": "{"}).status_code == 400


def test_sources_overview_counts(client):
    s = client.get("/api/sources").json()
    assert s["total"] == len(s["items"]) == sum(x["count"] for x in s["by_status"])


def test_evaluation_is_saved_and_reloaded(client):
    r = client.post("/api/evaluation", json={"kind": "extraction"}).json()
    assert "claim_f1" in r and r["model"] is None
    assert client.get("/api/evaluation").json()["results"]["extraction"]["claim_f1"] == r["claim_f1"]
    assert client.post("/api/evaluation", json={"kind": "other"}).status_code == 400


@pytest.mark.parametrize("path", ["/", "/performance", "/history", "/sources"])
def test_every_page_has_its_own_link(path):
    r = TestClient(main.app).get(path)
    assert r.status_code == 200 and "/app.js" in r.text
