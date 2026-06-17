"""Byte-pinned, append-only evaluation artifacts (rule + validator snapshots).

Each file is the VERBATIM source of a historical evaluation component, stored so its sha256 equals
the hash that real events recorded under that version carry. NEVER edit these files - editing
rotates the hash and orphans old events. New versions are ADDED as new files, never replacing old
ones."""
