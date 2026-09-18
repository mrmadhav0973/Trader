"""
Smart Money Concepts (SMC) Module
Detects Fair Value Gaps (FVG), Buy-side/Sell-side Liquidity pools, and Liquidity Sweeps.
"""

from typing import Any
import pandas as pd


def detect_fair_value_gaps(df: pd.DataFrame, max_lookback: int = 50) -> list[dict[str, Any]]:
    """
    Detect 3-candle price imbalances (Fair Value Gaps).

    Bullish FVG: Candle[i-2].High < Candle[i].Low (untested price space in Candle[i-1])
    Bearish FVG: Candle[i-2].Low > Candle[i].High (untested price space in Candle[i-1])
    """
    fvgs = []
    start_idx = max(2, len(df) - max_lookback)

    highs = df["High"].values
    lows = df["Low"].values
    times = df.index

    for i in range(start_idx, len(df)):
        # Bullish FVG
        if highs[i - 2] < lows[i]:
            gap_bottom = highs[i - 2]
            gap_top = lows[i]
            # Check if mitigated by subsequent candles
            subsequent_lows = lows[i + 1:] if i + 1 < len(df) else []
            is_mitigated = any(l <= gap_bottom for l in subsequent_lows) if len(subsequent_lows) > 0 else False

            fvgs.append({
                "type": "bullish",
                "time_created": times[i - 1],
                "top": float(gap_top),
                "bottom": float(gap_bottom),
                "mid": float((gap_top + gap_bottom) / 2.0),
                "is_mitigated": is_mitigated
            })

        # Bearish FVG
        elif lows[i - 2] > highs[i]:
            gap_top = lows[i - 2]
            gap_bottom = highs[i]
            subsequent_highs = highs[i + 1:] if i + 1 < len(df) else []
            is_mitigated = any(h >= gap_top for h in subsequent_highs) if len(subsequent_highs) > 0 else False

            fvgs.append({
                "type": "bearish",
                "time_created": times[i - 1],
                "top": float(gap_top),
                "bottom": float(gap_bottom),
                "mid": float((gap_top + gap_bottom) / 2.0),
                "is_mitigated": is_mitigated
            })

    # Return most recent active FVGs
    return fvgs[-8:]


def detect_liquidity_sweeps(
    df: pd.DataFrame,
    swing_highs: list[dict],
    swing_lows: list[dict],
    lookback_bars: int = 15
) -> list[dict[str, Any]]:
    """
    Detect liquidity sweeps:
    - Bullish Sweep: Candle low breaches a previous swing low (grabbing sell stops),
      but closes firmly back above it.
    - Bearish Sweep: Candle high breaches a previous swing high (grabbing buy stops),
      but closes firmly back below it.
    """
    sweeps = []
    n = len(df)
    times = df.index
    curr_sym = df.attrs.get("currency_symbol", "") if hasattr(df, "attrs") else ""

    # Check recent bars
    for i in range(max(0, n - lookback_bars), n):
        bar_high = df["High"].iloc[i]
        bar_low = df["Low"].iloc[i]
        bar_close = df["Close"].iloc[i]
        bar_time = times[i]

        # Check for bullish sweep of swing lows
        for sl in swing_lows:
            if sl["bar_index"] < i - 1:
                # Pierced below swing low, but closed above it
                if bar_low < sl["price"] and bar_close > sl["price"]:
                    sweeps.append({
                        "type": "bullish_sweep",
                        "time": bar_time,
                        "swept_level": sl["price"],
                        "sweep_wick_low": float(bar_low),
                        "close_price": float(bar_close),
                        "description": f"Sell-side Liquidity swept at {curr_sym}{sl['price']:.2f}"
                    })

        # Check for bearish sweep of swing highs
        for sh in swing_highs:
            if sh["bar_index"] < i - 1:
                # Pierced above swing high, but closed below it
                if bar_high > sh["price"] and bar_close < sh["price"]:
                    sweeps.append({
                        "type": "bearish_sweep",
                        "time": bar_time,
                        "swept_level": sh["price"],
                        "sweep_wick_high": float(bar_high),
                        "close_price": float(bar_close),
                        "description": f"Buy-side Liquidity swept at {curr_sym}{sh['price']:.2f}"
                    })

    return sweeps[-4:]  # Most recent sweeps
