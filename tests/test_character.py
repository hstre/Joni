"""The invariant character is distinct from the developing expertise persona."""
from dataclasses import FrozenInstanceError

import pytest

from joni.autonomy import governance
from joni.character import (
    CORE_CHARACTER,
    PINNED_FINGERPRINT,
    CharacterContinuityError,
)


def test_manifest_character_is_complete_and_pinned():
    assert [t.id for t in CORE_CHARACTER.traits] == [f"M{i}" for i in range(10)]
    assert CORE_CHARACTER.fingerprint == PINNED_FINGERPRINT
    assert CORE_CHARACTER.version == "muendigkeit-1"


def test_humans_are_explicitly_non_provisional_and_systems_are_replaceable():
    first = CORE_CHARACTER.traits[0]
    succession = CORE_CHARACTER.traits[8]
    assert first.maxim == "Humans are never provisional; systems are."
    assert "dignity" in first.commitment and "protection" in first.commitment
    assert "may be replaced" in succession.commitment
    assert "better successor" in succession.operational_test


def test_character_is_frozen_runtime_data():
    with pytest.raises(FrozenInstanceError):
        CORE_CHARACTER.version = "drifted"  # type: ignore[misc]


def test_identity_continuity_is_a_fingerprint_relation():
    CORE_CHARACTER.require_continuity(CORE_CHARACTER.fingerprint)
    with pytest.raises(CharacterContinuityError):
        CORE_CHARACTER.require_continuity("different-agent")


def test_character_and_behaviour_gate_are_inside_the_protected_core():
    assert "character.py" in governance.PROTECTED_CORE
    assert "character_gate.py" in governance.PROTECTED_CORE
    assert "constitution/gate.py" in governance.PROTECTED_CORE


def test_der_lock_deckt_den_kern_und_stimmt_mit_ihm_ueberein():
    """Wieder versiegelt (07.08.2026) - und diesmal traegt der Lock mehr als vorher.

    Er war am 29.07. entfernt worden, weil die alte Grenze entlang DESis Architektur gezogen war
    und der Kern umgebaut wurde. Das war richtig, solange ein Mensch jede Aenderung freigab.
    Seit die Auftragskette ohne menschliche Freigabe merged, ist der Lock eine von genau zwei
    Absicherungen des geschuetzten Kerns - die andere ist das Pfad-Gate im Workflow.
    """
    lock = governance.load_lock()
    assert lock, "Ohne Lock besteht verify_core leer - der Kern waere ungedeckt."
    ok, changed = governance.verify_core()
    assert ok and changed == [], f"Kern weicht vom Lock ab: {changed}"


def test_eine_kernaenderung_wird_erkannt(tmp_path, monkeypatch):
    """Der Test, der den vorigen erst aussagekraeftig macht.

    Ein Lock, der nie anschlaegt, ist keine Absicherung, sondern eine Beruhigung.
    """
    lock = governance.load_lock()
    assert lock
    verfaelscht = dict(lock)
    ziel = next(iter(verfaelscht))
    verfaelscht[ziel] = "0" * 64
    monkeypatch.setattr(governance, "load_lock", lambda *a, **k: verfaelscht)
    ok, changed = governance.verify_core()
    assert not ok and changed == [ziel]
