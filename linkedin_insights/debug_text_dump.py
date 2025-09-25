"""
debug_text_dump.py
==================

Extracts raw text from a LinkedIn Talent Insights PDF and saves it to a file.

Usage:
    python debug_text_dump.py /path/to/Insights.pdf
"""

import argparse
from pathlib import Path
from linkedin_insights.pdf_utils import PDFTextExtractor

def main():
    parser = argparse.ArgumentParser(description="Extract raw PDF text only.")
    parser.add_argument("pdf", type=Path, help="Path to PDF file")
    args = parser.parse_args()

    # Extract raw text from the PDF
    raw_text = PDFTextExtractor.extract_text(args.pdf)

    # Write to debug output file
    debug_file = Path("debug_output.txt")
    debug_file.write_text(raw_text, encoding="utf-8")

    print(f"✅ Raw text extracted to: {debug_file.resolve()}")

if __name__ == "__main__":
    main()