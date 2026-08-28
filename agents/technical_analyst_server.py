"""
Technical Analyst Agent - A2A Server (Port 8002).

NSE-focused technical agent for Indian equities.
"""

import os
import sys

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.google_llm import Gemini
from google.genai import types

from config.agent_prompts import TECHNICAL_ANALYST_PROMPT
from tools import polygon_fetcher, technical_indicators

load_dotenv()

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def get_technical_indicators(ticker: str, days: int = 365) -> str:
    """Calculate technical indicators for an NSE/BSE symbol."""
    import json

    return json.dumps(technical_indicators.calculate_indicators(ticker, days=days), indent=2)


def get_price_history(ticker: str, days: int = 180) -> str:
    """Get NSE/BSE price history for technical analysis."""
    import json

    return json.dumps(polygon_fetcher.get_price_history(ticker, days=days), indent=2)


def get_support_resistance(ticker: str) -> str:
    """Get support and resistance levels for an NSE/BSE symbol."""
    import json

    return json.dumps(technical_indicators.get_support_resistance(ticker), indent=2)


technical_analyst = LlmAgent(
    model=Gemini(
        model="gemini-2.0-flash-exp",
        retry_options=retry_config,
        generation_config={"response_mime_type": "application/json", "temperature": 0.3},
    ),
    name="technical_analyst",
    description=(
        "Expert NSE technical analyst specializing in price action, RSI, MACD, "
        "support and resistance, and trend identification for Indian equities."
    ),
    instruction=TECHNICAL_ANALYST_PROMPT,
    tools=[get_technical_indicators, get_price_history, get_support_resistance],
)

app = to_a2a(technical_analyst, port=8002)

print("Technical Analyst Agent initialized")
print("  Market: NSE / India")
print("  Tools: get_technical_indicators, get_price_history, get_support_resistance")
print("  Port: 8002")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
