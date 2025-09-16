"""
pdf_utils.py
============

Helpers for extracting visible text from PDFs via **PyMuPDF (fitz)**.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import fitz  # PyMuPDF


class PDFTextExtractor:
    """Extract plain-text layers from a PDF."""

    @staticmethod
    def extract_text(pdf_path: Path) -> str:
        """
        Concatenate text from all pages.

        Parameters
        ----------
        pdf_path
            Path to the PDF file.

        Returns
        -------
        str
            Combined page text separated by newlines.

        Raises
        ------
        FileNotFoundError
            If `pdf_path` does not exist.
        RuntimeError
            When no text layer exists (likely a scanned PDF).
        """
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        text_parts: List[str] = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text_parts.append(page.get_text("text") or "")

        combined: str = "\n".join(text_parts).strip()
        if not combined:
            raise RuntimeError(
                "No text extracted; the PDF appears to be scan-only. "
                "Add an OCR step if required."
            )
        return combined