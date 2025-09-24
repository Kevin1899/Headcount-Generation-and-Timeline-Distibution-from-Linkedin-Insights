# timeline_reasoning_llm.py

from linkedin_insights.llm_utils import call_gpt


def add_reasoning(timeline, role, insights):
    """
    Given a list of {timeframe, count}, returns the same list with LLM-generated 'reasoning' added per bucket.
    Uses a single GPT call to generate all justifications.
    """
    prompt = build_combined_prompt(timeline, role, insights)
    response = call_gpt(prompt, temperature=0.3)

    # Parse bullet point responses
    justifications = parse_justifications(response, len(timeline))

    # Attach reasoning per bucket
    updated = []
    for i, bucket in enumerate(timeline):
        updated.append({
            "timeframe": bucket["timeframe"],
            "count": bucket["count"],
            "reasoning": justifications[i],
        })

    return updated


def build_combined_prompt(timeline, role, insights):
    """
    Builds a single prompt that asks GPT to generate justifications for all timeline buckets at once.
    """
    timeline_description = "\n".join(
        f"- {bucket['timeframe']}: {bucket['count']} hire(s)" for bucket in timeline
    )

    return f"""
You are an expert in strategic workforce planning.

A company is hiring for the role of **{role}**. Here is the planned hiring breakdown across timeframes:

{timeline_description}

You are provided with LinkedIn Talent Insights (in JSON format) that include patterns in attrition, job transitions, tenure, demand-supply, and skill shortages.

Your task:
- Write one **justification per timeframe** (in the same order).
- Each justification should be 2–3 sentences long and based on the insights.
- Justify why hiring **that number of people in that timeframe** makes sense.
- Focus on **market timing, demand spikes, attrition periods, or budget cycles**.
- Avoid generic language and copy-paste phrasing across timeframes.

Return your answer as exactly 5 bullet points (no titles, no intro).

Insights (JSON):
{insights}
""".strip()


def parse_justifications(response: str, expected_count: int) -> list:
    """
    Extracts bullet point justifications from GPT response text.
    Returns a list of strings aligned with the timeline order.
    Pads or trims if mismatch in count.
    """
    lines = response.splitlines()
    bullets = [
        line.lstrip("-•0123456789. ").strip()
        for line in lines
        if line.strip() and not line.lower().startswith("insight")  # skip junk
    ]

    # Pad or trim to match timeline length
    if len(bullets) < expected_count:
        bullets += [""] * (expected_count - len(bullets))
    else:
        bullets = bullets[:expected_count]

    return bullets
