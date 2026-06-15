"""Pinned model profiles + captured, replayable calls.

Reproducibility without removing semantics: a re-run replays persisted captures.
"""

import json

from joni.autonomy import model_call, model_profile


def test_profiles_separate_sampling_from_desi_state_k(monkeypatch):
    # the two axes are distinct fields, not the same knob
    sem = model_profile.profile("joni-semantic")
    assert sem.state_k == 5 and sem.sampling.temperature == 0.0      # Granite start k (calibrate)
    ref = model_profile.profile("reference")
    assert ref.state_k == 5                                          # the control arm's density
    kev = model_profile.profile("kevin")
    assert kev.state_k == 0 and kev.sampling.temperature == 0.7      # creative, own profile
    rnd = model_profile.profile("renderer")
    assert rnd.state_k == 0 and rnd.name == "renderer"               # voice only, separate
    # env re-pins a profile without code changes
    monkeypatch.setenv("JONI_SEMANTIC_STATE_K", "3")
    monkeypatch.setenv("JONI_GRANITE_SLUG", "ibm-granite/granite-x")
    sem2 = model_profile.profile("joni-semantic")
    assert sem2.state_k == 3 and sem2.served_slug == "ibm-granite/granite-x"


def test_hard_tasks_use_deepseek_pro_v4_directly(monkeypatch):
    # difficult semantic work -> DeepSeek Pro v4 via the DeepSeek API, NOT a micro model
    hard = model_profile.profile("joni-hard")
    assert hard.provider == "deepseek"
    assert hard.base_url == "https://api.deepseek.com"
    assert hard.key_env == "DEEPSEEK_API_KEY"
    assert hard.model_id == "deepseek-v4-pro"                        # per the DeepSeek API docs
    assert hard.served_slug == "deepseek-v4-pro"                     # NOT the deprecated v4-flash
    assert hard.state_k == 3                                         # its own start k over {3,5}
    # the rest (structured papers / extraction) -> Granite 4.1 8B, not a tiny model
    sem = model_profile.profile("joni-semantic")
    assert sem.model_id == "granite-4.1-8b"
    assert sem.served_slug == "ibm-granite/granite-4.1-8b-20260429"
    # state_k is task-specific, never inherited
    assert hard.state_k != sem.state_k
    # the exact DeepSeek slug is env-pinned and captured (no silent label)
    monkeypatch.setenv("JONI_DEEPSEEK_SLUG", "deepseek-reasoner")
    assert model_profile.profile("joni-hard").served_slug == "deepseek-reasoner"


def test_task_router_sends_difficult_to_deepseek_and_rest_to_granite():
    assert model_profile.for_task("conflict").name == "joni-hard"
    assert model_profile.for_task("source-analysis").name == "joni-hard"
    assert model_profile.for_task("extraction").name == "joni-semantic"
    assert model_profile.for_task("paper-audit").name == "joni-semantic"


def test_unknown_profile_is_never_silently_substituted():
    import pytest
    with pytest.raises(KeyError):
        model_profile.profile("mystery-model")


def test_call_captures_then_replays(monkeypatch, tmp_path):
    calls = []

    def fake_complete(profile, system, user):
        calls.append(profile.served_slug)
        return "extracted: routing reduces latency"
    monkeypatch.setattr(model_call, "_complete", fake_complete)

    prof = model_profile.profile("joni-semantic")
    out1, cap1 = model_call.call(prof, "sys", "the source text", run_id="r1", store_dir=tmp_path)
    assert out1 == "extracted: routing reduces latency"
    assert cap1.replayed is False and len(calls) == 1
    # the capture carries the full reproducibility record
    assert cap1.requested_model == prof.model_id and cap1.served_model == prof.served_slug
    assert cap1.state_k == 5 and cap1.temperature == 0.0 and cap1.seed == prof.sampling.seed
    assert cap1.prompt_sha and cap1.output_sha and cap1.run_id == "r1" and cap1.call_id
    assert cap1.escalation_reason is None                            # primary call, not escalated

    # same prompt + pinned config -> REPLAY from the persisted capture, no second network call
    out2, cap2 = model_call.call(prof, "sys", "the source text", run_id="r2", store_dir=tmp_path)
    assert out2 == out1 and cap2.replayed is True
    assert len(calls) == 1                                           # _complete not called again

    # the audit log persisted both calls with all fields
    log = (tmp_path / "calls.jsonl").read_text().strip().splitlines()
    assert len(log) == 2
    rec = json.loads(log[0])
    for field in ("requested_model", "served_model", "provider", "temperature", "seed",
                  "max_tokens", "sampling_sha", "state_k", "prompt_sha", "output_sha",
                  "run_id", "call_id", "replayed", "escalation_reason"):
        assert field in rec


def test_telemetry_reads_real_capture_records(monkeypatch, tmp_path):
    # two Granite calls + one DeepSeek escalation, one of them a replay -> the dashboard numbers
    # come straight from calls.jsonl, never guessed.
    monkeypatch.setattr(model_call, "_complete", lambda p, s, u: "out")
    gran = model_profile.profile("joni-semantic")
    hard = model_profile.profile("joni-hard")
    model_call.call(gran, "sys", "a", run_id="r1", store_dir=tmp_path)
    model_call.call(gran, "sys", "a", run_id="r2", store_dir=tmp_path)          # same -> replay
    model_call.call(hard, "sys", "b", run_id="r1", store_dir=tmp_path,
                    escalation_reason="high_conflict_load")
    t = model_call.telemetry(tmp_path)
    assert t["llm_calls"] == 3
    assert t["granite_calls"] == 2 and t["deepseek_escalations"] == 1
    assert t["cached_calls"] == 1 and t["live_calls"] == 2
    assert t["last_call"]                                        # an ISO timestamp was recorded
    assert t["est_cost_eur"] >= 0.0
    # an empty store is all-zeros, never an error
    assert model_call.telemetry(tmp_path / "nope")["llm_calls"] == 0


def test_a_failed_call_is_no_proposal_not_a_fallback(monkeypatch, tmp_path):
    def boom(profile, system, user):
        raise RuntimeError("model unavailable")
    monkeypatch.setattr(model_call, "_complete", boom)
    prof = model_profile.profile("joni-semantic")
    out, cap = model_call.call(prof, "sys", "text", run_id="r1", store_dir=tmp_path)
    assert out is None and cap is None                              # no output, no silent switch
    assert not (tmp_path / "calls.jsonl").exists()                  # nothing captured on failure
