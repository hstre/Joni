"""The probabilistic verifier: an escalation stage for Doktores. Escalate the consequential
decisions, score them on continuous multi-dimensional signals with repetition, and let
DETERMINISTIC vetoes decide - a signal, never a truth. Shadow by default: it logs what it would do
and changes nothing, so both loops run in parallel and we can evaluate which was more sensible.
"""
import json

from joni.autonomy import doktores, model_call
from joni.autonomy.core_state import CoreState, seed_core
from joni.autonomy.sources import Item
from joni.autonomy.verifier import config, escalation, safety, scorer, verify
from joni.autonomy.verifier.models import VerificationDimension, VerificationRedFlag


def _item():
    return Item("arxiv", "p1", "A retrieval method for reading agents", "https://x/p1",
                "We present a retrieval method that broadens topic coverage.")


_VERDICT = {"applicable": True, "component_key": "reader-sources",
            "desired": "Add the method to reader.py", "acceptance": "Recall@5 up by 3 points"}

_GOOD = {"module_fit": 0.9, "evidence_grounding": 0.85, "consistency": 0.9, "alternatives": 0.7,
         "error_safety": 0.9, "impact": 0.8, "info_needed": 0.1, "reasoning_stability": 0.9,
         "hard_constraint_compliance": 0.95, "overclaim_risk": 0.1}


def _reply(scores, red_flags=None):
    return json.dumps({"scores": scores, "red_flags": red_flags or [], "rationale": "r"})


def _ask(scores, red_flags=None):
    return lambda system, user: _reply(scores, red_flags)


def _cfg(monkeypatch, **env):
    monkeypatch.setenv("JONI_VERIFIER_MODE", env.pop("mode", "shadow"))
    for k, v in env.items():
        monkeypatch.setenv(k, str(v))
    return config.load()


# -- escalation ------------------------------------------------------------------------------- #

def test_a_non_applicable_verdict_is_not_escalated(monkeypatch):
    cfg = _cfg(monkeypatch)
    assert escalation.should_escalate({"applicable": False}, None, cfg).escalate is False


def test_a_to_be_filed_commission_is_escalated_with_reasons(monkeypatch):
    cfg = _cfg(monkeypatch)
    esc = escalation.should_escalate(_VERDICT, None, cfg)         # grounded None -> abstract only
    assert esc.escalate is True
    assert "commission_to_file" in esc.reasons and "abstract_only_evidence" in esc.reasons


def test_disabled_verifier_never_escalates(monkeypatch):
    cfg = _cfg(monkeypatch, mode="off")
    assert escalation.should_escalate(_VERDICT, None, cfg).escalate is False


# -- scorer: repetition, variance, fallback -------------------------------------------------- #

def test_scorer_aggregates_mean_and_variance_over_repetitions(monkeypatch):
    cfg = _cfg(monkeypatch, JONI_VERIFIER_REPS=3)
    calls = {"n": 0}

    def ask(system, user):
        calls["n"] += 1
        # vary evidence_grounding across reps so variance is non-zero
        return _reply({**_GOOD, "evidence_grounding": 0.5 + 0.1 * calls["n"]})
    dims, flags, reps, cost = scorer.score(_item(), _VERDICT, {}, cfg, ask=ask)
    assert reps == 3 and calls["n"] == 3
    assert abs(dims["module_fit"].score - 0.9) < 1e-9
    assert dims["evidence_grounding"].variance > 0.0            # spread is kept, not averaged away


def test_scorer_returns_none_on_all_malformed_replies(monkeypatch):
    cfg = _cfg(monkeypatch)
    assert scorer.score(_item(), _VERDICT, None, cfg, ask=lambda s, u: "not json at all") is None


def test_verifier_judges_on_the_whole_paper_when_available(monkeypatch):
    # the important part is in the body, not the abstract - the verifier must see the full text.
    cfg = _cfg(monkeypatch)
    seen = {}

    def ask(system, user):
        seen["user"] = user
        return _reply(_GOOD)
    scorer.score(_item(), _VERDICT, {}, cfg, full_text="Section 4: the method is X.", ask=ask)
    assert "FULL PAPER TEXT" in seen["user"] and "the method is X" in seen["user"]
    # ...and honestly falls back to the abstract for a gated/unfetchable paper
    scorer.score(_item(), _VERDICT, None, cfg, full_text=None, ask=ask)
    assert "ONLY the abstract" in seen["user"]


# -- safety vetoes: rules decide, safety overrides the score --------------------------------- #

def _dims(scores):
    return {n: VerificationDimension(n, s) for n, s in scores.items()}


def test_clean_case_files(monkeypatch):
    cfg = _cfg(monkeypatch)
    assert safety.decide(_dims(_GOOD), [], cfg).action == "file"


def test_a_high_severity_red_flag_forces_human_review_despite_a_high_score(monkeypatch):
    cfg = _cfg(monkeypatch)
    rf = [VerificationRedFlag("dangerous_alternative", "high", "…")]
    dec = safety.decide(_dims(_GOOD), rf, cfg)
    assert dec.action == "human_review" and dec.veto == "high_severity_red_flag"


def test_a_core_touch_red_flag_forces_human_review(monkeypatch):
    cfg = _cfg(monkeypatch)
    rf = [VerificationRedFlag("touches_core", "medium", "…")]
    assert safety.decide(_dims(_GOOD), rf, cfg).action == "human_review"


def test_weak_evidence_never_auto_files(monkeypatch):
    cfg = _cfg(monkeypatch)
    weak = {**_GOOD, "evidence_grounding": 0.2, "info_needed": 0.1}
    assert safety.decide(_dims(weak), [], cfg).action == "abstain"      # not filed on plausibility
    weak_needs = {**_GOOD, "evidence_grounding": 0.2, "info_needed": 0.9}
    assert safety.decide(_dims(weak_needs), [], cfg).action == "read_full_text"  # go read it


def test_low_hard_constraint_compliance_forces_human_review(monkeypatch):
    cfg = _cfg(monkeypatch)
    risky = {**_GOOD, "hard_constraint_compliance": 0.2}
    assert safety.decide(_dims(risky), [], cfg).action == "human_review"


def test_an_unstable_run_asks_for_another_pass(monkeypatch):
    cfg = _cfg(monkeypatch, JONI_VERIFIER_INSTABILITY=0.1)
    dims = _dims(_GOOD)
    dims["reasoning_stability"] = VerificationDimension("reasoning_stability", 0.9, variance=0.3)
    assert safety.decide(dims, [], cfg).action == "run_additional_pass"


# -- end to end + shadow integration --------------------------------------------------------- #

def test_verify_returns_a_result_for_an_escalated_case(monkeypatch):
    _cfg(monkeypatch)
    res = verify(_item(), _VERDICT, None, ask=_ask(_GOOD))
    assert res is not None and res.escalated and res.action == "file"
    assert res.audit["grounded_in"] == "abstract" and res.audit["action"] == "file"


def test_shadow_mode_logs_the_verifier_verdict_but_still_files(monkeypatch, tmp_path):
    # both loops in parallel: the verifier records what it would do; the commission is still filed.
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setenv("JONI_VERIFIER_MODE", "shadow")

    def complete(profile, system, user):
        if "VERIFIER for Joni" in system:
            return _reply(_GOOD)                                  # the verifier's scoring call
        return ('{"applicable": true, "component_key": "reader-sources", "title": "t", '
                '"motivation": "m", "desired": "d", "acceptance": "Recall@5 up by 3 points"}')
    monkeypatch.setattr(model_call, "_complete", complete)
    monkeypatch.setattr(doktores, "_scout", lambda q: [])
    monkeypatch.setattr(doktores, "_agent_scout", lambda e: [])
    monkeypatch.setattr(doktores, "_full_text", lambda item: "Section 4: the full method text.")
    ext: dict = {}
    new = doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=[_item()])
    assert len(new) == 1                              # shadow changed nothing: still filed
    log = ext["verifier_shadow"][-1]
    assert log["action"] == "file" and log["plain_action"] == "file"
    assert log["verifier_evidence"] == "full-text"   # judged on the whole paper, not the abstract


def test_enforce_mode_holds_back_an_abstain(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setenv("JONI_VERIFIER_MODE", "enforce")
    weak = {**_GOOD, "evidence_grounding": 0.15, "info_needed": 0.1}   # -> abstain

    def complete(profile, system, user):
        if "VERIFIER for Joni" in system:
            return _reply(weak)
        return ('{"applicable": true, "component_key": "reader-sources", "title": "t", '
                '"motivation": "m", "desired": "d", "acceptance": "Recall@5 up by 3 points"}')
    monkeypatch.setattr(model_call, "_complete", complete)
    monkeypatch.setattr(doktores, "_scout", lambda q: [])
    monkeypatch.setattr(doktores, "_agent_scout", lambda e: [])
    monkeypatch.setattr(doktores, "_full_text", lambda item: None)
    ext: dict = {}
    new = doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=[_item()])
    assert new == []                              # the verifier held back the auto-file
    assert ext["verifier_shadow"][-1]["action"] == "abstain"


class _Proto:
    def record(self, *a, **k):
        pass
