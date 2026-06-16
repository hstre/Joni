"""Architecture invariants against the recurring error class the review named:
'nominal path present, functional semantics absent'. A component may be wired, emit calls and
pass tests while its actual semantic function is missing - these tests refuse to let that pass
silently. They encode: instrument (don't guess) empty outputs, and never present a synthetic
trial as effectiveness evidence."""


from joni.autonomy import model_call, model_profile, site


def test_kevin_raw_response_preserved_and_empty_classified(monkeypatch, tmp_path):
    """KEVIN_RAW_RESPONSE_PRESERVED + KEVIN_CREATIVE_OUTPUT diagnosable: an empty answer is
    captured with finish_reason/tokens/raw and CLASSIFIED, not silently dropped or guessed at."""
    monkeypatch.setattr(model_call, "_complete", lambda p, s, u: model_call.Raw(
        text="", finish_reason="length", served="deepseek-v4-pro",
        completion_tokens=2048, reasoning_tokens=2048, reasoning_len=8000, raw_json='{"r":1}'))
    prof = model_profile.profile("kevin")
    out, cap = model_call.call(prof, "s", "u", run_id="kevin-c1", store_dir=tmp_path)
    assert out == "" and cap.content_len == 0 and cap.finish_reason == "length"
    assert cap.raw_sha and cap.reasoning_tokens == 2048           # the evidence is preserved
    assert list((tmp_path / "outputs").glob("*.raw.json"))        # raw response on disk
    t = model_call.telemetry(tmp_path)
    assert t["empty_truncated"] == 1 and t["empty_with_reasoning"] == 0  # the cause is provable


def test_method_trial_never_presented_as_effectiveness():
    """METHOD_TRIAL_NOT_MOCK_IN_PRODUCTION: while the trial is the synthetic simulator, the site
    must label it a simulation with no epistemic weight - never as method effectiveness."""
    data = {"snapshot": {"tick": 0, "topics": [], "last_route": None, "research_topics": 0,
                         "method_trials": 539, "methods_ready": 0,
                         "epistemically_usable": {"rate": 0.8, "n": 1, "flags": {}}},
            "budget": {"spent_eur": 0.0, "cap_eur": 20.0, "runs": 5},
            "window": {"start": "t", "runs": 5}, "generated": "t", "protocol": [],
            "extensions": {}, "telemetry": {"llm_calls": 0}, "commissions_done": []}
    h = site.build(data)
    assert "synthetische Simulation" in h
    assert "epistemic_weight=none" in h
    assert "kein</b> semantischer oder empirischer Wirksamkeitsnachweis" in h


def test_capture_carries_the_diagnostic_fields():
    """The capture schema must keep room for the evidence; if these get dropped, the four failure
    classes silently re-merge."""
    import dataclasses
    fields = {f.name for f in dataclasses.fields(model_call.Capture)}
    for f in ("finish_reason", "served_actual", "prompt_tokens", "completion_tokens",
              "reasoning_tokens", "content_len", "reasoning_len", "raw_sha"):
        assert f in fields, f"diagnostic field {f} missing from Capture"
