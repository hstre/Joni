"""The in-doubt term-judge: OFF by default, parses yes/no, always fails back to the rule."""

from joni.autonomy import model_call, term_judge


def _answer(monkeypatch, text):
    monkeypatch.setattr(model_call, "call", lambda *a, **k: (text, None))


def test_disabled_by_default_makes_no_model_call(monkeypatch):
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        return ("yes", None)

    monkeypatch.setattr(model_call, "call", boom)
    monkeypatch.delenv("JONI_TERM_JUDGE", raising=False)
    assert term_judge.enabled() is False
    assert term_judge.judge("dass", cycle=1) is None      # dormant -> defer to the rule
    assert calls["n"] == 0                                 # and it never touches the model


def test_enabled_parses_yes_and_no(monkeypatch):
    monkeypatch.setenv("JONI_TERM_JUDGE", "1")
    _answer(monkeypatch, "yes")
    assert term_judge.judge("attention") is True
    _answer(monkeypatch, "No.")
    assert term_judge.judge("uzbek") is False


def test_unavailable_or_unparseable_defers_to_the_rule(monkeypatch):
    monkeypatch.setenv("JONI_TERM_JUDGE", "1")
    _answer(monkeypatch, "")            # over budget / empty
    assert term_judge.judge("x") is None
    _answer(monkeypatch, None)          # (None, None) -> failed / no model
    assert term_judge.judge("y") is None
    _answer(monkeypatch, "maybe")       # unparseable
    assert term_judge.judge("z") is None


def test_empty_term_is_never_judged(monkeypatch):
    monkeypatch.setenv("JONI_TERM_JUDGE", "1")
    _answer(monkeypatch, "yes")
    assert term_judge.judge("   ") is None
