# timeline_allocator.py

from linkedin_insights.timeline_splitter import round_distribution  # ✅ import the correct rounding method

BUCKETS = [
    ("0–1 month", 1),
    ("1–3 months", 2),
    ("3–6 months", 3),
    ("6–9 months", 3),
    ("9+ months", 3),  # treated as “rest of year”
]

def allocate_buckets(total, role, insights):
    """
    Distribute total headcount across timeline buckets proportionally.
    Returns a list of {timeframe, count} dicts.
    """
    weights = [weight for _, weight in BUCKETS]
    total_weight = sum(weights)

    # Use float ratios to compute raw counts
    raw_counts = [(weight / total_weight) * total for weight in weights]

    # ✅ Use Hamilton method to fix rounding error
    rounded_counts = round_distribution(raw_counts, total)

    # Build timeline with correct counts
    timeline = []
    for (timeframe, _), count in zip(BUCKETS, rounded_counts):
        timeline.append({
            "timeframe": timeframe,
            "count": count,
        })

    return timeline
