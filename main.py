# main.py — PDF → JSON → Headcount Forecast → Timeline Split + LLM Reasoning

from pathlib import Path
import argparse
import logging
import json

from linkedin_insights.extractor import extract_insights
from linkedin_insights.linkedin_insights_llm_predictor import predict_headcount_llm
from linkedin_insights.timeline_allocator import allocate_buckets
from linkedin_insights.timeline_reasoning_llm import add_reasoning

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def _pretty_table(buckets):
    lines = [
        f"{'Timeframe':<12} | {'Count':>5} | Reasoning",
        "-" * 80,
    ]
    for b in buckets:
        lines.append(f"{b['timeframe']:<12} | {b['count']:>5} | {b['reasoning']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Predict 12‑month head‑count and generate timeline breakdown for a target role."
    )
    parser.add_argument("pdf", type=Path, help="Path to LinkedIn Insights PDF")
    parser.add_argument("--role", "-r", default="AI Engineer", help="Target role to forecast")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print predictor debug")
    parser.add_argument("--json-only", action="store_true", help="Output timeline as raw JSON")
    args = parser.parse_args()

    # Step 1: Extract insights
    logging.info("Extracting Insights JSON …")
    insights = extract_insights(args.pdf)
    print(f"\nExtracted Insights JSON:{json.dumps(insights, indent=2)}...\n")

    # Step 2: Predict headcount (and get confidence)
    logging.info("\n▶ Running LLM head‑count predictor …\n")
    full_result = predict_headcount_llm(insights, role=args.role, verbose=args.verbose, return_full=True)

    headcount = full_result["result"]["headcount"]
    confidence = full_result["result"]["forecast_confidence"]

    print("\n===========================================")
    print(f"Predicted 12‑month hires for {args.role}: {headcount}")
    print(f"Forecast confidence: {confidence}")
    print("===========================================\n")

    # Step 3: Allocate to timeline buckets
    logging.info("Allocating hires to timeline buckets …")
    timeline = allocate_buckets(headcount, args.role, insights)

    # Step 4: Generate LLM-based reasoning per bucket
    logging.info("Generating reasoning per bucket …")
    timeline = add_reasoning(timeline, args.role, insights)

    # Step 5: Output
    if args.json_only:
        print(json.dumps(timeline, indent=2, ensure_ascii=False))
    else:
        print(_pretty_table(timeline))


if __name__ == "__main__":
    main()
