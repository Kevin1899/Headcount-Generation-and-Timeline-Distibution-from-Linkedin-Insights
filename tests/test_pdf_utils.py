"""
Unit tests for pdf_utils.PDFTextExtractor.
"""
from pathlib import Path
import pytest

import linkedin_insights.pdf_utils as pdf_utils


def test_missing_pdf_raises_file_not_found(tmp_path: Path) -> None:
    """Non-existent path should raise FileNotFoundError."""
    missing = tmp_path / "does_not_exist.pdf"
    with pytest.raises(FileNotFoundError):
        pdf_utils.PDFTextExtractor.extract_text(missing)


def test_scan_only_pdf_raises_runtime(monkeypatch) -> None:
    """
    If PyMuPDF returns no text for any page, the util must raise RuntimeError.
    """
    class DummyPage:  # noqa: D401 – simple stub
        def get_text(self, *_args, **_kwargs):  # noqa: D401
            return ""

    class DummyDoc(list):  # inherits list so it is iterable like pages
        def __enter__(self):
            return self

        def __exit__(self, *_ex):
            return False

    dummy_doc = DummyDoc([DummyPage(), DummyPage()])

    def fake_open(_path):
        return dummy_doc

    monkeypatch.setattr(pdf_utils.fitz, "open", fake_open)

    with pytest.raises(RuntimeError):
        pdf_utils.PDFTextExtractor.extract_text(Path("/irrelevant.pdf"))
