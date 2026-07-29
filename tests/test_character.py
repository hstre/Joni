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


def test_ohne_lock_blockiert_die_pruefung_nicht():
    """Der Kern wird umgebaut, deshalb ist ``joni_core.lock`` entfernt (29.07.2026).

    Die Mechanik bleibt absichtlich stehen: ``verify_core`` behandelt einen fehlenden Lock als
    "noch nicht eingefroren" und laesst durch. Entfernt wurde damit die *Grenze*, nicht das
    *Verfahren* - die alte Grenze war entlang DESis Architektur gezogen, und DESi ist geschlossen.

    Sobald der umgebaute Kern steht, versiegelt ``governance.write_lock()`` die neue Grenze, und
    an dieser Stelle gehoert dann wieder ein Gleichheitstest hin. Bis dahin haelt dieser Test nur
    fest, dass der Zustand "kein Lock" bewusst ist und nichts blockiert.
    """
    assert governance.load_lock() == {}
    ok, changed = governance.verify_core()
    assert ok and changed == []
