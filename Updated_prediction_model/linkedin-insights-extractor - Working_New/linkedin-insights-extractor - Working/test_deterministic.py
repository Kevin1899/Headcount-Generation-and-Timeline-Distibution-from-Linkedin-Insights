#!/usr/bin/env python3
"""
Test script to verify deterministic behavior of the LLM predictor.
Stores each run's headcount and confidence into a CSV file.
"""

import json
import csv
import os
from datetime import datetime
from linkedin_insights.extractor import extract_insights
from linkedin_insights.linkedin_insights_llm_predictor import predict_headcount_llm

def test_deterministic_behavior(pdf_path, role, num_runs=3, csv_file="deterministic_results.csv"):
    """Test that multiple runs produce identical results and store them in CSV."""
    print(f"🔍 Testing deterministic behavior for role: '{role}'")
    print(f"📄 PDF: {pdf_path}")
    print(f"🔄 Running {num_runs} times...\n")
    
    # Extract insights once
    print("Extracting insights...")
    insights = extract_insights(pdf_path)
    
    results = []
    for i in range(num_runs):
        print(f"Run {i+1}/{num_runs}...")
        result = predict_headcount_llm(
            insights, 
            role=role, 
            return_full=True, 
            verbose=False
        )
        
        headcount = result.get("result", {}).get("headcount")
        confidence = result.get("result", {}).get("forecast_confidence")
        
        results.append({
            "run": i+1,
            "headcount": headcount,
            "confidence": confidence,
            "full_result": result
        })
        
        print(f"  → Headcount: {headcount}, Confidence: {confidence}")
    
    # Save results to CSV
    write_results_to_csv(results, pdf_path, role, csv_file)
    
    # Check for consistency
    print("\n" + "="*50)
    print("📊 DETERMINISTIC TEST RESULTS")
    print("="*50)
    
    headcounts = [r["headcount"] for r in results]
    confidences = [r["confidence"] for r in results]
    
    headcount_consistent = len(set(headcounts)) == 1
    confidence_consistent = len(set(confidences)) == 1
    
    print(f"Headcounts: {headcounts}")
    print(f"Confidences: {confidences}")
    print(f"Headcount consistent: {'✅ YES' if headcount_consistent else '❌ NO'}")
    print(f"Confidence consistent: {'✅ YES' if confidence_consistent else '❌ NO'}")
    
    if headcount_consistent and confidence_consistent:
        print("\n🎉 SUCCESS: All runs produced identical results!")
        print(f"Final result: Headcount={headcounts[0]}, Confidence={confidences[0]}")
        return True
    else:
        print("\n❌ FAILURE: Results are not deterministic!")
        
        # Show detailed differences
        if not headcount_consistent:
            print(f"Headcount variations: {set(headcounts)}")
        if not confidence_consistent:
            print(f"Confidence variations: {set(confidences)}")
            
        # Show first difference in detail
        print("\nDetailed comparison of first two runs:")
        for key in ["inputs", "confidence"]:
            calc1 = results[0]["full_result"].get("calc", {}).get(key, {})
            calc2 = results[1]["full_result"].get("calc", {}).get(key, {})
            if calc1 != calc2:
                print(f"Difference in {key}:")
                print(f"  Run 1: {json.dumps(calc1, indent=2)}")
                print(f"  Run 2: {json.dumps(calc2, indent=2)}")
        
        return False


def write_results_to_csv(results, pdf_path, role, csv_file):
    """Write headcount and confidence from each run to a CSV file."""
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "pdf_path", "role", "run", "headcount", "confidence"])
        timestamp = datetime.now().isoformat()
        for r in results:
            writer.writerow([timestamp, pdf_path, role, r["run"], r["headcount"], r["confidence"]])
    print(f"\n📂 Results saved to {csv_file}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test_deterministic.py <pdf_path> [role] [num_runs]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    role = sys.argv[2] if len(sys.argv) > 2 else "AI Engineer"
    num_runs = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    
    success = test_deterministic_behavior(pdf_path, role, num_runs)
    sys.exit(0 if success else 1)
