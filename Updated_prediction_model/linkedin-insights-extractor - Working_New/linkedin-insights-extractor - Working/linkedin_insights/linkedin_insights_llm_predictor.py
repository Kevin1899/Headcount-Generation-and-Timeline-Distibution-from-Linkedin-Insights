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
from .prompt_templates_predictor import PREDICTION_USER_TEMPLATE

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

# ---------------------------------------------------------------------------
#  Main function
# ---------------------------------------------------------------------------

def predict_headcount_llm(
    insights: Dict[str, Any],
    *,
    role: str,
    client: OpenAI | None = None,
    verbose: bool = False,
    return_full: bool = False,
) -> Union[int, Dict[str, Any]]:
    """
    Return forecast for *role* using LLM, with full confidence reasoning if requested.
    """

    if client is None:
        client = OpenAI()

    insights_str = json.dumps(insights, separators=(",", ":"))
    from collections import defaultdict

    class SafeDict(defaultdict):
        def __missing__(self, key):
            return '{' + key + '}'

    user_prompt = PREDICTION_USER_TEMPLATE.format_map(
        SafeDict(str, insights_json=insights_str, role=role)
    )

    # === Strict response schema with confidence audit ===
    response_format_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "HeadcountForecast",
            "strict": True,
            "schema": {
                "type": "object",
                "required": ["calc", "result"],
                "properties": {
                    "calc": {
                        "type": "object",
                        "required": ["inputs", "formulas", "substitutions", "confidence", "consistency_ok"],
                        "properties": {
                            "inputs": {
                                "type": "object",
                                "required": [
                                    "function_hint", "employees_current", "open_jobs",
                                    "growth_rate_percent_1y", "company_attrition_percent_1y",
                                    "function_share", "function_headcount", "role_share",
                                    "attrition_rate", "k", "n"
                                ],
                                "properties": {
                                    "function_hint": {"type": "string"},
                                    "employees_current": {"type": "integer"},
                                    "open_jobs": {"type": "integer"},
                                    "growth_rate_percent_1y": {"type": "number"},
                                    "company_attrition_percent_1y": {"type": "number"},
                                    "function_share": {"type": "number"},
                                    "function_headcount": {"type": "integer"},
                                    "role_share": {"type": "number"},
                                    "attrition_rate": {"type": "number"},
                                    "k": {"type": "integer"},
                                    "n": {"type": "integer"},
                                },
                                "additionalProperties": False,
                            },
                            "formulas": {
                                "type": "object",
                                "required": ["active_demand", "growth_demand", "backfill_demand", "headcount"],
                                "properties": {
                                    "active_demand": {"type": "string"},
                                    "growth_demand": {"type": "string"},
                                    "backfill_demand": {"type": "string"},
                                    "headcount": {"type": "string"},
                                },
                                "additionalProperties": False,
                            },
                            "substitutions": {
                                "type": "object",
                                "required": ["active_demand", "growth_demand", "backfill_demand", "headcount"],
                                "properties": {
                                    "active_demand": {"type": "string"},
                                    "growth_demand": {"type": "string"},
                                    "backfill_demand": {"type": "string"},
                                    "headcount": {"type": "string"},
                                },
                                "additionalProperties": False,
                            },
                            "confidence": {
                                "type": "object",
                                "required": ["parameters", "audit", "forecast_confidence"],
                                "properties": {
                                    "parameters": {
                                        "type": "object",
                                        # 🔹 REQUIRED array now explicitly lists every property
                                        "required": [
                                            "employees_current",
                                            "open_jobs",
                                            "growth_rate_percent_1y",
                                            "company_attrition_percent_1y",
                                            "function_share",
                                            "function_headcount",
                                            "role_share",
                                            "attrition_rate",
                                            "team_breakdown",
                                            "headcount_per_team",
                                            "historical_headcount_role",
                                            "expected_growth_team",
                                            "historical_attrition_team",
                                            "open_roles_team",
                                            "role_share_team"
                                        ],
                                        "properties": {
                                            "employees_current": _param_schema(),
                                            "open_jobs": _param_schema(),
                                            "growth_rate_percent_1y": _param_schema(),
                                            "company_attrition_percent_1y": _param_schema(),
                                            "function_share": _param_schema(),
                                            "function_headcount": _param_schema(),
                                            "role_share": _param_schema(),
                                            "attrition_rate": _param_schema(),
                                            "team_breakdown": _param_schema(scores=False),
                                            "headcount_per_team": _param_schema(scores=False),
                                            "historical_headcount_role": _param_schema(scores=False),
                                            "expected_growth_team": _param_schema(scores=False),
                                            "historical_attrition_team": _param_schema(scores=False),
                                            "open_roles_team": _param_schema(scores=False),
                                            "role_share_team": _param_schema(scores=False),
                                        },
                                        "additionalProperties": False,
                                    },
                                    "audit": {
                                        "type": "object",
                                        "required": [
                                            "per_parameter_penalties",
                                            "team_vs_department_penalty",
                                            "missing_majority_key_penalty",
                                            "sum_penalties",
                                            "raw_confidence",
                                            "clamped_confidence",
                                            "final_confidence",
                                            "key_counts",
                                            "team_counts",
                                            "rules_version"
                                        ],
                                        "properties": {
                                            "per_parameter_penalties": {
                                                "type": "array",
                                                "minItems": 15,
                                                "maxItems": 15,
                                                "items": {
                                                    "type": "object",
                                                    "required": ["parameter", "source", "penalty", "json_pointer", "reason"],
                                                    "properties": {
                                                        "parameter": {"type": "string"},
                                                        "source": {"type": "string", "enum": ["explicit", "derived", "fallback"]},
                                                        "penalty": {"type": "number", "enum": [0.0, -0.1, -0.2]},
                                                        "json_pointer": {"type": "string"},
                                                        "reason": {"type": "string"},
                                                    },
                                                    "additionalProperties": False,
                                                },
                                            },
                                            "team_vs_department_penalty": {"type": "number"},
                                            "missing_majority_key_penalty": {"type": "number"},
                                            "sum_penalties": {"type": "number"},
                                            "raw_confidence": {"type": "number"},
                                            "clamped_confidence": {"type": "number"},
                                            "final_confidence": {"type": "number"},
                                            "key_counts": {
                                                "type": "object",
                                                "required": ["explicit", "derived", "fallback", "total", "derived_or_fallback"],
                                                "properties": {
                                                    "explicit": {"type": "integer"},
                                                    "derived": {"type": "integer"},
                                                    "fallback": {"type": "integer"},
                                                    "total": {"type": "integer"},
                                                    "derived_or_fallback": {"type": "integer"}
                                                },
                                                "additionalProperties": False
                                            },
                                            "team_counts": {
                                                "type": "object",
                                                "required": ["explicit", "derived", "fallback", "total"],
                                                "properties": {
                                                    "explicit": {"type": "integer"},
                                                    "derived": {"type": "integer"},
                                                    "fallback": {"type": "integer"},
                                                    "total": {"type": "integer"}
                                                },
                                                "additionalProperties": False
                                            },
                                            "rules_version": {"type": "string"},
                                        },
                                        "additionalProperties": False,
                                    },
                                    "forecast_confidence": {"type": "number", "minimum": 0.5, "maximum": 1.0},
                                },
                                "additionalProperties": False,
                            },

                            "consistency_ok": {"type": "boolean"},
                        },
                        "additionalProperties": False,
                    },
                    "result": {
                        "type": "object",
                        "required": [
                            "function_hint", "function_share", "function_headcount", "role_share",
                            "active_demand", "growth_demand", "backfill_demand", "headcount",
                            "forecast_confidence"
                        ],
                        "properties": {
                            "function_hint": {"type": "string"},
                            "function_share": {"type": "number"},
                            "function_headcount": {"type": "integer"},
                            "role_share": {"type": "number"},
                            "active_demand": {"type": "integer"},
                            "growth_demand": {"type": "integer"},
                            "backfill_demand": {"type": "integer"},
                            "headcount": {"type": "integer"},
                            "forecast_confidence": {"type": "number", "minimum": 0.5, "maximum": 1.0},
                        },
                        "additionalProperties": False,
                    },
                },
                "additionalProperties": False,
            },
        },
    }

    # --- Call the API
    response = client.chat.completions.create(
        model=_MODEL,
        temperature=_TEMPERATURE,
        max_tokens=2000,
        response_format=response_format_schema,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_json = response.choices[0].message.content
    obj = json.loads(raw_json)

    # --- Verbose output: print reasoning
    if verbose:
        print("\n------- LLM PREDICTION DEBUG -------")
        print("=== PROMPT SENT TO MODEL ===\n", user_prompt[:1000], "...\n")
        print("=== RAW JSON RETURNED ===\n", json.dumps(obj, indent=2), "\n")
        res = obj.get("result", {})
        calc = obj.get("calc", {})
        conf = calc.get("confidence", {})
        print(f"Headcount: {res.get('headcount')} | Forecast confidence: {res.get('forecast_confidence')}")
        audit = conf.get("audit", {})
        if audit:
            print("\n-- Confidence math --")
            print(f"team_vs_department_penalty: {audit.get('team_vs_department_penalty')}")
            print(f"missing_majority_key_penalty: {audit.get('missing_majority_key_penalty')}")
            print(f"sum_penalties: {audit.get('sum_penalties')}")
            print(f"raw -> clamped -> final: {audit.get('raw_confidence')} -> "
                  f"{audit.get('clamped_confidence')} -> {audit.get('final_confidence')}")
        ppen = audit.get("per_parameter_penalties", [])
        if ppen:
            print("\n-- Per-parameter penalties --")
            for item in ppen:
                print(f"  {item.get('parameter')}: source={item.get('source')}, penalty={item.get('penalty')}, "
                      f"path={item.get('json_pointer')}, reason={item.get('reason')}")
        print("------------------------------------\n")

    # Return full JSON if requested
    if return_full:
        return obj

    # Default return: just headcount (backward compatible)
    if "result" in obj and isinstance(obj["result"], dict):
        hc = obj["result"].get("headcount")
        if hc is not None:
            return int(hc)
    if "headcount" in obj:
        return int(obj["headcount"])

    raise ValueError("Model response missing 'headcount' key in both result and top-level.")

