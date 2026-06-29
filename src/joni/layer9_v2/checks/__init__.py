"""Slice-quality checks wired to the v2 graph — the plausible-wrong-slice signals on real data.

These produce the slice-INDEPENDENT scan inputs (omitted opposition, provenance families, scope)
that DESi's ``report_from_snapshot`` consumes. Joni-side and DESi-free: the module
only reads the v2 store and returns plain dicts; the routing decision stays in DESi.
"""
