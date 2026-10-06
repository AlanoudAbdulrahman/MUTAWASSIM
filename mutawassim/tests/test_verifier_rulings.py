"""Every ruling written in the sources file must map to a verdict."""
import json

import pytest

from mutawassim import config
from mutawassim.verification.verifier import _status_from_ruling

SOURCES = json.loads(config.SOURCES_FILE.read_text(encoding="utf-8"))


def test_every_source_ruling_maps_to_a_status():
    unmapped = sorted({d["ruling"] for d in SOURCES if d.get("ruling") and not _status_from_ruling(d["ruling"])})
    assert unmapped == [], f"rulings with no verdict: {unmapped}"


@pytest.mark.parametrize("ruling, status", [
    ("نص قرآني (سورة الفاتحة)", "confirmed"),
    ("ليس بحديث (مقولة لأبي علي الدقاق)", "fabricated"),
    ("ليس بحديث بل قاعدة فقهية", "fabricated"),
    ("لا أصل له (موضوع)", "fabricated"),
    ("موضوع بهذا اللفظ", "fabricated"),
    ("ضعيف جدا", "weak"),
    ("صحيح", "confirmed"),
])
def test_ruling_examples(ruling, status):
    assert _status_from_ruling(ruling) == status
