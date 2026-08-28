"""
News and Sentiment Analyst Agent - A2A Server (Port 8003).

NSE-focused sentiment agent for Indian equities.
"""

import os
import sys

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.google_llm import Gemini
from google.genai import types

from config.agent_prompts import SENTIMENT_ANALYST_PROMPT
from tools import news_fetcher

load_dotenv()

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def get_recent_news(ticker: str, days: int = 7) -> str:
    """Get recent India-market news for a stock."""
    import json

    return json.dumps(news_fetcher.get_recent_news(ticker, days=days, limit=20), indent=2)


def analyze_news_sentiment(ticker: str, days: int = 7) -> str:
    """Get sentiment analysis and key events for a stock."""
    import json

    return json.dumps(news_fetcher.get_news_with_sentiment(ticker, days=days), indent=2)


def detect_key_events(ticker: str) -> str:
    """Detect event categories from recent India-market news flow."""
    import json

    articles = news_fetcher.get_recent_news(ticker, days=14, limit=30)
    return json.dumps({"ticker": ticker, "key_events": news_fetcher.detect_key_events(articles)}, indent=2)


sentiment_analyst = LlmAgent(
    model=Gemini(
        model="gemini-2.0-flash-exp",
        retry_options=retry_config,
        generation_config={"response_mime_type": "application/json", "temperature": 0.4},
    ),
    name="sentiment_analyst",
    description=(
        "Expert NSE sentiment analyst specializing in public news flow, company events, "
        "and short-term event impact for Indian stocks."
    ),
    instruction=SENTIMENT_ANALYST_PROMPT,
    tools=[get_recent_news, analyze_news_sentiment, detect_key_events],
)

app = to_a2a(sentiment_analyst, port=8003)

print("Sentiment Analyst Agent initialized")
print("  Market: NSE / India")
print("  Tools: get_recent_news, analyze_news_sentiment, detect_key_events")
print("  Port: 8003")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="info")
