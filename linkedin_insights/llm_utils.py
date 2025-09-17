# llm_utils.py

import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not set in .env")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Always use this model
MODEL = "gpt-4o-mini-2024-07-18"

# Optional default system prompt (can be overridden per call)
DEFAULT_SYSTEM_PROMPT = (
    "You are a highly accurate and concise assistant focused on reasoning for workforce planning. "
    "Always return short, factual, and helpful responses based on user prompts. "
    "Avoid repetition. Do not hallucinate insights. Respond only based on the provided prompt or data."
)


def call_gpt(
    prompt: str,
    temperature: float = 0.3,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
) -> str:
    """
    Calls OpenAI ChatCompletion API and returns the raw content string.
    
    Args:
        prompt (str): The user message to send.
        temperature (float): Sampling temperature.
        system_prompt (Optional[str]): Override default system message.
        max_tokens (int): Response token limit.

    Returns:
        str: The response content.
    """
    response = client.chat.completions.create(
        model=MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()
