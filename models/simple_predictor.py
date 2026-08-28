"""
Simple prediction model for NSE-focused analysis reports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Tuple
import re

import numpy as np


class StockPredictor:
    """Rule-based predictor tuned for Indian-equity analysis signals."""

    def predict_from_reports(
        self,
        fundamental_report: Dict[str, Any],
        technical_report: Dict[str, Any],
        sentiment_report: Dict[str, Any],
        macro_report: Dict[str, Any],
        regulatory_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        signals = {
            "fundamental": (
                fundamental_report.get("directional_signal", 0.0),
                fundamental_report.get("confidence_score", 50.0),
            ),
            "technical": (
                technical_report.get("directional_signal", 0.0),
                technical_report.get("confidence_score", 50.0),
            ),
            "sentiment": (
                sentiment_report.get("directional_signal", 0.0),
                sentiment_report.get("confidence_score", 50.0),
            ),
            "macro": (
                macro_report.get("directional_signal", 0.0),
                macro_report.get("confidence_score", 50.0),
            ),
            "regulatory": (
                regulatory_report.get("directional_signal", 0.0),
                regulatory_report.get("confidence_score", 50.0),
            ),
        }

        weighted_signal, overall_confidence, weights = self._calculate_weighted_signal(signals)
        recommendation = self._signal_to_recommendation(weighted_signal)
        risk_level = self._assess_risk(signals, weighted_signal)
        rationale = self._generate_rationale(signals, weights, weighted_signal, recommendation)
        price_target = self._estimate_price_target(fundamental_report, technical_report, weighted_signal)

        return {
            "recommendation": recommendation,
            "price_target": price_target,
            "confidence": round(overall_confidence, 1),
            "risk_level": risk_level,
            "rationale": rationale,
            "contributing_factors": {key: round(value, 3) for key, value in weights.items()},
            "fundamental_score": round(signals["fundamental"][0], 2),
            "technical_score": round(signals["technical"][0], 2),
            "sentiment_score": round(signals["sentiment"][0], 2),
            "macro_score": round(signals["macro"][0], 2),
            "regulatory_score": round(signals["regulatory"][0], 2),
            "timestamp": datetime.now().isoformat(),
        }

    def _calculate_weighted_signal(self, signals: Dict[str, Tuple[float, float]]) -> Tuple[float, float, Dict[str, float]]:
        """Weight signals with a slight bias toward fundamentals and technicals for NSE stocks."""
        base_weights = {
            "fundamental": 0.32,
            "technical": 0.26,
            "sentiment": 0.18,
            "macro": 0.14,
            "regulatory": 0.10,
        }

        total_weight = 0.0
        weighted_sum = 0.0
        confidence_sum = 0.0
        final_weights: Dict[str, float] = {}

        for key, (signal, confidence) in signals.items():
            confidence_weight = confidence / 100.0
            weight = base_weights[key] * (0.55 + 0.45 * confidence_weight)
            final_weights[key] = weight
            total_weight += weight
            weighted_sum += signal * weight
            confidence_sum += confidence * base_weights[key]

        if total_weight > 0:
            for key in final_weights:
                final_weights[key] /= total_weight
            weighted_signal = weighted_sum / total_weight
        else:
            weighted_signal = 0.0

        return weighted_signal, confidence_sum, final_weights

    def _signal_to_recommendation(self, signal: float) -> str:
        if signal > 0.22:
            return "BUY"
        if signal < -0.22:
            return "SELL"
        return "HOLD"

    def _assess_risk(self, signals: Dict[str, Tuple[float, float]], weighted_signal: float) -> str:
        signal_values = [s[0] for s in signals.values()]
        signal_std = np.std(signal_values)
        avg_confidence = np.mean([s[1] for s in signals.values()])

        if signal_std > 0.6 or avg_confidence < 40:
            return "HIGH"
        if signal_std > 0.3 or avg_confidence < 60 or abs(weighted_signal) > 0.75:
            return "MEDIUM"
        return "LOW"

    def _generate_rationale(
        self,
        signals: Dict[str, Tuple[float, float]],
        weights: Dict[str, float],
        weighted_signal: float,
        recommendation: str,
    ) -> str:
        parts = [f"NSE synthesis recommends {recommendation} with aggregate signal {weighted_signal:.2f}."]
        sorted_signals = sorted(signals.items(), key=lambda x: abs(x[1][0]), reverse=True)
        for key, (signal, confidence) in sorted_signals[:3]:
            direction = "positive" if signal > 0 else "negative" if signal < 0 else "neutral"
            parts.append(
                f"{key.title()} is {direction} at {signal:.2f}, confidence {confidence:.1f}%, weight {weights[key]:.1%}."
            )
        if np.std([s[0] for s in signals.values()]) > 0.5:
            parts.append("Signals disagree meaningfully, so position sizing should stay conservative.")
        return " ".join(parts)

    def _estimate_price_target(
        self,
        fundamental_report: Dict[str, Any],
        technical_report: Dict[str, Any],
        weighted_signal: float,
    ) -> float | None:
        current_price = self._extract_price(fundamental_report) or self._extract_price(technical_report)
        if current_price is None:
            return None
        adjustment = weighted_signal * 0.15
        return round(current_price * (1 + adjustment), 2)

    def _extract_price(self, report: Dict[str, Any]) -> float | None:
        value = report.get("key_metrics", {}).get("current_price")
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"([-+]?\d*\.?\d+)", value.replace(",", ""))
            if match:
                return float(match.group(1))
        return None


def predict(
    fundamental: Dict[str, Any],
    technical: Dict[str, Any],
    sentiment: Dict[str, Any],
    macro: Dict[str, Any],
    regulatory: Dict[str, Any],
) -> Dict[str, Any]:
    """Public helper for the predictor agent."""
    return StockPredictor().predict_from_reports(fundamental, technical, sentiment, macro, regulatory)
