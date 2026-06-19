"""Benefit-review of adopted extensions: an arm active a full window with no contribution is
auto-deactivated (flag overridden off in state; code kept). Review the value, prune the failures."""

from joni.autonomy import extension_review


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")          # projection.enabled() -> True
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))


def test_a_contributing_extension_is_kept(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    ext = {"doktores_review": [{"x": 1}]}                       # some activity
    extension_review.review(ext, _Proto(), 0)                  # opens the window
    ext["doktores_review"].append({"x": 2})                    # it keeps contributing
    out = extension_review.review(ext, _Proto(), 100)          # past the 60-cycle window
    assert "doktores" not in out["disabled"]
    assert extension_review.active("doktores") is True


def test_an_idle_extension_is_auto_deactivated(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    ext = {"doktores_review": [{"x": 1}]}                       # active...
    extension_review.review(ext, _Proto(), 0)                  # window opens at count=1
    proto = _Proto()
    out = extension_review.review(ext, proto, 100)             # ...but no growth in the window
    assert "doktores" in out["disabled"]
    assert extension_review.active("doktores") is False        # honoured by the arm's enabled()
    assert any("deactivated" in s for _, s in proto.events)


def test_disabled_state_persists_and_arm_honours_it(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from joni.autonomy import doktores
    ext = {"doktores_review": [{"x": 1}]}
    extension_review.review(ext, _Proto(), 0)
    extension_review.review(ext, _Proto(), 100)                # deactivates doktores
    assert doktores.enabled() is False                         # the arm reads the disable
