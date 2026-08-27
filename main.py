#!/usr/bin/env python3
"""
Stock Prediction System - Main Entry Point.

CLI wrapper for the NSE-focused orchestrator.
"""

import argparse
import json
import re
import sys

from agents.kaggle_orchestrator import KaggleOrchestrator as StrategistOrchestrator


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="NSE Stock Prediction System - Multi-Agent Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --ticker RELIANCE
  python main.py --ticker TCS --verbose
  python main.py --ticker INFY --json
  python main.py --ticker HDFCBANK --horizon next_year
        """,
    )

    parser.add_argument(
        "--ticker",
        "-t",
        required=True,
        help="NSE/BSE ticker symbol (e.g., RELIANCE, TCS, INFY, BAJAJ-AUTO, M&M, RELIANCE.NS)",
    )
    parser.add_argument(
        "--horizon",
        "-H",
        default="next_quarter",
        choices=["next_week", "next_month", "next_quarter", "next_year"],
        help="Prediction time horizon (default: next_quarter)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed intermediate outputs from all agents",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()
    ticker = args.ticker.upper().strip()

    if not re.fullmatch(r"[A-Z0-9.&-]{1,20}", ticker):
        print(f"Error: Invalid ticker symbol '{ticker}'")
        print("Ticker should use NSE/BSE-style characters only (letters, numbers, ., &, -).")
        sys.exit(1)

    try:
        strategist = StrategistOrchestrator()
        result = strategist.analyze_stock(
            ticker=ticker,
            horizon=args.horizon,
            verbose=args.verbose,
        )

        if "error" in result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Analysis failed: {result['error']}")
            sys.exit(1)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            display_results(result, args.verbose)

    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"Unexpected error: {str(e)}")
            print("Troubleshooting:")
            print("  1. Verify your internet connectivity for market/news data")
            print("  2. Ensure optional A2A agents are running if you want full agent health")
            print("  3. Check environment overrides for India macro data if needed")
        sys.exit(1)


def display_results(result: dict, verbose: bool):
    """Display results in a readable console format."""
    prediction = result.get("prediction", result)

    print("=" * 70)
    print(f"NSE STOCK ANALYSIS REPORT: {result.get('ticker')}")
    print("=" * 70)
    print(f"Recommendation : {prediction.get('recommendation', 'N/A')}")
    print(f"Confidence     : {prediction.get('confidence', 0)}%")
    print(f"Risk Level     : {prediction.get('risk_level', 'N/A')}")
    print(f"Weighted Signal: {prediction.get('weighted_signal', result.get('weighted_signal', 'N/A'))}")

    print("\nRationale")
    print("-" * 70)
    print(prediction.get("rationale", "No rationale available"))

    print("\nTiming")
    print("-" * 70)
    print(f"Elapsed : {result.get('elapsed_time_seconds', result.get('elapsed_seconds', 0)):.2f}s")
    print(f"Time    : {result.get('timestamp', '')}")

    if verbose and "intermediate_reports" in result:
        print("\nDetailed Reports")
        print("-" * 70)
        print(json.dumps(result["intermediate_reports"], indent=2))


if __name__ == "__main__":
    main()
