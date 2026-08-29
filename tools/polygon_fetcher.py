"""
NSE-oriented market data fetcher.

This module preserves the old function names so the rest of the codebase can
keep importing `polygon_fetcher`, but the implementation now targets Indian
equities through Yahoo Finance style symbols such as `RELIANCE.NS`.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

import yfinance as yf


def normalize_ticker(ticker: str) -> str:
    """Normalize a user ticker into a Yahoo Finance NSE/BSE symbol."""
    symbol = ticker.strip().upper()
    if symbol.endswith((".NS", ".BO")):
        return symbol
    return f"{symbol}.NS"


def _base_symbol(ticker: str) -> str:
    """Return the symbol without exchange suffix."""
    return normalize_ticker(ticker).split(".")[0]


def _get_history_by_period(symbol: str, period: str, interval: str) -> Any:
    """Fetch history using a named yfinance period (e.g. '5d', '1y', 'max')."""
    ticker = yf.Ticker(symbol)
    return ticker.history(period=period, interval=interval, auto_adjust=False)


def _get_history(symbol: str, days: int, interval: str) -> Any:
    """
    Fetch history spanning an exact number of calendar days.

    yfinance's `period` parameter only accepts a fixed set of named values
    (1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max) — an arbitrary string like
    "365d" is silently forwarded to Yahoo's API, which doesn't recognize it
    and falls back to a much shorter default range. Passing explicit
    start/end dates avoids that entirely and gives back exactly the window
    we asked for.
    """
    ticker = yf.Ticker(symbol)
    end = datetime.now()
    # Pad the request so trading-day gaps (weekends/holidays) don't leave us
    # short of the calendar-day window we actually need (e.g. 200 SMA
    # periods needs ~200 *trading* days, which spans more calendar days).
    start = end - timedelta(days=max(days, 5) * 2 + 30)
    return ticker.history(start=start, end=end, interval=interval, auto_adjust=False)


def _extract_info(symbol: str) -> Dict[str, Any]:
    """Fetch company metadata from yfinance, swallowing brittle field errors."""
    ticker = yf.Ticker(symbol)
    try:
        return ticker.info or {}
    except Exception:
        return {}


def get_fundamentals(ticker: str) -> Dict[str, Any]:
    """
    Get basic company and valuation data for an NSE/BSE stock.

    The shape mirrors the older Polygon-based response closely enough for the
    existing agents and orchestrator.
    """
    symbol = normalize_ticker(ticker)

    try:
        info = _extract_info(symbol)
        history = _get_history_by_period(symbol, period="5d", interval="1d")

        current_price = 0.0
        if not history.empty:
            current_price = float(history["Close"].dropna().iloc[-1])

        market_cap = info.get("marketCap") or 0
        shares_outstanding = info.get("sharesOutstanding") or 0

        return {
            "ticker": _base_symbol(symbol),
            "exchange_ticker": symbol,
            "name": info.get("longName") or info.get("shortName") or _base_symbol(symbol),
            "market_cap": market_cap,
            "shares_outstanding": shares_outstanding,
            "current_price": current_price,
            "currency": info.get("currency", "INR"),
            "sector": info.get("sector") or info.get("industry") or "Unknown",
            "industry": info.get("industry", "Unknown"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "description": info.get("longBusinessSummary", ""),
            "homepage_url": info.get("website", ""),
            "total_employees": info.get("fullTimeEmployees"),
            "country": info.get("country", "India"),
            "data_source": "yfinance_nse",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "error": f"Failed to fetch NSE fundamentals: {str(e)}",
            "ticker": _base_symbol(symbol),
            "exchange_ticker": symbol,
            "timestamp": datetime.now().isoformat(),
        }


def get_price_history(
    ticker: str,
    days: int = 365,
    timespan: str = "day",
) -> Dict[str, Any]:
    """Get historical OHLCV data for an NSE/BSE stock."""
    symbol = normalize_ticker(ticker)
    interval_map = {
        "day": ("1d", max(days, 5)),
        "week": ("1wk", max(days, 30)),
        "month": ("1mo", max(days, 90)),
    }
    interval, effective_days = interval_map.get(timespan, ("1d", max(days, 5)))

    try:
        if interval == "1mo":
            # "max" is a genuinely valid named yfinance period.
            history = _get_history_by_period(symbol, period="max", interval=interval)
        else:
            # Exact calendar-day window via start/end — avoids passing an
            # invalid "{N}d" string as a named period (see _get_history).
            history = _get_history(symbol, days=effective_days, interval=interval)

        # Drop any incomplete bar (e.g. today's in-progress session, or a
        # holiday row Yahoo returns with NaN OHLC) — a single NaN close here
        # poisons every downstream calculation (RSI, SMA, current_price).
        if not history.empty:
            history = history.dropna(subset=["Open", "High", "Low", "Close"])

        if history.empty:
            return {
                "error": f"No price history available for {symbol}",
                "ticker": _base_symbol(symbol),
                "exchange_ticker": symbol,
            }

        formatted_data: List[Dict[str, Any]] = []
        for idx, row in history.tail(days).iterrows():
            formatted_data.append(
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
                    "vwap": None,
                    "transactions": None,
                }
            )

        return {
            "ticker": _base_symbol(symbol),
            "exchange_ticker": symbol,
            "timespan": timespan,
            "data": formatted_data,
            "count": len(formatted_data),
            "query_count": len(formatted_data),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "error": f"Failed to fetch NSE price history: {str(e)}",
            "ticker": _base_symbol(symbol),
            "exchange_ticker": symbol,
        }


def get_latest_price(ticker: str) -> Dict[str, Any]:
    """Get the latest available close for an NSE/BSE stock."""
    symbol = normalize_ticker(ticker)

    try:
        history = _get_history_by_period(symbol, period="5d", interval="1d")
        if not history.empty:
            history = history.dropna(subset=["Open", "High", "Low", "Close"])
        if history.empty:
            return {"error": f"No price data available for {symbol}", "ticker": _base_symbol(symbol)}

        row = history.iloc[-1]
        idx = history.index[-1]
        return {
            "ticker": _base_symbol(symbol),
            "exchange_ticker": symbol,
            "date": idx.strftime("%Y-%m-%d"),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
            "vwap": None,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "error": f"Failed to get latest NSE price: {str(e)}",
            "ticker": _base_symbol(symbol),
            "exchange_ticker": symbol,
        }


def get_stock_news(ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get stock-related news.

    yfinance news availability varies by symbol and region, so callers should
    still be prepared for an empty list and fall back to Google News RSS.
    """
    symbol = normalize_ticker(ticker)

    try:
        items = yf.Ticker(symbol).news or []
        articles: List[Dict[str, Any]] = []
        for item in items[:limit]:
            published_ts = item.get("providerPublishTime")
            published_date = ""
            if published_ts:
                published_date = datetime.fromtimestamp(published_ts).isoformat()

            articles.append(
                {
                    "title": item.get("title", ""),
                    "author": item.get("publisher", "Unknown"),
                    "published_date": published_date,
                    "article_url": item.get("link", ""),
                    "description": item.get("summary", ""),
                    "source": item.get("publisher", "Yahoo Finance"),
                    "tickers": [_base_symbol(symbol)],
                    "keywords": [],
                }
            )
        return articles
    except Exception:
        return []


def get_company_financials(ticker: str, filing_type: str = "annual") -> Dict[str, Any]:
    """Return lightweight financial summary data for an NSE/BSE stock."""
    symbol = normalize_ticker(ticker)
    info = get_fundamentals(symbol)
    if "error" in info:
        return info

    return {
        "ticker": info["ticker"],
        "exchange_ticker": symbol,
        "filing_type": filing_type,
        "financials": {
            "market_cap": info.get("market_cap"),
            "trailing_pe": info.get("pe_ratio"),
            "forward_pe": info.get("forward_pe"),
            "price_to_book": info.get("price_to_book"),
            "eps": info.get("eps"),
            "dividend_yield": info.get("dividend_yield"),
        },
        "source": "yfinance_nse",
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    ticker = "RELIANCE"

    print("Testing NSE market data fetcher...")
    print(f"\n1. Fundamentals for {ticker}:")
    print(get_fundamentals(ticker))

    print(f"\n2. Latest price for {ticker}:")
    print(get_latest_price(ticker))

    print(f"\n3. Recent news for {ticker}:")
    news = get_stock_news(ticker, limit=3)
    for article in news[:2]:
        print(f"  - {article['title']}")

    print(f"\n4. Price history (last 30 days):")
    history = get_price_history(ticker, days=30)
    if "data" in history:
        print(f"  Retrieved {len(history['data'])} data points")