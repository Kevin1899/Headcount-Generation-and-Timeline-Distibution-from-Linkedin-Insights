"""
cli.py
======

Console entry-point:

    python linkedin_insights/cli.py /path/to/Insights.pdf
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from pprint import pp

from .extractor import extract_insights

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

def main() -> None:
    """Parse CLI args and run the extraction."""
    parser = argparse.ArgumentParser(
        description="Convert a LinkedIn Talent Insights PDF to JSON."
    )
    parser.add_argument("pdf", type=Path, help="Path to Insights PDF")
    args = parser.parse_args()

    result = extract_insights(args.pdf)
    pp(result)

if __name__ == "__main__":
    main()
