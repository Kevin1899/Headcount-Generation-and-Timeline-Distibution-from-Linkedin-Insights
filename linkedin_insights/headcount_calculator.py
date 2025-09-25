"""
Enhanced Headcount Calculator with Location Support
Handles tokenization, skill matching, mathematical operations, confidence scoring, and location-based predictions
"""

import re
import math
from typing import Dict, List, Tuple, Optional, Any,Union
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from openai import OpenAI
import json

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class HeadcountCalculator:
    def __init__(self):
        self.stopwords = set(stopwords.words('english'))
        # Add custom stopwords for role processing
        self.custom_stopwords = {
            "and", "of", "for", "the", "a", "an", "to", "in", "on", "with",
            "senior", "sr", "jr", "junior", "lead", "principal", "manager", 
            "mgr", "director", "head", "chief", "vp", "vice", "president", 
            "executive", "specialist", "analyst", "associate", "coordinator"
        }
        self.all_stopwords = self.stopwords.union(self.custom_stopwords)
        
        # Abbreviation mapping
        self.abbrev_map = {
            "ai": "artificial intelligence",
            "ml": "machine learning", 
            "js": "javascript",
            "py": "python",
            "dev": ["development", "developer"],
            "ops": "operations",
            "qa": "quality assurance",
            "ui": "user interface",
            "ux": "user experience"
        }
    
    def tokenize_role(self, role: str) -> List[str]:
        """Tokenize role using NLTK and custom rules"""
        # Lowercase and replace special characters
        role_clean = role.lower()
        role_clean = re.sub(r'[-/_]', ' ', role_clean)
        
        # Tokenize using NLTK
        tokens = word_tokenize(role_clean)
        
        # Remove stopwords and empty tokens
        tokens = [token for token in tokens if token and token not in self.all_stopwords]
        
        # Remove punctuation-only tokens
        tokens = [token for token in tokens if re.search(r'[a-zA-Z]', token)]
        
        return tokens
    

    def determine_function_hint(self,insights:Dict,role:str,client=None)->str:
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
    
    def extract_function_share(self, insights_json: Dict, function_hint: str) -> Tuple[float, str]:
        """Extract function share from top_functions_percent"""
        top_functions = insights_json.get('top_functions_percent', [])
        
        for func in top_functions:
            if func.get('function') == function_hint:
                return round(func.get('percent_employees', 0) / 100, 6), "explicit"
        
        return 0.05, "fallback"  # Default fallback
    
    def ai_match_tokens_to_skills(
    self,
    insights: Dict, 
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
        
        # --- Step 1: NLTK-based Tokenization ---
        role_clean = re.sub(r"[-/_]", " ", role.lower())
        tokens = word_tokenize(role_clean)              
        role_tokens = [t for t in tokens if t.isalnum() and t not in self.all_stopwords]

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
    1. Match each token to skills using exact match, whole-word match, or abbrev expansion ({json.dumps(self.abbrev_map)}).
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
            print(f"This is the Output from CHATGPT {output}")
        except json.JSONDecodeError:
            raise ValueError(f"AI did not return valid JSON:\n{content}")

        # Normalize matched_skill key
        if "matched_skill" in output and output["matched_skill"] is not None:
            ms = output["matched_skill"]
            if "skill_name" in ms:
                ms["name"] = ms.pop("skill_name")
            output["matched_skill"] = ms
        
        matches = output.get("matches", [])
        matched_skill = output.get("matched_skill")

        # --- Step 4: Compute function hint & frozen function share (fs) ---
        function_hint = self.determine_function_hint(insights=insights, role=role, client=client)
        fs = self.extract_function_share(insights_json=insights,function_hint=function_hint)
        fh,fh_source = self.calculate_function_headcount(insights_json=insights,function_hint=function_hint,function_share=fs,matched_skill=matched_skill)

        # --- Step 5: Department fallback if no matches ---
        

        if not matches or matched_skill is None:
            # No skill matches → use department fallback
            output["matches"] = []
            output["matches_reason"] = f"No skill matches found for role tokens {role_tokens}. Using department fallback."
            if fh is None or fh <= 0:
                fh = round(employees_current * fs) if fs else 1
            source_type = "function_headcount"


        # --- Step 6: Compute frozen role share (rs) ---
        rs_result = self.ai_role_share(
            role_tokens=role_tokens,
            role=role,
            skill_entries=[matched_skill] if matched_skill else None,
            function_hint=function_hint,
            function_share=fs,
            employees_current=employees_current,
            function_headcount=fh,
        )

        output.update({
            "role_tokens": role_tokens,
            "function_hint": function_hint,
            "function_share": fs,
            "function_headcount": fh,
            "role_share": rs_result["role_share"],
            "match_reason": rs_result["matches_reason"],
            "source_type": rs_result["source_type"],
        })

        return rs_result['role_share'],rs_result['source_type'],matched_skill
    def ai_role_share(
            self,
    role: str,
    role_tokens: List[str],
    function_hint: str,
    skill_entries: Union[List[Dict], Dict, None],
    function_share: float,
    employees_current: int,
    function_headcount:int,
    fs: float = 1.0,
    verbose: bool = True
) -> Dict[str, Any]:
        """
        Compute role_share (rs):
        - Condition 1: rs = 1.0 if role contains function_hint as substring
        - Condition 2: AI skill-role matching with formula:
                rs = matched_employees / employees_current
        """

        if function_share is None:
            function_share = 0.0

        result = {
            "matches": [],
            "matched_skill": None,
            "matches_reason": "",
            "role_tokens": role_tokens,
            "function_hint": function_hint,
            "function_share": function_share,
            "employees_current": employees_current,
            "role_share": 0.0,
            "source_type": ""
        }

        # ==== Condition 1: Exact match ====
        if function_hint.lower() in role.lower():
            result["role_share"] = 1.0
            result["matches_reason"] = "Exact function match (100%)"
            result["source_type"] = "function_exact"

            if verbose:
                print(f"[Condition 1] Role contains function_hint → rs=1.0")
            return result

        # ==== Condition 2: Skill-role match ====
        if not skill_entries:
            # No skills → fallback
            result["role_share"] = max(0.05, function_share)
            result["matches_reason"] = "No skills provided, fallback to function_share"
            result["source_type"] = "department_fallback"
            return result

        if skill_entries:
            # matched_employees = sum(s.get("employees", 0) for s in skill_entries)
            raw_ratio = function_headcount / max(employees_current, 1)
            rs = min(max(round(raw_ratio, 2), 0.05), fs)    

            result["matches"] = skill_entries
            result["matched_skill"] = skill_entries[0]["name"]
            result["matches_reason"] = (
                f"AI skill matches found → rs = matched_employees / employees_current "
                f"= {function_headcount} / {employees_current} = {rs}"
            )
            result["role_share"] = rs
            result["source_type"] = "skill_match"
        else:
            rs = max(0.05, function_share)
            result["role_share"] = rs
            result["matches_reason"] = "No valid matches, fallback to function_share"
            result["source_type"] = "department_fallback"

        return result

    
    def parse_location_from_query(self, query: str) -> str:
        """Extract location from natural language query"""
        # Common location patterns
        location_patterns = [
            r'in\s+([^?]+?)(?:\s+over|\s+in|\s*\?|$)',
            r'at\s+([^?]+?)(?:\s+over|\s+in|\s*\?|$)',
            r'for\s+([^?]+?)(?:\s+over|\s+in|\s*\?|$)',
        ]
        
        query_lower = query.lower()
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                location = match.group(1).strip()
                # Clean up common words
                location = re.sub(r'\b(the|next|12|months?|years?)\b', '', location).strip()
                return location
        
        return None
    
    def extract_location_info(self, insights_json: Dict, location_query: str = None) -> Tuple[float, str, Dict]:
        """Extract location share and info"""
        locations = insights_json.get('locations', [])
        
        if not locations:
            return 1.0, "fallback", None
        
        # If specific location requested, find it
        if location_query:
            location_query_lower = location_query.lower().strip()
            for location in locations:
                location_name = location.get('location', '').lower()

                # Try multiple matching strategies
                matches = [
                    location_query_lower in location_name,
                    location_name in location_query_lower,
                    # Check for key words (e.g., "beijing" matches "Beijing, China")
                    any(word in location_name for word in location_query_lower.split() if len(word) > 2),
                    # Check for exact city match (e.g., "bengaluru" matches "Greater Bengaluru Area")
                    any(word in location_query_lower for word in location_name.split() if len(word) > 3)
                ]

                if any(matches):
                    employees_current = insights_json.get('company_profile', {}).get('employees_current', 1)
                    location_employees = location.get('employees', 0)
                    location_share = round(location_employees / employees_current, 6) if employees_current > 0 else 0.0
                    return location_share, "explicit", location
        
        # If no specific location or not found, calculate total location share
        total_location_employees = sum(loc.get('employees', 0) for loc in locations)
        employees_current = insights_json.get('company_profile', {}).get('employees_current', 1)
        
        if total_location_employees > 0 and employees_current > 0:
            location_share = round(total_location_employees / employees_current, 6)
            return location_share, "derived", {"total_employees": total_location_employees}
        
        return 1.0, "fallback", None

    def extract_attrition_rate(self, insights_json: Dict, function_hint: str) -> Tuple[float, str]:
        """Extract attrition rate for function"""
        attrition_breakdown = insights_json.get('attrition_breakdown', {})
        by_function = attrition_breakdown.get('by_function', [])

        # Look for function-specific attrition rate
        for func in by_function:
            if func.get('function', '').lower() == function_hint.lower():
                return round(func.get('attrition_percent', 0) / 100, 4), "explicit"

        # Fallback to company-wide attrition
        company_attrition = insights_json.get('company_profile', {}).get('attrition_percent_1y', 0)
        if company_attrition > 0:
            return round(company_attrition / 100, 4), "derived"

        return 0.05, "fallback"  # Default fallback

    def calculate_function_headcount(self, insights_json: Dict, function_hint: str,
                                   matched_skill: Optional[Dict], function_share: float) -> Tuple[int, str]:
        """Calculate function headcount"""
        # If we have a matched skill, use its employee count
        if matched_skill:
            return matched_skill['employees'], "explicit"

        # Check function_headcount in JSON
        function_headcount_list = insights_json.get('function_headcount', [])
        for func in function_headcount_list:
            if func.get('function') == function_hint:
                return func.get('headcount', 0), "explicit"

        # Calculate from employees_current * function_share
        employees_current = insights_json.get('company_profile', {}).get('employees_current', 0)
        if employees_current > 0:
            calculated = max(1, round(employees_current * function_share))
            return calculated, "derived"

        return 1, "fallback"  # Default fallback

    def calculate_demands(self, open_jobs: int, function_headcount: int,
                         function_share: float, role_share: float,
                         growth_rate: float, attrition_rate: float) -> Dict[str, int]:
        """Calculate active, growth, and backfill demands"""
        # Calculate intermediate values with high precision
        fsr = function_share * role_share
        grr = (growth_rate / 100) * role_share
        arr = attrition_rate * role_share

        # Apply ceiling to final calculations
        active_demand = math.ceil(open_jobs * fsr)
        growth_demand = math.ceil(function_headcount * grr)
        backfill_demand = math.ceil(function_headcount * arr)

        headcount = active_demand + growth_demand + backfill_demand

        return {
            'active_demand': active_demand,
            'growth_demand': growth_demand,
            'backfill_demand': backfill_demand,
            'headcount': headcount
        }

    def calculate_confidence_score(self, parameter_sources: Dict[str, str],
                                 function_hint: str, role: str) -> Dict[str, Any]:
        """Calculate confidence score based on parameter sources"""
        # Define penalty mapping
        penalty_map = {
            'explicit': 0.0,
            'derived': -0.1,
            'fallback': -0.2
        }

        # Key parameters (8)
        key_params = [
            'employees_current', 'open_jobs', 'growth_rate_percent_1y',
            'company_attrition_percent_1y', 'function_share', 'function_headcount',
            'role_share', 'attrition_rate'
        ]

        # Team parameters (7) - always fallback
        team_params = [
            'team_breakdown', 'headcount_per_team', 'historical_headcount_role',
            'expected_growth_team', 'historical_attrition_team', 'open_roles_team',
            'role_share_team'
        ]

        # Location parameters (3) - new addition
        location_params = [
            'location_share', 'location_attrition', 'location_growth'
        ]

        # Calculate per-parameter penalties
        per_parameter_penalties = []
        key_derived_fallback_count = 0

        # Process key parameters
        for param in key_params:
            source = parameter_sources.get(param, 'fallback')
            penalty = penalty_map.get(source, -0.2)

            if source in ['derived', 'fallback']:
                key_derived_fallback_count += 1

            per_parameter_penalties.append({
                'parameter': param,
                'source': source,
                'penalty': penalty,
                'json_pointer': f'/company_profile/{param}' if source == 'explicit' else 'n/a',
                'reason': f'Value from {source}'
            })

        # Process team parameters (always fallback)
        for param in team_params:
            per_parameter_penalties.append({
                'parameter': param,
                'source': 'fallback',
                'penalty': -0.2,
                'json_pointer': 'n/a',
                'reason': 'No data available'
            })

        # Process location parameters
        for param in location_params:
            source = parameter_sources.get(param, 'fallback')
            penalty = penalty_map.get(source, -0.2)
            per_parameter_penalties.append({
                'parameter': param,
                'source': source,
                'penalty': penalty,
                'json_pointer': f'/locations/{param}' if source == 'explicit' else 'n/a',
                'reason': f'Location {source}'
            })

        # Calculate additional penalties
        per_parameter_sum = sum(p['penalty'] for p in per_parameter_penalties)

        # Team vs department penalty
        team_vs_department_penalty = -0.1 if (role.lower() != function_hint.lower() and
                                            all(p['source'] == 'fallback' for p in per_parameter_penalties[8:15])) else 0.0

        # Missing majority penalty
        missing_majority_key_penalty = -0.05 if key_derived_fallback_count > 4 else 0.0

        # Evidence penalty (simplified)
        evidence_penalty = 0.0

        # Total penalty calculation
        total_penalty = (per_parameter_sum + team_vs_department_penalty +
                        missing_majority_key_penalty + evidence_penalty)

        # Apply scaling factor
        scaled_penalty = total_penalty * 0.1

        # Calculate final confidence
        raw_confidence = 1.0 + scaled_penalty
        clamped_confidence = max(0.5, min(1.0, raw_confidence))
        final_confidence = math.floor(clamped_confidence * 100) / 100

        return {
            'per_parameter_penalties': per_parameter_penalties,
            'team_vs_department_penalty': team_vs_department_penalty,
            'missing_majority_key_penalty': missing_majority_key_penalty,
            'evidence_penalty': evidence_penalty,
            'sum_penalties': per_parameter_sum,
            'raw_confidence': raw_confidence,
            'clamped_confidence': clamped_confidence,
            'final_confidence': final_confidence,
            'key_counts': {
                'explicit': sum(1 for p in per_parameter_penalties[:8] if p['source'] == 'explicit'),
                'derived': sum(1 for p in per_parameter_penalties[:8] if p['source'] == 'derived'),
                'fallback': sum(1 for p in per_parameter_penalties[:8] if p['source'] == 'fallback'),
                'total': 8,
                'derived_or_fallback': key_derived_fallback_count
            },
            'team_counts': {
                'explicit': 0,
                'derived': 0,
                'fallback': 7,
                'total': 7
            },
            'location_counts': {
                'explicit': sum(1 for p in per_parameter_penalties[15:18] if p['source'] == 'explicit'),
                'derived': sum(1 for p in per_parameter_penalties[15:18] if p['source'] == 'derived'),
                'fallback': sum(1 for p in per_parameter_penalties[15:18] if p['source'] == 'fallback'),
                'total': 3
            }
        }

    def calculate_headcount_prediction(self, insights_json: Dict, role: str, location_query: str = None,client: Any = None,) -> Dict[str, Any]:
        """Main method to calculate headcount prediction with optional location support"""
        # Parse location from query if provided
        target_location = None
        if location_query:
            target_location = self.parse_location_from_query(location_query)
        
        employees_current = insights_json.get("company_profile", {}).get("employees_current", 0)


        # Step 1: Determine function hint
        function_hint = self.determine_function_hint(insights=insights_json, role=role, client=client)

        # Step 2: Extract function share
        function_share, fs_source = self.extract_function_share(insights_json, function_hint)
            
        # Step 3: Calculating Role share
        role_share,rs_source,matched_skill = self.ai_match_tokens_to_skills(insights=insights_json,role=role,employees_current=employees_current,client=client)

        # Step 4: Calculate function headcount
        function_headcount, fh_source = self.calculate_function_headcount(
                insights_json, function_hint, matched_skill, function_share)

        # Step 5: Extract attrition rate
        attrition_rate, ar_source = self.extract_attrition_rate(insights_json, function_hint)

        # Step 6: Extract location information
        location_share, ls_source, location_info = self.extract_location_info(insights_json, target_location)

        # Step 7: Extract other required values
        company_profile = insights_json.get('company_profile', {})
        employees_current = company_profile.get('employees_current', 0)
        open_jobs = company_profile.get('open_jobs', 0)
        growth_rate = company_profile.get('growth_rate_percent_1y', 0)
        company_attrition = company_profile.get('attrition_percent_1y', 0)

        # Step 8: Calculate demands
        demands = self.calculate_demands(
                open_jobs, function_headcount, function_share,
                role_share, growth_rate, attrition_rate)

        # Step 9: Calculate location-specific demand if applicable
        location_demand = None
        if location_share < 1.0:  # Only calculate if specific location
                location_demand = math.ceil(demands['headcount'] * location_share)

        # Step 10: Prepare parameter sources for confidence calculation
        parameter_sources = {
                'employees_current': 'explicit' if employees_current > 0 else 'fallback',
                'open_jobs': 'explicit' if open_jobs > 0 else 'fallback',
                'growth_rate_percent_1y': 'explicit' if growth_rate > 0 else 'fallback',
                'company_attrition_percent_1y': 'explicit' if company_attrition > 0 else 'fallback',
                'function_share': fs_source,
                'function_headcount': fh_source,
                'role_share': rs_source,
                'attrition_rate': ar_source,
                'location_share': ls_source,
                'location_attrition': 'fallback',  # Not implemented yet
                'location_growth': 'fallback'      # Not implemented yet
            }

        # Step 11: Calculate confidence
        confidence_data = self.calculate_confidence_score(parameter_sources, function_hint, role)

        # Step 12: Prepare final result
        result = {
                'calc': {
                    'inputs': {
                        'function_hint': function_hint,
                        'employees_current': employees_current,
                        'open_jobs': open_jobs,
                        'growth_rate_percent_1y': growth_rate,
                        'company_attrition_percent_1y': company_attrition,
                        'function_share': function_share,
                        'function_headcount': function_headcount,
                        'role_share': role_share,
                        'attrition_rate': attrition_rate,
                        'location_share': location_share,
                        'source_type': 'skills_headcount' if matched_skill else 'function_headcount',
                    },
                    'confidence': {
                        'audit': confidence_data,
                        'forecast_confidence': confidence_data['final_confidence']
                    }
                },
                'result': {
                    'function_hint': function_hint,
                    'function_share': function_share,
                    'function_headcount': function_headcount,
                    'role_share': role_share,
                    'active_demand': demands['active_demand'],
                    'growth_demand': demands['growth_demand'],
                    'backfill_demand': demands['backfill_demand'],
                    'headcount': demands['headcount'],
                    'location_demand': location_demand,
                    'forecast_confidence': confidence_data['final_confidence']
                },
                'debug_info': {
                    'matched_skill': matched_skill,
                    'parameter_sources': parameter_sources,
                    'target_location': target_location,
                    'location_info': location_info
                }
            }

        return result
