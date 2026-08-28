"""
Predictor Agent - A2A Server (Port 8006).

NSE-focused synthesis agent for Indian equities.
"""

import json
import os
import sys

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.google_llm import Gemini
from google.genai import types

from config.agent_prompts import PREDICTOR_AGENT_PROMPT
from models.simple_predictor import predict as ml_predict

load_dotenv()

retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def ml_model_predict(
    fundamental_report: str,
    technical_report: str,
    sentiment_report: str,
    macro_report: str,
    regulatory_report: str,
) -> str:
    """Generate an NSE-oriented prediction from all analysis reports."""
    try:
        prediction = ml_predict(
            json.loads(fundamental_report),
            json.loads(technical_report),
            json.loads(sentiment_report),
            json.loads(macro_report),
            json.loads(regulatory_report),
        )
        return json.dumps(prediction, indent=2)
    except Exception as e:
        return json.dumps(
            {
                "error": f"Prediction failed: {str(e)}",
                "recommendation": "HOLD",
                "confidence": 0.0,
                "risk_level": "HIGH",
            },
            indent=2,
        )


def calculate_risk(
    fundamental_report: str,
    technical_report: str,
    sentiment_report: str,
    macro_report: str,
    regulatory_report: str,
) -> str:
    """Calculate synthesis risk from report disagreement and confidence."""
    try:
        import numpy as np

        reports = [
            json.loads(fundamental_report),
            json.loads(technical_report),
            json.loads(sentiment_report),
            json.loads(macro_report),
            json.loads(regulatory_report),
        ]
        signals = [report.get("directional_signal", 0) for report in reports]
        confidences = [report.get("confidence_score", 50) for report in reports]
        signal_std = np.std(signals)
        avg_confidence = np.mean(confidences)

        if signal_std > 0.6 or avg_confidence < 40:
            risk_level = "HIGH"
        elif signal_std > 0.3 or avg_confidence < 60:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return json.dumps(
            {
                "risk_level": risk_level,
                "signal_disagreement": round(signal_std, 3),
                "average_confidence": round(avg_confidence, 1),
                "explanation": (
                    f"Risk assessed as {risk_level} based on analyst disagreement "
                    f"and conviction for this NSE stock."
                ),
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"risk_level": "UNKNOWN", "error": str(e)}, indent=2)


predictor_agent = LlmAgent(
    model=Gemini(
        model="gemini-2.0-flash-exp",
        retry_options=retry_config,
        generation_config={"response_mime_type": "application/json", "temperature": 0.2},
    ),
    name="predictor_agent",
    description=(
        "Chief NSE prediction synthesizer that converts the five specialist reports "
        "into a final BUY, HOLD, or SELL recommendation with confidence and risk."
    ),
    instruction=PREDICTOR_AGENT_PROMPT,
    tools=[ml_model_predict, calculate_risk],
)

app = to_a2a(predictor_agent, port=8006)

print("Predictor Agent initialized")
print("  Market: NSE / India")
print("  Tools: ml_model_predict, calculate_risk")
print("  Port: 8006")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006, log_level="info")
