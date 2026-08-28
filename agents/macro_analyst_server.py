"""
Macro Analyst Agent - A2A Server (Port 8004).

NSE-focused macro agent for Indian equities.
"""

import os
import sys

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.google_llm import Gemini
from google.genai import types

from config.agent_prompts import MACRO_ANALYST_PROMPT
from tools import fred_fetcher

load_dotenv()

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def get_macro_indicators() -> str:
    """Get India-focused macro indicators for market analysis."""
    import json

    return json.dumps(fred_fetcher.get_macro_indicators(), indent=2)


def get_gdp_data() -> str:
    """Get India GDP trend data."""
    import json

    return json.dumps(fred_fetcher.get_gdp_data(), indent=2)


def get_inflation_data() -> str:
    """Get India CPI inflation data."""
    import json

    return json.dumps(fred_fetcher.get_inflation_data(), indent=2)


def get_fed_rate() -> str:
    """Compatibility wrapper returning RBI repo-rate context."""
    import json

    return json.dumps(fred_fetcher.get_fed_rate(), indent=2)


def get_treasury_yields() -> str:
    """Get India government security yields for multiple maturities."""
    import json

    return json.dumps(
        {
            "2_year": fred_fetcher.get_treasury_yield("2"),
            "10_year": fred_fetcher.get_treasury_yield("10"),
            "30_year": fred_fetcher.get_treasury_yield("30"),
        },
        indent=2,
    )


macro_analyst = LlmAgent(
    model=Gemini(
        model="gemini-2.0-flash-exp",
        retry_options=retry_config,
        generation_config={"response_mime_type": "application/json", "temperature": 0.3},
    ),
    name="macro_analyst",
    description=(
        "Expert macro analyst specializing in Indian economic conditions, RBI policy, "
        "inflation, growth, yields, and how they affect NSE-listed stocks."
    ),
    instruction=MACRO_ANALYST_PROMPT,
    tools=[get_macro_indicators, get_gdp_data, get_inflation_data, get_fed_rate, get_treasury_yields],
)

app = to_a2a(macro_analyst, port=8004)

print("Macro Analyst Agent initialized")
print("  Market: NSE / India")
print("  Tools: get_macro_indicators, get_gdp_data, get_inflation_data, get_fed_rate, get_treasury_yields")
print("  Port: 8004")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")
