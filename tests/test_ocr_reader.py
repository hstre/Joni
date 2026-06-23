"""OCR input port (Auftrag #161): image/scanned files in the inbox are transcribed by a pluggable,
fail-closed backend into the standard Doc feed - the same governed reading pipeline as PDF/Markdown.

The headline metric (50-page scan <120s) belongs to the real model on real hardware and needs the
weights + a 50-page fixture, neither in CI. These tests pin the READER + backend seam, deterministic
stub: discovery, dedupe, bounds, fail-closed behaviour, and that the text feeds the shared claim
filter.
"""

from pathlib import Path

from joni.autonomy import documents, ocr


class _StubOCR:
    name = "stub"

    def transcribe(self, image_path: str) -> str:
        stem = Path(image_path).stem
        return (f"The scanned page about {stem} reports that the method measurably "
                f"improves accuracy in a controlled study.")


def _img(p: Path, name: str) -> None:
    (p / name).write_bytes(b"\x89PNG not-a-real-image")


def test_reads_images_into_docs_and_dedupes(tmp_path):
    _img(tmp_path, "alpha.png")
    _img(tmp_path, "beta.jpg")
    ocr._reset_for_tests(_StubOCR())
    try:
        seen: set[str] = set()
        docs = ocr.read_inbox(tmp_path, seen, limit=5)
        assert sorted(d.source_id for d in docs) == ["ocr:alpha.png", "ocr:beta.jpg"]
        assert all(d.url.endswith((".png", ".jpg")) and d.title in ("alpha", "beta") for d in docs)
        assert all("scanned page" in d.text for d in docs)
        # a second pass with the same processed-set returns nothing new (dedupe by filename)
        assert ocr.read_inbox(tmp_path, seen, limit=5) == []
    finally:
        ocr._reset_for_tests(None)


def test_limit_bounds_per_cycle(tmp_path):
    for n in ("a", "b", "c", "d"):
        _img(tmp_path, f"{n}.png")
    ocr._reset_for_tests(_StubOCR())
    try:
        assert len(ocr.read_inbox(tmp_path, set(), limit=2)) == 2
    finally:
        ocr._reset_for_tests(None)


def test_transcribed_text_feeds_the_shared_claim_filter(tmp_path):
    _img(tmp_path, "x.png")
    ocr._reset_for_tests(_StubOCR())
    try:
        doc = ocr.read_inbox(tmp_path, set(), limit=1)[0]
        assert documents.claims_from(doc.text), "OCR text must yield candidate claim-sentences"
    finally:
        ocr._reset_for_tests(None)


def test_absent_backend_is_a_noop(tmp_path):
    _img(tmp_path, "a.png")
    ocr.set_backend(None)               # force 'no engine installed'
    try:
        assert ocr.available() is False
        assert ocr.info()["backend"] == "none"
        assert ocr.read_inbox(tmp_path, set(), limit=2) == []
    finally:
        ocr._reset_for_tests(None)


def test_broken_backend_fails_closed(tmp_path):
    _img(tmp_path, "a.png")

    class _Boom:
        name = "boom"

        def transcribe(self, image_path: str) -> str:
            raise RuntimeError("model exploded")

    ocr._reset_for_tests(_Boom())
    try:
        assert ocr.available() is True          # a backend IS registered ...
        assert ocr.read_inbox(tmp_path, set(), limit=2) == []   # ... but a crash is swallowed
    finally:
        ocr._reset_for_tests(None)


def test_set_backend_registers_a_real_engine(tmp_path):
    _img(tmp_path, "p.png")
    ocr.set_backend(_StubOCR())             # the seam an operator uses for the Unlimited-OCR model
    try:
        assert ocr.available() and ocr.info()["backend"] == "stub"
        docs = ocr.OcrReader(_StubOCR()).read_inbox(tmp_path, set())
        assert docs and docs[0].title == "p"
    finally:
        ocr._reset_for_tests(None)
