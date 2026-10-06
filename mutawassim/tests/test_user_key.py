"""Bring-your-own-key: public visitors pay with their own key; the server key stays private."""
import pytest
from fastapi.testclient import TestClient

from mutawassim import benchmark, config, llm
from mutawassim.api import main, security
from mutawassim.retrieval import retriever

USER_KEY = "sk-visitor-" + "a" * 30
SERVER_KEY = "sk-server-" + "b" * 30
POSTS = {"posts": [{"post_id": "p1", "text": "حديث حب الوطن من الإيمان"}]}


class _FakeOpenAI:
    """Records which key each model call used; returns harmless canned replies."""
    def __init__(self, seen):
        self.seen = seen
        self.chat = type("C", (), {"completions": type("X", (), {"create": self._chat})()})()
        self.embeddings = type("E", (), {"create": self._embed})()

    def _chat(self, **_):
        self.seen.append(llm.current_key())
        msg = type("M", (), {"content": '{"status": "needs_review", "confidence": 0}'})()
        return type("R", (), {"choices": [type("Ch", (), {"message": msg})()]})()

    def _embed(self, input, **_):
        self.seen.append(llm.current_key())
        return type("R", (), {"data": [type("D", (), {"embedding": [1.0, 0.0]})() for _ in input]})()


@pytest.fixture
def real_mode(monkeypatch):
    seen = []
    monkeypatch.setattr(config, "MOCK_MODE", False)
    monkeypatch.setattr(config, "LLM_API_KEY", SERVER_KEY)
    monkeypatch.setattr(config, "USE_LLM_EXTRACT", True)
    monkeypatch.setattr(config, "EMBED_PROVIDER", "openai")
    monkeypatch.setattr(llm, "openai_client", lambda: _FakeOpenAI(seen))
    monkeypatch.setattr(retriever, "_DOCS", None)
    monkeypatch.setattr(retriever, "_VECS", None)
    return seen


def _remote(https=True):
    return TestClient(main.app, base_url="https://testserver" if https else "http://testserver",
                      client=("203.0.113.9", 5000))


def test_public_visitor_without_key_is_asked_for_one(real_mode):
    r = _remote().post("/api/analyze", json=POSTS)
    assert r.status_code == 401 and "مفتاح" in r.json()["detail"]
    assert real_mode == []  # the server key was never used
    assert _remote().get("/api/info").json()["mode"]["needs_user_key"] is True


def test_public_visitor_pays_with_their_own_key(real_mode):
    r = _remote().post("/api/analyze", json=POSTS, headers={"X-LLM-Key": USER_KEY})
    assert r.status_code == 200
    assert real_mode and set(real_mode) == {USER_KEY}
    assert USER_KEY not in r.text
    assert USER_KEY not in config.DB_FILE.read_bytes().decode("utf-8", "ignore")
    assert llm.current_key() == SERVER_KEY  # request key does not leak into later code


def test_key_is_refused_over_plain_http_from_the_internet(real_mode):
    r = _remote(https=False).post("/api/analyze", json=POSTS, headers={"X-LLM-Key": USER_KEY})
    assert r.status_code == 400 and "HTTPS" in r.json()["detail"]
    assert real_mode == []


def test_malformed_key_is_rejected(real_mode):
    r = _remote().post("/api/analyze", json=POSTS, headers={"X-LLM-Key": "not-a-key"})
    assert r.status_code == 400


def test_owner_on_localhost_uses_the_server_key(real_mode):
    local = TestClient(main.app)
    assert local.get("/api/info").json()["mode"]["needs_user_key"] is False
    assert local.post("/api/analyze", json=POSTS).status_code == 200
    assert set(real_mode) == {SERVER_KEY}


def test_server_key_for_all_when_configured(real_mode, monkeypatch):
    monkeypatch.setattr(security, "SERVER_KEY_FOR", "all")
    assert _remote().post("/api/analyze", json=POSTS).status_code == 200
    assert set(real_mode) == {SERVER_KEY}


def test_server_key_for_none_even_locally(real_mode, monkeypatch):
    monkeypatch.setattr(security, "SERVER_KEY_FOR", "none")
    assert TestClient(main.app).post("/api/analyze", json=POSTS).status_code == 401


def test_internet_visitors_never_trigger_the_paid_auto_benchmark(monkeypatch):
    calls = []
    monkeypatch.setattr(benchmark, "ensure_fresh", lambda: calls.append(1))
    _remote().get("/api/info")
    _remote().get("/api/evaluation")
    assert calls == []
    TestClient(main.app).get("/api/info")
    assert calls == [1]


def test_failed_source_embedding_does_not_leave_a_broken_index(real_mode, monkeypatch):
    def boom(*_, **__):
        raise RuntimeError("bad key")

    monkeypatch.setattr(retriever, "embed", boom)
    with pytest.raises(RuntimeError):
        retriever.build_index()
    assert retriever._DOCS is None  # the next request retries instead of searching without vectors


def test_untrusted_localhost_gets_no_server_privileges(real_mode, monkeypatch):
    # behind a reverse proxy every visitor looks like 127.0.0.1
    monkeypatch.setattr(security, "TRUST_LOCALHOST", False)
    local = TestClient(main.app)
    assert local.post("/api/analyze", json=POSTS).status_code == 401
    assert local.post("/api/evaluation", json={"kind": "extraction"}).status_code == 403
    assert local.get("/api/info").json()["mode"]["needs_user_key"] is True


def test_wrong_key_gets_a_clear_message_and_nothing_is_saved(real_mode, monkeypatch):
    class AuthenticationError(Exception):
        pass

    def reject(*_, **__):
        raise AuthenticationError()

    monkeypatch.setattr(llm, "openai_client", reject)
    c = _remote()
    r = c.post("/api/analyze", json=POSTS, headers={"X-LLM-Key": USER_KEY})
    assert r.status_code == 401 and "المفتاح غير صحيح" in r.json()["detail"]
    assert c.get("/api/history").json() == []
