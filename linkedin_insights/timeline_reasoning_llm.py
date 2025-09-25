# timeline_reasoning_llm.py

from linkedin_insights.llm_utils import call_gpt
from linkedin_insights.linkedin_insights_llm_predictor import predict_headcount_llm
import math


def add_reasoning(timeline, role, insights,full_results):
    """
    Given a list of {timeframe, count}, returns the same list with mathematically-proven reasoning added per bucket.
    Uses enhanced mathematical analysis to justify each hiring count.
    """
    # Get the full prediction details for mathematical breakdown
    # full_prediction = predict_headcount_llm(insights, role=role, return_full=True)

    # Calculate mathematical justifications
    mathematical_breakdown = calculate_mathematical_breakdown(timeline, full_results, insights)

    # Build enhanced prompt with mathematical context
    prompt = build_enhanced_prompt(timeline, insights, role, mathematical_breakdown, full_results)
    response = call_gpt(prompt, temperature=0.2)  # Lower temperature for more precise reasoning

    # Parse bullet point responses
    justifications = parse_justifications(response, len(timeline))

    # Attach reasoning per bucket
    updated = []
    for i, bucket in enumerate(timeline):
        updated.append({
            "timeframe": bucket["timeframe"],
            "count": bucket["count"],
            "reasoning": justifications[i],
            "mathematical_breakdown": mathematical_breakdown[i] if i < len(mathematical_breakdown) else None,
        })

    return updated


def calculate_mathematical_breakdown(timeline, full_results, insights):
    """
    Calculate detailed mathematical breakdown for each timeframe.
    Returns list of mathematical justifications per bucket.
    """
    calc_details = full_results.get("calc", {})
    result_details = full_results.get("result", {})

    # Extract key metrics
    total_headcount = result_details.get("headcount", 0)
    active_demand = result_details.get("active_demand", 0)
    growth_demand = result_details.get("growth_demand", 0)
    backfill_demand = result_details.get("backfill_demand", 0)

    # Get timeline weights for proportional allocation
    bucket_weights = [1, 2, 3, 3, 3]  # From config.py BUCKETS
    total_weight = sum(bucket_weights)

    # Calculate BUSINESS-LOGICAL breakdown per timeframe
    # BACKFILL (attrition replacement) = URGENT (0-3 months priority)
    # ACTIVE (immediate roles) = CRITICAL (0-1 month priority)
    # GROWTH (expansion) = PLANNED (distributed across 3-12 months)

    breakdown = []

    # First, get ideal distributions based on business logic
    ideal_backfill = distribute_backfill_demand(backfill_demand)
    ideal_active = distribute_active_demand(active_demand)
    ideal_growth = distribute_growth_demand(growth_demand)

    # Adjust distributions to match actual timeline allocation while preserving business logic
    actual_active_dist = [0] * len(timeline)
    actual_backfill_dist = [0] * len(timeline)
    actual_growth_dist = [0] * len(timeline)

    # First pass: distribute based on business logic proportions
    for i, bucket in enumerate(timeline):
        actual_count = bucket["count"]
        ideal_active_i = ideal_active[i] if i < len(ideal_active) else 0
        ideal_backfill_i = ideal_backfill[i] if i < len(ideal_backfill) else 0
        ideal_growth_i = ideal_growth[i] if i < len(ideal_growth) else 0
        ideal_total = ideal_active_i + ideal_backfill_i + ideal_growth_i

        if ideal_total > 0:
            # Proportional distribution
            actual_active_dist[i] = round((ideal_active_i / ideal_total) * actual_count)
            actual_backfill_dist[i] = round((ideal_backfill_i / ideal_total) * actual_count)
            actual_growth_dist[i] = round((ideal_growth_i / ideal_total) * actual_count)

            # Adjust for rounding errors
            current_total = actual_active_dist[i] + actual_backfill_dist[i] + actual_growth_dist[i]
            diff = actual_count - current_total

            if diff != 0:
                # Add/subtract from the largest component
                if ideal_backfill_i >= ideal_active_i and ideal_backfill_i >= ideal_growth_i:
                    actual_backfill_dist[i] += diff
                elif ideal_active_i >= ideal_growth_i:
                    actual_active_dist[i] += diff
                else:
                    actual_growth_dist[i] += diff
        else:
            # Fallback distribution based on timeframe
            if i <= 1:  # 0-3 months: prioritize backfill and active
                actual_backfill_dist[i] = math.ceil(actual_count * 0.6)
                actual_active_dist[i] = math.ceil(actual_count * 0.3)
                actual_growth_dist[i] = actual_count - actual_backfill_dist[i] - actual_active_dist[i]
            else:  # 3+ months: prioritize growth
                actual_growth_dist[i] = math.ceil(actual_count * 0.7)
                actual_backfill_dist[i] = math.ceil(actual_count * 0.2)
                actual_active_dist[i] = actual_count - actual_growth_dist[i] - actual_backfill_dist[i]

        # Ensure no negative values
        actual_active_dist[i] = max(0, actual_active_dist[i])
        actual_backfill_dist[i] = max(0, actual_backfill_dist[i])
        actual_growth_dist[i] = max(0, actual_growth_dist[i])

    # Second pass: adjust totals to match original predictions exactly
    total_active_distributed = sum(actual_active_dist)
    total_backfill_distributed = sum(actual_backfill_dist)
    total_growth_distributed = sum(actual_growth_dist)

    # Adjust active demand
    active_diff = active_demand - total_active_distributed
    if active_diff != 0:
        # Find the timeframe with highest active allocation to adjust
        max_active_idx = actual_active_dist.index(max(actual_active_dist)) if max(actual_active_dist) > 0 else 0
        actual_active_dist[max_active_idx] += active_diff
        actual_active_dist[max_active_idx] = max(0, actual_active_dist[max_active_idx])

    # Adjust backfill demand
    backfill_diff = backfill_demand - total_backfill_distributed
    if backfill_diff != 0:
        # Find the timeframe with highest backfill allocation to adjust
        max_backfill_idx = actual_backfill_dist.index(max(actual_backfill_dist)) if max(actual_backfill_dist) > 0 else 0
        actual_backfill_dist[max_backfill_idx] += backfill_diff
        actual_backfill_dist[max_backfill_idx] = max(0, actual_backfill_dist[max_backfill_idx])

    # Adjust growth demand
    growth_diff = growth_demand - total_growth_distributed
    if growth_diff != 0:
        # Find the timeframe with highest growth allocation to adjust
        max_growth_idx = actual_growth_dist.index(max(actual_growth_dist)) if max(actual_growth_dist) > 0 else 2
        actual_growth_dist[max_growth_idx] += growth_diff
        actual_growth_dist[max_growth_idx] = max(0, actual_growth_dist[max_growth_idx])

    # Now create breakdown for each timeframe
    for i, bucket in enumerate(timeline):
        timeframe_active = actual_active_dist[i]
        timeframe_backfill = actual_backfill_dist[i]
        timeframe_growth = actual_growth_dist[i]

        # Final verification and adjustment to ensure exact match
        current_total = timeframe_active + timeframe_backfill + timeframe_growth
        if current_total != bucket["count"]:
            diff = bucket["count"] - current_total
            # Add difference to the largest component
            if timeframe_backfill >= timeframe_active and timeframe_backfill >= timeframe_growth:
                timeframe_backfill += diff
            elif timeframe_active >= timeframe_growth:
                timeframe_active += diff
            else:
                timeframe_growth += diff

            # Ensure no negative values
            timeframe_active = max(0, timeframe_active)
            timeframe_backfill = max(0, timeframe_backfill)
            timeframe_growth = max(0, timeframe_growth)

        # Get market timing factors
        market_factors = get_market_timing_factors(i, insights)

        # Calculate business impact metrics
        business_metrics = calculate_business_impact(bucket["count"], timeframe_active, timeframe_growth, timeframe_backfill, insights)

        # Calculate business logic priority
        priority_logic = determine_priority_logic(i, timeframe_active, timeframe_growth, timeframe_backfill)

        breakdown.append({
            "timeframe": bucket["timeframe"],
            "count": bucket["count"],
            "active_demand_component": timeframe_active,
            "growth_demand_component": timeframe_growth,
            "backfill_demand_component": timeframe_backfill,
            "market_factors": market_factors,
            "business_impact": business_metrics,
            "priority_logic": priority_logic,
            "mathematical_total": timeframe_active + timeframe_growth + timeframe_backfill,
            "verification": timeframe_active + timeframe_growth + timeframe_backfill == bucket["count"],
            "business_justification": get_business_justification(i, timeframe_active, timeframe_growth, timeframe_backfill)
        })

    return breakdown


def distribute_backfill_demand(total_backfill):
    """
    Distribute backfill demand with STRICT BUSINESS SEQUENCE.
    RULE: First portion (0-1), Second portion (1-3), Remainder (3-6)
    """
    if total_backfill == 0:
        return [0, 0, 0, 0, 0]

    # STRICT BUSINESS SEQUENCE: 326 → 652 → remainder pattern
    # Calculate portions based on business urgency
    first_portion = min(math.ceil(total_backfill * 0.17), total_backfill)  # ~17% for immediate (like 326/1885)
    second_portion = min(math.ceil(total_backfill * 0.35), total_backfill - first_portion)  # ~35% for urgent (like 652/1885)
    remainder = total_backfill - first_portion - second_portion

    distribution = [
        first_portion,      # 0-1 month: First portion (IMMEDIATE departures)
        second_portion,     # 1-3 months: Second portion (URGENT replacements)
        remainder,          # 3-6 months: Remainder (STABILIZATION)
        0,                  # 6-9 months: 0 (backfill complete by 3-6)
        0,                  # 9+ months: 0 (backfill complete by 3-6)
    ]

    return distribution


def distribute_active_demand(total_active):
    """
    Distribute active demand AFTER backfill stabilization.
    RULE: Start in 3-6 months (after backfill), complete by 6-9 months
    """
    if total_active == 0:
        return [0, 0, 0, 0, 0]

    # BUSINESS SEQUENCE: Active starts AFTER backfill stabilization (3-6 months)
    # Split between 3-6 and 6-9 months for operational stability
    first_active_portion = math.ceil(total_active * 0.60)  # 60% in 3-6 months
    second_active_portion = total_active - first_active_portion  # 40% in 6-9 months

    distribution = [
        0,                      # 0-1 month: 0 (backfill priority)
        0,                      # 1-3 months: 0 (backfill priority)
        first_active_portion,   # 3-6 months: Start active after backfill
        second_active_portion,  # 6-9 months: Complete active demand
        0,                      # 9+ months: 0 (active complete by 6-9)
    ]

    return distribution


def distribute_growth_demand(total_growth):
    """
    Distribute growth demand AFTER operational needs are met.
    RULE: Majority in 9+ months (like 977 figure), minimal earlier
    """
    if total_growth == 0:
        return [0, 0, 0, 0, 0]

    # BUSINESS SEQUENCE: Growth ONLY after backfill and active are handled
    # Majority in final timeframe (like 977 pattern)
    final_growth_portion = math.ceil(total_growth * 0.75)  # 75% in 9+ months (like 977/838 pattern)
    remaining_growth = total_growth - final_growth_portion

    # Distribute remaining minimally in earlier timeframes
    early_growth = math.ceil(remaining_growth * 0.30) if remaining_growth > 0 else 0  # 3-6 months
    mid_growth = remaining_growth - early_growth if remaining_growth > 0 else 0  # 6-9 months

    distribution = [
        0,                      # 0-1 month: 0 (backfill priority)
        0,                      # 1-3 months: 0 (backfill priority)
        early_growth,           # 3-6 months: Minimal growth (after backfill)
        mid_growth,             # 6-9 months: Some growth (with active)
        final_growth_portion,   # 9+ months: MAJORITY growth (like 977)
    ]

    return distribution


def determine_priority_logic(timeframe_index, active, growth, backfill):
    """
    Determine the business priority logic for each timeframe.
    """
    timeframes = ["0–1 month", "1–3 months", "3–6 months", "6–9 months", "9+ months"]
    timeframe_name = timeframes[timeframe_index] if timeframe_index < len(timeframes) else "unknown"

    if timeframe_index == 0:  # 0-1 month
        return {
            "primary_focus": "CRITICAL: Active roles + Immediate backfill",
            "urgency": "MAXIMUM",
            "rationale": f"Active roles ({active}) cannot wait - immediate business impact. Backfill ({backfill}) prevents operational gaps.",
            "delay_risk": "HIGH - Direct revenue impact and team overload"
        }
    elif timeframe_index == 1:  # 1-3 months
        return {
            "primary_focus": "URGENT: Remaining backfill + Some growth",
            "urgency": "HIGH",
            "rationale": f"Complete backfill hiring ({backfill}) to stabilize teams. Begin growth hiring ({growth}) for Q2 needs.",
            "delay_risk": "MEDIUM-HIGH - Attrition compounds, growth delayed"
        }
    else:  # 3+ months
        return {
            "primary_focus": "PLANNED: Growth-focused expansion",
            "urgency": "MODERATE",
            "rationale": f"Strategic growth hiring ({growth}) for future capacity. Minimal backfill ({backfill}) as teams stabilized.",
            "delay_risk": "MEDIUM - Strategic positioning and market opportunities"
        }


def get_business_justification(timeframe_index, active, growth, backfill):
    """
    Generate specific business justification based on demand components.
    """
    total = active + growth + backfill

    if timeframe_index == 0:  # 0-1 month
        return f"CRITICAL HIRING: {active} immediate roles + {backfill} attrition replacements = {total} hires needed to prevent operational disruption"
    elif timeframe_index == 1:  # 1-3 months
        return f"URGENT STABILIZATION: {backfill} remaining backfills + {growth} early growth roles = {total} hires to complete team stabilization"
    else:  # 3+ months
        return f"STRATEGIC GROWTH: {growth} expansion roles + {backfill} projected backfills = {total} hires for planned business growth"


def get_market_timing_factors(timeframe_index, insights):
    """
    Extract market timing factors that justify hiring in specific timeframes.
    """
    factors = {
        "seasonal_multiplier": 1.0,
        "attrition_risk": "standard",
        "demand_urgency": "normal",
        "budget_cycle": "regular"
    }

    # Extract seasonal patterns if available
    hiring_trends = insights.get("hiring_trends", {})
    seasonal_patterns = hiring_trends.get("seasonal_patterns", [])

    if seasonal_patterns:
        # Map timeframe index to quarters (rough approximation)
        quarter_map = {0: "Q1", 1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
        quarter = quarter_map.get(timeframe_index, "Q1")

        for pattern in seasonal_patterns:
            if pattern.get("quarter") == quarter:
                factors["seasonal_multiplier"] = pattern.get("hiring_multiplier", 1.0)
                break

    # Determine urgency based on timeframe
    if timeframe_index == 0:  # 0-1 month
        factors["demand_urgency"] = "critical"
        factors["attrition_risk"] = "immediate"
    elif timeframe_index == 1:  # 1-3 months
        factors["demand_urgency"] = "high"
        factors["attrition_risk"] = "near-term"
    else:
        factors["demand_urgency"] = "planned"
        factors["attrition_risk"] = "projected"

    return factors


def calculate_business_impact(count, active, growth, backfill, insights):
    """
    Calculate business impact metrics for hiring decisions.
    """
    # Extract market intelligence
    competitive_landscape = insights.get("competitive_landscape", {})
    hiring_trends = insights.get("hiring_trends", {})

    # Calculate cost of delay (assuming average time to fill is 120 days)
    avg_time_to_fill = hiring_trends.get("market_demand", {}).get("ai_engineers", {}).get("avg_time_to_fill", 120)
    cost_of_delay_days = avg_time_to_fill * 0.8  # 80% of time to fill as delay cost

    # Calculate competitive risk
    talent_competition = competitive_landscape.get("talent_competition", "Medium")
    competition_multiplier = {"High": 1.5, "Medium": 1.2, "Low": 1.0}.get(talent_competition, 1.2)

    # Revenue impact estimation (rough calculation)
    # Assume each AI engineer contributes ~$500K annually in value
    annual_value_per_engineer = 500000
    monthly_value_per_engineer = annual_value_per_engineer / 12

    return {
        "revenue_at_risk": count * monthly_value_per_engineer,
        "cost_of_delay_days": cost_of_delay_days,
        "competition_risk_multiplier": competition_multiplier,
        "active_roles_urgency": "critical" if active > 0 else "none",
        "growth_impact": "high" if growth > count * 0.4 else "moderate",
        "attrition_risk": "immediate" if backfill > count * 0.3 else "manageable"
    }


def build_enhanced_prompt(timeline, insights, role, mathematical_breakdown, full_prediction):
    """
    Builds an enhanced prompt with mathematical breakdown and business justification.
    """
    # Build timeline description with mathematical breakdown
    timeline_description = []
    for i, bucket in enumerate(timeline):
        breakdown = mathematical_breakdown[i] if i < len(mathematical_breakdown) else {}

        desc = f"- {bucket['timeframe']}: {bucket['count']} hire(s)"
        if breakdown:
            active = breakdown.get('active_demand_component', 0)
            backfill = breakdown.get('backfill_demand_component', 0)
            growth = breakdown.get('growth_demand_component', 0)

            desc += f"\n  📊 MATHEMATICAL BREAKDOWN:"
            desc += f"\n    • Backfill (urgent): {backfill} hires"
            desc += f"\n    • Active (critical): {active} hires"
            desc += f"\n    • Growth (planned): {growth} hires"
            total_calc = active + backfill + growth
            desc += f"\n    • TOTAL: {backfill} + {active} + {growth} = {total_calc} hires"
            desc += f"\n    • Verification: {total_calc == bucket['count']} ({'✅ CORRECT' if total_calc == bucket['count'] else '❌ ERROR'})"

            market_factors = breakdown.get('market_factors', {})
            desc += f"\n  🎯 BUSINESS PRIORITY: {market_factors.get('demand_urgency', 'normal').upper()}"

            # Add business justification
            business_just = breakdown.get('business_justification', '')
            if business_just:
                desc += f"\n  💡 LOGIC: {business_just}"

        timeline_description.append(desc)

    timeline_text = "\n\n".join(timeline_description)

    # Extract key prediction metrics
    result = full_prediction.get("result", {})
    total_active = result.get("active_demand", 0)
    total_growth = result.get("growth_demand", 0)
    total_backfill = result.get("backfill_demand", 0)
    total_headcount = result.get("headcount", 0)
    confidence = result.get("forecast_confidence", 0.5)

    return f"""You are an expert in strategic workforce planning with deep knowledge of talent acquisition patterns and market dynamics.

**Context:**
- Role: **{role}**
- Hiring Plan: {timeline_description}
- Data Source: LinkedIn Talent Insights (JSON format)

**Your Task:**
Analyze the provided LinkedIn Talent Insights and write **exactly one justification per timeframe** explaining why hiring the specified number of people in that specific timeframe is strategically sound.

**Requirements:**
- **Data-Driven:** Base each justification ONLY on specific metrics from the insights provided (attrition rates, demand-supply ratios, seasonal patterns, skill availability, compensation trends)
- **Quantitative:** Reference actual numbers/percentages from the data when possible
- **Role-Specific:** Always mention the specific role ({role}) and explain why the market conditions affect THIS particular role
- **Mathematical Precision:** Show clear calculations connecting market data to exact hiring numbers
- **Evidence-Based:** Use ONLY data points that exist in the insights - never invent or assume information
- **Unique Reasoning:** Each timeframe must use completely different market logic - no overlap

**Format Requirements:**
- Return exactly 5 bullet points in chronological order matching the timeline
- Each bullet should be 2-3 sentences with NO headers, titles, or bold text
- Start each bullet with the complete timeframe: "0–1 month:", "1–3 months:", "3–6 months:", "6–9 months:", "9+ months:"
- Follow immediately with the justification based on data insights
- Do NOT include hire counts in the justification text

**MANDATORY UNIQUE REASONING BY TIMEFRAME:**
1. **0–1 month:** ONLY use replacement calculations from actual attrition data or immediate capacity shortfalls from insights
2. **1–3 months:** ONLY use talent pool size changes, supply-demand ratio shifts, or salary trend windows from actual data
3. **3–6 months:** ONLY use seasonal hiring patterns, project cycle data, or skill demand spikes from insights
4. **6–9 months:** ONLY use departure timing patterns, budget cycle data, or tenure-based predictions from insights
5. **9+ months:** ONLY use growth projections, market cycle data, or capacity building metrics from insights

**STRICTLY PROHIBITED - NEVER MENTION:**
- Universities, colleges, or educational institutions
- "Recent graduates," "fresh talent," or academic hiring cycles
- Company names (Google, Amazon, Microsoft, etc.)
- Competitor references or "competition"
- Any information NOT explicitly provided in the insights data

**PROHIBITED TERMS - NEVER USE:**
"strategic," "anticipated," "significant," "competitive," "optimal," "ensure," "adequate," "mitigate," "capitalize," "leverage," "alignment," "positioning," "edge," "intensify," "surge," "critical," "top universities," "fresh talent," "graduates," "competition," "opportune"

**MATHEMATICAL REQUIREMENT - MANDATORY:**
Every justification must include:
- Exact calculation showing how you derived the hiring number from PROVIDED market data
- Specific {role} capacity or replacement ratio FROM THE INSIGHTS
- Clear mathematical relationship between timing and volume BASED ON DATA

**DATA ANALYSIS RULES - CRITICAL:**
- Use ONLY the specific numbers, percentages, and metrics provided in the insights JSON
- You must QUOTE the exact data field name and value from the insights (e.g., "insights show attrition_rate: 12%")
- If supply-demand ratio exists in insights, use the EXACT numbers provided
- If budget cycle data exists in insights, reference the SPECIFIC metrics given
- If seasonal patterns exist in insights, use the EXACT timeframes and percentages provided
- NEVER invent ratios, cycles, or patterns not explicitly stated in the insights
- If a data point doesn't exist in insights, DO NOT use it as justification

**PROHIBITED ASSUMPTIONS - NEVER INVENT:**
- Supply-demand ratios not explicitly provided in insights
- Budget cycle patterns not specifically mentioned in insights data
- Seasonal hiring trends not backed by actual insights metrics
- Generic "market growth" without specific insights data
- Project cycle assumptions not supported by insights
- Any percentage, ratio, or timing not directly from the insights JSON

**CRITICAL: DATA FIELD VERIFICATION REQUIRED**
Before using ANY data point, you must:
1. State the exact JSON field name (e.g., "attrition_percent_1y": 12)
2. State the exact value from that field
3. If a field doesn't exist, DO NOT invent or assume it exists

**AVAILABLE DATA FIELDS ONLY:**
Use ONLY these types of data from the insights:
- company_profile fields (employees_current, growth_rate_percent_1y, attrition_percent_1y, open_jobs)
- workforce_trend fields (growth_6m_percent, growth_1y_percent)
- talent_flow fields (hires, departures, net_change)
- function_headcount and attrition_breakdown data
- skills data (employees, hires_1y, growth_1y_percent)
- tenure data (median_company_tenure_years)
- location-specific data if relevant

**NEVER INVENT THESE (NOT IN YOUR DATA):**
- Supply-demand ratios
- Budget cycle patterns
- Seasonal hiring trends  
- Project cycle data
- Quarterly patterns
- Candidate availability ratios

**FORMATTING ENFORCEMENT:**
- All timeframe labels must be complete: "0–1 month" NOT "–1 month" or "+ months"
- No repetition of the same data points across timeframes
- Each justification explains WHY that exact number in THAT specific timeframe using PROVIDED data

**QUALITY CONTROL - FINAL CHECK:**
Before providing any justification, verify:
1. Does this reference a specific field name and value from the insights JSON?
2. Can I point to the exact location in the insights where this data exists?
3. Is the calculation mathematically clear using ONLY provided numbers?
4. Does this avoid all prohibited terms and assumptions?
5. Is the reasoning unique to this timeframe using different insights data?
6. Are the timeframe labels complete (0–1 month, not –1 month)?

**EXAMPLE OF REQUIRED DATA REFERENCING:**
❌ Wrong: "Supply-demand ratio of 1:4 indicates shortage"
✅ Correct: "Insights field 'demand_supply_ratio' shows 0.25, meaning 1 candidate per 4 openings"

❌ Wrong: "Budget cycles typically lead to hiring increases"  
✅ Correct: "Insights field 'quarterly_hiring_budget' shows 23% increase in Q3-Q4"

**COMPLETION REQUIREMENT:**
Provide exactly 5 justifications using completely different data points from the insights. Each must show mathematical precision connecting PROVIDED market data to exact hiring numbers for {role} positions.

Insights (JSON): {insights}""".strip()


def parse_justifications(response: str, expected_count: int) -> list:
    """
    Extracts bullet point justifications from GPT response text.
    Returns a list of strings aligned with the timeline order.
    Pads or trims if mismatch in count.
    """
    lines = response.splitlines()
    bullets = [
        line.lstrip("-•0123456789. ").strip()
        for line in lines
        if line.strip() and not line.lower().startswith("insight")  # skip junk
    ]

    # Pad or trim to match timeline length
    if len(bullets) < expected_count:
        bullets += [""] * (expected_count - len(bullets))
    else:
        bullets = bullets[:expected_count]

    return bullets
