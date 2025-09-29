# linkedin_insights/__init__.py

"""
linkedin_insights
=================

Convert LinkedIn Talent-Insights PDFs into structured JSON metrics.

Public API
----------
extract_insights(pdf_path: Path | str) -> dict
"""
from pathlib import Path
from typing import Any, Dict

from .extractor import extract_insights  # re-export


__all__ = ["extract_insights", "predict_headcount_llm"]
