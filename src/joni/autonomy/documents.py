"""Joni's non-PDF input ports - read Markdown and LaTeX, not just PDFs.

Two more ways into the same governed reading pipeline (extracted sentences enter as
*candidate* claims through the gate; the DESi Semantic Layer still decides every relation):

  * **Markdown** - drop ``*.md`` / ``*.markdown`` in the inbox; notes, write-ups, READMEs.
  * **LaTeX**    - drop ``*.tex`` / ``*.latex`` in the inbox; paper sources (e.g. arXiv source).

Both work fully offline with no dependency: strip the markup deterministically to plain text,
then reuse ``pdf.claim_sentences`` to keep the claim-like sentences. Bounded per cycle and
deduped by filename, exactly like the PDF inbox.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .pdf import claim_sentences  # the same deterministic claim filter the PDF port uses

# LaTeX environments whose *content* is not prose (math, floats, code, bibliography): dropped
# whole so their symbols never reach the claim filter.
_DROP_ENVS = ("equation", "align", "alignat", "gather", "multline", "eqnarray", "displaymath",
              "math", "array", "matrix", "pmatrix", "bmatrix", "figure", "table", "tabular",
              "verbatim", "lstlisting", "minted", "tikzpicture", "thebibliography")

# LaTeX commands that wrap prose we want to keep (\textbf{...} -> ...).
_KEEP_ARG = ("textbf", "textit", "textrm", "texttt", "emph", "title", "section", "subsection",
             "subsubsection", "paragraph", "chapter", "caption", "footnote", "mbox", "text")

# LaTeX commands whose argument is metadata, not prose (\cite{...}, \label{...}): dropped.
_DROP_CMD = ("cite", "citep", "citet", "ref", "eqref", "autoref", "label", "includegraphics",
             "bibliography", "bibliographystyle", "usepackage", "documentclass", "input",
             "include", "newcommand", "renewcommand", "def", "hypersetup", "pagestyle")


@dataclass(frozen=True)
class Doc:
    source_id: str
    url: str
    title: str
    text: str


def markdown_to_text(md: str) -> str:
    """Strip Markdown to plain prose, keeping link/emphasis text, dropping code and structure."""
    t = md or ""
    t = re.sub(r"```.*?```", " ", t, flags=re.S)              # fenced code blocks
    t = re.sub(r"`[^`]*`", " ", t)                            # inline code
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)               # images
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)            # links -> their text
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)       # ATX headings
    t = re.sub(r"^\s{0,3}>\s?", "", t, flags=re.M)            # block quotes
    t = re.sub(r"^\s{0,3}([*+-]|\d+\.)\s+", "", t, flags=re.M)  # list markers
    t = re.sub(r"^\s*\|.*\|\s*$", " ", t, flags=re.M)         # table rows
    t = re.sub(r"[*_~]{1,3}", "", t)                          # bold/italic/strike markers
    t = re.sub(r"<[^>]+>", " ", t)                            # inline HTML
    return t


def latex_to_text(tex: str) -> str:
    """Strip LaTeX to plain prose: drop comments, math, floats, and markup; keep prose args."""
    t = re.sub(r"(?<!\\)%.*$", "", tex or "", flags=re.M)     # line comments
    for env in _DROP_ENVS:
        t = re.sub(rf"\\begin\{{{env}\*?\}}.*?\\end\{{{env}\*?\}}", " ", t, flags=re.S)
    t = re.sub(r"\$\$.*?\$\$", " ", t, flags=re.S)            # display math $$...$$
    t = re.sub(r"\\\[.*?\\\]", " ", t, flags=re.S)            # display math \[...\]
    t = re.sub(r"\$[^$]*\$", " ", t)                          # inline math $...$
    t = re.sub(rf"\\(?:{'|'.join(_KEEP_ARG)})\*?\{{([^{{}}]*)\}}", r"\1", t)   # keep prose arg
    t = re.sub(rf"\\(?:{'|'.join(_DROP_CMD)})\s*(?:\[[^\]]*\])?\s*(?:\{{[^{{}}]*\}})?",
               " ", t)                                        # drop metadata commands + args
    t = re.sub(r"\\[a-zA-Z@]+\*?(?:\[[^\]]*\])?", " ", t)     # any remaining command
    t = t.replace("{", " ").replace("}", " ")
    t = re.sub(r"[~^&\\]", " ", t)                            # stray LaTeX punctuation
    return t


def _read_inbox(inbox: Path, processed: set[str], patterns, transform, tag: str,
                limit: int) -> list[Doc]:
    """Read new files matching ``patterns`` from the inbox, transform to text, dedupe by name."""
    if not inbox.exists():
        return []
    files: set[Path] = set()
    for pat in patterns:
        files.update(inbox.glob(pat))
    out: list[Doc] = []
    for path in sorted(files):
        if len(out) >= limit:
            break
        if path.name in processed:
            continue
        processed.add(path.name)
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        text = transform(raw)
        if text.strip():
            out.append(Doc(source_id=f"{tag}:{path.name}", url=str(path),
                           title=path.stem, text=text))
    return out


def read_markdown_inbox(inbox: Path, processed: set[str], *, limit: int = 3) -> list[Doc]:
    return _read_inbox(inbox, processed, ("*.md", "*.markdown"), markdown_to_text, "md", limit)


def read_latex_inbox(inbox: Path, processed: set[str], *, limit: int = 3) -> list[Doc]:
    return _read_inbox(inbox, processed, ("*.tex", "*.latex"), latex_to_text, "tex", limit)


def claims_from(text: str, *, max_claims: int = 5) -> list[str]:
    """Convenience: plain text (already stripped) -> claim sentences."""
    return claim_sentences(text, max_claims=max_claims)
