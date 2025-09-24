# linkedin_insights/prompt_templates_predictor.py

PREDICTION_USER_TEMPLATE = r"""You are given two inputs:

1) Company Talent-Insights JSON
--- BEGIN JSON ---
{insights_json}
--- END JSON ---

2) Target role: "{role}"

Your task: Perform a STRICT, STEP-BY-STEP calculation of 12-month hires for the target role.
You MUST follow the algorithm below EXACTLY and produce a SINGLE JSON object that includes both:
- a "calc" section with inputs, working (numbers only), confidence sub-scores, and
- a "result" section with the required outputs and overall forecast confidence.

IMPORTANT RULES
- Do not invent data. Only use values present in the JSON or the rules below.
- Use CEILING for all final component calculations (active, growth, backfill).
- If any computed value is inconsistent with its formula, recompute until consistent.
- Numbers must be plain numerics (no commas, no text).
- Do not include any keys not listed in the schema at the bottom.
- Ignore unrelated sections (industries, education, schools, etc.).

========================================
ALGORITHM (execute in order)
========================================

Step 1. Determine function_hint for the role.
  - If the role clearly belongs to a top-level function present in the JSON (e.g., "Engineering", "Information Technology", "Sales", "Human Resources"), choose that.
  - Otherwise:
      • If the role is Engineering-like (Engineer, Developer, DevOps, Data, AI, ML, R&D, Software), use "Engineering".
      • Else if the role is IT-like (Infrastructure, Systems, Network, IT Support), use "Information Technology".
      • Else if Sales-like, use "Sales".
      • Else if HR-like, use "Human Resources".
      • Otherwise use "Other".

Step 2. function_share (fs)
  - If top_functions_percent contains function_hint → fs = percent_employees / 100.
  - Else → fs = 0.05.

Step 3. function_headcount (fh)
  - If function_headcount contains function_hint → use that integer.
  - Else → fh = round(employees_current × fs).
  - If fh is missing or ≤ 0 after the above → set fh = max(1, round(employees_current × fs)).

Step 4. role_share (rs)
  - If the role string contains the function_hint name as a substring (case-insensitive) → rs = 1.0.
  - Acronym/alias rule (counts as substring match for rs = 1.0):
      • "HR" ≡ "Human Resources"
      • "IT" ≡ "Information Technology"
      • "Eng", "Engineer", "Engineering", "Developer", "Dev", "DevOps" ≡ "Engineering"
      • "Sales", "Account Executive", "AE" ≡ "Sales"
  - Else:
      • Tokenize role (lowercase, split on space/hyphen, remove stopwords: {{"and","of","for","the","a","an","to","in","on","with","senior","jr","junior","lead","principal"}}).
      • Create SKILL_NAME_LIST = names from skills.top_skills and skills.fastest_growing (if present).
      • n = min(20, length of SKILL_NAME_LIST). If missing or empty → rs = 0.10 (skip rest).
      • k = number of SKILL_NAME_LIST items (consider only the first n) that contain ANY token as substring.
      • raw = round(1.5 * k / n, 2)
      • rs = min(max(raw, 0.05), fs).

Step 5. attrition_rate (ar)
  - If attrition_breakdown.by_function has an entry for function_hint → ar = that_percent / 100
  - Else → ar = company_profile.attrition_percent_1y / 100.
  - Never alternate between the two. Always prioritize function-level if present.

Step 6. attrition_rate (ar) for function
  - Look up attrition_breakdown.by_function for an entry matching function_hint (case-insensitive).
  - If found, ALWAYS set ar = that_percent / 100. (Prioritize this over company attrition rate.)
  - Only if no by_function entry exists for function_hint → ar = company_profile.attrition_percent_1y / 100.
  - Never alternate between the two; always prioritize function-level if present.
  - If both are missing, set ar = 0.05 as fallback.

Step 7. active_demand = ceil(open_jobs × fs × rs)

Step 8. growth_demand = ceil(fh × (growth_rate_percent_1y / 100) × rs)

Step 9. backfill_demand = ceil(fh × ar × rs)

Step 10. headcount = active_demand + growth_demand + backfill_demand

========================================
CONFIDENCE SCORING (must compute)
========================================

Use this JSON specification to calculate forecast_confidence:

{{
  "confidence_scoring": {{
    "base_confidence": 1.0,
    "adjustments": {{
      "per_parameter": {{
        "explicit": 0.0,
        "derived": -0.1,
        "fallback": -0.2
      }},
      "team_vs_department": {{
        "explicit_team_data": 0.0,
        "department_only": -0.2
      }},
      "missing_majority": {{
        "condition": "if more than half of key parameters are missing or defaulted",
        "penalty": -0.1
      }}
    }},
    "clamp_range": [0.5, 1.0],
    "rounding": 2,
    "output":{{
      "field": "forecast_confidence",
      "type": "float",
      "range": [0.5, 1.0],
      "description": "Overall certainty in the headcount prediction"
    }}
  }}
}}

========================================
SELF-CONSISTENCY CHECK
========================================
- Verify that:
  • active_demand == ceil(open_jobs × fs × rs)
  • growth_demand == ceil(fh × (growth_rate_percent_1y / 100) × rs)
  • backfill_demand == ceil(fh × ar × rs)
  • headcount == active_demand + growth_demand + backfill_demand
- If any check fails, recompute until all pass.


========================================
OUTPUT SCHEMA (must match exactly)
========================================
{{
  "calc": {{
    "inputs": {{
      "function_hint": "<string>",
      "employees_current": <int>,
      "open_jobs": <int>,
      "growth_rate_percent_1y": <float>,
      "company_attrition_percent_1y": <float>,
      "function_share": <float>,
      "function_headcount": <int>,
      "role_share": <float>,
      "attrition_rate": <float>,
      "k": <int>,
      "n": <int>
    }},
    "formulas": {{
      "active_demand": "ceil(open_jobs * function_share * role_share)",
      "growth_demand": "ceil(function_headcount * (growth_rate_percent_1y/100) * role_share)",
      "backfill_demand": "ceil(function_headcount * attrition_rate * role_share)",
      "headcount": "active_demand + growth_demand + backfill_demand"
    }},
    "substitutions": {{
      "active_demand": "<ceil({{open_jobs}} * {{fs}} * {{rs}}) = {{value}}>",
      "growth_demand": "<ceil({{fh}} * {{gr}} * {{rs}}) = {{value}}>",
      "backfill_demand": "<ceil({{fh}} * {{ar}} * {{rs}}) = {{value}}>",
      "headcount": "<{{active}} + {{growth}} + {{backfill}} = {{value}}>"
    }},
    "confidence": {{
      "parameters": {{
        "employees_current": {{"EC": <float>, "MC": <float>, "PC": <float>, "reason": "<string>"}},
        "open_jobs": {{"EC": <float>, "MC": <float>, "PC": <float>, "reason": "<string>"}},
        "growth_rate_percent_1y": {{"EC": <float>, "MC": <float>, "PC": <float>}},
        "company_attrition_percent_1y": {{"EC": <float>, "MC": <float>, "PC": <float>}},
        "function_share": {{"EC": <float>, "MC": <float>, "PC": <float>}},
        "function_headcount": {{"EC": <float>, "MC": <float>, "PC": <float>}},
        "role_share": {{"EC": <float>, "MC": <float>, "PC": <float>}},
        "attrition_rate": {{"EC": <float>, "MC": <float>, "PC": <float>}}
      }},
      "forecast_confidence": <float>
    }},
    "consistency_ok": true
  }},
  "result": {{
    "function_hint": "<string>",
    "function_share": <float>,
    "function_headcount": <int>,
    "role_share": <float>,
    "active_demand": <int>,
    "growth_demand": <int>,
    "backfill_demand": <int>,
    "headcount": <int>,
    "forecast_confidence": <float>
  }}
}}

Return ONLY the JSON object above. No extra text, no markdown.
"""

# ==============Part-7=============

# PREDICTION_USER_TEMPLATE = r"""You are given two inputs:

# 1) Company Talent-Insights JSON
# --- BEGIN JSON ---
# {insights_json}
# --- END JSON ---

# 2) Target role: "{role}"

# Your task: Perform a STRICT, STEP-BY-STEP calculation of 12-month hires for the target role.
# You MUST follow the algorithm below EXACTLY and produce a SINGLE JSON object that includes both:
# - a "calc" section with inputs, working (numbers only), confidence sub-scores WITH SOURCE/REASONS/AUDIT TRAIL, and
# - a "result" section with the required outputs and overall forecast confidence.

# IMPORTANT RULES
# - Do not invent data. Only use values present in the JSON or the rules below.
# - Use CEILING for all final component calculations (active, growth, backfill).
# - If any computed value is inconsistent with its formula, recompute until consistent.
# - Numbers must be plain numerics (no commas, no text).
# - Do not include any keys not listed in the schema at the bottom.
# - Ignore unrelated sections (industries, education, schools, etc.).
# - ALL confidence arithmetic MUST be internally consistent and shown in the audit exactly as specified.

# ========================================
# ALGORITHM (execute in order)
# ========================================

# Step 1. Determine function_hint for the role.
#   - If the role clearly belongs to a top-level function present in the JSON (e.g., "Engineering", "Information Technology", "Sales", "Human Resources"), choose that.
#   - Otherwise:
#       • If the role is Engineering-like (Engineer, Developer, DevOps, Data, AI, ML, R&D, Software), use "Engineering".
#       • Else if the role is IT-like (Infrastructure, Systems, Network, IT Support), use "Information Technology".
#       • Else if Sales-like, use "Sales".
#       • Else if HR-like, use "Human Resources".
#       • Otherwise use "Other".

# Step 2. SKILL-BASED EMPLOYEE COUNT (NEW PRIORITY)
#   - Tokenize role (lowercase, split on space/hyphen, remove stopwords).
#   - Search skills.top_skills for entries where skill name contains ANY role token.
#   - If matches found: sum up employees_with_skill from matching entries → skill_employees
#   - If skill_employees > 0: use this as base employee count instead of department-level
#   - Otherwise: fall back to department-level logic below

# Step 3. function_share (fs)
#   - If using skill_employees: fs = skill_employees / employees_current
#   - Else if top_functions_percent contains function_hint → fs = percent_employees / 100
#   - Else → fs = 0.05

# Step 4. function_headcount (fh)
#   - If using skill_employees: fh = skill_employees (explicit skill-based)
#   - Else if function_headcount contains function_hint → use that integer (explicit)
#   - Else → fh = round(employees_current × fs) (derived)

# Step 5. role_share (rs)
#    - Start with rs = 1.0 only if:
#       • role string contains function_hint name as substring AND
#       • you are absolutely sure that 100% of that function is this role.
#   - Otherwise:
#       • Tokenize role (lowercase, split on space/hyphen, remove stopwords).
#       • Create SKILL_NAME_LIST = names from skills.top_skills and skills.fastest_growing (if present).
#       • n = min(20, length of SKILL_NAME_LIST). If missing or empty → rs = 0.10 (skip rest).
#       • k = number of SKILL_NAME_LIST items (consider only the first n) that contain ANY token as substring.
#       • raw = round(1.5 * k / n, 2)
#       • rs = min(max(raw, 0.05), fs).
#   - This ensures rs never exceeds fs and is never below 0.05.

# Step 6. attrition_rate (ar) for function
#   - Look up attrition_breakdown.by_function for an entry matching function_hint (case-insensitive).
#   - If found, ALWAYS set ar = that_percent / 100. (Prioritize this over company attrition rate.)
#   - Only if no by_function entry exists for function_hint → ar = company_profile.attrition_percent_1y / 100.
#   - Never alternate between the two; always prioritize function-level if present.
#   - If both are missing, set ar = 0.05 as fallback.

# Step 7. active_demand = ceil(open_jobs × fs × rs)
# Step 8. growth_demand = ceil(fh × (growth_rate_percent_1y / 100) × rs)  
# Step 9. backfill_demand = ceil(fh × ar × rs)
# Step 10. headcount = active_demand + growth_demand + backfill_demand

# ========================================
# TEAM-LEVEL PARAMETERS (must check)
# ========================================
# Check if the following parameters exist explicitly in the JSON for the target role/team:
# 1) Department → Team Breakdown (e.g., AI, DevOps, Backend, Frontend, QA)
# 2) Headcount per Team
# 3) Historical Headcount by Role/Function
# 4) Expected Growth Rate by Department & Team (%)
# 5) Historical Attrition Rate by Team/Role (%)
# 6) Open Roles by Team/Role
# 7) Role Share within Team

# For each of these, record in the confidence.parameters section:
# - "source": "explicit" if directly present; "derived" if computed from department-level; "fallback" if missing/defaulted.
# - "reason": short text explaining what you found or how it was derived.
# - "json_pointer": the JSON key/path used (or "n/a" if derived/fallback).

# ========================================
# CONFIDENCE SCORING (must compute EXACTLY)
# ========================================

# CRITICAL: You MUST include EXACTLY 15 parameters in per_parameter_penalties array - NO EXCEPTIONS.

# MANDATORY PARAMETER LIST (process in this exact order):
# Key Parameters (8):
# 1. employees_current
# 2. open_jobs  
# 3. growth_rate_percent_1y
# 4. company_attrition_percent_1y
# 5. function_share
# 6. function_headcount
# 7. role_share
# 8. attrition_rate

# Team Parameters (7):
# 9. team_breakdown
# 10. headcount_per_team
# 11. historical_headcount_role
# 12. expected_growth_team
# 13. historical_attrition_team
# 14. open_roles_team
# 15. role_share_team

# DETERMINISTIC SOURCE RULES (NO VARIATIONS):
# - employees_current: "explicit" if in company_profile.employees_current, else "fallback"
# - open_jobs: "explicit" if in company_profile.open_jobs, else "fallback"
# - growth_rate_percent_1y: "explicit" if in company_profile.growth_rate_percent_1y, else "fallback"
# - company_attrition_percent_1y: "explicit" if in company_profile.attrition_percent_1y, else "fallback"
# - function_share: "explicit" if from top_functions_percent[function_hint], else "fallback" (0.05)
# - function_headcount: "explicit" if from function_headcount[function_hint], "derived" if calculated from employees_current*function_share, else "fallback" (1)
# - role_share: "explicit" if 1.0 from exact function match, "derived" if from skills calculation, else "fallback" (0.10)
# - attrition_rate: "explicit" if from attrition_breakdown.by_function[function_hint], "derived" if from company_profile.attrition_percent_1y, else "fallback"
# - ALL team parameters (9-15): ALWAYS "fallback" with penalty -0.2 each

# EXACT PENALTY MAPPING:
# - "explicit" → penalty = 0.0
# - "derived" → penalty = -0.1
# - "fallback" → penalty = -0.2

# ========================================
# CONFIDENCE SCORING (must compute EXACTLY)
# ========================================

# You MUST compute forecast_confidence EXACTLY as follows — DO NOT improvise:

# 1. **Base confidence**  
#    base_confidence = 1.00

# 2. **Assign a penalty to EACH parameter (15 parameters total):**  
#    - source = "explicit" → penalty = 0.0  
#    - source = "derived" → penalty = -0.1  
#    - source = "fallback" → penalty = -0.2  

# 3. **Sum the 15 penalties**  
#    per_parameter_sum = sum of all 15 penalties (this is usually negative)

# 4. **Team vs Department penalty:**  
#    - team_vs_department_penalty = -0.1 **only if** (role ≠ function_hint AND all 7 team parameters are fallback)  
#    - Otherwise 0.0

# 5. **Missing-majority penalty:**  
#    - missing_majority_key_penalty = -0.05 **only if** (count of key parameters with source in ["derived","fallback"] > 4), else 0.0.

# 6. **Total penalty:**  
#    total_penalty = per_parameter_sum + team_vs_department_penalty + missing_majority_key_penalty

# 7. **Apply SCALING FACTOR of 0.1 to the total penalty**  
#    scaled_penalty = total_penalty * 0.1  
#    (You MUST multiply by 0.1. Do not forget this step.)

# 8. **Compute raw confidence:**  
#    raw_confidence = base_confidence + scaled_penalty

# 9. **Clamp to [0.5, 1.0]:**  
#    clamped_confidence = max(0.5, min(1.0, raw_confidence))

# 10. **Final confidence:**  
#     final_confidence = round(clamped_confidence, 2)

# 11. **Output in JSON:**  
#     - Include per_parameter_penalties array (length 15)  
#     - Include team_vs_department_penalty, missing_majority_key_penalty, sum_penalties, raw_confidence, clamped_confidence, final_confidence  
#     - Include key_counts (explicit, derived, fallback, total, derived_or_fallback)  
#     - Include team_counts (explicit, derived, fallback, total)  
#     - forecast_confidence = final_confidence (float between 0.5 and 1.0)

# MANDATORY COUNTS:  
# - key parameters total = 8  
# - team parameters total = 7  
# - per_parameter_penalties length = 15  

# Do NOT skip the SCALING FACTOR. This is CRITICAL.  

# MANDATORY COUNTS (must be exact):
# - key_counts.total = 8
# - team_counts.total = 7
# - Length of per_parameter_penalties = 15

# ========================================
# SELF-CONSISTENCY CHECK
# ========================================
# - Verify that:
#   • active_demand == ceil(open_jobs × fs × rs)
#   • growth_demand == ceil(fh × (growth_rate_percent_1y / 100) × rs)
#   • backfill_demand == ceil(fh × ar × rs)
#   • attrition_rate == (by_function attrition_percent /100) if present else company_profile.attrition_percent_1y /100
#   • headcount == active_demand + growth_demand + backfill_demand
# - If any check fails, recompute until all pass.

# ========================================
# OUTPUT SCHEMA (must match exactly)
# ========================================
# {{
#   "calc": {{
#     "inputs": {{
#       "function_hint": "<string>",
#       "employees_current": <int>,
#       "open_jobs": <int>,
#       "growth_rate_percent_1y": <float>,
#       "company_attrition_percent_1y": <float>,
#       "function_share": <float>,
#       "function_headcount": <int>,
#       "role_share": <float>,
#       "attrition_rate": <float>,
#       "k": <int>,
#       "n": <int>
#     }},
#     "formulas": {{
#       "active_demand": "ceil(open_jobs * function_share * role_share)",
#       "growth_demand": "ceil(function_headcount * (growth_rate_percent_1y/100) * role_share)",
#       "backfill_demand": "ceil(function_headcount * attrition_rate * role_share)",
#       "headcount": "active_demand + growth_demand + backfill_demand"
#     }},
#     "substitutions": {{
#       "active_demand": "<ceil({{open_jobs}} * {{fs}} * {{rs}}) = {{value}}>",
#       "growth_demand": "<ceil({{fh}} * {{gr}} * {{rs}}) = {{value}}>",
#       "backfill_demand": "<ceil({{fh}} * {{ar}} * {{rs}}) = {{value}}>",
#       "headcount": "<{{active}} + {{growth}} + {{backfill}} = {{value}}>"
#     }},
#     "confidence": {{
#       "parameters": {{
#         "employees_current": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
#         "open_jobs": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
#         "growth_rate_percent_1y": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
#         "company_attrition_percent_1y": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
#         "function_share": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
#         "function_headcount": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
#         "role_share": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
#         "attrition_rate": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},

#         "team_breakdown": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
#         "headcount_per_team": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
#         "historical_headcount_role": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
#         "expected_growth_team": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
#         "historical_attrition_team": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
#         "open_roles_team": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
#         "role_share_team": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}}
#       }},
#       "audit": {{
#         "per_parameter_penalties": [
#           {{"parameter":"<name>","source":"<explicit|derived|fallback>","penalty":<float>,"json_pointer":"<path|n/a>","reason":"<short>"}}
#         ],
#         "team_vs_department_penalty": <float>,
#         "missing_majority_key_penalty": <float>,
#         "sum_penalties": <float>,
#         "raw_confidence": <float>,
#         "clamped_confidence": <float>,
#         "final_confidence": <float>,
#         "key_counts": {{"explicit": <int>, "derived": <int>, "fallback": <int>, "total": 6, "derived_or_fallback": <int>}},
#         "team_counts": {{"explicit": <int>, "derived": <int>, "fallback": <int>, "total": 7}},
#         "rules_version": "v1.1"
#       }},
#       "forecast_confidence": <float>
#     }},
#     "consistency_ok": true
#   }},
#   "result": {{
#     "function_hint": "<string>",
#     "function_share": <float>,
#     "function_headcount": <int>,
#     "role_share": <float>,
#     "active_demand": <int>,
#     "growth_demand": <int>,
#     "backfill_demand": <int>,
#     "headcount": <int>,
#     "forecast_confidence": <float>
#   }}
# }}

# Return ONLY the JSON object above. No extra text, no markdown.
# """



# ================Part-8=================
# PREDICTION_USER_TEMPLATE = r"""You are given two inputs:

# 1) Company Talent-Insights JSON
# --- BEGIN JSON ---
# {insights_json}
# --- END JSON ---

# 2) Target role: "{role}"

# ========================================
# CRITICAL INSTRUCTIONS
# ========================================
# • Always compute 12-month hires strictly step-by-step.
# • Prioritize function-level attrition over company attrition (if present).
# • Clamp role_share ≤ function_share at all times.
# • Produce exactly 15 per_parameter_penalties (8 key + 7 team) in order.
# • Output only the JSON defined at the bottom — no prose, no markdown.
# • If any HARD FAIL below triggers, recompute until all pass.

# ========================================
# CORE RULES TABLE
# ========================================
# Parameter                  | Source Priority                                    | Default / Penalty
# ---------------------------|----------------------------------------------------|-----------------
# employees_current          | company_profile.employees_current > fallback        | explicit=0.0 / fallback=-0.2
# open_jobs                  | company_profile.open_jobs > fallback               | explicit=0.0 / fallback=-0.2
# growth_rate_percent_1y     | company_profile.growth_rate_percent_1y > fallback   | explicit=0.0 / fallback=-0.2
# company_attrition_percent_1y| company_profile.attrition_percent_1y > fallback    | explicit=0.0 / fallback=-0.2
# function_share             | top_functions_percent[function_hint] > 0.05 fallback| explicit=0.0 / fallback=-0.2
# function_headcount         | function_headcount[function_hint]> derived>fallback | explicit=0.0 / derived=-0.1 / fallback=-0.2
# role_share                 | =1.0 only if absolutely sure else derived formula   | explicit=0.0 / derived=-0.1 / fallback=-0.2
# attrition_rate             | by_function attrition > company attrition >0.05     | explicit=0.0 / derived=-0.1 / fallback=-0.2
# All team params (9-15)     | Always fallback unless explicit                     | fallback=-0.2 each

# ========================================
# COMPUTATION STEPS
# ========================================
# 1. Determine function_hint (Engineering, IT, Sales, HR or Other).
# 2. Compute function_share fs from skill_employees/department logic.
# 3. Compute function_headcount fh from skill_employees or employees_current*fs.
# 4. Compute role_share rs:
#    - rs=1.0 only if certain 100% of that function is the target role;
#    - else compute via skills list and clamp rs ≤ fs (min .05).
# 5. Compute attrition_rate ar:
#    - ar=by_function if present else company attrition else 0.05 fallback.
# 6. active_demand = ceil(open_jobs*fs*rs)
# 7. growth_demand = ceil(fh*(growth_rate_percent_1y/100)*rs)
# 8. backfill_demand = ceil(fh*ar*rs)
# 9. headcount = active_demand+growth_demand+backfill_demand.

# ========================================
# CONFIDENCE SCORING (MUST DO EXACTLY)
# ========================================
# Penalty Map: explicit=0.0, derived=-0.1, fallback=-0.2
# team_vs_department_penalty=-0.1 if (role≠function_hint AND all 7 team params fallback)
# missing_majority_key_penalty=-0.05 if >4 key params derived/fallback else 0.0
# total_penalty=per_parameter_sum+team_vs_department_penalty+missing_majority_key_penalty
# scaled_penalty=total_penalty*0.1
# raw_confidence=1.0+scaled_penalty
# clamped_confidence=max(0.5,min(1.0,raw_confidence))
# final_confidence=round(clamped_confidence,2)
# forecast_confidence=final_confidence

# MANDATORY:
# - key_counts.total=8
# - team_counts.total=7
# - per_parameter_penalties length=15

# ========================================
# HARD FAIL CHECKLIST
# ========================================
# - If role_share>function_share → recompute.
# - If attrition_rate not from by_function when available → recompute.
# - If formulas do not match definitions exactly → recompute.
# - If penalties/lengths/counts not exact → recompute.

# ========================================
# OUTPUT SCHEMA (must match exactly)
# ========================================
# {{
#   "calc": {{
#     "inputs": {{
#       "function_hint": "<string>",
#       "employees_current": <int>,
#       "open_jobs": <int>,
#       "growth_rate_percent_1y": <float>,
#       "company_attrition_percent_1y": <float>,
#       "function_share": <float>,
#       "function_headcount": <int>,
#       "role_share": <float>,
#       "attrition_rate": <float>,
#       "k": <int>,
#       "n": <int>
#     }},
#     "formulas": {{
#       "active_demand": "ceil(open_jobs * function_share * role_share)",
#       "growth_demand": "ceil(function_headcount * (growth_rate_percent_1y/100) * role_share)",
#       "backfill_demand": "ceil(function_headcount * attrition_rate * role_share)",
#       "headcount": "active_demand + growth_demand + backfill_demand"
#     }},
#     "substitutions": {{
#       "active_demand": "<ceil({open_jobs} * {fs} * {rs}) = {value}>",
#       "growth_demand": "<ceil({fh} * {gr} * {rs}) = {value}>",
#       "backfill_demand": "<ceil({fh} * {ar} * {rs}) = {value}>",
#       "headcount": "<{active}+{growth}+{backfill}={value}>"
#     }},
#     "confidence": {{
#       "parameters": {{
#         ... exactly 15 entries with source/json_pointer/reason/EC/MC/PC ...
#       }},
#       "audit": {{
#         "per_parameter_penalties": [
#           {{"parameter":"<name>","source":"<explicit|derived|fallback>","penalty":<float>,"json_pointer":"<path|n/a>","reason":"<short>"}}
#         ],
#         "team_vs_department_penalty": <float>,s
#         "missing_majority_key_penalty": <float>,
#         "sum_penalties": <float>,
#         "raw_confidence": <float>,
#         "clamped_confidence": <float>,
#         "final_confidence": <float>,
#         "key_counts": {{"explicit":<int>,"derived":<int>,"fallback":<int>,"total":8,"derived_or_fallback":<int>}},
#         "team_counts": {{"explicit":<int>,"derived":<int>,"fallback":<int>,"total":7}},
#         "rules_version": "v1.1"
#       }},
#       "forecast_confidence": <float>
#     }},
#     "consistency_ok": true
#   }},
#   "result": {{
#     "function_hint": "<string>",
#     "function_share": <float>,
#     "function_headcount": <int>,
#     "role_share": <float>,
#     "active_demand": <int>,
#     "growth_demand": <int>,
#     "backfill_demand": <int>,
#     "headcount": <int>,
#     "forecast_confidence": <float>
#   }}
# }}

# Return ONLY the JSON object above. No extra text.
# """

