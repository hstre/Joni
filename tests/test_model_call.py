"""Pinned model profiles + captured, replayable calls.

Reproducibility without removing semantics: a re-run replays persisted captures.
"""

import json

from joni.autonomy import model_call, model_profile


def test_profiles_separate_sampling_from_desi_state_k(monkeypatch):
    # the two axes are distinct fields, not the same knob
    sem = model_profile.profile("joni-semantic")
    assert sem.state_k == 1 and sem.sampling.temperature == 0.0      # deterministic projector
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
    assert cap1.state_k == 1 and cap1.temperature == 0.0 and cap1.seed == prof.sampling.seed
    assert cap1.prompt_sha and cap1.output_sha and cap1.run_id == "r1" and cap1.call_id

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
                  "run_id", "call_id", "replayed"):
        assert field in rec


def test_a_failed_call_is_no_proposal_not_a_fallback(monkeypatch, tmp_path):
    def boom(profile, system, user):
        raise RuntimeError("model unavailable")
    monkeypatch.setattr(model_call, "_complete", boom)
    prof = model_profile.profile("joni-semantic")
    out, cap = model_call.call(prof, "sys", "text", run_id="r1", store_dir=tmp_path)
    assert out is None and cap is None                              # no output, no silent switch
    assert not (tmp_path / "calls.jsonl").exists()                  # nothing captured on failure
