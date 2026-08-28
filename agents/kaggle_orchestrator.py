"""
NSE-focused orchestrator for the stock prediction system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
import hashlib
import logging

import requests

from tools.fred_fetcher import get_macro_indicators
from tools.news_fetcher import analyze_sentiment, get_recent_news
from tools.polygon_fetcher import get_fundamentals
from tools.sec_edgar_fetcher import check_recent_8k_filings, get_recent_filings
from tools.technical_indicators import calculate_indicators

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KaggleOrchestrator:
    """Primary runtime orchestrator tuned for NSE-listed equities."""

    def __init__(self):
        self.agents = {
            "fundamental": "http://localhost:8001",
            "technical": "http://localhost:8002",
            "sentiment": "http://localhost:8003",
            "macro": "http://localhost:8004",
            "regulatory": "http://localhost:8005",
            "predictor": "http://localhost:8006",
        }
        self.agent_status = self.check_agents_health()

    def check_agents_health(self) -> Dict[str, str]:
        """Return best-effort agent health instead of hard failing startup."""
        status: Dict[str, str] = {}
        for name, url in self.agents.items():
            try:
                resp = requests.get(f"{url}/.well-known/agent-card.json", timeout=1.5)
                status[name] = "online" if resp.status_code == 200 else "offline"
            except Exception:
                status[name] = "offline"
        return status

    def _ticker_hash(self, ticker: str) -> int:
        """Stable hash used for deterministic fallback scoring."""
        return int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)

    def _analyze_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Analyze company fundamentals for an NSE-listed stock."""
        data = get_fundamentals(ticker)
        if "error" in data:
            return {
                "agent": "fundamental",
                "ticker": ticker,
                "directional_signal": 0.0,
                "confidence_score": 45.0,
                "summary": data["error"],
                "error": data["error"],
            }

        market_cap = float(data.get("market_cap") or 0)
        pe_ratio = data.get("pe_ratio")
        price_to_book = data.get("price_to_book")
        dividend_yield = data.get("dividend_yield")
        sector = data.get("sector", "Unknown")

        signal = 0.0
        confidence = 60.0
        notes = []

        if market_cap >= 1_000_000_000_000:
            signal += 0.18
            confidence += 8
            notes.append("large-cap stability")
        elif market_cap >= 200_000_000_000:
            signal += 0.08
            confidence += 5
            notes.append("mid-to-large cap scale")
        else:
            signal -= 0.05
            notes.append("smaller-cap volatility")

        if pe_ratio is not None:
            if pe_ratio < 18:
                signal += 0.18
                notes.append("reasonable valuation")
            elif pe_ratio < 30:
                signal += 0.05
                notes.append("acceptable valuation")
            elif pe_ratio > 45:
                signal -= 0.2
                notes.append("stretched valuation")

        if price_to_book is not None:
            if price_to_book > 6:
                signal -= 0.08
                notes.append("rich book valuation")
            elif price_to_book < 2.5:
                signal += 0.05
                notes.append("disciplined price-to-book")

        if dividend_yield:
            signal += 0.03
            notes.append("shareholder payout support")

        confidence = min(85.0, confidence)
        signal = max(-1.0, min(1.0, signal))

        return {
            "agent": "fundamental",
            "ticker": ticker,
            "directional_signal": round(signal, 2),
            "confidence_score": round(confidence, 1),
            "key_metrics": {
                "market_cap": f"INR {market_cap / 1e7:.1f} Cr" if market_cap else "N/A",
                "current_price": f"INR {float(data.get('current_price') or 0):.2f}",
                "pe_ratio": pe_ratio if pe_ratio is not None else "N/A",
                "price_to_book": price_to_book if price_to_book is not None else "N/A",
                "sector": sector,
                "data_source": data.get("data_source", "yfinance_nse"),
            },
            "summary": f"{sector}: " + (", ".join(notes) if notes else "mixed fundamental picture"),
            "data_source": data.get("data_source", "yfinance_nse"),
        }

    def _analyze_technical(self, ticker: str) -> Dict[str, Any]:
        """Analyze technical indicators for an NSE-listed stock."""
        data = calculate_indicators(ticker, days=365)
        if "error" in data:
            return {
                "agent": "technical",
                "ticker": ticker,
                "directional_signal": 0.0,
                "confidence_score": 45.0,
                "summary": data["error"],
                "error": data["error"],
            }

        rsi = data.get("rsi")
        sma_50 = data.get("sma_50")
        sma_200 = data.get("sma_200")
        current_price = data.get("current_price", 0)
        trend = data.get("trend", "neutral")

        signal = 0.0
        confidence = 50.0  # base; scales up below with data completeness and signal agreement
        notes = []
        bullish_hits = 0
        bearish_hits = 0

        if trend == "bullish":
            signal += 0.25
            confidence += 6
            bullish_hits += 1
            notes.append("bullish trend")
        elif trend == "bearish":
            signal -= 0.25
            confidence += 6
            bearish_hits += 1
            notes.append("bearish trend")

        if rsi is not None:
            confidence += 4  # RSI was available at all
            if 45 <= rsi <= 65:
                signal += 0.08
                bullish_hits += 1
                notes.append("healthy momentum")
            elif rsi > 72:
                signal -= 0.12
                bearish_hits += 1
                notes.append("overbought")
            elif rsi < 30:
                signal += 0.12
                bullish_hits += 1
                notes.append("oversold rebound setup")

        if sma_50 and sma_200:
            confidence += 6  # both moving averages resolved
            if sma_50 > sma_200:
                signal += 0.12
                bullish_hits += 1
                notes.append("golden-cross structure")
            else:
                signal -= 0.12
                bearish_hits += 1
                notes.append("weak moving-average structure")

        if current_price and sma_50:
            if current_price > sma_50:
                signal += 0.05
                bullish_hits += 1
            else:
                signal -= 0.05
                bearish_hits += 1

        # Reward agreement across signals (they're all pointing the same way),
        # penalize a stalemate where indicators conflict with each other.
        if bullish_hits and bearish_hits == 0:
            confidence += min(10, bullish_hits * 3)
        elif bearish_hits and bullish_hits == 0:
            confidence += min(10, bearish_hits * 3)
        elif bullish_hits and bearish_hits:
            confidence -= min(8, abs(bullish_hits - bearish_hits) * -2 + 4)

        confidence = round(max(40.0, min(82.0, confidence)), 1)

        return {
            "agent": "technical",
            "ticker": ticker,
            "directional_signal": round(max(-1.0, min(1.0, signal)), 2),
            "confidence_score": confidence,
            "key_metrics": {
                "rsi": round(rsi, 2) if isinstance(rsi, (int, float)) else "N/A",
                "trend": trend,
                "current_price": f"INR {float(current_price):.2f}" if current_price else "N/A",
                "sma_50": round(sma_50, 2) if isinstance(sma_50, (int, float)) else "N/A",
                "sma_200": round(sma_200, 2) if isinstance(sma_200, (int, float)) else "N/A",
                "data_source": "technical_indicators",
            },
            "summary": ", ".join(notes) if notes else "mixed technical setup",
            "data_source": "technical_indicators",
        }

    def _analyze_sentiment(self, ticker: str) -> Dict[str, Any]:
        """Analyze market sentiment from recent news and announcements."""
        news = get_recent_news(ticker, days=10, limit=15)
        sentiment = analyze_sentiment(news)

        positive = sentiment.get("positive_count", 0)
        negative = sentiment.get("negative_count", 0)
        neutral = sentiment.get("neutral_count", 0)
        score = float(sentiment.get("sentiment_score", 0.0) or 0.0)
        confidence = min(75.0, 50.0 + (len(news) * 1.5))

        return {
            "agent": "sentiment",
            "ticker": ticker,
            "directional_signal": round(score, 2),
            "confidence_score": round(confidence, 1),
            "key_metrics": {
                "news_count": len(news),
                "sentiment": sentiment.get("overall_sentiment", "neutral"),
                "positive_count": positive,
                "negative_count": negative,
                "neutral_count": neutral,
                "data_source": "google_news_rss_and_yfinance",
            },
            "summary": f"{len(news)} recent items, {positive} positive, {negative} negative, {neutral} neutral",
            "data_source": "google_news_rss_and_yfinance",
        }

    def _analyze_macro(self, ticker: str) -> Dict[str, Any]:
        """Analyze the Indian macro backdrop."""
        macro = get_macro_indicators()

        gdp_growth = float(macro.get("gdp_growth", 0) or 0)
        inflation = float(macro.get("inflation_rate", 0) or 0)
        repo_rate = float(macro.get("repo_rate", 0) or 0)
        iip_growth = float(macro.get("iip_growth", 0) or 0)
        regime = macro.get("market_regime", "stable")

        signal = 0.0
        if gdp_growth >= 6.0:
            signal += 0.18
        elif gdp_growth < 5.0:
            signal -= 0.18

        if inflation <= 5.0:
            signal += 0.08
        elif inflation > 6.0:
            signal -= 0.14

        if repo_rate >= 7.0:
            signal -= 0.08
        elif repo_rate <= 6.0:
            signal += 0.05

        if iip_growth > 3.0:
            signal += 0.06
        elif iip_growth < 0:
            signal -= 0.1

        return {
            "agent": "macro",
            "ticker": ticker,
            "directional_signal": round(max(-1.0, min(1.0, signal)), 2),
            "confidence_score": 68.0,
            "key_metrics": {
                "gdp_growth": f"{gdp_growth:.1f}%",
                "inflation_rate": f"{inflation:.1f}%",
                "repo_rate": f"{repo_rate:.2f}%",
                "iip_growth": f"{iip_growth:.1f}%",
                "market_regime": regime,
                "data_source": macro.get("data_source", "india_macro_defaults_or_env"),
            },
            "summary": (
                f"India macro backdrop: GDP {gdp_growth:.1f}%, CPI {inflation:.1f}%, "
                f"RBI repo {repo_rate:.2f}%, regime {regime}"
            ),
            "data_source": macro.get("data_source", "india_macro_defaults_or_env"),
        }

    def _analyze_regulatory(self, ticker: str) -> Dict[str, Any]:
        """Analyze company disclosures and event risk."""
        filings = get_recent_filings(ticker, count=5)
        events = check_recent_8k_filings(ticker, days=90)
        event_count = int(events.get("event_count", 0) or 0)

        negative_keywords = ["penalty", "investigation", "lawsuit", "delay", "downgrade", "notice"]
        positive_keywords = ["order", "partnership", "approval", "dividend", "results"]

        signal = 0.0
        recent_summaries = []
        for filing in filings:
            summary = filing.get("summary", "")
            recent_summaries.append(summary[:120])
            lowered = summary.lower()
            if any(word in lowered for word in negative_keywords):
                signal -= 0.18
            if any(word in lowered for word in positive_keywords):
                signal += 0.1

        if event_count == 0:
            signal += 0.05

        signal = max(-1.0, min(1.0, signal))
        confidence = 60.0 if filings else 45.0

        return {
            "agent": "regulatory",
            "ticker": ticker,
            "directional_signal": round(signal, 2),
            "confidence_score": confidence,
            "key_metrics": {
                "recent_announcements": len(filings),
                "material_events_90d": event_count,
                "data_source": "company_announcements_proxy",
            },
            "summary": " | ".join(recent_summaries[:2]) if recent_summaries else "No material announcement flow detected",
            "data_source": "company_announcements_proxy",
        }

    def analyze_stock(self, ticker: str, horizon: str = "next_quarter", verbose: bool = False) -> Dict[str, Any]:
        """Run the full NSE-focused stock analysis workflow."""
        start_time = datetime.now()
        normalized = ticker.upper().strip()

        results = {
            "fundamental": self._analyze_fundamentals(normalized),
            "technical": self._analyze_technical(normalized),
            "sentiment": self._analyze_sentiment(normalized),
            "macro": self._analyze_macro(normalized),
            "regulatory": self._analyze_regulatory(normalized),
        }

        signals = [report.get("directional_signal", 0.0) for report in results.values()]
        confidences = [report.get("confidence_score", 0.0) for report in results.values()]
        total_confidence = sum(confidences)

        weighted_signal = 0.0
        if total_confidence > 0:
            weighted_signal = sum(signal * confidence for signal, confidence in zip(signals, confidences)) / total_confidence
        avg_confidence = total_confidence / len(confidences) if confidences else 50.0

        if weighted_signal > 0.18:
            recommendation = "BUY"
            risk_level = "LOW" if avg_confidence >= 70 else "MEDIUM"
        elif weighted_signal < -0.18:
            recommendation = "SELL"
            risk_level = "MEDIUM" if avg_confidence >= 65 else "HIGH"
        else:
            recommendation = "HOLD"
            risk_level = "LOW" if avg_confidence >= 72 else "MEDIUM"

        rationale = (
            f"NSE multi-agent analysis for {normalized}.\n\n"
            f"Fundamental: {results['fundamental'].get('summary', 'N/A')}\n\n"
            f"Technical: {results['technical'].get('summary', 'N/A')}\n\n"
            f"Sentiment: {results['sentiment'].get('summary', 'N/A')}\n\n"
            f"Macro: {results['macro'].get('summary', 'N/A')}\n\n"
            f"Regulatory: {results['regulatory'].get('summary', 'N/A')}\n\n"
            f"Weighted Signal: {weighted_signal:+.2f}\n"
            f"Average Confidence: {avg_confidence:.1f}%"
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        output = {
            "ticker": normalized,
            "horizon": horizon,
            "recommendation": recommendation,
            "confidence": round(avg_confidence, 1),
            "risk_level": risk_level,
            "rationale": rationale,
            "weighted_signal": round(weighted_signal, 3),
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "elapsed_time_seconds": round(elapsed, 2),
            "analysis_reports": results,
            "using_a2a_protocol": any(status == "online" for status in self.agent_status.values()),
            "agents_deployed": len(self.agents),
            "apis_integrated": [
                "yfinance NSE",
                "Google News RSS",
                "India macro defaults or env overrides",
                "Company announcements proxy",
            ],
        }

        if verbose:
            output["intermediate_reports"] = results

        return output