import requests
import os
import json
import pandas as pd
from time import sleep
from pathlib import Path
from google import genai
import re

# Your Gemini API key
API_KEY = "AIzaSyCiCNq3Am7C_Wa4P12PGRkET8R2IG7-rpA"


def extract_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text.strip()


def parse_rule_string(rule_str: str) -> dict | None:
    """
    Convert a string like "contract_end_date days until < 30"
    into structured rule format if recognizable.
    """
    rule_str = rule_str.strip()

    # Known fields and qualifiers
    FIELD_SCHEMA = {
        "upgradeEligibility.eligibilityStatus",
        "contract_end_date",
        "contract_start_date",
        "device_android",
        "device_google",
        "flex_pay_eligible",
        "ee_service_mrc_incl_vat",
        "ee_high_credit_risk_score"
    }

    pattern = r"(?P<field>\w+(?:\.\w+)?)(?:\s+(?P<qualifier>[a-zA-Z_]+))?\s*(?P<operator>=|!=|<|>|<=|>=)\s*(?P<value>.+)"
    match = re.match(pattern, rule_str)
    if match:
        groups = match.groupdict()
        field = groups["field"]
        if field not in FIELD_SCHEMA:
            return None
        rule = {
            "type": "rule",
            "field": field,
            "operator": groups["operator"],
            "value": groups["value"].strip()
        }
        if groups["qualifier"]:
            rule["qualifier"] = groups["qualifier"]
        return rule

    return None  # unrecognized string


def convert_row_to_json(row: dict) -> dict:
    """
    Convert a single Excel row (as dict) to a structured JSON object using Gemini.
    """
    prompt = f"""
    You are a helpful assistant. Convert the following action definition into a well-structured JSON object.

    Input Data:
    {json.dumps(row, indent=2)}

    Expected Output JSON Format:
    {{
      "actionCardId": "",
      "name": "",
      "category": "",
      "enabled": true,
      "metadata": {{
        "manufacturer": "",
        "location": "",
        "productType": "",
        "channel": [],
        "activeState": ""
      }},
      "eligibilityRules": [
        {{ "rule": "" }}
      ],
      "description": "",
      "tags": {{
        "Product Tags": [],
        "Life Stage Tags": [],
        "Intent Tags": [],
        "Business Label Tags": []
      }},
      "contentVariants": [
        {{
          "deviceFeature": "",
          "body": "",
          "title": "",
          "ctaText": "",
          "appDeepLink": "",
          "webUrl": ""
        }}
      ],
      "notes": ""
    }}

    Instructions:
    - Analyze the input data and populate the JSON accordingly.
    - Use your best judgment to infer tag values based on product name, description, and eligibility.
    - Output only valid JSON with no extra commentary or explanation.
    """

    client = genai.Client(api_key=API_KEY)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        print("✅ Gemini call done")

        # Safely parse JSON response
        response_text = response.text.strip()
        cleaned_json = extract_json(response_text)
        result = json.loads(cleaned_json)

        # 🎯 Parse string-based eligibility rules into structured rule format
        raw_rules = result.get("eligibilityRules", [])
        structured_rules = []
        for rule_obj in raw_rules:
            if isinstance(rule_obj, dict) and "rule" in rule_obj:
                parsed = parse_rule_string(rule_obj["rule"])
                if parsed:
                    structured_rules.append(parsed)
        result["eligibilityRules"] = structured_rules

        return result

    except json.JSONDecodeError:
        print("❌ Failed to parse JSON:\n", response_text)
        raise

    except Exception as e:
        print("❌ Gemini call failed:", str(e))
        raise


if __name__ == "__main__":
    sample_row = {
        "New Action Card ID": "SALES-1234",
        "Action Name": "Upgrade Test",
        "Category": "Test Category",
        "Manufacturer": "Samsung",
        "Location": "HERO",
        "Product Type": "Flex Pay",
        "Channel": "App and Web",
        "Active State": "Always On",
        "Description": "Try the new plan",
        "Device Feature": "S25 Edge",
        "Title": "Upgrade Now",
        "CTA Text": "Upgrade",
        "App deep link": "some-deep-link",
        "Web URL": "http://example.com",
        "Eligibilities on SST": "upgradeEligibility.eligibilityStatus = Y"
    }

    print(json.dumps(convert_row_to_json(sample_row), indent=2))
