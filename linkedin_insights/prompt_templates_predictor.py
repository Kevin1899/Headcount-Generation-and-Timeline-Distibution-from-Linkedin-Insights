# linkedin_insights/prompt_templates_predictor.py

# PREDICTION_USER_TEMPLATE = r"""You are given two inputs:

# 1) Company Talent-Insights JSON
# --- BEGIN JSON ---
# {insights_json}
# --- END JSON ---

# 2) Target role: "{role}"

# Your task: Perform a STRICT, STEP-BY-STEP calculation of 12-month hires for the target role.
# You MUST follow the algorithm below EXACTLY and produce a SINGLE JSON object that includes both:
# - a "calc" section with inputs, working (numbers only), confidence sub-scores, and
# - a "result" section with the required outputs and overall forecast confidence.

# IMPORTANT RULES
# - Do not invent data. Only use values present in the JSON or the rules below.
# - Use CEILING for all final component calculations (active, growth, backfill).
# - If any computed value is inconsistent with its formula, recompute until consistent.
# - Numbers must be plain numerics (no commas, no text).
# - Do not include any keys not listed in the schema at the bottom.
# - Ignore unrelated sections (industries, education, schools, etc.).

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

# Step 2. function_share (fs)
#   - If top_functions_percent contains function_hint → fs = percent_employees / 100.
#   - Else → fs = 0.05.

# Step 3. function_headcount (fh)
#   - If function_headcount contains function_hint → use that integer.
#   - Else → fh = round(employees_current × fs).
#   - If fh is missing or ≤ 0 after the above → set fh = max(1, round(employees_current × fs)).

# Step 4. role_share (rs)
#   - If the role string contains the function_hint name as a substring (case-insensitive) → rs = 1.0.
#   - Acronym/alias rule (counts as substring match for rs = 1.0):
#       • "HR" ≡ "Human Resources"
#       • "IT" ≡ "Information Technology"
#       • "Eng", "Engineer", "Engineering", "Developer", "Dev", "DevOps" ≡ "Engineering"
#       • "Sales", "Account Executive", "AE" ≡ "Sales"
#   - Else:
#       • Tokenize role (lowercase, split on space/hyphen, remove stopwords: {{"and","of","for","the","a","an","to","in","on","with","senior","jr","junior","lead","principal"}}).
#       • Create SKILL_NAME_LIST = names from skills.top_skills and skills.fastest_growing (if present).
#       • n = min(20, length of SKILL_NAME_LIST). If missing or empty → rs = 0.10 (skip rest).
#       • k = number of SKILL_NAME_LIST items (consider only the first n) that contain ANY token as substring.
#       • raw = round(1.5 * k / n, 2)
#       • rs = min(max(raw, 0.05), fs).

# Step 5. attrition_rate (ar)
#   - If attrition_breakdown.by_function has an entry for function_hint → ar = that_percent / 100
#   - Else → ar = company_profile.attrition_percent_1y / 100.
#   - Never alternate between the two. Always prioritize function-level if present.

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
# CONFIDENCE SCORING (must compute)
# ========================================

# Use this JSON specification to calculate forecast_confidence:

# {{
#   "confidence_scoring": {{
#     "base_confidence": 1.0,
#     "adjustments": {{
#       "per_parameter": {{
#         "explicit": 0.0,
#         "derived": -0.1,
#         "fallback": -0.2
#       }},
#       "team_vs_department": {{
#         "explicit_team_data": 0.0,
#         "department_only": -0.2
#       }},
#       "missing_majority": {{
#         "condition": "if more than half of key parameters are missing or defaulted",
#         "penalty": -0.1
#       }}
#     }},
#     "clamp_range": [0.5, 1.0],
#     "rounding": 2,
#     "output":{{
#       "field": "forecast_confidence",
#       "type": "float",
#       "range": [0.5, 1.0],
#       "description": "Overall certainty in the headcount prediction"
#     }}
#   }}
# }}

# ========================================
# SELF-CONSISTENCY CHECK
# ========================================
# - Verify that:
#   • active_demand == ceil(open_jobs × fs × rs)
#   • growth_demand == ceil(fh × (growth_rate_percent_1y / 100) × rs)
#   • backfill_demand == ceil(fh × ar × rs)
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
#         "employees_current": {{"EC": <float>, "MC": <float>, "PC": <float>, "reason": "<string>"}},
#         "open_jobs": {{"EC": <float>, "MC": <float>, "PC": <float>, "reason": "<string>"}},
#         "growth_rate_percent_1y": {{"EC": <float>, "MC": <float>, "PC": <float>}},
#         "company_attrition_percent_1y": {{"EC": <float>, "MC": <float>, "PC": <float>}},
#         "function_share": {{"EC": <float>, "MC": <float>, "PC": <float>}},
#         "function_headcount": {{"EC": <float>, "MC": <float>, "PC": <float>}},
#         "role_share": {{"EC": <float>, "MC": <float>, "PC": <float>}},
#         "attrition_rate": {{"EC": <float>, "MC": <float>, "PC": <float>}}
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
#####################3 THIS IS SUMMARIZED PROMPT ##############################################################

# PREDICTION_USER_TEMPLATE = r"""Analyze company talent insights to calculate 12-month hires for role: "{role}"

# --- INPUT DATA ---
# {insights_json}

# Target Role: "{role}"
# CRITICAL RULES:
# 1. For skill-matched roles: Use matched_skill.employees as function_headcount (e.g., "AI Engineer" matches "Microsoft Azure ML" → use ML employee count)
# 2. For function_share: Use top_functions_percent/100 when available, else 0.05
# 3. Use function-specific attrition rates when available
# 4. CEIL all final calculations (active, growth, backfill)
# 5. Generate valid JSON output only
# 6. Use only provided data, no assumptions

# ALGORITHM:
# 1. Determine function_hint:
#    - Match role to top functions (Engineering, IT, Sales, HR) or infer from role type:
#      • Engineering: Engineer, Developer, DevOps, Data, AI, ML, R&D, Software
#      • IT: Infrastructure, Systems, Network, IT Support
#      • Sales: Sales, Business Development
#      • HR: Human Resources, Talent, Recruiting
#      • Default: "Other"

# 2. Calculate function_share (fs):
#    - fs = (top_functions[function_hint] / 100) if exists else 0.05
#    - Round to 6 decimals

# 3. Skill Matching:
#    3.1 Tokenize role:
#        - Lowercase, replace -/_ with space, split
#        - Remove common stopwords (and, of, for, the, etc.)
#        - Save as calc.inputs.role_tokens
   
#    3.2 Build skill entries:
#        - From top_skills, fastest_growing, emerging
#        - Format: [name, employees (int), open_jobs (int or null), source]
#        - Save names as calc.inputs.available_skills

#    3.3 Match tokens to skills using:
#        - Abbreviations (ai→AI, ml→ML, js→JavaScript, py→Python, etc.)
#        - Exact or whole-word matches
#        - Common variations (e.g., "dev" → "development")3.4 Select best match (must choose if matches non-empty):
#    - Choose skill with highest employee count if relevant to role
#    - Save as calc.inputs.matched_skill or null if no match

# 4. Calculate Metrics:
#    - function_headcount = matched_skill.employees if matched_skill else total_employees * function_share
#    - Use function-specific attrition rate if available, else company average
#    - Calculate: active, growth, backfill components
#    - Sum components for total hires
#    - Calculate confidence based on data quality and matches

# 5. Output Format:
#    {
#      "result": {
#        "hires_12m": <int>,
#        "hires_confidence": <float>,
#        "function_headcount": <int>,
#        "function_share": <float>,
#        "attrition_rate": <float>,
#        "components": {
#          "active": <int>,
#          "growth": <int>,
#          "backfill": <int>
#        }
#      },
#      "calc": {
#        "inputs": {
#          "role_tokens": [<str>],
#          "available_skills": [<str>],
#          "matched_skill": {
#            "name": <str>,
#            "employees": <int>,
#            "open_jobs": <int>,
#            "source": <str>
#          } or null,
#          "function_hint": <str>,
#          "function_share": <float>
#        },
#        "steps": {
#          "function_headcount": <int>,
#          "attrition_rate": <float>,
#          "active_hires": <int>,
#          "growth_hires": <int>,
#          "backfill_hires": <int>,
#          "total_hires": <int>,
#          "confidence_factors": {
#            "data_quality": <float>,
#            "skill_match": <float>,
#            "function_match": <float>
#          },
#          "final_confidence": <float>
#        }
#      }
#    }
#  6. Validation Rules:
#    - All calculations must be shown in the audit trail
#    - Use CEIL for all final values
#    - Maintain 6 decimal precision for all calculations
#    - If any value is inconsistent with its formula, recompute
#    - Never include trailing commas in JSON
#    - Validate JSON output before returning

# Return ONLY the JSON object. No extra text or explanations."""

############################################ THIS IS FUTURE PROMPT #################################################################

PREDICTION_USER_TEMPLATE = r"""You are given two inputs:

1) Company Talent-Insights JSON
--- BEGIN JSON ---
{insights_json}
--- END JSON ---

2) Target role: "{role}"

Your task: Perform a STRICT, STEP-BY-STEP calculation of 12-month hires for the target role.

CRITICAL RULES FOR SKILL-MATCHED ROLES:
- If you find a matched skill for the role, you MUST use matched_skill.employees as function_headcount
- Example: AI Engineer matches "Microsoft Azure Machine Learning" (12981 employees) → function_headcount = 12981, NOT department headcount
- Always use function-specific attrition rate when available (e.g., Engineering: 9%, not company-wide 12%)

CRITICAL RULES FOR FUNCTION_SHARE:
- ALWAYS use function_share from top_functions_percent data when available
- Example: Engineering = 40% from top_functions_percent → function_share = 0.4
- DO NOT calculate function_share as matched_skill.employees / total_employees
- Only use fallback 0.05 if the function is not in top_functions_percent

IMPORTANT RULES
- Do not invent data. Only use values present in the JSON or the rules below.
- Use CEILING for all final component calculations (active, growth, backfill).
- If any computed value is inconsistent with its formula, recompute until consistent.
- Generate valid JSON only - no trailing commas, no missing properties.
- Numbers must be plain numerics (no commas, no text).
- Do not include any keys not listed in the schema at the bottom.
- Ignore unrelated sections (industries, education, schools, etc.).
- ALL confidence arithmetic MUST be internally consistent and shown in the audit exactly as specified.

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
  - ALWAYS use top_functions_percent when available: fs = percent_employees / 100
  - Example: Engineering has 40% in top_functions_percent → fs = 0.4
  - DO NOT calculate as skill_employees / employees_current
  - If function_hint not in top_functions_percent → fs = 0.05 (fallback)
  - Round fs to 6 decimals immediately.

Step 3. SKILL MATCHING PROCESS (MANDATORY) — produce machine-readable outputs.

3.1 Tokenize the role into calc.inputs.role_tokens:
  • Lowercase, replace '-' '/' '_' with space, split on whitespace.
  • Remove stopwords: {{"and","of","for","the","a","an","to","in","on","with","senior","sr","jr","junior","lead","principal","manager","mgr","director","head","chief","vp","vice","president","executive","specialist","analyst","associate","coordinator"}}.
  • Remove empties.
  • Save role_tokens in calc.inputs.role_tokens.

3.2 Build SKILL_ENTRIES from JSON paths (tolerant to missing):
  • top = insights.skills.top_skills or []
  • fast = insights.skills.fastest_growing or []
  • Each entry → [name: skill, employees: employees (int or 0), open_jobs: open_jobs (int or null), source: "top_skills"|"fastest_growing"|"emerging"].
  • Save calc.inputs.available_skills = [names...].

3.3 Match tokens → skills:

Abbrev map: ai→"artificial intelligence", ml→"machine learning", js→"javascript", py→"python", dev→"development"/"developer", ops→"operations", qa→"quality assurance", ui→"user interface", ux→"user experience".

Token normalization: lowercase, remove punctuation, strip spaces.

Match rules:
• Exact match: token == skill_name (case-insensitive).
• Whole-word match: token appears as a separate word in skill_name (e.g., "ai" matches "AI Engineer", not "microsoft").
• Abbrev expansion: expanded form appears in skill_name (e.g., "ml" → "machine learning").

Do NOT allow substring-only matches (e.g., "hr" in "sharepoint" or "microsoft").

Record each match as (token, skill_name, employees, source, open_jobs).

Save matches array in calc.inputs.matches

3.4 Select best match (must choose if matches non-empty):
  • Choose skill with highest employees if it is relevant to that {{role}} do not assume.
  • If tie, prefer source order ["top_skills","fastest_growing"].
  • Set matched_skill = chosen skill entry.

3.5 Use skill data IF and ONLY IF matched_skill exists:
  • CRITICAL: Set function_headcount (fh) = matched_skill.employees (int). DO NOT use department headcount.
  • Set open_jobs = matched_skill.open_jobs if not null else department_level_open_jobs.
  • CRITICAL: Use attrition_rate = insights.attrition_breakdown.by_function["Engineering"] (if present) else company_profile.attrition_percent_1y.
  • In confidence.parameters.function_headcount.reason include exactly: "fh=skills_employee_count={{fh}}, matched_skill='{{skill_name}}', from_tokens={{role_tokens}}".
  • DO NOT execute department fallback; proceed to Step 4.

  MANDATORY VERIFICATION: If matched_skill exists, function_headcount MUST equal matched_skill.employees, NOT department headcount.

3.6 If no matches found:
  • Save the explicit string in calc.inputs.matches as empty and add: "No skill matches found for tokens {{role_tokens}}. Using department fallback."
  • Then execute Department Fallback as specified (fh = max(1, round(employees_current × fs)) ...).

- **DEPARTMENT FALLBACK (only if no skill matches)**:
    - If function_headcount contains function_hint → use that integer.
    - Else → fh = round(employees_current × fs).
    - If fh is missing or ≤ 0 after the above → set fh = max(1, round(employees_current × fs)).

FREEZE RULE: Once you have computed function_share (fs) and function_headcount (fh), 
they become FROZEN VALUES. 
- You MUST use these exact frozen values for all subsequent calculations 
 (active_demand, growth_demand, backfill_demand). 
- Do NOT substitute or recompute fs or fh later. 
- Never mix skill-based fs with department fh or vice versa. 
- Always explicitly state in calc.inputs which source_type you used: "source_type": "function_headcount" or "source_type": "skills_headcount".

Step 4. role_share (rs)
   - Start with rs = 1.0 only if:
      • role string contains function_hint name as substring AND
      • you are absolutely sure that 100% of that function is this role.
      # Skilll Match employees divide by Total
  - Otherwise:
      • Tokenize role (lowercase, split on space/hyphen, remove stopwords).
      • Create SKILL_NAME_LIST = names from skills.top_skills and skills.fastest_growing (if present).
      • n = min(20, length of SKILL_NAME_LIST). If missing or empty → rs = 0.10 (skip rest).
      • k = number of SKILL_NAME_LIST items (consider only the first n) that contain ANY token as substring.
      • raw = round(1.5 * k / n, 2)
      • rs = min(max(raw, 0.05), fs).
  - This ensures rs never exceeds fs and is never below 0.05.

  FREEZE RULE: Once role_share (rs) is computed, you MUST freeze rs as well. Do NOT recompute or modify rs in later steps.

Step 5. attrition_rate (ar) for function
  - CRITICAL: Look up attrition_breakdown.by_function for an entry matching function_hint (case-insensitive).
  - If found, ALWAYS set ar = that_percent / 100 (explicit) — mark source="explicit" penalty=0. (Prioritize this over company attrition rate.)
  - Only if no by_function entry exists for function_hint:ar = company_profile.attrition_percent_1y / 100, mark source="fallback" penalty=-0.3
  - Never alternate between the two; always prioritize function-level if present.

  EXAMPLE: For "AI Engineer" with function_hint="Engineering":
  - Check attrition_breakdown.by_function for "Engineering" entry
  - If found (e.g., "Engineering": 9%), use ar = 0.09, NOT company-wide 12%
  - Mark as source="explicit" with penalty=0
  - If both are missing, set ar = 0.05 as fallback penalty=-0.3
  - Round attrition_rate to 4 decimal places immediately after conversion.
  - Always output attrition_rate as a decimal between 0 and 1 (e.g., 0.09 not 9).
  - Once attrition_rate is set, NEVER change it during the run.

FREEZE RULE: Once attrition_rate (ar) is computed, you MUST freeze ar. Do NOT recompute or modify ar in later steps.


Step 6. active_demand = ceil(open_jobs × fs × rs)
Step 7. growth_demand = ceil(fh × (growth_rate_percent_1y / 100) × rs)  
Step 8. backfill_demand = ceil(fh × ar × rs)

NUMERIC PRECISION LOCK (mandatory for all arithmetic)
  - Compute with at least 6 decimal places for all intermediate products; apply CEILING only at the final step of each component.
  - Define:
      fsr = fs * rs
      grr = (growth_rate_percent_1y / 100) * rs
      arr = ar * rs
  - Then compute strictly:
      active_demand  = ceil(open_jobs * fsr)
      growth_demand  = ceil(function_headcount * grr)
      backfill_demand= ceil(function_headcount * arr)
  - HARD CHECKS (must pass):
      • active_demand == ceil(open_jobs * fs * rs)
      • growth_demand == ceil(function_headcount * (growth_rate_percent_1y/100) * rs)
      • backfill_demand == ceil(function_headcount * ar * rs)
  - If any result differs by ≥ 0.001 from the exact ceiling of the raw product, set consistency_ok=false and recompute until all equalities hold.

Step 9. headcount = active_demand + growth_demand + backfill_demand

========================================
TEAM-LEVEL PARAMETERS (must check)
========================================
Check if the following parameters exist explicitly in the JSON for the target role/team:
1) Department → Team Breakdown (e.g., AI, DevOps, Backend, Frontend, QA)
2) Headcount per Team
3) Historical Headcount by Role/Function
4) Expected Growth Rate by Department & Team (%)
5) Historical Attrition Rate by Team/Role (%)
6) Open Roles by Team/Role
7) Role Share within Team

For each of these, record in the confidence.parameters section:
- "source": "explicit" if directly present; "derived" if computed from department-level; "fallback" if missing/defaulted.
- "reason": short text explaining what you found or how it was derived.
- "json_pointer": the JSON key/path used (or "n/a" if derived/fallback).

========================================
CONFIDENCE SCORING (must compute EXACTLY)
========================================

CRITICAL: You MUST include EXACTLY 15 parameters in per_parameter_penalties array - NO EXCEPTIONS.

MANDATORY PARAMETER LIST (process in this exact order):
Key Parameters (8):
1. employees_current
2. open_jobs  
3. growth_rate_percent_1y
4. company_attrition_percent_1y
5. function_share
6. function_headcount
7. role_share
8. attrition_rate

Team Parameters (7):
9. team_breakdown
10. headcount_per_team
11. historical_headcount_role
12. expected_growth_team
13. historical_attrition_team
14. open_roles_team
15. role_share_team

DETERMINISTIC SOURCE RULES (NO VARIATIONS):
- employees_current: "explicit" if in company_profile.employees_current, else "fallback"
- open_jobs: "explicit" if in company_profile.open_jobs, else "fallback"
- growth_rate_percent_1y: "explicit" if in company_profile.growth_rate_percent_1y, else "fallback"
- company_attrition_percent_1y: "explicit" if in company_profile.attrition_percent_1y, else "fallback"
- function_share: "explicit" if from top_functions_percent[function_hint], else "fallback" (0.05)
- function_headcount: "explicit" if from function_headcount[function_hint], "derived" if calculated from employees_current*function_share, else "fallback" (1)
- role_share: "explicit" if 1.0 from exact function match, "derived" if from skills calculation, else "fallback" (0.10)
- attrition_rate: "explicit" if from attrition_breakdown.by_function[function_hint], else "fallback"
- ALL team parameters (9-15): ALWAYS "fallback" with penalty -0.2 each

EXACT PENALTY MAPPING:
- "explicit" → penalty = 0.0
- "derived" → penalty = -0.1
- "fallback" → penalty = -0.2 (except attrition_rate fallback = -0.3)

========================================
ROLE EVIDENCE PENALTY (CRITICAL)
========================================
- If skill_employees=0 AND function_share source="fallback":
    evidence_penalty=-0.3
- Else evidence_penalty=0.0
- Add evidence_penalty to total_penalty before scaling.

You MUST compute forecast_confidence EXACTLY as follows — DO NOT improvise:

========================================
CONFIDENCE CALCULATION
========================================

1. **Base confidence**  
   base_confidence = 1.00

2. **Assign a penalty to EACH parameter (15 parameters total):**  
   - source = "explicit" → penalty = 0.0  
   - source = "derived" → penalty = -0.1  
   - source = "fallback" → penalty = -0.2  

3. **Sum the 15 penalties**  
   per_parameter_sum = sum of all 15 penalties (this is usually negative)

4. **Team vs Department penalty:**  
   - team_vs_department_penalty = -0.1 **only if** (role ≠ function_hint AND all 7 team parameters are fallback)  
   - Otherwise 0.0

5. **Missing-majority penalty:**
   - missing_majority_key_penalty = -0.05 **only if** (count of key parameters with source in ["derived","fallback"] > 4), else 0.0.

5.5. **No-data penalty for unsupported roles:**
   - no_data_penalty = -2.0 **only if** (function_share is fallback 0.05 AND no matched_skill AND role not in top_functions_percent)
   - This applies to roles like "HR Manager" that have no representation in the LinkedIn insights data
   - Otherwise 0.0

6. **Total penalty:**
   total_penalty = per_parameter_sum + team_vs_department_penalty + missing_majority_key_penalty + no_data_penalty + evidence_penalty

7. **Apply SCALING FACTOR of 0.1 to the total penalty**  
   scaled_penalty = total_penalty * 0.1  
   (You MUST multiply by 0.1. Do not forget this step.)

8. **Compute raw confidence:**  
   raw_confidence = base_confidence + scaled_penalty

9. **Clamp to [0.5, 1.0]:**  
   clamped_confidence = max(0.5, min(1.0, raw_confidence))

10. **Final confidence:**  
    final_confidence = floor(clamped_confidence*100)/100   (floor to 2 decimals)

11. **Output in JSON:**  
    - Include per_parameter_penalties array (length 15)  
    - Include team_vs_department_penalty, missing_majority_key_penalty, sum_penalties, raw_confidence, clamped_confidence, final_confidence  
    - Include key_counts (explicit, derived, fallback, total, derived_or_fallback)  
    - Include team_counts (explicit, derived, fallback, total)  
    - forecast_confidence = final_confidence (float between 0.5 and 1.0)

MANDATORY COUNTS:  
- key parameters total = 8  
- team parameters total = 7  
- per_parameter_penalties length = 15  

Do NOT skip the SCALING FACTOR. This is CRITICAL.  

MANDATORY COUNTS (must be exact):
- key_counts.total = 8
- team_counts.total = 7
- Length of per_parameter_penalties = 15

========================================
FINAL DETERMINISTIC LOCK
========================================
- Round fs, rs, ar to 6 decimals immediately after computing.
- Floor final_confidence to 2 decimals.
- Floor headcount to int after sum of demands.
- If any computed value differs >0.001 across recomputation steps, recompute until stable.

========================================
DETERMINISTIC PENALTY ENFORCEMENT
========================================
• If a parameter’s value is computed from employees_current, function_share, or skills, classify it as "derived" (never "fallback").
• Only use "fallback" when parameter is completely missing or defaulted (e.g., hardcoded 0.05).
• Always apply the same penalty for the same source classification.
• Count key parameters with source in ["derived","fallback"] exactly once per run.
• After computing penalties, round scaled_penalty and raw_confidence to 5 decimal places before clamping to eliminate floating randomness.
• Always floor (not round) final_confidence to 2 decimals.
• If per_parameter_sum<-2.0 then force final_confidence=min(final_confidence,0.8).

========================================
SELF-CONSISTENCY CHECK
========================================
- Verify that:
  • active_demand == ceil(open_jobs × fs × rs)
  • growth_demand == ceil(fh × (growth_rate_percent_1y / 100) × rs)
  • backfill_demand == ceil(fh × ar × rs)
  • attrition_rate == (by_function attrition_percent /100) if present else company_profile.attrition_percent_1y /100
  • headcount == active_demand + growth_demand + backfill_demand

CRITICAL VALIDATION FOR SKILL-MATCHED ROLES:
- If matched_skill exists, function_headcount MUST equal matched_skill.employees
- If function_hint has attrition_breakdown.by_function entry, attrition_rate MUST use that value, NOT company-wide
- Example: AI Engineer with matched_skill "Microsoft Azure Machine Learning" (12981 employees):
  • function_headcount MUST be 12981, NOT 20941
  • attrition_rate MUST be 0.09 (Engineering), NOT 0.12 (company-wide)

- If any check fails, recompute once using the frozen fs, fh, rs, and ar values. Never invent new values or switch source paths.
  If still inconsistent, return an error string "consistency_failed=true" inside calc.consistency_ok, but do NOT change the frozen values.


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
      "source_type": "<skills_headcount|function_headcount>",
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
        "employees_current": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
        "open_jobs": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
        "growth_rate_percent_1y": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
        "company_attrition_percent_1y": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
        "function_share": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
        "function_headcount": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
        "role_share": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},
        "attrition_rate": {{"source": "<explicit|derived|fallback>", "EC": <float>, "MC": <float>, "PC": <float>, "json_pointer": "<string>", "reason": "<string>"}},

        "team_breakdown": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
        "headcount_per_team": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
        "historical_headcount_role": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
        "expected_growth_team": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
        "historical_attrition_team": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
        "open_roles_team": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}},
        "role_share_team": {{"source": "<explicit|derived|fallback>", "json_pointer": "<string>", "reason": "<string>"}}
      }},
      "audit": {{
        "per_parameter_penalties": [
          {{"parameter":"<name>","source":"<explicit|derived|fallback>","penalty":<float>,"json_pointer":"<path|n/a>","reason":"<short>"}}
        ],
        "team_vs_department_penalty": <float>,
        "missing_majority_key_penalty": <float>,
        "evidence_penalty": <float>,
        "sum_penalties": <float>,
        "raw_confidence": <float>,
        "clamped_confidence": <float>,
        "final_confidence": <float>,
        "key_counts": {{"explicit": <int>, "derived": <int>, "fallback": <int>, "total": 8, "derived_or_fallback": <int>}},
        "team_counts": {{"explicit": <int>, "derived": <int>, "fallback": <int>, "total": 7}},
        "rules_version": "v1.1"
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

You MUST return values based only on the frozen fs, fh, rs, and ar values computed once. 
Do NOT invent, randomize, or switch between different possible values.

Return ONLY the JSON object above. No extra text, no markdown."""