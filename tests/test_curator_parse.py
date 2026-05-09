from src.orchestrator import _parse_curator_output, _parse_research_output


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


def test_research_parser_fills_defaults():
    # Broken input still returns the defensive shape — keys present, values empty.
    out = _parse_research_output("not json at all")
    assert out["primary_author"] == {}
    assert out["coauthors"] == []
    assert out["notes"] == ""

    out2 = _parse_research_output('{"primary_author": {"name": "Alice"}, "coauthors": []}')
    assert out2["primary_author"]["name"] == "Alice"
    assert out2["coauthors"] == []


def test_research_parser_normalizes_missing_fields():
    # Researcher returns just {"notes": "..."} — defaults should be filled in.
    out = _parse_research_output('{"notes": "couldn\'t find anyone"}')
    assert "primary_author" in out
    assert "coauthors" in out
    assert out["notes"] == "couldn't find anyone"
