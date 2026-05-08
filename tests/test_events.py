from src.events import Event


def test_dedup_key():
    e = Event(source="trending_models", event_id="meta-llama/Llama-3-8B", title="x", url="x")
    assert e.dedup_key == "trending_models::meta-llama/Llama-3-8B"


def test_round_trip():
    e = Event(
        source="daily_papers",
        event_id="2401.12345",
        title="A Paper",
        url="https://example",
        likes=42,
        tags=["nlp", "evals"],
        extra={"arxiv_id": "2401.12345"},
    )
    d = e.to_dict()
    back = Event.from_dict(d)
    assert back.dedup_key == e.dedup_key
    assert back.likes == 42
    assert back.tags == ["nlp", "evals"]
    assert back.extra["arxiv_id"] == "2401.12345"


def test_unknown_keys_ignored():
    # from_dict should drop unexpected fields rather than crash.
    e = Event.from_dict(
        {
            "source": "new_models",
            "event_id": "x",
            "title": "x",
            "url": "x",
            "BOGUS": "ignore me",
        }
    )
    assert e.event_id == "x"
