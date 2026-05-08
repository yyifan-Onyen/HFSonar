from src.orchestrator import _parse_curator_output


def test_plain_json():
    s = '{"chosen": [{"event_dedup_key": "a::b", "angle": "x"}]}'
    out = _parse_curator_output(s)
    assert out == [{"event_dedup_key": "a::b", "angle": "x"}]


def test_fenced_json():
    s = "```json\n{\"chosen\": []}\n```"
    out = _parse_curator_output(s)
    assert out == []


def test_extracts_first_object_from_prose():
    s = (
        "Here are my picks:\n"
        '{"chosen": [{"event_dedup_key": "a::b", "angle": "x"}]}\n'
        "let me know if you want changes."
    )
    out = _parse_curator_output(s)
    assert out == [{"event_dedup_key": "a::b", "angle": "x"}]


def test_invalid_json_returns_empty():
    assert _parse_curator_output("not json at all") == []
    assert _parse_curator_output("") == []
