#extractor.py

import re
from pathlib import Path
from .pdf_utils import PDFTextExtractor
from .prompt_templates import USER_TEMPLATE
from .openai_client import chat_to_json

def extract_insights(pdf_path: str | Path) -> dict:
    path = Path(pdf_path)
    
    # 1) grab raw text
    raw_text = PDFTextExtractor.extract_text(path)
    
    # 2) isolate just the “Overview” metrics block on page 2
    #    (EMPLOYEES, HIRES, ATTRITION, JOBS)
    m = re.search(
        r"EMPLOYEES\s+The number of employees.*?\n"
        r"(\d{1,3}(?:,\d{3})*)\s*\n"       # employees
        r"(\d{1,3}(?:,\d{3})*)\s*\n"       # hires
        r"(\d{1,3})%\s*\n"                 # attrition %
        r"(\d{1,3}(?:,\d{3})*)\s*\n",      # jobs
        raw_text,
        re.S
    )
    if not m:
        # fallback: send all text to LLM if block not found
        snippet = raw_text
    else:
        employees, hires, attr_pct, jobs = m.groups()
        snippet = (
            f"EMPLOYEES: {employees}\n"
            f"HIRES: {hires}\n"
            f"ATTRITION: {attr_pct}%\n"
            f"JOBS: {jobs}\n\n"
            # then append the rest of raw_text so you still get locations etc.
            + raw_text
        )
    
    # write debug dump of exactly what you’re sending to file
    Path("debug_output.txt").write_text(snippet, encoding="utf-8")
    
    # build prompt from this cleaned snippet
    user_prompt = USER_TEMPLATE.format(insights_text=snippet)
    return chat_to_json(user_prompt)
