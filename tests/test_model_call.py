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


def test_empty_answer_is_diagnosable_not_guessed(monkeypatch, tmp_path):
    # the review's point: an empty answer must be CLASSIFIABLE. The seam returns the full Raw
    # evidence; the capture records finish_reason / tokens / content vs reasoning length.
    def truncated(profile, system, user):
        return model_call.Raw(text="", finish_reason="length", served="deepseek-v4-pro",
                              prompt_tokens=120, completion_tokens=768, reasoning_tokens=768,
                              reasoning_len=4096, raw_json='{"x":1}')
    monkeypatch.setattr(model_call, "_complete", truncated)
    prof = model_profile.profile("joni-hard")
    out, cap = model_call.call(prof, "s", "u", run_id="r1", store_dir=tmp_path)
    assert out == "" and cap.finish_reason == "length" and cap.content_len == 0
    assert cap.reasoning_tokens == 768 and cap.reasoning_len == 4096 and cap.raw_sha
    assert (tmp_path / "outputs").glob("*.raw.json")            # the raw response is preserved
    t = model_call.telemetry(tmp_path)
    # finish_reason==length + content empty PROVES the token-budget cause - not a guess
    assert t["empty_calls"] == 1 and t["empty_truncated"] == 1
    assert t["empty_with_reasoning"] == 0 and t["empty_silent"] == 0

    # a different empty class: content empty but reasoning present and NOT truncated -> adapter bug
    def adapter_bug(profile, system, user):
        return model_call.Raw(text="", finish_reason="stop", reasoning_len=200)
    monkeypatch.setattr(model_call, "_complete", adapter_bug)
    model_call.call(prof, "s", "v", run_id="r2", store_dir=tmp_path)
    t2 = model_call.telemetry(tmp_path)
    assert t2["empty_with_reasoning"] == 1                      # distinct class, not conflated


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


def test_empty_output_is_not_cached_so_it_retries(monkeypatch, tmp_path):
    # cache-poisoning fix: an empty live answer must NOT be cached (else it replays forever as a
    # stable empty "success"). The next call re-hits the network instead of replaying "".
    calls = []
    def empty(profile, system, user):
        calls.append(1)
        return model_call.Raw(text="", finish_reason="length", reasoning_tokens=768)
    monkeypatch.setattr(model_call, "_complete", empty)
    prof = model_profile.profile("joni-hard")
    out1, c1 = model_call.call(prof, "s", "u", run_id="r", store_dir=tmp_path)
    out2, c2 = model_call.call(prof, "s", "u", run_id="r", store_dir=tmp_path)
    assert out1 == "" and out2 == ""
    assert len(calls) == 2                          # retried (not replayed from a cached "")
    assert c1.replayed is False and c2.replayed is False
    assert not list((tmp_path / "outputs").glob("*.txt"))                     # nothing cached


def test_real_response_parser_surfaces_truncation_evidence():
    # the original-bug locus: a reasoning model returns content=None + finish_reason=length +
    # nested reasoning_tokens. The real parser must yield text='' WITH the evidence, not hide it.
    class _Msg:
        content = None
        reasoning_content = "...long internal reasoning..."

    class _Choice:
        message = _Msg()
        finish_reason = "length"

    class _Details:
        reasoning_tokens = 2048

    class _Usage:
        prompt_tokens = 120
        completion_tokens = 2048
        completion_tokens_details = _Details()

    class _Resp:
        choices = [_Choice()]
        usage = _Usage()
        model = "deepseek-v4-pro"

        def model_dump_json(self):
            return '{"ok":1}'

    raw = model_call._to_raw(_Resp())
    assert raw.text == "" and raw.finish_reason == "length"
    assert raw.reasoning_tokens == 2048 and raw.reasoning_len > 0
    assert raw.served == "deepseek-v4-pro"
