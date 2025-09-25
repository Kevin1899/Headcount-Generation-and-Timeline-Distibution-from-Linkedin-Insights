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
