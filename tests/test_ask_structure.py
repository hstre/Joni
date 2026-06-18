"""A core-ask carries structure: component, what would change, evidence, risk, idea-vs-request."""

from joni.autonomy.improve import Improvement, structured_ask


def _imp(target="operator"):
    return Improvement("core_change", "Rethinking the conflict-resolution operator", target,
                       "reading suggests a change to protected core logic", "arxiv:1", "http://x")


def test_structured_ask_has_the_five_fields():
    a = structured_ask(_imp("operator"), cycle=7)
    assert a["request_type"] == "observation"          # an idea, not a worked-out request
    assert "operator" in a["component"]                 # which protected component
    assert a["proposed_change"]                         # what would change (honest: unspecified)
    assert a["evidence"]["source_title"].startswith("Rethinking")
    assert a["evidence"]["source_url"] == "http://x"
    assert "high" in a["risk"].lower()                  # risk stated
    assert a["cycle"] == 7


def test_risk_and_component_vary_by_target():
    op = structured_ask(_imp("operators"), 1)
    rt = structured_ask(_imp("router algorithm"), 1)
    assert op["component"] != rt["component"]
    assert op["risk"] != rt["risk"]


def test_unknown_target_falls_back_safely():
    a = structured_ask(_imp("something-core"), 1)
    assert a["component"] == "protected core logic"
    assert "high" in a["risk"].lower()
    # Note: core asks are still generated (and filed for a human), but the website no longer
    # renders an "Asks" card — that surface was retired when the autonomous loop was stopped.
