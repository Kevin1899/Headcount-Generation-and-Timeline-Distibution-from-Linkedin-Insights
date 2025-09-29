# #!/usr/bin/env python3
"""
Location-Aware LinkedIn Insights Headcount Predictor
Supports queries like: "How many AI Engineers will be hired in Greater Bengaluru over the next 12 months?"
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from openai import OpenAI


# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

from linkedin_insights.extractor import extract_insights
from linkedin_insights.headcount_calculator import HeadcountCalculator
from linkedin_insights.timeline_allocator import allocate_buckets
from linkedin_insights.timeline_reasoning_llm import add_reasoning

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def _pretty_table(buckets):
    lines = [
        f"{'Timeframe':<12} | {'Count':>5} | Reasoning",
        "-" * 80,
    ]
    for b in buckets:
        lines.append(f"{b['timeframe']:<12} | {b['count']:>5} | {b['reasoning']}")
    return "\n".join(lines)


def verify_role(
        role: str,
        insights: dict,
        client: OpenAI | None = None,
        verbose: bool = False
    ) -> dict:
        """
        Verify if a given role is relevant for the company insights using OpenAI.

        Args:
            role: Role/job title to verify
            insights: Company insights JSON
            client: Optional OpenAI client
            verbose: If True, print debug info

        Returns:
            dict: {
                'is_relevant': bool,
                'explanation': str
            }
        """
        if client is None:
            client = OpenAI()

        prompt = f"""
You are an expert analyzing company insights to determine if a role is relevant.

Role: "{role}"

Company insights (JSON):
{json.dumps(insights)}

Instructions:
- If the role is clearly represented by any function, skill, or department in the insights, mark it as relevant.
- If the role does not appear in any top functions, skills, or departments, mark it as not relevant.
- Provide a brief explanation supporting your answer.

Return JSON only in this format:
{{
  "is_relevant": true/false,
  "explanation": "short reasoning"
}}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise company insights verification assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        content = response.choices[0].message.content.strip()

        # Remove code fences if present
        if content.startswith("```json"):
            content = content[len("```json"):].strip()
        if content.startswith("```"):
            content = content[len("```"):].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        try:
            output = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError(f"OpenAI did not return valid JSON:\n{content}")

        if verbose:
            print(f"[verify_role] Output from OpenAI: {output}")

        # Ensure keys exist
        is_relevant = output.get("is_relevant", False)
        explanation = output.get("explanation", "")

        return {
            "is_relevant": is_relevant,
            "explanation": explanation
        }


def main():
    parser = argparse.ArgumentParser(description='Location-Aware LinkedIn Insights Headcount Predictor')
    parser.add_argument('pdf_path', help='Path to the LinkedIn Insights PDF file')
    parser.add_argument('--role', '-r', help='Target role to predict (e.g., "AI Engineer")')
    parser.add_argument('--location', '-l', help='Target location (e.g., "Greater Bengaluru")')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--output', '-o', help='Output JSON file path (optional)')

    args = parser.parse_args()

    # Validate arguments
    if not args.role:
        parser.error("Either --role or --query must be provided")
    
    try:
    
        # Step 1: Extract insights from PDF
        logger.info("📊 Extracting LinkedIn insights from PDF...")
        start_time = time.time()
        
        insights_json = extract_insights(args.pdf_path)
        
        extraction_time = time.time() - start_time
        logger.info(f"✅ Insights extracted in {extraction_time:.2f}s")

        logger.info("🔎 Verifying role relevance using OpenAI...")
        verification = verify_role(role = args.role, insights=insights_json, verbose=args.verbose)

        if not verification["is_relevant"]:
            logger.warning(f"❌ Role '{args.role}' is not relevant: {verification['explanation']}")
            print("\n" + "=" * 70)
            print("🌍 LOCATION-AWARE HEADCOUNT PREDICTION RESULTS")
            print("=" * 70)
            print(f"🎯 Role: {args.role}")
            print(f"❌ Not relevant: {verification['explanation']}")
            sys.exit(0)
        
        if args.verbose:
            company_name = insights_json.get('company_profile', {}).get('industry', 'Unknown')
            employee_count = insights_json.get('company_profile', {}).get('employees_current', 0)
            locations = insights_json.get('locations', [])
            logger.info(f"📈 Company: {company_name}, Employees: {employee_count:,}")
            logger.info(f"🌍 Locations available: {len(locations)}")
        
        # Step 2: Determine query type and location
        location_query = args.location
        
        # Step 3: Calculate headcount using location-aware calculator
        logger.info("🧮 Calculating location-aware headcount...")
        calc_start_time = time.time()
        
        calculator = HeadcountCalculator()
        result = calculator.calculate_headcount_prediction(insights_json, args.role, location_query)

        headcount = result['result']['headcount']
        
        calc_time = time.time() - calc_start_time
        logger.info(f"✅ Calculation completed in {calc_time:.3f}s")
        
        # Step 4: Display results
        print("\n" + "=" * 70)
        print("🌍 LOCATION-AWARE HEADCOUNT PREDICTION RESULTS")
        print("=" * 70)
        
        
        print(f"🎯 Role: {args.role}")
        
        # Show location information
        target_location = result['debug_info']['target_location']
        location_info = result['debug_info']['location_info']
        location_flag = result['debug_info']['is_location_valid']
        print(f"Here is the Target Location {target_location} ")
        print(f"Here is the Location Info{location_info}")
        print(f"Here is the Location Flag {location_flag}")
        
        if location_flag and location_info.get('location'):
            print(f"📍 Target Location: {location_info.get('location')}")
            print(f"   Employees: {location_info.get('employees', 0):,}")
            print(f"   Location Share: {result['calc']['inputs']['location_share']:.1%}")
        elif location_info is None or not location_info.get('location'):
            print(f"📍 Target Location: {target_location} (not found in data)")
        else:
            print(f"📍 Scope: Global")
        
        # Show predictions
        print(f"\n📊 PREDICTIONS:")
        print(f"   Global 12-month hires: {result['result']['headcount']}")
        
        if result['result']['location_demand']:
            print(f"   Location-specific hires: {result['result']['location_demand']}")
        
        print(f"   Forecast confidence: {result['result']['forecast_confidence']:.2f}")
        
        if args.verbose:
            print(f"\n🔍 DETAILED BREAKDOWN:")
            inputs = result['calc']['inputs']
            res = result['result']
            
            print(f"  Function: {inputs['function_hint']}")
            print(f"  Function Share: {inputs['function_share']}")
            print(f"  Function Headcount: {inputs['function_headcount']:,}")
            print(f"  Role Share: {inputs['role_share']}")
            print(f"  Attrition Rate: {inputs['attrition_rate']}")
            # print("Location Flag",location_flag)
            matched_skill = result['debug_info']['matched_skill']
            matched_reason = result['debug_info']['match_reason']
            if matched_skill:
                print(f"  Matched Skill: {matched_skill['name']} ({matched_skill['employees']:,} employees) and Reason is : {matched_reason}")
            else:
                print(f"  Matched Skill: None (using department calculation)")
            
            print(f"\n📐 CALCULATION STEPS:")
            # print(f"  Tokens: {result['debug_info']['tokens']}")
            print(f"  Global Calculation:")
            print(f"    Active Demand = ceil({inputs['open_jobs']} × {inputs['function_share']} × {inputs['role_share']}) = {res['active_demand']}")
            print(f"    Growth Demand = ceil({inputs['function_headcount']} × {inputs['growth_rate_percent_1y']/100} × {inputs['role_share']}) = {res['growth_demand']}")
            print(f"    Backfill Demand = ceil({inputs['function_headcount']} × {inputs['attrition_rate']} × {inputs['role_share']}) = {res['backfill_demand']}")
            print(f"    Total = {res['active_demand']} + {res['growth_demand']} + {res['backfill_demand']} = {res['headcount']}")
            
            if location_flag and res['location_demand']:
                print(f"  Location-Specific:")
                print(f"    Location Demand = ceil({res['headcount']} × {inputs['location_share']}) = {res['location_demand']}")
        
        # Step 5: Show available locations
        locations = insights_json.get('locations', [])
        if locations and args.verbose:
            print(f"\n🌍 AVAILABLE LOCATIONS:")
            for loc in locations:
                employees = loc.get('employees', 0)
                share = employees / insights_json.get('company_profile', {}).get('employees_current', 1) * 100
                print(f"   {loc.get('location', 'Unknown')}: {employees:,} employees ({share:.1f}%)")
        
        # Step 6: Allocating Buckets
        logging.info("Allocating hires to timeline buckets …")
        timeline = allocate_buckets(total=headcount, role=args.role, insights=insights_json)
        
       # Step 7: Generate LLM-based reasoning per bucket

        logging.info("Generating reasoning per bucket …")
        timeline = add_reasoning(timeline=timeline, role=args.role, insights=insights_json,full_results=result)
        # Step 8: Performance summary
        total_time = extraction_time + calc_time
        print(f"\n⚡ PERFORMANCE:")
        print(f"  PDF extraction: {extraction_time:.2f}s")
        print(f"  Headcount calculation: {calc_time:.3f}s")
        print(f"  Total time: {total_time:.2f}s")
        
        # Step 9: Save output (if requested)
        if args.output:
            logger.info(f"💾 Saving results to {args.output}")
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
        
            print(f"✅ Results saved to {args.output}")
        # Printing Reasoning
        print(_pretty_table(timeline))
        print(f"\n🎉 Location-aware prediction completed successfully!")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Prediction failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()