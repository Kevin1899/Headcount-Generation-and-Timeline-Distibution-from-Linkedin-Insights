"""
Integration-ish test for extractor.extract_insights.

We stub out PDF extraction and OpenAI, verifying the glue code works.
"""
from pathlib import Path
from typing import Any, Dict

import linkedin_insights.extractor as extractor


def test_extract_insights_happy_path(monkeypatch, tmp_path: Path) -> None:
    """Extractor returns whatever chat_to_json returns when all stubs OK."""
    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_text("does not matter")  # file must exist

    # 1. Stub PDFTextExtractor to avoid fitz
    monkeypatch.setattr(
        extractor.PDFTextExtractor,
        "extract_text",
        lambda _p: "dummy raw text",
        raising=True,
    )

    # 2. Stub chat_to_json to avoid OpenAI
    expected: Dict[str, Any] = {"company_profile": {"employees_current": 10}}
    monkeypatch.setattr(
        extractor, "chat_to_json", lambda _p: expected, raising=True
    )

    result = extractor.extract_insights(dummy_pdf)
    assert result == expected