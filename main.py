# main.py — PDF → JSON → Headcount Forecast → Timeline Split + LLM Reasoning

from pathlib import Path
import argparse
import logging
import json
import hashlib


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

def get_cache_key(pdf_path: Path) -> str:
    """Generate a unique cache key based on file path and modification time."""
    # Get file stats for modification time
    stat = pdf_path.stat()
    # Create a unique key using file path and modification time
    key = f"{pdf_path.resolve()}:{stat.st_mtime}"
    # Return MD5 hash of the key
    return hashlib.md5(key.encode()).hexdigest()

def get_cached_insights(cache_key: str) -> dict | None:
    """Retrieve cached insights if they exist."""
    cache_dir = Path(".insights_cache")
    cache_file = cache_dir / f"{cache_key}.json"
    
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logging.warning(f"Error reading cache file {cache_file}: {e}")
            return None
    return None

def save_insights_to_cache(cache_key: str, insights: dict) -> None:
    """Save insights to cache."""
    cache_dir = Path(".insights_cache")
    try:
        cache_dir.mkdir(exist_ok=True)
        cache_file = cache_dir / f"{cache_key}.json"
        cache_file.write_text(json.dumps(insights, indent=2))
    except OSError as e:
        logging.warning(f"Could not save insights to cache: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Predict 12‑month head‑count and generate timeline breakdown for a target role."
    )
    parser.add_argument("pdf", type=Path, help="Path to LinkedIn Insights PDF")
    parser.add_argument("--role", "-r", default="AI Engineer", help="Target role to forecast")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print predictor debug")
    parser.add_argument("--json-only", action="store_true", help="Output timeline as raw JSON")
    parser.add_argument("--force-update", action="store_true", help="Force update the cache even if cached version exists")
    args = parser.parse_args()

    # Step 1: Extract insights
    if not args.pdf.exists():
        raise FileNotFoundError(f"PDF file not found: {args.pdf}")

    cache_key = get_cache_key(args.pdf)
    insights = None
    
    # Try to get cached insights if not forcing an update
    if not args.force_update:
        insights = get_cached_insights(cache_key)
        if insights:
            logging.info("Using cached insights")
    
    # If no cache hit or force update, extract fresh insights
    if not insights:
        logging.info("Extracting Insights JSON (this may take a moment)...")
        insights = extract_insights(args.pdf)
        # Save to cache
        save_insights_to_cache(cache_key, insights)
        logging.info("Saved insights to cache")
    
    if args.verbose:
        print(f"\nExtracted Insights JSON:{json.dumps(insights, indent=2)}...\n")


    # Step 2: Predict headcount (and get confidence)
    logging.info("\n▶ Running LLM head‑count predictor …\n")
    full_result = predict_headcount_llm(insights, role=args.role, verbose=args.verbose, return_full=True)
    
    # logging.info("\n▶ This is Manually Extracting the Data")
    # calc_results = building_step_3(insights=insights,role=args.role)
    # try:
    #  json_str = json.dumps(calc_results, indent=2)
    #  print(json_str)
    # except TypeError as e:
    #  logging.error(f"JSON serialization error: {e}")


    headcount = full_result['headcount']
    # confidence = full_result["result"]["forecast_confidence"]

    # print(f"This is Results {full_result}")

    print("\n===========================================")
    print(f"Predicted 12‑month hires for {args.role}: {headcount}")
    # print(f"Forecast confidence: {confidence}")
    print("===========================================\n")

    # # Step 3: Allocate to timeline buckets
    logging.info("Allocating hires to timeline buckets …")
    timeline = allocate_buckets(headcount, args.role, insights)

    # # Step 4: Generate LLM-based reasoning per bucket
    logging.info("Generating reasoning per bucket …")
    timeline = add_reasoning(timeline, args.role, insights)

    # # Step 5: Output
    if args.json_only:
        print(json.dumps(timeline, indent=2, ensure_ascii=False))
    else:
        print(_pretty_table(timeline))


if __name__ == "__main__":
    main()
