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
from .prompt_templates_predictor import (
    PREDICTION_USER_TEMPLATE
)

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
    "return ONLY a JSON object that matches the schema by calling the provided tool. "
    "No prose, no markdown, no additional keys."
)

# ---------------------------------------------------------------------------
#  Helper to build parameter schema for confidence
# ---------------------------------------------------------------------------

def _build_param(
    name: str,
    desc: str,
    required: bool = True,
    schema_type: str = "string",
) -> Dict[str, Any]:
    """Build a JSON schema for a parameter."""
    return {
        name: {"type": schema_type, "description": desc},
        "required": [name] if required else [],
    }

# ---------------------------------------------------------------------------
#  Main exported function
# ---------------------------------------------------------------------------

def predict_headcount_llm(
    insights: Dict[str, Any],
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
    
    user_prompt = PREDICTION_USER_TEMPLATE.format(
        insights_json=insights_str,
        role=role
    )

    # === Strict response schema with confidence audit ===
    response_schema = {
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
                                "n": {"type": "integer"}
                            }
                        },
                        "formulas": {
                            "type": "object",
                            "required": [
                                "function_share", "function_headcount", "role_share",
                                "attrition_rate", "active_demand", "growth_demand",
                                "backfill_demand", "headcount"
                            ],
                            "properties": {
                                "function_share": {"type": "string"},
                                "function_headcount": {"type": "string"},
                                "role_share": {"type": "string"},
                                "attrition_rate": {"type": "string"},
                                "active_demand": {"type": "string"},
                                "growth_demand": {"type": "string"},
                                "backfill_demand": {"type": "string"},
                                "headcount": {"type": "string"}
                            }
                        },
                        "substitutions": {
                            "type": "object",
                            "required": [
                                "function_share", "function_headcount", "role_share",
                                "attrition_rate", "active_demand", "growth_demand", "backfill_demand"
                            ],
                            "properties": {
                                "function_share": {"type": "string"},
                                "function_headcount": {"type": "string"},
                                "role_share": {"type": "string"},
                                "attrition_rate": {"type": "string"},
                                "active_demand": {"type": "string"},
                                "growth_demand": {"type": "string"},
                                "backfill_demand": {"type": "string"}
                            }
                        },
                        "confidence": {
                            "type": "object",
                            "required": [
                                "base", "per_parameter_penalties", "team_vs_department_penalty",
                                "missing_majority_key_penalty", "sum_penalties", "raw_confidence",
                                "clamped_confidence", "final_confidence"
                            ],
                            "properties": {
                                "base": {"type": "number"},
                                "per_parameter_penalties": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["parameter", "json_pointer", "source", "penalty"],
                                        "properties": {
                                            "parameter": {"type": "string"},
                                            "json_pointer": {"type": "string"},
                                            "source": {"type": "string", "enum": ["explicit", "derived", "fallback"]},
                                            "penalty": {"type": "number"}
                                        }
                                    }
                                },
                                "team_vs_department_penalty": {"type": "number"},
                                "missing_majority_key_penalty": {"type": "number"},
                                "sum_penalties": {"type": "number"},
                                "raw_confidence": {"type": "number"},
                                "clamped_confidence": {"type": "number"},
                                "final_confidence": {"type": "number"}
                            }
                        },
                        "consistency_ok": {"type": "boolean"}
                    }
                },
                "result": {
                    "type": "object",
                    "required": ["headcount", "forecast_confidence"],
                    "properties": {
                        "headcount": {"type": "integer"},
                        "forecast_confidence": {"type": "number"}
                    }
                }
            }
        }

    # === Call OpenAI API ===
    completion = client.chat.completions.create(
        model=_MODEL,
        temperature=_TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        tool_choice={"type": "function", "function": {"name": "HeadcountForecast"}},
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "HeadcountForecast",
                    "description": "The predicted headcount and confidence score.",
                    "parameters": response_schema,
                },
            }
        ],
    )

    # Extract the JSON string from the tool_calls
    tool_calls = completion.choices[0].message.tool_calls
    if tool_calls:
        obj_str = tool_calls[0].function.arguments
    else:
        # Fallback for debugging: check if content is a plain JSON string
        raw_content = completion.choices[0].message.content
        if raw_content:
            try:
                obj = json.loads(raw_content)
                # If it's a JSON string, we can use it directly
            except json.JSONDecodeError:
                 raise ValueError(f"Model response did not include the expected tool call and content was not valid JSON: {raw_content}")
        else:
            raise ValueError("Model response did not include the expected tool call or any content.")

    if 'obj' not in locals():
      obj = json.loads(obj_str)

    # === Optional debug dump ===
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