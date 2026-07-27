"""Schlafmodus S1-S4: refragmentation (with the thin-overlap bar), the procedural-structure audit,
the grounded defect reports, and the handover whose headline is ripening, not activity."""
from __future__ import annotations

import json
from types import SimpleNamespace

from joni.autonomy import sleep, sleep_passes, sleep_report
from joni.method_trial import provisional as pv


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _paths(tmp_path):
    return SimpleNamespace(
        provisional=tmp_path / "provisional.jsonl",
        refragment=tmp_path / "refragment.jsonl",
        sleep_audit=tmp_path / "sleep_audit.jsonl",
        sleep_revisions=tmp_path / "sleep_revisions.jsonl",
        wake_queue=tmp_path / "wake_queue.json",
        sleep_report=tmp_path / "sleep_report.md")


def _entry(content, **over):
    base = dict(kind=pv.EntryKind.OBSERVATION, content=content, source="s", created_cycle=1)
    base.update(over)
    return pv.ProvisionalEntry(**base)


# --- S1: refragmentation -----------------------------------------------------------------------

def test_a_substantive_shared_fragment_becomes_a_proposed_link():
    a = _entry("Die Zuordnung der Einheit scheitert reproduzierbar.")
    b = _entry("Anderswo: die Zuordnung der Einheit scheitert reproduzierbar; Ursache offen.")
    out = sleep_passes.refragment([a, b])
    assert out["links_total"] == 1
    assert out["links"][0]["entries"] == [a.entry_id(), b.entry_id()]


def test_a_thin_overlap_is_discarded_and_counted_not_emitted():
    # the lesson from the recurrence junk: two entries sharing only a short phrase are NOT a link
    a, b = _entry("Routing failed."), _entry("Routing failed.")
    out = sleep_passes.refragment([a, b])
    assert out["links_total"] == 0                 # 2 content words < MIN_FRAGMENT_WORDS
    assert out["thin_discarded"] == 2              # but the rejection stays visible


def test_a_phrase_shared_by_many_entries_is_boilerplate_not_a_link():
    # found on the first live run: a genuine association is RARE. A sentence two dozen entries
    # share is a form Joni writes with, not something he noticed.
    entries = [_entry(f"gemeinsame stabile schablone hier; eigenheit {'ab' * (i + 1)}")
               for i in range(8)]
    out = sleep_passes.refragment(entries)
    assert out["links_total"] == 0 and out["boilerplate_discarded"] == 1


def test_a_family_of_one_token_variants_is_a_template_and_is_dropped_whole():
    # the exact live shape: "across my forum claims X recurs through line worth testing"
    entries = []
    for word in ("abundance", "electrical", "ransomware", "predictive"):
        for half in ("erste", "zweite"):
            entries.append(_entry(f"across my forum claims {word} recurs worth testing; {half}"))
    out = sleep_passes.refragment(entries)
    assert out["links_total"] == 0                      # each pair alone is under the degree cap
    assert out["template_discarded"] == 4               # ...but they are one template family


def test_unrelated_entries_produce_no_link():
    a = _entry("Der Sandbox-Runner meldet einen Zeitüberschreitungsfehler beim Start.")
    b = _entry("Die Literaturquelle liefert seit gestern keine neuen Eintraege mehr.")
    assert sleep_passes.refragment([a, b])["links_total"] == 0


def test_the_link_cap_bounds_the_output():
    # genuinely distinct fragments (not one-token variants of each other), each shared by one pair
    frags = ["sandbox runner meldet zeitueberschreitung",
             "literaturquelle liefert keine eintraege",
             "einheiten weichen zwischen tabellen ab",
             "konflikt bleibt ueber zyklen offen",
             "budget reicht fuer keinen aufruf",
             "benchmark fehlt fuer diese prozedur"]
    entries = []
    for frag in frags:
        entries += [_entry(f"{frag}; erste haelfte"), _entry(f"{frag}; zweite haelfte")]
    out = sleep_passes.refragment(entries, max_links=3)
    assert out["links_total"] == 6 and len(out["links"]) == 3


# --- S2: the procedural-structure audit ---------------------------------------------------------

def test_procedure_score_names_exactly_what_is_missing():
    score, missing = sleep_passes.procedure_score(
        "unit-normalise", "When the units differ, apply the conversion, then verify against the "
                          "frozen baseline.")
    assert score == 3 and missing == []
    score2, missing2 = sleep_passes.procedure_score("unit-normalise",
                                                    "When units differ, apply the conversion.")
    assert score2 == 2 and missing2 == ["verification"]
    assert sleep_passes.procedure_score("thing", "")[1] == ["trigger", "steps", "verification"]


def _cs(methods):
    core = SimpleNamespace(all=lambda _t: methods)
    return SimpleNamespace(core=core)


def _m(mid, name, summary):
    return SimpleNamespace(id=mid, name=name, summary=summary,
                           status=SimpleNamespace(value="candidate"))


def test_audit_skips_paper_titles_instead_of_scoring_them_zero():
    # scoring known junk as 0/3 would inflate the bar with things the breakdown already buckets
    long_title = "On the Emergent Properties of Large Scale Retrieval Augmented Generation Systems"
    methods = [_m("M-1", long_title, "abstract text"),
               _m("M-2", "unit-normalise", "When units differ, apply the step, then verify it.")]
    out = sleep_passes.audit(_cs(methods))
    assert out["skipped_titles"] == 1 and out["scored"] == 1
    assert out["by_score"][3] == 1 and len(out["complete"]) == 1


def test_a_single_missing_component_is_a_concrete_defect_two_are_not():
    methods = [_m("M-1", "unit-normalise", "When units differ, apply the conversion step."),
               _m("M-2", "vague-lens", "a lens")]
    out = sleep_passes.audit(_cs(methods))
    ids = [d["id"] for d in out["defects"]]
    assert ids == ["M-1"]                      # M-2 misses all three: not a nameable single defect


# --- S3: defect reports ------------------------------------------------------------------------

def test_revisions_report_the_gap_and_never_apply_or_invent():
    aud = {"defects": [{"id": "M-1", "name": "unit-normalise", "missing": ["verification"]}]}
    revs = sleep_passes.revisions(aud, cycle=7)
    assert len(revs) == 1
    r = revs[0]
    assert r["applied"] is False and r["method_id"] == "M-1" and r["missing"] == "verification"
    assert "kein Prüfkriterium" in r["defect"]
    # a defect report names the gap; it does not write the missing content
    assert "ergänzen oder die Methode verwerfen" in r["proposal"]


def test_revisions_are_hard_capped():
    aud = {"defects": [{"id": f"M-{i}", "name": "n", "missing": ["steps"]} for i in range(10)]}
    assert len(sleep_passes.revisions(aud, cycle=1, max_revisions=2)) == 2


# --- the orchestrator --------------------------------------------------------------------------

def test_run_passes_persists_all_three_artefacts(tmp_path):
    p = _paths(tmp_path)
    pv.record([_entry("Die Zuordnung der Einheit scheitert reproduzierbar."),
               _entry("Erneut: die Zuordnung der Einheit scheitert reproduzierbar.")],
              store_path=p.provisional)
    methods = [_m("M-1", "unit-normalise", "When units differ, apply the conversion step.")]
    ext, proto = {}, _Proto()
    out = sleep_passes.run_passes(_cs(methods), ext, proto, 5, paths=p)
    assert out["refragment"]["links_total"] == 1 and len(out["revisions"]) == 1
    assert p.refragment.exists() and p.sleep_audit.exists() and p.sleep_revisions.exists()
    assert ext["sleep_passes"] is out
    assert any(k == "sleep_work" for k, _ in proto.events)


def test_missing_stores_yield_empty_results_rather_than_an_error():
    # no core, no paths - the passes degrade to "nothing found", which is the honest answer
    out = sleep_passes.run_passes(None, {}, _Proto(), 1, paths=SimpleNamespace())
    assert out["refragment"]["links_total"] == 0 and out["audit"]["scored"] == 0
    assert out["revisions"] == []


def test_run_passes_is_fail_open(monkeypatch):
    # a genuinely raising store must not break the cycle
    monkeypatch.setattr(pv, "load", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    proto = _Proto()
    assert sleep_passes.run_passes(None, {}, proto, 1, paths=SimpleNamespace()) == {}
    assert any("übersprungen" in s for _, s in proto.events)


# --- S4: the handover --------------------------------------------------------------------------

def test_zero_structurally_complete_methods_is_itself_the_top_finding():
    # the live measurement: 73 of 74 real procedure names score 0/3. That is not "nothing to
    # report" - it says the trial pipeline is starved at the SOURCE, and it outranks every item.
    passes = {"audit": {"scored": 74, "by_score": {0: 73, 1: 1, 2: 0, 3: 0}, "complete": []},
              "revisions": [], "refragment": {"links": []}}
    q = sleep_report.build_queue(passes)
    assert q[0]["kind"] == "structural_finding" and "73/74" in q[0]["name"]
    assert "an der Quelle" in q[0]["why"]
    # survives a JSON round-trip, where the score keys become strings
    q2 = sleep_report.build_queue(json.loads(json.dumps(passes)))
    assert q2[0]["name"] == q[0]["name"]
    # ...and it is NOT raised when something is actually complete
    passes["audit"]["complete"] = [{"id": "M-1", "name": "unit-normalise"}]
    assert sleep_report.build_queue(passes)[0]["kind"] == "drain_target"


def test_the_queue_ranks_trialable_targets_above_associations():
    passes = {
        "audit": {"complete": [{"id": "M-9", "name": "unit-normalise"}]},
        "revisions": [{"method_id": "M-1", "name": "n", "defect": "kein Prüfkriterium"}],
        "refragment": {"links": [{"fragment": "f", "entries": ["a", "b"]}]},
    }
    q = sleep_report.build_queue(passes)
    assert [r["kind"] for r in q] == ["drain_target", "defect_report", "associative_link"]


def test_the_report_leads_with_nothing_ripened_when_nothing_ripened(tmp_path):
    p = _paths(tmp_path)
    st = {"last_wake": {"slept_cycles": 6, "matured": False,
                        "delta": {"valid_tests": 0, "skills": 0, "episodes_resolved": 0,
                                  "hindsight_reviews": 0}}}
    passes = {"refragment": {"links_total": 400, "considered": 900, "thin_discarded": 12,
                             "links": []},
              "audit": {"scored": 10, "skipped_titles": 3, "by_score": {0: 10},
                        "complete": []}, "revisions": []}
    sleep_report.run_report(st, passes, _Proto(), 20, paths=p)
    text = p.sleep_report.read_text(encoding="utf-8")
    head = text.splitlines()[2]
    # 400 links is a lot of motion; the headline must still say the window matured nothing
    assert "**nichts gereift**" in head and "400" not in head
    # the only handover is the structural finding - no drain target, no defect, no link
    items = json.loads(p.wake_queue.read_text())["items"]
    assert [r["kind"] for r in items] == ["structural_finding"]


def test_the_report_says_ripened_when_a_counter_moved(tmp_path):
    p = _paths(tmp_path)
    st = {"last_wake": {"slept_cycles": 2, "matured": True,
                        "delta": {"valid_tests": 1, "skills": 0, "episodes_resolved": 0,
                                  "hindsight_reviews": 0}}}
    sleep_report.run_report(st, {}, _Proto(), 9, paths=p)
    text = p.sleep_report.read_text(encoding="utf-8")
    assert "**gereift**" in text.splitlines()[2] and "| Valide Tests | +1 |" in text


def test_run_report_is_fail_open():
    assert sleep_report.run_report({}, {}, _Proto(), 1, paths=SimpleNamespace()) == {"items": []}


# --- the wiring rule ---------------------------------------------------------------------------

def test_the_passes_run_on_the_state_not_on_the_gate(monkeypatch):
    # the whole observation design: asleep -> the work runs; the gate only governs the FAST
    monkeypatch.delenv("JONI_SLEEP", raising=False)
    st = {"state": sleep.SLEEP_DEEP}
    assert sleep.is_asleep(st) is True and sleep.intake_suppressed(st) is False
    assert sleep.is_asleep({"state": sleep.WAKE_TRANSITION}) is False    # handover, not work
    assert sleep.woke_this_cycle({"state": sleep.AWAKE}, sleep.WAKE_TRANSITION) is True
    assert sleep.woke_this_cycle({"state": sleep.AWAKE}, sleep.AWAKE) is False
