from pathlib import Path

from src.ledger import Ledger


def test_ledger_round_trip(tmp_path: Path):
    p = tmp_path / "ledger.jsonl"
    ledger = Ledger(p)
    assert not ledger.has("a")
    ledger.record("a", source="trending_models")
    assert ledger.has("a")

    # Reload should preserve membership.
    ledger2 = Ledger(p)
    assert ledger2.has("a")
    assert len(ledger2) == 1


def test_ledger_filter_unseen(tmp_path: Path):
    ledger = Ledger(tmp_path / "ledger.jsonl")
    ledger.record("a")
    ledger.record("b")
    unseen = ledger.filter_unseen(["a", "c", "b", "d"])
    assert unseen == ["c", "d"]


def test_ledger_idempotent_record(tmp_path: Path):
    p = tmp_path / "ledger.jsonl"
    ledger = Ledger(p)
    ledger.record("a")
    ledger.record("a")
    assert len(ledger) == 1
    assert p.read_text(encoding="utf-8").count("\n") == 1
