"""Tests never call a paid model and never touch the real history or saved results."""
import pytest

from mutawassim import benchmark, config


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "MOCK_MODE", True)
    monkeypatch.setattr(config, "AUTO_EVALUATE", False)
    monkeypatch.setattr(config, "DB_FILE", tmp_path / "history.db")
    monkeypatch.setattr(benchmark, "CACHE", tmp_path / "last_evaluation.json")
