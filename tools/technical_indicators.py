"""
Technical indicators calculator for NSE/BSE stocks.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
import warnings

import numpy as np
import pandas as pd

try:
    import talib

    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    warnings.warn("TA-Lib not available. Using simplified calculations.")

from tools.polygon_fetcher import get_price_history, normalize_ticker


def calculate_indicators(ticker: str, days: int = 365, timespan: str = "day") -> Dict[str, Any]:
    """Calculate standard technical indicators using NSE-compatible price history."""
    symbol = normalize_ticker(ticker)
    try:
        price_data = get_price_history(symbol, days=days, timespan=timespan)
        if "error" in price_data or "data" not in price_data:
            return {"error": "Could not fetch price data", "ticker": symbol}

        df = pd.DataFrame(price_data["data"])
        if len(df) < 50:
            return {"error": f"Insufficient data: only {len(df)} periods available", "ticker": symbol}

        close_prices = np.array(df["close"].values, dtype=float)
        high_prices = np.array(df["high"].values, dtype=float)
        low_prices = np.array(df["low"].values, dtype=float)
        volumes = np.array(df["volume"].values, dtype=float)

        indicators = {"ticker": symbol, "timespan": timespan, "exchange": "NSE"}
        if TALIB_AVAILABLE:
            indicators.update(_calculate_with_talib(close_prices, high_prices, low_prices, volumes))
        else:
            indicators.update(_calculate_simplified(close_prices))

        indicators["trend"] = _determine_trend(indicators)
        indicators["current_price"] = float(close_prices[-1])
        indicators["price_change_pct"] = float(((close_prices[-1] - close_prices[0]) / close_prices[0]) * 100)
        indicators["timestamp"] = datetime.now().isoformat()
        return indicators
    except Exception as e:
        return {"error": f"Error calculating indicators: {str(e)}", "ticker": symbol}


def _calculate_with_talib(close: np.ndarray, high: np.ndarray, low: np.ndarray, volume: np.ndarray) -> Dict[str, Any]:
    """Calculate technical indicators with TA-Lib."""
    indicators: Dict[str, Any] = {}
    try:
        rsi = talib.RSI(close, timeperiod=14)
        macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        sma_50 = talib.SMA(close, timeperiod=50)
        sma_200 = talib.SMA(close, timeperiod=200)
        ema_12 = talib.EMA(close, timeperiod=12)
        ema_26 = talib.EMA(close, timeperiod=26)
        bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
        atr = talib.ATR(high, low, close, timeperiod=14)
        obv = talib.OBV(close, volume)

        indicators["rsi"] = float(rsi[-1]) if not np.isnan(rsi[-1]) else None
        indicators["macd"] = {
            "macd_line": float(macd[-1]) if not np.isnan(macd[-1]) else None,
            "signal_line": float(macd_signal[-1]) if not np.isnan(macd_signal[-1]) else None,
            "histogram": float(macd_hist[-1]) if not np.isnan(macd_hist[-1]) else None,
        }
        indicators["sma_50"] = float(sma_50[-1]) if not np.isnan(sma_50[-1]) else None
        indicators["sma_200"] = float(sma_200[-1]) if not np.isnan(sma_200[-1]) else None
        indicators["ema_12"] = float(ema_12[-1]) if not np.isnan(ema_12[-1]) else None
        indicators["ema_26"] = float(ema_26[-1]) if not np.isnan(ema_26[-1]) else None
        indicators["bollinger_bands"] = {
            "upper": float(bb_upper[-1]) if not np.isnan(bb_upper[-1]) else None,
            "middle": float(bb_middle[-1]) if not np.isnan(bb_middle[-1]) else None,
            "lower": float(bb_lower[-1]) if not np.isnan(bb_lower[-1]) else None,
        }
        indicators["atr"] = float(atr[-1]) if not np.isnan(atr[-1]) else None
        indicators["obv"] = float(obv[-1]) if not np.isnan(obv[-1]) else None
    except Exception:
        pass
    return indicators


def _calculate_simplified(close: np.ndarray) -> Dict[str, Any]:
    """Fallback indicator calculations when TA-Lib is unavailable."""
    indicators: Dict[str, Any] = {}
    try:
        indicators["rsi"] = float(_simple_rsi(close, period=14))
        if len(close) >= 50:
            indicators["sma_50"] = float(np.mean(close[-50:]))
        if len(close) >= 200:
            indicators["sma_200"] = float(np.mean(close[-200:]))
        indicators["ema_12"] = float(_simple_ema(close, 12))
        indicators["ema_26"] = float(_simple_ema(close, 26))
        macd_line = indicators["ema_12"] - indicators["ema_26"]
        indicators["macd"] = {"macd_line": float(macd_line), "signal_line": None, "histogram": None}
        sma_20 = np.mean(close[-20:])
        std_20 = np.std(close[-20:])
        indicators["bollinger_bands"] = {
            "upper": float(sma_20 + 2 * std_20),
            "middle": float(sma_20),
            "lower": float(sma_20 - 2 * std_20),
        }
    except Exception:
        pass
    return indicators


def _simple_rsi(prices: np.ndarray, period: int = 14) -> float:
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _simple_ema(prices: np.ndarray, period: int) -> float:
    multiplier = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    return ema


def _determine_trend(indicators: Dict[str, Any]) -> str:
    bullish = 0
    bearish = 0
    rsi = indicators.get("rsi")
    if rsi is not None:
        if rsi > 50:
            bullish += 1
        elif rsi < 50:
            bearish += 1
    macd = indicators.get("macd", {})
    if macd.get("macd_line") is not None and macd.get("signal_line") is not None:
        if macd["macd_line"] > macd["signal_line"]:
            bullish += 1
        else:
            bearish += 1
    sma_50 = indicators.get("sma_50")
    sma_200 = indicators.get("sma_200")
    current_price = indicators.get("current_price")
    if sma_50 and sma_200:
        if sma_50 > sma_200:
            bullish += 2
        else:
            bearish += 2
    if current_price and sma_50:
        if current_price > sma_50:
            bullish += 1
        else:
            bearish += 1
    if bullish > bearish + 1:
        return "bullish"
    if bearish > bullish + 1:
        return "bearish"
    return "neutral"


def get_support_resistance(ticker: str, days: int = 180) -> Dict[str, Any]:
    """Identify support and resistance using NSE-compatible history."""
    symbol = normalize_ticker(ticker)
    try:
        price_data = get_price_history(symbol, days=days)
        if "error" in price_data or "data" not in price_data:
            return {"error": "Could not fetch price data", "ticker": symbol}
        df = pd.DataFrame(price_data["data"])
        highs = df["high"].values
        lows = df["low"].values
        resistance = float(np.max(highs[-90:]))
        support = float(np.min(lows[-90:]))
        current_price = float(df["close"].iloc[-1])
        return {
            "ticker": symbol,
            "resistance": resistance,
            "support": support,
            "current_price": current_price,
            "distance_to_resistance_pct": ((resistance - current_price) / current_price) * 100,
            "distance_to_support_pct": ((current_price - support) / current_price) * 100,
        }
    except Exception as e:
        return {"error": f"Error calculating support/resistance: {str(e)}", "ticker": symbol}


if __name__ == "__main__":
    ticker = "RELIANCE"
    print(calculate_indicators(ticker, days=365))
