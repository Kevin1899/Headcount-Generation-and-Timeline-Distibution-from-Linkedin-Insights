from pathlib import Path
import argparse
import logging
import json
import csv
from datetime import datetime

from linkedin_insights.extractor import extract_insights
from linkedin_insights.linkedin_insights_llm_predictor import predict_headcount_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def _normalize_prediction(pred):
    """
    Accepts the full dictionary from predict_headcount_llm.
    Returns (total_hires, forecast_confidence, details_dict).
    Returns None for confidence if it's not explicitly found.
    """
    if not isinstance(pred, dict):
        return None, None, {"raw": pred}

    result_section = pred.get("result") or {}
    total = (
        result_section.get("headcount")
        or pred.get("headcount")
    )
    
    # Return the actual confidence score, or None if it's missing
    confidence = result_section.get("forecast_confidence")

    return total, confidence, pred

def _append_csv(row: dict, out_path: Path):
    """Append a dictionary row to a CSV file with fixed headers."""
    file_exists = out_path.exists() and out_path.stat().st_size > 0
    
    # Use a fixed, stable set of columns for the CSV output
    fieldnames = ["timestamp", "pdf", "role", "run_index", "total_hires", "forecast_confidence"]

    with out_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def _append_jsonl(obj: dict, out_path: Path):
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def main() -> None:
    """CLI entry-point: PDF → JSON → head-count forecast."""
    parser = argparse.ArgumentParser(
        description="Predict 12-month head-count for a target role using LinkedIn Talent-Insights data.",
    )
    parser.add_argument("pdf", type=Path, help="Path to the Talent-Insights PDF (e.g. Microsoft_APAC.pdf)")
    parser.add_argument("--role", "-r", default="AI Engineer", help="Target role to forecast (default: AI Engineer)")
    parser.add_argument(
        "--runs", "-n",
        type=int,
        default=1,
        help="How many times to run predictions per role (default: 1)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print intermediate variables from the LLM chain")
    parser.add_argument("--out", "-o", type=Path, default=Path("results.csv"),
                        help="Output file to append results (default: results.csv)")
    parser.add_argument("--format", "-f", choices=["csv", "jsonl"], default="csv",
                        help="Results file format (default: csv)")
    args = parser.parse_args()

    logging.info("Extracting Insights JSON …")
    insights = extract_insights(args.pdf)
    
    pdf_name = args.pdf.name
    successful_runs = 0

    for i in range(args.runs):
        run_number = i + 1
        timestamp_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        logging.info(f"\n▶ Run {run_number}/{args.runs} → Predicting head-count for role: '{args.role}'\n")
        
        # Always request the full response to get the confidence score
        pred = predict_headcount_llm(insights, role=args.role, verbose=args.verbose, return_full=True)
        total, confidence, details = _normalize_prediction(pred)

        # Only save the run if we have both a headcount and a confidence score
        if total is not None and confidence is not None:
            print("\n===========================================")
            print(f"Run {run_number}: '{args.role}' → Headcount={total} | Confidence={confidence:.2f}")
            print("===========================================\n")

            record = {
                "timestamp": timestamp_iso,
                "pdf": pdf_name,
                "role": args.role,
                "run_index": run_number,
                "total_hires": total,
                "forecast_confidence": confidence
            }
            
            if isinstance(details, dict) and args.format == 'jsonl':
                record["details_json"] = json.dumps(details, ensure_ascii=False)

            args.out.parent.mkdir(parents=True, exist_ok=True)
            if args.format == "csv":
                _append_csv(record, args.out)
            else:
                _append_jsonl(record, args.out)
            
            successful_runs += 1
        else:
            logging.warning(f"Run {run_number} skipped because a valid headcount or confidence score was not returned.")

    logging.info(f"Results for {successful_runs}/{args.runs} successful runs appended to: {args.out.resolve()} ({args.format})")

if __name__ == "__main__":
    main()
