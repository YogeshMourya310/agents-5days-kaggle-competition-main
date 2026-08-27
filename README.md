# NSE Multi-Agent Stock Analysis System

NSE-focused stock analysis platform built around a multi-agent architecture. The system now targets Indian equities, uses NSE-style symbols such as `RELIANCE`, `TCS`, and `INFY`, and explains recommendations in an India-market context.

## What It Does

- Analyzes a stock across five dimensions:
  - Fundamental
  - Technical
  - Sentiment
  - Macro
  - Regulatory / disclosures
- Produces a `BUY`, `HOLD`, or `SELL` recommendation
- Returns confidence, rationale, and per-agent reports
- Supports both CLI and frontend-driven usage

## Data Sources

The codebase was migrated away from the original US-market assumptions.

- Market data: `yfinance` with NSE-style symbols such as `RELIANCE.NS`
- Technical indicators: local calculations in `tools/technical_indicators.py`
- News and sentiment: Google News RSS plus available market-news fallbacks
- Macro: India-oriented environment/default inputs in `tools/fred_fetcher.py`
- Regulatory / disclosures: company announcement proxy layer in `tools/sec_edgar_fetcher.py`

## Important Note

This repository is now optimized for NSE use, but some free data inputs are best-effort rather than licensed exchange feeds.

- Good for: prototypes, internal demos, experimentation
- Not ideal for: production-grade official exchange-data workflows

If you need official exchange-grade data, integrate licensed NSE/BSE feeds separately.

## Main Runtime Files

- `main.py`: CLI entrypoint
- `frontend_api.py`: FastAPI backend for the frontend
- `agents/kaggle_orchestrator.py`: primary NSE-focused orchestrator
- `tools/polygon_fetcher.py`: NSE market-data compatibility layer
- `tools/fred_fetcher.py`: India macro compatibility layer
- `tools/sec_edgar_fetcher.py`: company-announcement compatibility layer

## Example Usage

```bash
python main.py --ticker RELIANCE
python main.py --ticker TCS --verbose
python main.py --ticker INFY --json
```

## Supported Ticker Style

Accepted examples:

- `RELIANCE`
- `TCS`
- `INFY`
- `M&M`
- `BAJAJ-AUTO`
- `RELIANCE.NS`

## Optional Environment Overrides

The India macro layer supports simple overrides so you can tune the macro context without wiring a paid API:

```bash
INDIA_GDP_GROWTH=6.7
INDIA_CPI_INFLATION=4.8
RBI_REPO_RATE=6.5
INDIA_IIP_GROWTH=4.2
INDIA_UNEMPLOYMENT_RATE=7.8
INR_USD=83.4
INDIA_GSEC_10Y=7.1
RBI_POLICY_STANCE=neutral
```

## Local Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Frontend setup:

```bash
cd frontend
npm install
cd ..
```

Run the backend:

```bash
python frontend_api.py
```

Run the frontend separately from the `frontend/` directory if needed.

## Migration Summary

The following core areas were updated for NSE orientation:

- US market-data assumptions replaced with NSE symbol normalization
- US macro framing replaced with India macro framing
- SEC-specific disclosure logic replaced with Indian company announcement logic
- User-facing explanations rewritten for INR and India-market context

## Current Limitations

- Macro inputs are default/env-driven rather than sourced from a fully wired live India macro API
- Regulatory signals are based on public announcement proxies, not licensed exchange feeds
- Some optional A2A agent servers may still contain older descriptions even though the main runtime path is NSE-focused

## Recommended Next Steps

- Wire official or curated India macro APIs if you need live macro
- Add a stronger NSE/BSE disclosures integration if you need formal filing coverage
- Update the remaining A2A server descriptions and frontend labels for full India-market consistency
