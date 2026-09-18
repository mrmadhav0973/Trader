"""
Algorithmic Patterns Module - Advanced Veteran Suite
Candlestick anatomy (pin bars, engulfing, inside bars), market structure (Dow/Wyckoff),
volatility contraction (VCP), algorithmic trendlines, and S/R clustering.
"""

from typing import Any
import numpy as np
import pandas as pd


def detect_swing_points(df: pd.DataFrame, window: int = 4) -> tuple[list[dict], list[dict]]:
    """
    Detect local swing highs and swing lows using rolling fractals.
    """
    highs = df["High"].values
    lows = df["Low"].values
    times = df.index
    n = len(df)

    swing_highs = []
    swing_lows = []

    for i in range(window, n - window):
        current_high = highs[i]
        current_low = lows[i]

        is_swing_high = all(current_high >= highs[i - j] for j in range(1, window + 1)) and \
                        all(current_high >= highs[i + j] for j in range(1, window + 1))
        if is_swing_high:
            swing_highs.append({
                "bar_index": i,
                "timestamp": times[i],
                "price": float(current_high)
            })

        is_swing_low = all(current_low <= lows[i - j] for j in range(1, window + 1)) and \
                       all(current_low <= lows[i + j] for j in range(1, window + 1))
        if is_swing_low:
            swing_lows.append({
                "bar_index": i,
                "timestamp": times[i],
                "price": float(current_low)
            })

    return swing_highs, swing_lows


def analyze_candlestick_anatomy(df: pd.DataFrame, lookback: int = 5) -> list[dict[str, Any]]:
    """
    Analyze the anatomy of recent candlesticks:
    - Pin Bar / Hammer (Demand Rejection)
    - Shooting Star (Supply Rejection)
    - Bullish / Bearish Engulfing
    - Inside Bar (Volatility compression)
    """
    patterns = []
    n = len(df)
    curr_sym = df.attrs.get("currency_symbol", "") if hasattr(df, "attrs") else ""

    for i in range(max(1, n - lookback), n):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        dt = df.index[i]

        o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
        prev_o, prev_c = prev["Open"], prev["Close"]

        candle_range = h - l
        if candle_range <= 0:
            continue

        body = abs(c - o)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        # 1. Bullish Pin Bar / Hammer (Demand Rejection wick >= 50% of candle range)
        if lower_wick >= (0.50 * candle_range) and upper_wick <= (0.25 * candle_range):
            patterns.append({
                "bar_index": i,
                "time": dt,
                "name": "Bullish Pin Bar / Hammer",
                "type": "bullish_reversal",
                "detail": f"Aggressive rejection of lows at {curr_sym}{l:.2f}. Buyers absorbed sellers and pushed close to top."
            })

        # 2. Shooting Star / Bearish Pin Bar (Supply Rejection)
        elif upper_wick >= (0.50 * candle_range) and lower_wick <= (0.25 * candle_range):
            patterns.append({
                "bar_index": i,
                "time": dt,
                "name": "Shooting Star / Supply Rejection",
                "type": "bearish_reversal",
                "detail": f"Aggressive rejection of highs at {curr_sym}{h:.2f}. Overhead supply slapped price down."
            })

        # 3. Bullish Engulfing
        if prev_c < prev_o and c > o and o <= prev_c and c >= prev_o and body > (prev["High"] - prev["Low"]) * 0.8:
            patterns.append({
                "bar_index": i,
                "time": dt,
                "name": "Bullish Engulfing",
                "type": "bullish_momentum",
                "detail": "Decisive buyer takeover: green candle completely swallowed the previous down-bar."
            })

        # 4. Inside Bar (Compression)
        if h <= prev["High"] and l >= prev["Low"]:
            patterns.append({
                "bar_index": i,
                "time": dt,
                "name": "Inside Bar (Volatility Compression)",
                "type": "compression",
                "detail": "Price contracted inside previous bar. Energy coiled for a directional expansion."
            })

    return patterns


def analyze_market_structure(
    df: pd.DataFrame,
    swing_highs: list[dict],
    swing_lows: list[dict]
) -> dict[str, Any]:
    """
    Evaluate Wyckoff / Dow Theory Market Structure:
    - HH/HL sequence (Bullish Structure)
    - LH/LL sequence (Bearish Structure)
    - Identifies Market Phase: Accumulation, Markup, Distribution, Markdown, Chop
    """
    current_price = float(df["Close"].iloc[-1])
    ema20 = float(df["EMA_20"].iloc[-1])
    ema50 = float(df["EMA_50"].iloc[-1])
    ema200 = float(df["EMA_200"].iloc[-1])

    is_hh_hl = False
    is_lh_ll = False

    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        h1, h2 = swing_highs[-2]["price"], swing_highs[-1]["price"]
        l1, l2 = swing_lows[-2]["price"], swing_lows[-1]["price"]

        if h2 >= h1 and l2 >= l1:
            is_hh_hl = True
        elif h2 <= h1 and l2 <= l1:
            is_lh_ll = True

    # Determine Phase
    if current_price > ema20 and ema20 > ema50 and ema50 > ema200 and is_hh_hl:
        regime = "STAGE 2: STRONG TREND MARKUP"
        regime_desc = "Institutions in control. Dips into 20 EMA are buying opportunities."
        bias = "STRONGLY BULLISH"
    elif current_price < ema20 and ema20 < ema50 and ema50 < ema200 and is_lh_ll:
        regime = "STAGE 4: MARKDOWN / BEAR DOWNTREND"
        regime_desc = "Supply overwhelming demand. Avoid buying long; cash is king."
        bias = "STRONGLY BEARISH"
    elif current_price > ema50 and (is_hh_hl or not is_lh_ll):
        regime = "STAGE 1: WYCKOFF ACCUMULATION"
        regime_desc = "Smart money absorbing supply at key base. Building cause for markup."
        bias = "MILDLY BULLISH"
    elif current_price < ema50 and (is_lh_ll or not is_hh_hl):
        regime = "STAGE 3: DISTRIBUTION / CHURN"
        regime_desc = "High volume churn without upward progress. Smart money distributing to late retail."
        bias = "MILDLY BEARISH"
    else:
        regime = "CONSOLIDATION / NO-TREND CHOP"
        regime_desc = "Whipsaw market without directional edge. Strict patience required."
        bias = "NEUTRAL"

    return {
        "regime": regime,
        "regime_description": regime_desc,
        "bias": bias,
        "is_higher_highs": is_hh_hl,
        "is_lower_lows": is_lh_ll
    }


def calculate_algorithmic_trendlines(
    df: pd.DataFrame,
    swing_highs: list[dict],
    swing_lows: list[dict]
) -> dict[str, Any]:
    """Fit robust trendlines across recent swing points."""
    result = {"support_line": None, "resistance_line": None}

    if len(swing_lows) >= 2:
        recent_lows = sorted(swing_lows[-4:], key=lambda x: x["bar_index"])
        if len(recent_lows) >= 2:
            p1, p2 = recent_lows[-2], recent_lows[-1]
            x1, y1 = p1["bar_index"], p1["price"]
            x2, y2 = p2["bar_index"], p2["price"]

            if x2 != x1:
                slope = (y2 - y1) / (x2 - x1)
                intercept = y1 - slope * x1
                last_bar = len(df) - 1
                current_projected = slope * last_bar + intercept

                result["support_line"] = {
                    "start_time": p1["timestamp"],
                    "start_price": y1,
                    "end_time": df.index[-1],
                    "end_price": float(current_projected),
                    "slope": float(slope),
                    "is_ascending": slope > 0
                }

    if len(swing_highs) >= 2:
        recent_highs = sorted(swing_highs[-4:], key=lambda x: x["bar_index"])
        if len(recent_highs) >= 2:
            p1, p2 = recent_highs[-2], recent_highs[-1]
            x1, y1 = p1["bar_index"], p1["price"]
            x2, y2 = p2["bar_index"], p2["price"]

            if x2 != x1:
                slope = (y2 - y1) / (x2 - x1)
                intercept = y1 - slope * x1
                last_bar = len(df) - 1
                current_projected = slope * last_bar + intercept

                result["resistance_line"] = {
                    "start_time": p1["timestamp"],
                    "start_price": y1,
                    "end_time": df.index[-1],
                    "end_price": float(current_projected),
                    "slope": float(slope),
                    "is_descending": slope < 0
                }

    return result


def cluster_support_resistance_zones(
    df: pd.DataFrame,
    swing_highs: list[dict],
    swing_lows: list[dict],
    threshold_pct: float = 0.015
) -> list[dict[str, Any]]:
    """Cluster swing highs and lows into horizontal demand/supply zones."""
    current_price = float(df["Close"].iloc[-1])
    all_points = [(p["price"], "high") for p in swing_highs] + \
                 [(p["price"], "low") for p in swing_lows]

    if not all_points:
        return []

    all_points.sort(key=lambda x: x[0])
    zones = []
    cluster = [all_points[0]]

    for i in range(1, len(all_points)):
        price, point_type = all_points[i]
        prev_avg = np.mean([p[0] for p in cluster])

        if abs(price - prev_avg) / prev_avg <= threshold_pct:
            cluster.append(all_points[i])
        else:
            if len(cluster) >= 2:
                cluster_prices = [p[0] for p in cluster]
                zone_type = "support" if np.mean(cluster_prices) < current_price else "resistance"
                zones.append({
                    "type": zone_type,
                    "min_price": float(min(cluster_prices)),
                    "max_price": float(max(cluster_prices)),
                    "mid_price": float(np.mean(cluster_prices)),
                    "touches": len(cluster)
                })
            cluster = [all_points[i]]

    if len(cluster) >= 2:
        cluster_prices = [p[0] for p in cluster]
        zone_type = "support" if np.mean(cluster_prices) < current_price else "resistance"
        zones.append({
            "type": zone_type,
            "min_price": float(min(cluster_prices)),
            "max_price": float(max(cluster_prices)),
            "mid_price": float(np.mean(cluster_prices)),
            "touches": len(cluster)
        })

    zones.sort(key=lambda z: abs(z["mid_price"] - current_price))
    return zones[:6]
