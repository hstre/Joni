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


def test_character_is_inside_the_protected_core():
    assert "character.py" in governance.PROTECTED_CORE
    assert "constitution/gate.py" in governance.PROTECTED_CORE
