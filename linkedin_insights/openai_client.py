"""
openai_client.py

Wrapper around OpenAI client API using the newer SDK (>=1.0.0)
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from typing import Any

# Load API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not set in .env")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

MODEL = "gpt-4o-mini-2024-07-18"
SYSTEM_PROMPT = (
    "You are an expert at extracting structured JSON data from business reports."
    "Read noisy LinkedIn Talent Insights text and output one strict JSON object. "
    "Always match numbers carefully to their labels. "
    "Do not confuse 'attrition' (a percentage), 'open jobs' (a count), or 'growth' (a %). "
    "Convert textual numbers to plain numerics. Use null for missing values. "
    "Only return values with strong evidence in the text. Never guess or infer."
    "No commentary, no markdown."
)


def chat_to_json(user_prompt: str) -> dict[str, Any]:
    """
    Call GPT-4o-mini with a system/user prompt and return parsed JSON.
    """
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        max_tokens=8192,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return json.loads(response.choices[0].message.content)
