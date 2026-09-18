"""
Automated Test Suite for AlphaEdge Trader
Tests all modules: Data fetching, indicators, patterns, SMC, risk sizing, signals, and charting.
"""

import sys
import pandas as pd

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from core.data import fetch_ohlcv, normalize_symbol
from core.indicators import add_all_indicators
from core.patterns import detect_swing_points, calculate_algorithmic_trendlines, cluster_support_resistance_zones
from core.smc import detect_fair_value_gaps, detect_liquidity_sweeps
from core.risk import calculate_position_sizing
from core.signals import analyze_symbol
from core.charting import create_analysis_chart


def test_suite():
    print("=" * 60)
    print("RUNNING ALPHAEDGE TRADER AUTOMATED VERIFICATION SUITE")
    print("=" * 60)

    # 1. Test Symbol Normalization
    print("1. Testing Symbol Normalization...")
    assert normalize_symbol("tatamotors") == "TATAMOTORS.NS"
    assert normalize_symbol("RELIANCE.NS") == "RELIANCE.NS"
    assert normalize_symbol("BTC-USD") == "BTC-USD"
    print("   ✓ Normalization passed.")

    # 2. Test Risk Management Position Sizing (₹5,000 Capital & 2% Rule)
    print("2. Testing Risk Management Engine for ₹5,000 Capital...")
    # Entry: 400, Stop Loss: 390 (Risk/share = 10). Max risk = 2% of 5000 = 100.
    # Quantity should be 100 / 10 = 10 shares. 10 * 400 = 4000 <= 5000.
    risk_test = calculate_position_sizing(
        capital=5000.0,
        entry_price=400.0,
        stop_loss=390.0,
        risk_percentage=0.02
    )
    assert risk_test["quantity"] == 10, f"Expected 10 shares, got {risk_test['quantity']}"
    assert risk_test["max_loss"] == 100.0, f"Expected 100 max loss, got {risk_test['max_loss']}"
    assert risk_test["capital_deployed"] == 4000.0
    assert risk_test["target_1"] == 420.0  # 1:2 R:R (10 * 2 = +20)
    assert risk_test["target_2"] == 430.0  # 1:3 R:R (10 * 3 = +30)
    print("   ✓ Risk management math verified exactly.")

    # 3. Test Live Data Fetching
    print("3. Testing Live Market Data Fetching (TATAPOWER.NS)...")
    df = fetch_ohlcv("TATAPOWER.NS", timeframe="1d", period="6mo")
    assert not df.empty, "DataFrame should not be empty"
    assert all(col in df.columns for col in ["Open", "High", "Low", "Close", "Volume"])
    print(f"   ✓ Successfully fetched {len(df)} daily candles.")

    # 4. Test Indicators
    print("4. Testing Technical Indicators Calculation...")
    df_ind = add_all_indicators(df)
    assert "EMA_20" in df_ind.columns
    assert "EMA_50" in df_ind.columns
    assert "RSI" in df_ind.columns
    assert "MACD" in df_ind.columns
    assert "ATR" in df_ind.columns
    assert "Volume_SMA_20" in df_ind.columns
    print("   ✓ All technical indicators computed successfully.")

    # 5. Test Pattern, SMC & Veteran Analytics
    print("5. Testing Algorithmic Trendlines, SMC & Candlestick Anatomy...")
    sh, sl = detect_swing_points(df_ind, window=3)
    trendlines = calculate_algorithmic_trendlines(df_ind, sh, sl)
    zones = cluster_support_resistance_zones(df_ind, sh, sl)
    fvgs = detect_fair_value_gaps(df_ind)
    sweeps = detect_liquidity_sweeps(df_ind, sh, sl)
    print(f"   ✓ Detected {len(sh)} swing highs, {len(sl)} swing lows.")
    print(f"   ✓ Formed {len(zones)} S/R zones and {len(fvgs)} Fair Value Gaps.")

    # 6. Test Full Veteran Confluence Analysis
    print("6. Testing End-to-End Veteran Confluence Signal Analysis...")
    analysis = analyze_symbol(df, capital=5000.0, risk_pct=0.02)
    assert "signal_type" in analysis
    assert "confluence_score" in analysis
    assert "veteran_insights" in analysis
    assert "market_structure" in analysis
    vi = analysis["veteran_insights"]
    print(f"   ✓ Market Regime: {analysis['market_structure']['regime']}")
    print(f"   ✓ Strategy Archetype: {vi['strategy_archetype']}")
    print(f"   ✓ Trapped Traders Analysis: {vi['trapped_traders']}")
    print(f"   ✓ Confluence Analysis complete: {analysis['signal_type']} ({analysis['confluence_score']}%)")

    # 7. Test Chart Rendering (both Dark and Light themes)
    print("7. Testing Plotly Multi-Pane Chart Generation...")
    fig_dark = create_analysis_chart(analysis, theme="dark")
    fig_light = create_analysis_chart(analysis, theme="light")
    assert fig_dark is not None
    assert fig_light is not None
    print("   ✓ Both Dark and Light theme charts generated successfully.")

    print("=" * 60)
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_suite()
    except Exception as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
