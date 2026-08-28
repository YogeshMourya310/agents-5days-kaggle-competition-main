"""
Fundamental Analyst Agent - A2A Server (Port 8001).

NSE-focused fundamental agent for Indian equities.
"""

import os
import sys

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.google_llm import Gemini
from google.genai import types

from config.agent_prompts import FUNDAMENTAL_ANALYST_PROMPT
from tools import polygon_fetcher, sec_edgar_fetcher

load_dotenv()

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def get_fundamentals(ticker: str) -> str:
    """Get NSE-oriented company fundamentals and valuation context."""
    import json

    return json.dumps(polygon_fetcher.get_fundamentals(ticker), indent=2)


def get_sec_filings(ticker: str, filing_type: str = "ANNOUNCEMENT") -> str:
    """Get recent company announcements and disclosure-style events."""
    import json

    return json.dumps(sec_edgar_fetcher.get_recent_filings(ticker, filing_type, count=2), indent=2)


def get_risk_factors(ticker: str) -> str:
    """Get a lightweight risk summary from recent announcements and company profile."""
    import json

    return json.dumps(sec_edgar_fetcher.get_risk_factors(ticker), indent=2)


fundamental_analyst = LlmAgent(
    model=Gemini(
        model="gemini-2.0-flash-exp",
        retry_options=retry_config,
        generation_config={"response_mime_type": "application/json", "temperature": 0.3},
    ),
    name="fundamental_analyst",
    description=(
        "Expert NSE fundamental analyst specializing in valuation, business quality, "
        "and company-level financial interpretation for Indian listed companies."
    ),
    instruction=FUNDAMENTAL_ANALYST_PROMPT,
    tools=[get_fundamentals, get_sec_filings, get_risk_factors],
)

app = to_a2a(fundamental_analyst, port=8001)

print("Fundamental Analyst Agent initialized")
print("  Market: NSE / India")
print("  Tools: get_fundamentals, get_sec_filings, get_risk_factors")
print("  Port: 8001")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
