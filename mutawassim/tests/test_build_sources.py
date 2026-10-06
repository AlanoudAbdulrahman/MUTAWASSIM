"""build_sources must never silently wipe sources added directly to sources.json."""
import json

import pytest

from mutawassim.retrieval.build_sources import build_sources

HEADER = "id,text,url,ruling,source,type\n"


def _write(tmp_path, csv_rows, existing):
    seed = tmp_path / "seed.csv"
    seed.write_text(HEADER + "".join(csv_rows), encoding="utf-8")
    out = tmp_path / "sources.json"
    out.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
    return seed, out


def test_refuses_to_drop_existing_sources(tmp_path):
    seed, out = _write(tmp_path, ["s1,نص أول,u,صحيح,dorar.net/hadith,hadith\n"],
                       [{"text": "نص أول"}, {"text": "نص أضيف مباشرة"}])
    with pytest.raises(RuntimeError, match="ستمسح 1"):
        build_sources(seed, out)
    assert len(json.loads(out.read_text(encoding="utf-8"))) == 2  # untouched


def test_force_overwrites(tmp_path):
    seed, out = _write(tmp_path, ["s1,نص أول,u,صحيح,dorar.net/hadith,hadith\n"],
                       [{"text": "نص أول"}, {"text": "نص أضيف مباشرة"}])
    assert build_sources(seed, out, force=True) == 1


def test_superset_csv_is_allowed(tmp_path):
    seed, out = _write(tmp_path, ["s1,نص أول,u,صحيح,dorar.net/hadith,hadith\n",
                                  "s2,نص ثان,u,ضعيف,dorar.net/hadith,hadith\n"],
                       [{"text": "نص أول"}])
    assert build_sources(seed, out) == 2
