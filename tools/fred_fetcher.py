"""
India macro data fetcher.

The module name stays `fred_fetcher` for compatibility with the rest of the
project, but the implementation is now oriented around Indian macro signals
that matter for NSE-listed equities.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


def _env_float(name: str, default: float) -> float:
    """Safely parse float overrides from the environment."""
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _series_points(value: float, months: int = 6, step: float = 0.1) -> List[Dict[str, str]]:
    """Generate lightweight chronological series points for display/debugging."""
    today = datetime.now()
    points: List[Dict[str, str]] = []
    for offset in range(months - 1, -1, -1):
        month = max(1, today.month - offset)
        year = today.year if today.month - offset > 0 else today.year - 1
        adjusted = round(value - (offset * step), 2)
        points.append({"date": f"{year}-{month:02d}-01", "value": str(adjusted)})
    return points


def _determine_market_regime(indicators: Dict[str, Any]) -> str:
    """Classify the Indian macro backdrop."""
    gdp = float(indicators.get("gdp_growth", 0) or 0)
    inflation = float(indicators.get("inflation_rate", 0) or 0)
    repo_rate = float(indicators.get("repo_rate", 0) or 0)
    iip_growth = float(indicators.get("iip_growth", 0) or 0)

    if gdp >= 6.0 and inflation <= 5.0 and iip_growth >= 3.0:
        return "expansion"
    if gdp < 5.0 or inflation > 6.5 or iip_growth < 0:
        return "caution"
    if repo_rate >= 7.0 and inflation > 6.0:
        return "tightening"
    return "stable"


def get_macro_indicators() -> Dict[str, Any]:
    """
    Get India-focused macro indicators for NSE market analysis.

    Values can be overridden by environment variables for easier deployment:
    - INDIA_GDP_GROWTH
    - INDIA_CPI_INFLATION
    - RBI_REPO_RATE
    - INDIA_IIP_GROWTH
    - INR_USD
    - INDIA_UNEMPLOYMENT_RATE
    - INDIA_GSEC_10Y
    """
    indicators = {
        "gdp_growth": _env_float("INDIA_GDP_GROWTH", 6.7),
        "inflation_rate": _env_float("INDIA_CPI_INFLATION", 4.8),
        "repo_rate": _env_float("RBI_REPO_RATE", 6.5),
        "unemployment_rate": _env_float("INDIA_UNEMPLOYMENT_RATE", 7.8),
        "iip_growth": _env_float("INDIA_IIP_GROWTH", 4.2),
        "inr_usd": _env_float("INR_USD", 83.4),
        "ten_year_gsec": _env_float("INDIA_GSEC_10Y", 7.1),
        "policy_stance": os.getenv("RBI_POLICY_STANCE", "neutral"),
        "data_source": "india_macro_defaults_or_env",
    }
    indicators["market_regime"] = _determine_market_regime(indicators)
    indicators["timestamp"] = datetime.now().isoformat()
    return indicators


def get_gdp_data() -> Dict[str, Any]:
    """Return India GDP growth context."""
    latest = _env_float("INDIA_GDP_GROWTH", 6.7)
    data = _series_points(latest, months=4, step=0.15)
    return {
        "series_id": "INDIA_GDP_GROWTH",
        "latest_value": latest,
        "latest_date": data[-1]["date"],
        "recent_values": data,
        "series_name": "India Real GDP Growth Rate",
        "units": "Percent",
        "timestamp": datetime.now().isoformat(),
    }


def get_inflation_data() -> Dict[str, Any]:
    """Return India CPI inflation context."""
    latest = _env_float("INDIA_CPI_INFLATION", 4.8)
    data = _series_points(latest, months=12, step=0.05)
    return {
        "series_id": "INDIA_CPI_INFLATION",
        "latest_cpi": latest,
        "latest_date": data[-1]["date"],
        "inflation_rate_yoy": round(latest, 2),
        "series_name": "India CPI Inflation",
        "recent_values": data[-6:],
        "timestamp": datetime.now().isoformat(),
    }


def get_fed_rate() -> Dict[str, Any]:
    """
    Compatibility wrapper for the old Fed endpoint.

    The project now uses RBI repo rate but preserves the function name so the
    existing A2A macro server does not need interface changes.
    """
    current_rate = _env_float("RBI_REPO_RATE", 6.5)
    return {
        "series_id": "RBI_REPO_RATE",
        "current_rate": current_rate,
        "latest_date": datetime.now().strftime("%Y-%m-%d"),
        "series_name": "RBI Repo Rate",
        "units": "Percent",
        "recent_trend": os.getenv("RBI_RATE_TREND", "stable"),
        "timestamp": datetime.now().isoformat(),
    }


def get_treasury_yield(maturity: str = "10") -> Dict[str, Any]:
    """
    Compatibility wrapper for the old treasury function.

    Returns Indian government security yields.
    """
    series_map = {
        "3": ("INDIA_GSEC_3M", _env_float("INDIA_GSEC_3M", 6.7)),
        "2": ("INDIA_GSEC_2Y", _env_float("INDIA_GSEC_2Y", 6.9)),
        "10": ("INDIA_GSEC_10Y", _env_float("INDIA_GSEC_10Y", 7.1)),
        "30": ("INDIA_GSEC_30Y", _env_float("INDIA_GSEC_30Y", 7.3)),
    }
    series_id, current_yield = series_map.get(maturity, series_map["10"])
    return {
        "series_id": series_id,
        "maturity": f"{maturity}-Year",
        "current_yield": current_yield,
        "latest_date": datetime.now().strftime("%Y-%m-%d"),
        "series_name": f"India {maturity}-Year Government Security Yield",
        "units": "Percent",
        "timestamp": datetime.now().isoformat(),
    }


def get_unemployment_rate() -> Dict[str, Any]:
    """Return India unemployment context."""
    current_rate = _env_float("INDIA_UNEMPLOYMENT_RATE", 7.8)
    data = _series_points(current_rate, months=12, step=0.03)
    return {
        "series_id": "INDIA_UNEMPLOYMENT_RATE",
        "current_rate": current_rate,
        "latest_date": data[-1]["date"],
        "series_name": "India Unemployment Rate",
        "units": "Percent",
        "recent_trend": "falling" if current_rate < 8.0 else "stable",
        "timestamp": datetime.now().isoformat(),
    }


def _get_latest_value(series_id: str) -> Optional[float]:
    """Compatibility helper used by older code paths."""
    lookup = {
        "INDIA_GDP_GROWTH": _env_float("INDIA_GDP_GROWTH", 6.7),
        "INDIA_CPI_INFLATION": _env_float("INDIA_CPI_INFLATION", 4.8),
        "RBI_REPO_RATE": _env_float("RBI_REPO_RATE", 6.5),
        "INDIA_GSEC_10Y": _env_float("INDIA_GSEC_10Y", 7.1),
        "INDIA_UNEMPLOYMENT_RATE": _env_float("INDIA_UNEMPLOYMENT_RATE", 7.8),
    }
    return lookup.get(series_id)


def _get_series_observations(series_id: str, limit: int = 100) -> List[Dict[str, str]]:
    """Compatibility helper for legacy call sites."""
    value = _get_latest_value(series_id) or 0.0
    return _series_points(value, months=min(limit, 12))


def _calculate_inflation_rate(series_id: str) -> Optional[float]:
    """Compatibility helper for legacy call sites."""
    if series_id == "INDIA_CPI_INFLATION":
        return _env_float("INDIA_CPI_INFLATION", 4.8)
    return None


def _calculate_trend(values: List[float]) -> str:
    """Determine a simple trend direction."""
    if len(values) < 2:
        return "stable"
    if values[-1] > values[0]:
        return "rising"
    if values[-1] < values[0]:
        return "falling"
    return "stable"


def _get_mock_data(series_id: str) -> List[Dict[str, str]]:
    """Compatibility shim retained for old callers."""
    value = _get_latest_value(series_id) or 0.0
    return [{"date": datetime.now().strftime("%Y-%m-%d"), "value": str(value)}]


if __name__ == "__main__":
    print("Testing India macro fetcher...\n")

    print("1. Macro Indicators:")
    macro = get_macro_indicators()
    for key, value in macro.items():
        if key not in ["timestamp", "error"]:
            print(f"  {key}: {value}")

    print("\n2. GDP Data:")
    gdp = get_gdp_data()
    print(f"  Latest GDP Growth: {gdp['latest_value']}% ({gdp['latest_date']})")

    print("\n3. Inflation Data:")
    inflation = get_inflation_data()
    print(f"  CPI Inflation: {inflation['inflation_rate_yoy']}%")

    print("\n4. RBI Repo Rate:")
    repo_rate = get_fed_rate()
    print(f"  Current Rate: {repo_rate['current_rate']}%")

    print("\n5. Government Security Yields:")
    for maturity in ["2", "10", "30"]:
        gsec = get_treasury_yield(maturity)
        print(f"  {maturity}-Year: {gsec['current_yield']}%")
