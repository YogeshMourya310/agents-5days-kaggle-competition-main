"""
NSE-oriented corporate disclosures compatibility layer.

The file name remains `sec_edgar_fetcher` so existing imports keep working, but
the implementation now models Indian company announcements and corporate event
signals instead of SEC filings.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from tools import news_fetcher, polygon_fetcher


def _announcement_type_from_summary(summary: str) -> str:
    """Map text into a simple NSE-style announcement category."""
    text = summary.lower()
    if any(word in text for word in ["results", "quarter", "earnings", "revenue"]):
        return "Financial Results"
    if any(word in text for word in ["dividend", "buyback", "bonus", "split"]):
        return "Corporate Action"
    if any(word in text for word in ["board", "meeting", "approval"]):
        return "Board Update"
    if any(word in text for word in ["order", "contract", "partnership", "launch"]):
        return "Business Update"
    if any(word in text for word in ["investigation", "penalty", "notice", "litigation"]):
        return "Regulatory / Legal"
    return "General Announcement"


def get_recent_filings(ticker: str, filing_type: str = "ANNOUNCEMENT", count: int = 3) -> List[Dict[str, Any]]:
    """
    Get recent company announcements for an NSE/BSE stock.

    `filing_type` is retained for compatibility but is treated as a category hint.
    """
    exchange_ticker = polygon_fetcher.normalize_ticker(ticker)
    articles = news_fetcher.get_recent_news(ticker, days=60, limit=max(count * 3, 6))
    filings: List[Dict[str, Any]] = []

    for article in articles:
        summary = article.get("description") or article.get("title", "")
        announcement_type = _announcement_type_from_summary(summary)
        if filing_type not in {"ANNOUNCEMENT", "10-K", "10-Q", "8-K"} and filing_type != announcement_type:
            continue

        filings.append(
            {
                "filing_date": (article.get("published_date") or "")[:10] or "Unknown",
                "filing_type": announcement_type,
                "document_url": article.get("url", ""),
                "summary": summary.strip(),
                "ticker": polygon_fetcher._base_symbol(exchange_ticker),
                "exchange_ticker": exchange_ticker,
                "source": article.get("source", "News"),
            }
        )

        if len(filings) >= count:
            break

    if filings:
        return filings

    return [
        {
            "filing_date": datetime.now().strftime("%Y-%m-%d"),
            "filing_type": "General Announcement",
            "document_url": "",
            "summary": f"No recent public corporate announcements were detected for {polygon_fetcher._base_symbol(exchange_ticker)}.",
            "ticker": polygon_fetcher._base_symbol(exchange_ticker),
            "exchange_ticker": exchange_ticker,
            "source": "system_fallback",
        }
    ]


def get_risk_factors(ticker: str) -> Dict[str, Any]:
    """
    Build a lightweight India-market risk summary from company metadata and news.
    """
    fundamentals = polygon_fetcher.get_fundamentals(ticker)
    filings = get_recent_filings(ticker, count=5)

    if "error" in fundamentals:
        return {
            "error": "Could not build company risk summary",
            "ticker": polygon_fetcher._base_symbol(ticker),
        }

    sector = fundamentals.get("sector", "Unknown")
    pe_ratio = fundamentals.get("pe_ratio")
    price_to_book = fundamentals.get("price_to_book")
    market_cap = fundamentals.get("market_cap", 0)

    risk_points = []
    if pe_ratio and pe_ratio > 35:
        risk_points.append("Valuation appears elevated relative to many mature NSE large-caps.")
    if price_to_book and price_to_book > 5:
        risk_points.append("Price-to-book is rich, leaving less room for execution misses.")
    if market_cap and market_cap < 50_000_000_000:
        risk_points.append("Smaller market cap can increase liquidity and volatility risk in Indian markets.")
    if sector != "Unknown":
        risk_points.append(f"Sector-specific policy and competitive shifts remain important for {sector}.")

    for filing in filings:
        summary = filing.get("summary", "").lower()
        if any(word in summary for word in ["penalty", "investigation", "delay", "lawsuit", "downgrade"]):
            risk_points.append(f"Recent announcement risk noted: {filing.get('summary', '')[:180]}")

    if not risk_points:
        risk_points.append("No major public red flags were detected from the recent announcement set.")

    return {
        "ticker": fundamentals.get("ticker", polygon_fetcher._base_symbol(ticker)),
        "exchange_ticker": fundamentals.get("exchange_ticker", polygon_fetcher.normalize_ticker(ticker)),
        "filing_date": filings[0].get("filing_date") if filings else None,
        "filing_type": "Corporate Announcements",
        "risk_factors": " ".join(risk_points),
        "document_url": filings[0].get("document_url", "") if filings else "",
        "has_risks": any("risk" in point.lower() or "penalty" in point.lower() for point in risk_points),
        "timestamp": datetime.now().isoformat(),
    }


def get_mda_section(ticker: str) -> Dict[str, Any]:
    """Return a management-style summary synthesized from fundamentals and announcements."""
    fundamentals = polygon_fetcher.get_fundamentals(ticker)
    filings = get_recent_filings(ticker, count=3)

    if "error" in fundamentals:
        return {"error": "Could not summarize company commentary", "ticker": ticker}

    current_price = fundamentals.get("current_price", 0)
    sector = fundamentals.get("sector", "Unknown")
    summaries = [item.get("summary", "") for item in filings if item.get("summary")]
    combined = " ".join(summaries[:3]) or "Recent public updates were limited."

    mda = (
        f"{fundamentals.get('name', ticker)} trades in the {sector} space with a recent market price of "
        f"INR {current_price:.2f}. Recent public updates suggest: {combined}"
    )

    return {
        "ticker": fundamentals.get("ticker", ticker),
        "filing_date": filings[0].get("filing_date") if filings else None,
        "mda": mda,
        "document_url": filings[0].get("document_url", "") if filings else "",
        "timestamp": datetime.now().isoformat(),
    }


def check_recent_8k_filings(ticker: str, days: int = 90) -> Dict[str, Any]:
    """
    Compatibility wrapper that surfaces material company announcements.

    The response shape mirrors the old 8-K helper closely enough for callers.
    """
    filings = get_recent_filings(ticker, filing_type="ANNOUNCEMENT", count=10)
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_filings: List[Dict[str, Any]] = []

    for filing in filings:
        filing_date = filing.get("filing_date", "")
        try:
            parsed_date = datetime.fromisoformat(filing_date)
        except ValueError:
            recent_filings.append({**filing, "event_type": _announcement_type_from_summary(filing.get("summary", ""))})
            continue

        if parsed_date >= cutoff_date:
            recent_filings.append(
                {
                    **filing,
                    "event_type": _announcement_type_from_summary(filing.get("summary", "")),
                }
            )

    return {
        "ticker": polygon_fetcher._base_symbol(ticker),
        "recent_8k_count": len(recent_filings),
        "event_count": len(recent_filings),
        "filings": recent_filings,
        "days_lookback": days,
        "timestamp": datetime.now().isoformat(),
    }


def _get_cik_for_ticker(ticker: str) -> Optional[str]:
    """Compatibility shim retained for older imports; returns the normalized symbol."""
    return polygon_fetcher.normalize_ticker(ticker)


def _extract_section(text: str, section_name: str, max_chars: int = 10000) -> str:
    """Compatibility shim used only by legacy callers."""
    trimmed = text.strip()
    if len(trimmed) > max_chars:
        return trimmed[:max_chars] + "..."
    return trimmed


def _classify_8k_event(summary: str) -> str:
    """Compatibility shim for legacy callers."""
    return _announcement_type_from_summary(summary)


if __name__ == "__main__":
    ticker = "RELIANCE"

    print(f"Testing NSE disclosures fetcher for {ticker}...\n")

    print("1. Recent announcements:")
    filings = get_recent_filings(ticker, count=2)
    for filing in filings:
        print(f"  - {filing['filing_date']}: {filing['filing_type']}")

    print("\n2. Recent material events:")
    events = check_recent_8k_filings(ticker, days=90)
    print(f"  Found {events['event_count']} recent material events")

    print("\n3. Risk factors:")
    risks = get_risk_factors(ticker)
    print(f"  {risks.get('risk_factors', '')[:200]}...")
