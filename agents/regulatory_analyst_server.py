"""
Regulatory Analyst Agent - A2A Server (Port 8005).

NSE-focused regulatory and disclosure agent for Indian equities.
"""

import os
import sys

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.google_llm import Gemini
from google.genai import types

from config.agent_prompts import REGULATORY_ANALYST_PROMPT
from tools import news_fetcher, sec_edgar_fetcher

load_dotenv()

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def get_sec_filings(ticker: str, filing_type: str = "ANNOUNCEMENT") -> str:
    """Get recent company announcements and disclosure-style items."""
    import json

    return json.dumps(sec_edgar_fetcher.get_recent_filings(ticker, filing_type, count=3), indent=2)


def get_risk_factors(ticker: str) -> str:
    """Get a risk summary for an NSE/BSE company."""
    import json

    return json.dumps(sec_edgar_fetcher.get_risk_factors(ticker), indent=2)


def check_8k_filings(ticker: str, days: int = 90) -> str:
    """Compatibility wrapper returning material announcement events."""
    import json

    return json.dumps(sec_edgar_fetcher.check_recent_8k_filings(ticker, days=days), indent=2)


def get_industry_news(ticker: str) -> str:
    """Get recent industry and company-context news."""
    import json

    articles = news_fetcher.get_recent_news(ticker, days=30, limit=15)
    return json.dumps({"ticker": ticker, "industry_news": articles}, indent=2)


regulatory_analyst = LlmAgent(
    model=Gemini(
        model="gemini-2.0-flash-exp",
        retry_options=retry_config,
        generation_config={"response_mime_type": "application/json", "temperature": 0.3},
    ),
    name="regulatory_analyst",
    description=(
        "Expert NSE regulatory analyst specializing in company announcements, disclosure tone, "
        "legal risk, and sector-policy context for Indian listed companies."
    ),
    instruction=REGULATORY_ANALYST_PROMPT,
    tools=[get_sec_filings, get_risk_factors, check_8k_filings, get_industry_news],
)

app = to_a2a(regulatory_analyst, port=8005)

print("Regulatory Analyst Agent initialized")
print("  Market: NSE / India")
print("  Tools: get_sec_filings, get_risk_factors, check_8k_filings, get_industry_news")
print("  Port: 8005")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005, log_level="info")
