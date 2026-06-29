"""The deterministic subject key — a finer scope than topic, replay-stable, no model."""
from __future__ import annotations

from joni.layer9_v2.checks.subject import subject_key


def test_same_subject_different_phrasing_order_same_key():
    a = subject_key("the canary rollout deployment is safe", topic="deploy")
    b = subject_key("deployment rollout canary, safe", topic="deploy")
    assert a == b                                   # order-independent, same salient tokens


def test_different_subjects_same_topic_differ():
    a = subject_key("the canary rollout strategy", topic="deploy")
    b = subject_key("the database migration plan", topic="deploy")
    assert a != b


def test_topic_is_part_of_the_key_and_excluded_from_tokens():
    k = subject_key("privacy leakage in retrieval", topic="privacy")
    assert k.startswith("topic:privacy|")
    assert "privacy" not in k.split("|", 1)[1]      # the topic word itself is not a salient token


def test_empty_text_falls_back_to_topic():
    assert subject_key("", topic="memory") == "topic:memory"
    assert subject_key(None, topic=None) == "topic:"


def test_deterministic_across_calls():
    t = "field radius sweep under base pressure"
    assert subject_key(t, "physics") == subject_key(t, "physics")


def test_stopwords_do_not_define_a_subject():
    # only generic/stop words -> no salient subject, falls back to topic
    assert subject_key("this has been very good and also better", topic="x") == "topic:x"
