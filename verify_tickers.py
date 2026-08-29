"""
Batch verification script for the NSE stock analysis pipeline.

Runs KaggleOrchestrator across a diverse set of tickers and prints a
compact side-by-side table, so you can eyeball whether the recent fixes
(price-history fetch, NaN guard, auto_adjust, fundamental scoring) are
producing genuinely differentiated, sane output across many stocks at
once instead of checking one ticker per run.

Usage:
    python verify_tickers.py
    python verify_tickers.py --tickers RELIANCE TCS INFY HDFCBANK
"""

import argparse
import sys
import time

from agents.kaggle_orchestrator import KaggleOrchestrator

# A deliberately varied basket: different sectors, different market-cap
# tiers, and a mix of "stable" vs. "recently volatile" names, so any
# remaining scoring issues (e.g. things converging when they shouldn't)
# are more likely to surface.
DEFAULT_TICKERS = [
    "RELIANCE",   # Energy, mega-cap
    "TCS",        # Technology, mega-cap
    "HDFCBANK",   # Financials, mega-cap
    "INFY",       # Technology, mega-cap (compare vs TCS)
    "VEDL",       # Metals/mining, known volatile/large recent decline
    "ITC",        # FMCG, historically low-volatility
    "TATASTEEL",  # Metals, cyclical
    "SUNPHARMA",  # Pharma, defensive sector
]


def fmt(val, width=8):
    if val is None:
        return "N/A".rjust(width)
    if isinstance(val, float):
        return f"{val:.2f}".rjust(width)
    return str(val).rjust(width)


def main():
    parser = argparse.ArgumentParser(description="Batch-verify the NSE analysis pipeline across tickers.")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS, help="Tickers to test")
    args = parser.parse_args()

    orchestrator = KaggleOrchestrator()

    rows = []
    print(f"\nRunning {len(args.tickers)} tickers...\n")

    for ticker in args.tickers:
        t0 = time.time()
        try:
            result = orchestrator.analyze_stock(ticker, verbose=False)
            tech = result["analysis_reports"]["technical"]["key_metrics"]
            fund = result["analysis_reports"]["fundamental"]["key_metrics"]
            rows.append({
                "ticker": ticker,
                "rec": result["recommendation"],
                "conf": result["confidence"],
                "signal": result["weighted_signal"],
                "rsi": tech.get("rsi"),
                "sma_50": tech.get("sma_50"),
                "sma_200": tech.get("sma_200"),
                "trend": tech.get("trend"),
                "pe": fund.get("pe_ratio"),
                "elapsed": round(time.time() - t0, 1),
            })
        except Exception as e:
            rows.append({"ticker": ticker, "error": str(e)})

    # --- Print comparison table ---
    header = f"{'TICKER':<10} {'REC':<6} {'CONF':>6} {'SIGNAL':>7} {'RSI':>7} {'SMA50':>9} {'SMA200':>9} {'TREND':<9} {'PE':>7} {'SECS':>5}"
    print(header)
    print("-" * len(header))

    for r in rows:
        if "error" in r:
            print(f"{r['ticker']:<10} ERROR: {r['error']}")
            continue
        print(
            f"{r['ticker']:<10} {r['rec']:<6} {fmt(r['conf'],6)} {fmt(r['signal'],7)} "
            f"{fmt(r['rsi'],7)} {fmt(r['sma_50'],9)} {fmt(r['sma_200'],9)} "
            f"{str(r['trend']):<9} {fmt(r['pe'],7)} {fmt(r['elapsed'],5)}"
        )

    # --- Flag likely-remaining issues ---
    print("\n--- Sanity checks ---")
    valid_rows = [r for r in rows if "error" not in r]

    confidences = [r["conf"] for r in valid_rows]
    signals = [r["signal"] for r in valid_rows]

    if len(set(confidences)) == 1 and len(confidences) > 1:
        print("⚠️  All tickers have IDENTICAL confidence — investigate further.")
    else:
        print(f"✅ Confidence varies across tickers (range: {min(confidences):.1f}–{max(confidences):.1f})")

    if len(set(signals)) == 1 and len(signals) > 1:
        print("⚠️  All tickers have IDENTICAL weighted signal — investigate further.")
    else:
        print(f"✅ Weighted signal varies across tickers (range: {min(signals):.2f}–{max(signals):.2f})")

    na_technical = [r["ticker"] for r in valid_rows if r["sma_200"] is None or r["sma_200"] == "N/A"]
    if na_technical:
        print(f"⚠️  sma_200 still N/A for: {', '.join(na_technical)} — technical fetch may be failing for these.")
    else:
        print("✅ sma_200 populated for all tickers")

    recs = [r["rec"] for r in valid_rows]
    if len(set(recs)) == 1 and len(recs) > 2:
        print(f"⚠️  All tickers landed on the same recommendation ({recs[0]}) — worth a second look, "
              f"though this CAN be legitimate if market conditions are broadly similar right now.")
    else:
        print(f"✅ Recommendations vary: {dict((r, recs.count(r)) for r in set(recs))}")


if __name__ == "__main__":
    main()