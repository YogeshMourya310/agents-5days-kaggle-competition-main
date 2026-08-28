"""
News fetcher for NSE-oriented sentiment analysis.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv

from tools.polygon_fetcher import get_fundamentals, get_stock_news as market_get_news

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_BASE = "https://newsapi.org/v2"


def _search_terms_for_ticker(ticker: str) -> List[str]:
    """Build India-market search terms from ticker and company metadata."""
    base = ticker.upper().replace(".NS", "").replace(".BO", "")
    company = get_fundamentals(base)
    terms = [base, f"{base} NSE", f"{base} share price"]
    name = company.get("name") if isinstance(company, dict) else None
    if isinstance(name, str) and name and name.upper() != base:
        terms.extend([name, f"{name} NSE", f"{name} results"])
    return terms


def get_recent_news(ticker: str, days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent stock news from India-friendly queries and fallbacks."""
    articles: List[Dict[str, Any]] = []

    if NEWS_API_KEY:
        articles.extend(_fetch_from_news_api(ticker, days, limit))

    if len(articles) < limit:
        articles.extend(_fetch_from_market_data(ticker, limit - len(articles)))

    if len(articles) < limit:
        articles.extend(_fetch_from_google_news(ticker, limit - len(articles)))

    deduped = []
    seen = set()
    for article in articles:
        key = (article.get("title", "").strip().lower(), article.get("url", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(article)

    deduped.sort(key=lambda x: x.get("published_date", ""), reverse=True)
    return deduped[:limit]


def _fetch_from_news_api(ticker: str, days: int, limit: int) -> List[Dict[str, Any]]:
    """Fetch stock news from NewsAPI using India-market search terms."""
    try:
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query = " OR ".join(_search_terms_for_ticker(ticker)[:4])
        params = {
            "q": query,
            "from": from_date,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": limit,
            "apiKey": NEWS_API_KEY,
        }
        response = requests.get(f"{NEWS_API_BASE}/everything", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "ok":
            return []

        articles: List[Dict[str, Any]] = []
        for item in data.get("articles", []):
            if item.get("title") == "[Removed]":
                continue
            articles.append(
                {
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "source": item.get("source", {}).get("name", "Unknown"),
                    "published_date": item.get("publishedAt", ""),
                    "url": item.get("url", ""),
                    "author": item.get("author", ""),
                    "content": item.get("content", ""),
                    "data_source": "news_api_india_query",
                }
            )
        return articles
    except Exception:
        return []


def _fetch_from_market_data(ticker: str, limit: int) -> List[Dict[str, Any]]:
    """Use the market data provider's built-in news endpoint when available."""
    try:
        items = market_get_news(ticker, limit=limit)
        articles: List[Dict[str, Any]] = []
        for item in items:
            articles.append(
                {
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "source": item.get("source", "Market Data"),
                    "published_date": item.get("published_date", ""),
                    "url": item.get("article_url", ""),
                    "author": item.get("author", ""),
                    "keywords": item.get("keywords", []),
                    "data_source": "market_news",
                }
            )
        return articles
    except Exception:
        return []


def _fetch_from_google_news(ticker: str, limit: int) -> List[Dict[str, Any]]:
    """Fetch Google News RSS tuned for Indian equity search terms."""
    try:
        from bs4 import BeautifulSoup

        query = _search_terms_for_ticker(ticker)[0]
        url = f"https://news.google.com/rss/search?q={query}+NSE+India&hl=en-IN&gl=IN&ceid=IN:en"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")
        items = soup.find_all("item")[:limit]

        articles: List[Dict[str, Any]] = []
        for item in items:
            title = item.find("title")
            link = item.find("link")
            pub_date = item.find("pubDate")
            source = item.find("source")
            articles.append(
                {
                    "title": title.text if title else "",
                    "description": "",
                    "source": source.text if source else "Google News",
                    "published_date": pub_date.text if pub_date else "",
                    "url": link.text if link else "",
                    "data_source": "google_news_rss_india",
                }
            )
        return articles
    except Exception:
        return []


def analyze_sentiment(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run a lightweight finance-news sentiment pass."""
    if not articles:
        return {"overall_sentiment": "neutral", "sentiment_score": 0.0, "article_count": 0}

    positive_words = [
        "surge", "gain", "rise", "rally", "beat", "strong", "growth", "profit",
        "record", "order win", "approval", "upgrade", "dividend", "buyback",
    ]
    negative_words = [
        "plunge", "drop", "fall", "decline", "loss", "miss", "weak", "downgrade",
        "concern", "risk", "penalty", "notice", "investigation", "delay",
    ]

    positive_count = 0
    negative_count = 0
    neutral_count = 0

    for article in articles:
        text = (article.get("title", "") + " " + article.get("description", "")).lower()
        pos_score = sum(1 for word in positive_words if word in text)
        neg_score = sum(1 for word in negative_words if word in text)
        if pos_score > neg_score:
            positive_count += 1
        elif neg_score > pos_score:
            negative_count += 1
        else:
            neutral_count += 1

    total = len(articles)
    sentiment_score = (positive_count - negative_count) / total if total else 0.0
    overall = "positive" if sentiment_score > 0.2 else "negative" if sentiment_score < -0.2 else "neutral"
    return {
        "overall_sentiment": overall,
        "sentiment_score": round(sentiment_score, 2),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "article_count": total,
        "positive_ratio": round(positive_count / total, 2) if total else 0,
        "timestamp": datetime.now().isoformat(),
    }


def detect_key_events(articles: List[Dict[str, Any]]) -> List[str]:
    """Detect common company-event categories relevant to NSE investors."""
    events = set()
    event_keywords = {
        "Quarterly Results": ["quarterly results", "q1", "q2", "q3", "q4", "earnings", "eps"],
        "Corporate Action": ["dividend", "buyback", "bonus", "stock split"],
        "Order Win": ["order", "contract", "project", "deal won"],
        "Board Update": ["board meeting", "board approves", "fund raise", "allotment"],
        "Legal Issues": ["lawsuit", "investigation", "notice", "penalty", "regulatory"],
        "Management Change": ["ceo", "cfo", "appoints", "resigns", "executive"],
        "Partnership": ["partnership", "collaboration", "strategic alliance"],
    }
    for article in articles:
        text = (article.get("title", "") + " " + article.get("description", "")).lower()
        for event_type, keywords in event_keywords.items():
            if any(keyword in text for keyword in keywords):
                events.add(event_type)
    return sorted(events)


def get_news_with_sentiment(ticker: str, days: int = 7) -> Dict[str, Any]:
    """Return stock news plus sentiment and event summary."""
    articles = get_recent_news(ticker, days=days, limit=20)
    sentiment = analyze_sentiment(articles)
    key_events = detect_key_events(articles)
    return {
        "ticker": ticker,
        "articles": articles,
        "sentiment_analysis": sentiment,
        "key_events": key_events,
        "article_count": len(articles),
        "days_analyzed": days,
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    ticker = "RELIANCE"
    news_data = get_news_with_sentiment(ticker, days=7)
    print(f"Found {news_data['article_count']} articles for {ticker}")
