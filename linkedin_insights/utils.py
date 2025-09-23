# linkedin_insights/utils.py

import math
from typing import List


def round_distribution(raw_counts: List[float], total: int) -> List[int]:
    """
    Round a list of float counts to integers such that their sum equals `total`.

    Args:
        raw_counts (List[float]): Original float counts.
        total (int): Desired sum of the rounded values.

    Returns:
        List[int]: List of integers summing to `total`.
    """
    floored = [math.floor(x) for x in raw_counts]
    remainder = total - sum(floored)

    # Calculate decimal parts to determine where to add remaining units
    decimals = [(i, raw_counts[i] - floored[i]) for i in range(len(raw_counts))]
    decimals.sort(key=lambda x: x[1], reverse=True)

    # Add 1 to the top `remainder` indices
    for i in range(remainder):
        floored[decimals[i][0]] += 1

    return floored

import math

# Universal arithmetic helper
calc = lambda op, *args: {
    "add":      lambda a: sum(a),
    "sub":      lambda a: a[0] - a[1],
    "mul":      lambda a: math.prod(a),
    "div":      lambda a: a[0] / a[1] if len(a) == 2 else None,
    "ceil":     lambda a: math.ceil(a[0]),
    "floor":    lambda a: math.floor(a[0]),
    "round":    lambda a: round(a[0], int(a[1])) if len(a) == 2 else round(a[0]),
    "min":      lambda a: min(a),
    "max":      lambda a: max(a),
}[op](args)


def compute_forecast(llm_json: dict) -> dict:
    """
    Compute demand values (active_demand, growth_demand, backfill_demand, headcount)
    from the extracted inputs in the LLM JSON.
    """

    # Make a deep copy so we don’t mutate the original
    forecast = copy.deepcopy(llm_json)

    # Extract inputs
    inputs = forecast["calc"]["inputs"]
    open_jobs = inputs.get("open_jobs", 0) or 0
    growth_rate_percent = inputs.get("growth_rate_percent_1y", 0.0) or 0.0
    company_attrition_percent = inputs.get("company_attrition_percent_1y", 0.0) or 0.0
    fs = inputs.get("function_share", 0.0) or 0.0
    fh = inputs.get("function_headcount", 0) or 0
    rs = inputs.get("role_share", 0.0) or 0.0
    ar = inputs.get("attrition_rate", 0.0) or 0.0

    # Step 6. Active Demand
    active_demand = math.ceil(open_jobs * fs * rs)

    # Step 7. Growth Demand
    growth_demand = math.ceil(fh * (growth_rate_percent / 100.0) * rs)

    # Step 8. Backfill Demand
    backfill_demand = math.ceil(fh * ar * rs)

    # Step 9. Headcount Forecast
    headcount = active_demand + growth_demand + backfill_demand

    # Update substitutions
    forecast["calc"]["substitutions"].update({
        "active_demand": active_demand,
        "growth_demand": growth_demand,
        "backfill_demand": backfill_demand,
        "headcount": headcount
    })

    # Update result section
    forecast["result"].update({
        "active_demand": active_demand,
        "growth_demand": growth_demand,
        "backfill_demand": backfill_demand,
        "headcount": headcount
    })

    return forecast

