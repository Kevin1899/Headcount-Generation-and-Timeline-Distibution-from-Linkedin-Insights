#linkedin_insights/linkedin_insights_llm_predictor.py
from __future__ import annotations
"""
LLM-driven head-count predictor with full confidence audit
==========================================================

* Accepts a Talent-Insights JSON blob from `extract_insights()`.
* Accepts an arbitrary **target role** string.
* Builds a prompt (system + user) and returns the forecast for hires + full confidence reasoning.
"""

from typing import Any, Dict, Union
import json
import re
from .prompt_templates_predictor import PREDICTION_USER_TEMPLATE
from math import ceil


try:
    from openai import OpenAI
except ImportError as e:
    raise RuntimeError("openai>=1.3.0 is required: pip install openai") from e

# ---------------------------------------------------------------------------
#  Config
# ---------------------------------------------------------------------------

_MODEL = "gpt-4o-mini-2024-07-18"
_TEMPERATURE = 0  # deterministic output

SYSTEM_PROMPT = (
    "You are a deterministic hiring-demand calculator. "
    "Given structured LinkedIn Talent-Insights JSON and a target job role, "
    "you MUST follow the numerical rules in the user prompt verbatim and "
    "return ONLY a JSON object that matches the schema. "
    "No prose, no markdown, no additional keys."
)

# ---------------------------------------------------------------------------
#  Helper to build parameter schema for confidence
# ---------------------------------------------------------------------------

def _param_schema(scores: bool = True) -> Dict[str, Any]:
    keys = ["source", "json_pointer", "reason"]
    props = {
        "source": {"type": "string", "enum": ["explicit", "derived", "fallback"]},
        "json_pointer": {"type": "string"},
        "reason": {"type": "string"},
    }
    if scores:
        keys += ["EC", "MC", "PC"]
        props.update({
            "EC": {"type": "number"},
            "MC": {"type": "number"},
            "PC": {"type": "number"},
        })
    return {
        "type": "object",
        "required": keys,
        "properties": props,
        "additionalProperties": False,
    }

STOPWORDS = {"and","of","for","the","a","an","to","in","on","with","senior","sr","jr",
             "junior","lead","principal","manager","mgr","director","head","chief",
             "vp","vice","president","executive","specialist","analyst","associate",
             "coordinator"}

def ai_function_hint(insights:Dict[str,Any],role:str,client=None):
    prompt = """Step 1. Determine function_hint for the role.
  - If the role clearly belongs to a top-level function present in the JSON (e.g., "Engineering", "Information Technology", "Sales", "Human Resources"), choose that.
  - Otherwise:
      • If the role is Engineering-like (Engineer, Developer, DevOps, Data, AI, ML, R&D, Software), use "Engineering".
      • Else if the role is IT-like (Infrastructure, Systems, Network, IT Support), use "Information Technology".
      • Else if Sales-like, use "Sales".
      • Else if HR-like, use "Human Resources".
      • Otherwise use "Other". Return in Single Word only string Only"""
    
    if client is None:
        client = OpenAI()
    
    insights_str = json.dumps(insights)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt},{"role": "user", "content": role},{"role": "user", "content": insights_str}],
        temperature=0
    )

    function_hint = response.choices[0].message.content.strip()
    return function_hint
    

def calculate_function_share(insights: Dict[str, Any], role: str, function_hint: str) -> float | None:
    """
    Calculate function share (fs) based on function_hint and top_functions_percent.
    Returns a float between 0 and 1, or None if function_hint is not found.
    """
    top_functions = insights.get("top_functions_percent", [])

    fn_share = next(
        (f.get("percent_employees", 0) / 100 for f in top_functions if f.get("function") == function_hint),
        None
    )

    if fn_share is not None:
        return round(fn_share, 6)
    return None

ABBREV_MAP = {
    "ai": "artificial intelligence",
    "ml": "machine learning",
    "js": "javascript",
    "py": "python",
    "dev": "developer",
    "ops": "operations",
    "qa": "quality assurance",
    "ui": "user interface",
    "ux": "user experience"
}

def ai_match_tokens_to_skills(
    insights: Dict[str, Any], 
    role: str, 
    employees_current: int,
    client: OpenAI | None = None
) -> Dict[str, Any]:
    """
    Step 3.3–4: AI-assisted token → skill matching, best match selection,
    department fallback, and role share calculation with frozen values.
    
    Returns:
        matches, matched_skill, function_headcount (fh), function_share (fs),
        role_share (rs), source_type, role_tokens, function_hint
    """
    if client is None:
        client = OpenAI()

    # --- Step 1: Manual tokenization ---
    role_clean = re.sub(r"[-/_]", " ", role.lower())
    role_clean = re.sub(r"[^\w\s]", "", role_clean)
    role_tokens = [t.strip() for t in role_clean.split() if t.strip() not in STOPWORDS]

    # --- Step 2: Prepare skill list ---
    skill_entries = []
    for source_key, source_name in [("top_skills", "top_skills"), ("fastest_growing", "fastest_growing")]:
     skills_list = insights.get("skills", {}).get(source_key, [])
     for s in skills_list:
        # Extract the original skill string (support both "name" or "skill" keys)
        skill_name = s.get("skill") or s.get("name")
        if skill_name and isinstance(skill_name, str):
            skill_entries.append({
                "name": skill_name,
                "employees": s.get("employees", 0),
                "open_jobs": s.get("open_jobs", None),
                "source": source_name
            })


    # --- Step 3: Construct prompt for AI ---
    prompt = f"""
You are an expert at matching job roles to skills.

Role tokens: {json.dumps(role_tokens)}

Skills list: {json.dumps(skill_entries)}

Rules:
1. Match each token to skills using exact match, whole-word match, or abbrev expansion ({json.dumps(ABBREV_MAP)}).
2. Do NOT allow substring-only matches (e.g., "hr" in "sharepoint" is invalid).
3. Record each match as: (token, skill_name, employees, source, open_jobs)
4. After matching, select the best skill:
   - highest employees count
   - tie-breaker: top_skills > fastest_growing
5. Return JSON with two fields: "matches" (array of matched tokens & skills) and "matched_skill" (single chosen skill).
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a precise skill-matching assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    # Remove Markdown code fences if present
    if content.startswith("```json"):
        content = content[len("```json"):].strip()
    if content.startswith("```"):
        content = content[len("```"):].strip()
    if content.endswith("```"):
        content = content[:-3].strip()

    # Parse JSON
    try:
        output = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"AI did not return valid JSON:\n{content}")

    # Normalize matched_skill key
    if "matched_skill" in output and output["matched_skill"] is not None:
        ms = output["matched_skill"]
        if "skill_name" in ms:
            ms["name"] = ms.pop("skill_name")
        output["matched_skill"] = ms

    # --- Step 4: Compute function hint & frozen function share (fs) ---
    function_hint = ai_function_hint(insights=insights, role=role, client=client)
    fs = calculate_function_share(insights=insights,role=role,function_hint=function_hint)

    # --- Step 5: Department fallback if no matches ---
    matches = output.get("matches", [])
    matched_skill = output.get("matched_skill")

    if not matches or matched_skill is None:
        # No skill matches → use department fallback
        output["matches"] = []
        output["matches_reason"] = f"No skill matches found for role tokens {role_tokens}. Using department fallback."
        fh_list = insights.get("function_headcount", [])
        fh_entry = next((f for f in fh_list if f.get("function") == function_hint), None)
        fh = fh_entry.get("headcount") if fh_entry else None
        if fh is None or fh <= 0:
            fh = max(1, round(employees_current * fs)) if fs else 1
        source_type = "function_headcount"
    else:
        fh = matched_skill["employees"]
        source_type = "skills_headcount"

    fh = int(fh)  # freeze as integer

    # --- Step 6: Compute frozen role share (rs) ---
    rs_result = ai_role_share(role_tokens=role_tokens,role=role,skill_entries=skill_entries, function_hint=function_hint, function_share=fs,function_headcount=fh)

    output.update({
        "role_tokens": role_tokens,
        "function_hint": function_hint,
        "function_share": fs,
        "function_headcount": fh,
        "role_share": rs_result["role_share"],
        "match_reason":rs_result["matches_reason"],
        "source_type": rs_result["source_type"],
    })

    return output


################ Role Share - 1  ###############
def ai_role_share(
    role: str,
    role_tokens: List[str],
    function_hint: str,
    skill_entries: List[Dict[str, Any]],  # pre-built list of skills from JSON
    function_share: float,
    function_headcount: int,
    fs: float = 1.0,
    client=None
) -> Dict[str, Any]:
    """
    Compute role_share (rs) combining:
      - Condition 1: exact function match
      - Condition 2: AI skill-role matching
    Accepts pre-built skill_entries (list of dicts) instead of raw JSON.
    
    Returns a dictionary with role_share and detailed matching info.
    """
    if client is None:
        client = OpenAI()
    if function_share is None:
        function_share = 0.0

    result = {
        "matches": [],
        "matched_skill": None,
        "matches_reason": "",
        "role_tokens": role_tokens,
        "function_hint": function_hint,
        "function_share": function_share,
        "function_headcount": function_headcount,
        "role_share": 0.0,
        "source_type": ""
    }

    # ---- Condition 1: Exact function match ----
    if function_hint.lower() in role.lower():
        prompt_cond1 = f"""
Role: "{role}"
Function Hint: "{function_hint}"

Check if the role string fully represents the function.
Return 1.0 if yes, 0.0 if not. Only numeric value.
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert in role-function mapping."},
                {"role": "user", "content": prompt_cond1}
            ],
            temperature=0
        )
        try:
            rs = float(response.choices[0].message.content.strip())
        except ValueError:
            rs = 0.0

        if rs == 1.0:
            result["role_share"] = 1.0
            result["matches_reason"] = "Exact function match"
            result["source_type"] = "function_headcount"
            return result  # frozen role_share

    # ---- Condition 2: AI skill-role matching ----
    if not skill_entries:
        # fallback if no skills
        result["role_share"] = max(0.05, function_share)
        result["matches_reason"] = f"No skills available for role tokens {role_tokens}. Using fallback."
        result["source_type"] = "department_fallback"
        return result

    # Limit to top 20 skills
    skill_entries = skill_entries[:20]
    skill_names = [s["name"] for s in skill_entries]

    # AI determines matching skills
    prompt_cond2 = f"""
Role: "{role}"
Function Hint: "{function_hint}"
Tokens: {role_tokens}
Skills: {skill_names}

For each skill, determine if it belongs to this role.
Return a list of matched skills with their employee counts as JSON.
Example:
[{{"name": "Python", "employees": 12}}, {{"name": "AWS", "employees": 8}}]
"""
    response2 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert in role-skill mapping."},
            {"role": "user", "content": prompt_cond2}
        ],
        temperature=0
    )

    try:
        matched_skills = json.loads(response2.choices[0].message.content.strip())
    except Exception:
        matched_skills = []

    if matched_skills:
        matched_employees = sum(s.get("employees", 0) for s in matched_skills)
        rs = min(max(round(matched_employees / function_headcount, 2), 0.05), fs)
        result["matches"] = matched_skills
        result["matched_skill"] = matched_skills[0]["name"] if matched_skills else None
        result["matches_reason"] = "AI skill matches found"
        result["role_share"] = rs
        result["source_type"] = "skill_match"
    else:
        # fallback if no matches found
        rs = max(0.05, function_share)
        result["role_share"] = rs
        result["matches_reason"] = f"No skill matches found for role tokens {role_tokens}. Using department fallback."
        result["source_type"] = "department_fallback"

    return result

def compute_attrition_rate(insights: dict, function_hint: str) -> dict:
    """
    Step 5: attrition_rate (ar) for function.

    - If by_function has function_hint → ar = percent / 100, source="explicit", penalty=0
    - Else if company_profile.attrition_percent_1y → ar = percent / 100, source="fallback", penalty=-0.3
    - Else → safe default
    """
    result = {
        "attrition_rate": None,
        "source": None,
        "penalty": None,
        "function_hint": function_hint
    }

    # ---- Check function-level attrition first ----
    by_function = insights.get("attrition_breakdown", {}).get("by_function", [])
    func_entry = next(
        (f for f in by_function if f.get("function", "").lower() == function_hint.lower()),
        None
    )

    if func_entry and "attrition_percent" in func_entry:
        result["attrition_rate"] = func_entry["attrition_percent"] / 100.0
        result["source"] = "explicit"
        result["penalty"] = 0

    elif insights.get("company_profile", {}).get("attrition_percent_1y") is not None:
        company_attrition = insights["company_profile"]["attrition_percent_1y"]
        result["attrition_rate"] = company_attrition / 100.0
        result["source"] = "fallback"
        result["penalty"] = -0.3

    else:
        result["attrition_rate"] = 0.05  # safe default
        result["source"] = "missing"
        result["penalty"] = -0.5

    return result


from math import ceil
from typing import Dict, Any
import json

def predict_headcount_llm(
    insights: Dict[str, Any],
    *,
    role: str,
    client: Any = None,
    verbose: bool = False,
    return_full: bool = False,
):
    employees_current = insights.get("company_profile", {}).get("employees_current", 0)
    growth_rate_company = insights.get("company_profile", {}).get("growth_rate_percent_1y", 0) / 100
    open_jobs = insights.get("company_profile", {}).get("open_jobs", 0)

    # --- Step 1: Determine function hint ---
    function_hint = ai_function_hint(insights=insights, role=role, client=client)

    # --- Step 2: Function share ---
    function_share = calculate_function_share(insights=insights, role=role, function_hint=function_hint)
    if function_share is None:
        function_share = 0.0

    # --- Step 3: Skill matching & role_share ---
    skills = ai_match_tokens_to_skills(insights=insights, role=role, client=client, employees_current=employees_current)

    # Extract numeric role_share
    role_share_value = skills.get("role_share")
    if isinstance(role_share_value, dict):
        role_share_numeric = role_share_value.get("role_share", 0.0)
    else:
        role_share_numeric = role_share_value or 0.0

    # Function headcount
    function_headcount = skills.get("function_headcount") or 0

    # --- Step 4: Attrition rate ---
    attrition_rate_dict = compute_attrition_rate(insights=insights, function_hint=function_hint)
    attrition_rate_numeric = attrition_rate_dict.get("attrition_rate", 0.05)  # default fallback

    # --- Step 5: Calculate demands ---
    active_demand = ceil(open_jobs * function_share * role_share_numeric)
    growth_demand = ceil(function_headcount * growth_rate_company * role_share_numeric)
    backfill_demand = ceil(function_headcount * attrition_rate_numeric * role_share_numeric)

    # --- Step 6 : Headcount ---
    headcount = active_demand + growth_demand + backfill_demand

    if verbose:
        print(f"Role: {role}")
        print(f"Function Hint: {function_hint}")
        print(f"Function Share: {function_share}, Function Headcount: {function_headcount}")
        print(f"Role Share: {role_share_numeric}")
        print(f"Attrition Rate: {attrition_rate_numeric}")
        print(f"Active Demand: {active_demand}, Growth Demand: {growth_demand}, Backfill Demand: {backfill_demand}")
        print(f"Skill Matches: {skills}")
        print(f"Headcount : {headcount}")

    result = {
        "employees_current": employees_current,
        "growth_rate_company": growth_rate_company,
        "open_jobs": open_jobs,
        "role": role,
        "role_tokens": skills.get("role_tokens"),
        "function_hint": function_hint,
        "function_share": function_share,
        "function_headcount": function_headcount,
        "role_share": role_share_numeric,
        "matched_skill": skills.get("matched_skill"),
        "matches": skills.get("matches"),
        "match_reason": skills.get("match_reason"),
        "source_type": skills.get("source_type"),
        "attrition_rate": attrition_rate_numeric,
        "attrition_source": attrition_rate_dict.get("source"),
        "attrition_penalty": attrition_rate_dict.get("penalty"),
        "active_demand": active_demand,
        "growth_demand": growth_demand,
        "backfill_demand": backfill_demand,
        "headcount":headcount
    }

    return result
