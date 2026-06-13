from joni import Joni, persistence


def test_round_trip_is_lossless(tmp_path):
    j = Joni()
    j.live(ticks=8)
    p = tmp_path / "state.json"
    j.save(p)
    loaded = persistence.load(p)
    assert loaded is not None
    # The serialised form of the reloaded state equals the original, field for field.
    assert persistence.to_dict(loaded) == persistence.to_dict(j.state)


def test_load_missing_file_returns_none(tmp_path):
    assert persistence.load(tmp_path / "nope.json") is None


def test_resume_restores_the_same_identity(tmp_path):
    p = tmp_path / "state.json"
    a = Joni(state_path=p)
    a.live(ticks=8)
    a.save()
    ra = a.respond("your take on privacy?")

    # A fresh process resumes from disk - same memories, same rejected ideas.
    b = Joni(state_path=p)
    assert b.snapshot()["tick"] == 8
    assert b.snapshot()["claims"] == a.snapshot()["claims"]
    rb = b.respond("your take on privacy?")
    assert rb.conversation == ra.conversation
    assert rb.epistemic.ledger_event == ra.epistemic.ledger_event


def test_history_and_ledger_survive_round_trip(tmp_path):
    j = Joni()
    j.live(ticks=10)
    p = j.save(tmp_path / "state.json")
    loaded = persistence.load(p)
    # A rejected claim keeps its full transition history (the receipts) after reload.
    rejected = [c for c in loaded.claims.values() if c.history]
    assert rejected
    t = rejected[0].history[-1]
    assert t.ledger_id.startswith("L9-")
    assert any(e.id == t.ledger_id for e in loaded.ledger)


def test_autosave_writes_on_mutation(tmp_path):
    p = tmp_path / "state.json"
    j = Joni(state_path=p, autosave=True)
    assert not p.exists()
    j.tick()
    assert p.exists()  # autosaved after the tick
