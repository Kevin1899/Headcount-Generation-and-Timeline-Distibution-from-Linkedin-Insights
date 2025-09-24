# linkedin_insights/timeline_splitter.py

from typing import List, Dict
from .config import BUCKETS


def round_distribution(values: List[float], target_sum: int) -> List[int]:
    """
    Rounds a list of floats to integers so that their sum equals the target_sum.

    Uses Largest Remainder Method (Hamilton method).
    """
    floored = [int(x) for x in values]
    remainder = [x - int(x) for x in values]

    total = sum(floored)
    diff = target_sum - total

    # Add +1 to the items with largest fractional parts
    for i in sorted(range(len(remainder)), key=lambda i: -remainder[i])[:diff]:
        floored[i] += 1

    return floored


def split_headcount_into_buckets(total: int) -> List[Dict]:
    """
    Split the total headcount into predefined timeline buckets.

    Args:
        total (int): Total headcount to be forecasted over the next 12 months.

    Returns:
        List[Dict]: List of dictionaries with `bucket`, `count`, and `justification` (initially empty).
    """
    weights = [weight for _, weight in BUCKETS]
    total_weight = sum(weights)

    # Initial proportional counts (may include decimals)
    raw_counts = [(weight / total_weight) * total for weight in weights]

    # Round proportionally to ensure sum equals total
    rounded_counts = round_distribution(raw_counts, total)

    # Create output bucket structure
    bucket_distribution = []
    for (bucket_label, _), count in zip(BUCKETS, rounded_counts):
        bucket_distribution.append({
            "timeframe": bucket_label,
            "count": count,
            "justification": "",  # to be filled later by LLM
        })

    return bucket_distribution
