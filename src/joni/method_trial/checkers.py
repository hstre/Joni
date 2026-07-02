"""Deterministic answer checkers for the Gold Micro Battery — NO model, no judge.

Stage-2 solvers are pre-registered to end their attempt with a line ``Answer: <x>``. A checker reads
that final-answer region (falling back to the whole text) and compares deterministically, so a prose
attempt is graded without any LLM. Extraction is conservative: it reads the FINAL stated answer (not
a number mentioned in passing) — that is what makes the grade reproducible and un-gameable.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable

_ANSWER = re.compile(r"answer\s*[:\-]?\s*", re.I)
_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def answer_region(text: str) -> str:
    """Text after the last ``answer`` marker (the solver's final answer), else the whole text."""
    text = text or ""
    hits = list(_ANSWER.finditer(text))
    return text[hits[-1].end():] if hits else text


def _nums(s: str) -> list[float]:
    return [float(m.replace(",", "")) for m in _NUM.findall(s)]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())


def exact_int(gold: int) -> Callable[[str], bool]:
    def chk(ans: str) -> bool:
        ns = _nums(answer_region(ans))
        return bool(ns) and int(round(ns[-1])) == gold
    return chk


def numeric_in_band(lo: float, hi: float) -> Callable[[str], bool]:
    def chk(ans: str) -> bool:
        ns = _nums(answer_region(ans))
        return bool(ns) and lo <= ns[-1] <= hi
    return chk


def choice(gold: str, options: Iterable[str]) -> Callable[[str], bool]:
    opts = sorted({o.upper() for o in options}, key=len, reverse=True)
    pat = re.compile(r"\b(" + "|".join(re.escape(o) for o in opts) + r")\b")
    def chk(ans: str) -> bool:
        found = pat.findall(answer_region(ans).upper())
        return bool(found) and found[-1] == gold.upper()
    return chk


def index_set(gold: Iterable[int], universe: Iterable[int]) -> Callable[[str], bool]:
    goldset, uni = set(gold), set(universe)
    def chk(ans: str) -> bool:
        got = {int(n) for n in _nums(answer_region(ans)) if int(n) in uni}
        return got == goldset
    return chk


def contains_any(tokens: Iterable[str]) -> Callable[[str], bool]:
    toks = [t.lower() for t in tokens]
    def chk(ans: str) -> bool:
        n = _norm(answer_region(ans))
        return any(t in n for t in toks)
    return chk


def yesno(gold: str) -> Callable[[str], bool]:
    g = gold.lower()
    def chk(ans: str) -> bool:
        words = _norm(answer_region(ans)).split()
        hits = [w for w in words if w in ("yes", "no")]
        return bool(hits) and hits[-1] == g
    return chk
