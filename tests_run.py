# from pathlib import Path
# import argparse
# import logging
# import json
# import csv
# from datetime import datetime

# from linkedin_insights.extractor import extract_insights
# from linkedin_insights.linkedin_insights_llm_predictor import predict_headcount_llm

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
# )

# def _normalize_prediction(pred):
#     """
#     Accept either an int or a dict from predict_headcount_llm.
#     Returns (total_hires: int|None, details: dict|None).
#     """
#     if isinstance(pred, int):
#         return pred, None
#     if isinstance(pred, dict):
#         # Common keys you might produce later:
#         total = (
#             pred.get("total_headcount")
#             or pred.get("total_hires")
#             or pred.get("predicted_total")
#         )
#         return total, pred
#     return None, {"raw": pred}

# def _append_csv(row: dict, out_path: Path):
#     file_exists = out_path.exists()
#     # Ensure stable column order; include dynamic keys if present
#     base_fields = ["timestamp", "pdf", "role", "run_index", "total_hires"]
#     extra_fields = sorted([k for k in row.keys() if k not in base_fields])
#     fieldnames = base_fields + extra_fields

#     # If file exists but with different header, we still rewrite header for safety
#     with out_path.open("a", newline="", encoding="utf-8") as f:
#         writer = csv.DictWriter(f, fieldnames=fieldnames)
#         if not file_exists:
#             writer.writeheader()
#         writer.writerow(row)

# def _append_jsonl(obj: dict, out_path: Path):
#     with out_path.open("a", encoding="utf-8") as f:
#         f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# def main() -> None:
#     """CLI entry-point: PDF → JSON → head-count forecast."""
#     parser = argparse.ArgumentParser(
#         description="Predict 12-month head-count for a target role using LinkedIn Talent-Insights data.",
#     )
#     parser.add_argument("pdf", type=Path, help="Path to the Talent-Insights PDF (e.g. Microsoft_APAC.pdf)")
#     parser.add_argument("--role", "-r", default="AI Engineer", help="Target role to forecast (default: AI Engineer)")
#     parser.add_argument(
#         "--runs", "-n",
#         type=int,
#         default=1,
#         help="How many times to run predictions per role (default: 1)"
#     )
#     parser.add_argument("--verbose", "-v", action="store_true", help="Print intermediate variables from the LLM chain")
#     parser.add_argument("--out", "-o", type=Path, default=Path("results.csv"),
#                         help="Output file to append results (default: results.csv)")
#     parser.add_argument("--format", "-f", choices=["csv", "jsonl"], default="csv",
#                         help="Results file format (default: csv)")
#     args = parser.parse_args()

#     logging.info("Extracting Insights JSON …")
#     insights = extract_insights(args.pdf)
#     print(f"\nExtracted Insights JSON:{json.dumps(insights, indent=2)}...\n")

#     timestamp_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
#     pdf_name = args.pdf.name

#     for i in range(args.runs):
#         logging.info(f"\n▶ Run {i+1}/{args.runs} → Predicting head-count for role: {args.role}\n")
#         pred = predict_headcount_llm(insights, role=args.role, verbose=args.verbose)
#         total, details = _normalize_prediction(pred)

#         print("\n===========================================")
#         print(f"Predicted 12-month hires for {args.role} (Run {i+1}): {total:,}" if isinstance(total, int) else
#               f"Predicted 12-month hires for {args.role} (Run {i+1}): {total}")
#         print("===========================================\n")

#         # Build a single record to store
#         record = {
#             "timestamp": timestamp_iso,
#             "pdf": pdf_name,
#             "role": args.role,
#             "run_index": i + 1,
#             "total_hires": total,
#         }
#         # If details exist (e.g., timeline_distribution), flatten minimally or store raw object
#         if isinstance(details, dict) and details:
#             # Store raw JSON as a string column for CSV, or as nested in JSONL
#             record["details_json"] = json.dumps(details, ensure_ascii=False)

#         # Append to the chosen output format
#         args.out.parent.mkdir(parents=True, exist_ok=True)
#         if args.format == "csv":
#             _append_csv(record, args.out)
#         else:
#             _append_jsonl(record, args.out)

#     logging.info(f"Results appended to: {args.out.resolve()} ({args.format})")

# if __name__ == "__main__":
#     main()

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
    Accept either an int or a dict from predict_headcount_llm.
    Returns (total_hires, forecast_confidence, details_dict).
    """
    if isinstance(pred, int):
        return pred, None, None

    if isinstance(pred, dict):
        # Prefer the new structured format
        result_section = pred.get("result") or {}
        total = (
            result_section.get("headcount")
            or pred.get("headcount")
            or pred.get("total_headcount")
            or pred.get("total_hires")
            or pred.get("predicted_total")
        )
        confidence = (
            result_section.get("forecast_confidence")
            or pred.get("forecast_confidence")
        )
        return total, confidence, pred

    return None, None, {"raw": pred}

def _append_csv(row: dict, out_path: Path):
    file_exists = out_path.exists()
    # Ensure stable column order; include dynamic keys if present
    base_fields = ["timestamp", "pdf", "role", "run_index", "total_hires", "forecast_confidence"]
    extra_fields = sorted([k for k in row.keys() if k not in base_fields])
    fieldnames = base_fields + extra_fields

    with out_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
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
    print(f"\nExtracted Insights JSON:{json.dumps(insights, indent=2)}...\n")

    pdf_name = args.pdf.name

    for i in range(args.runs):
        timestamp_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        logging.info(f"\n▶ Run {i+1}/{args.runs} → Predicting head-count for role: {args.role}\n")
        pred = predict_headcount_llm(insights, role=args.role, verbose=args.verbose)
        total, confidence, details = _normalize_prediction(pred)

        print("\n===========================================")
        print(f"Run {i+1}: {args.role} → score={total}  confidence={confidence}")
        print("===========================================\n")

        # Build a single record to store
        record = {
            "timestamp": timestamp_iso,
            "pdf": pdf_name,
            "role": args.role,
            "run_index": i + 1,
            "total_hires": total,
            "forecast_confidence": confidence
        }

        # If details exist (e.g., full JSON returned by LLM), store it
        if isinstance(details, dict) and details:
            record["details_json"] = json.dumps(details, ensure_ascii=False)

        # Append to the chosen output format
        args.out.parent.mkdir(parents=True, exist_ok=True)
        if args.format == "csv":
            _append_csv(record, args.out)
        else:
            _append_jsonl(record, args.out)

    logging.info(f"Results appended to: {args.out.resolve()} ({args.format})")

if __name__ == "__main__":
    main()
