"""Cleaning: duplicates removed, post ids kept unique."""
from mutawassim.ingestion.cleaner import clean_posts


def test_duplicate_post_ids_are_made_unique():
    posts = clean_posts([{"post_id": "p1", "text": "حديث أول"},
                         {"post_id": "p1", "text": "حديث ثان"},
                         {"post_id": "p1", "text": "حديث ثالث"}])
    assert [p.post_id for p in posts] == ["p1", "p1_2", "p1_3"]


def test_duplicate_text_is_dropped_and_tatweel_removed():
    posts = clean_posts([{"post_id": "a", "text": "النبـــي  قال"},
                         {"post_id": "b", "text": "النبي قال"}])
    assert [(p.post_id, p.text) for p in posts] == [("a", "النبي قال")]


def test_missing_id_and_empty_text():
    posts = clean_posts([{"text": "   "}, {"text": "حديث"}])
    assert [p.post_id for p in posts] == ["p0001"]
