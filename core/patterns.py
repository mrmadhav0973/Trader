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


def calculate_algorithmic_parallel_channels(
    df: pd.DataFrame,
    swing_highs: list[dict],
    swing_lows: list[dict]
) -> dict[str, Any]:
    """
    Construct high-precision parallel channels (Upper Resistance, Lower Support, 50% Median Line).
    Determines slope, channel orientation (Ascending, Descending, Horizontal Corridor),
    and exact price position percentage within the corridor.
    """
    if df is None or len(df) < 15 or len(swing_highs) < 2 or len(swing_lows) < 2:
        return {"active": False}

    curr_p = float(df["Close"].iloc[-1])
    n = len(df)
    times = df.index

    # Use recent swing points (last 4 highs and last 4 lows)
    recent_highs = sorted(swing_highs[-4:], key=lambda x: x["bar_index"])
    recent_lows = sorted(swing_lows[-4:], key=lambda x: x["bar_index"])

    if len(recent_highs) < 2 or len(recent_lows) < 2:
        return {"active": False}

    l1, l2 = recent_lows[-2], recent_lows[-1]
    h1, h2 = recent_highs[-2], recent_highs[-1]

    dx_l = l2["bar_index"] - l1["bar_index"]
    slope_l = (l2["price"] - l1["price"]) / dx_l if dx_l != 0 else 0.0

    dx_h = h2["bar_index"] - h1["bar_index"]
    slope_h = (h2["price"] - h1["price"]) / dx_h if dx_h != 0 else 0.0

    # Determine dominant slope and channel orientation
    if slope_l > 0 and slope_h >= 0:
        dominant_slope = slope_l
        channel_type = "ASCENDING CHANNEL"
        orientation = "bullish"
    elif slope_h < 0 and slope_l <= 0:
        dominant_slope = slope_h
        channel_type = "DESCENDING CHANNEL"
        orientation = "bearish"
    else:
        dominant_slope = (slope_l + slope_h) / 2.0
        if abs(dominant_slope) < (curr_p * 0.0004):
            channel_type = "HORIZONTAL CORRIDOR"
            orientation = "neutral"
            dominant_slope = 0.0
        elif dominant_slope > 0:
            channel_type = "ASCENDING CHANNEL"
            orientation = "bullish"
        else:
            channel_type = "DESCENDING CHANNEL"
            orientation = "bearish"

    # Start bar is the earliest anchor of the two swing sets
    start_bar = max(0, min(recent_lows[-2]["bar_index"], recent_highs[-2]["bar_index"]))
    end_bar = n - 1

    # Find upper intercept (maximum residual among recent highs)
    c_upper = max(h["price"] - (dominant_slope * h["bar_index"]) for h in recent_highs)
    # Find lower intercept (minimum residual among recent lows)
    c_lower = min(l["price"] - (dominant_slope * l["bar_index"]) for l in recent_lows)

    # Ensure minimum channel height (at least 1.5% of price)
    if (c_upper - c_lower) < (curr_p * 0.015):
        diff = (curr_p * 0.015 - (c_upper - c_lower)) / 2.0
        c_upper += diff
        c_lower -= diff

    c_median = (c_upper + c_lower) / 2.0

    # Project coordinates at start and end
    y_up_start = dominant_slope * start_bar + c_upper
    y_up_end = dominant_slope * end_bar + c_upper

    y_low_start = dominant_slope * start_bar + c_lower
    y_low_end = dominant_slope * end_bar + c_lower

    y_med_start = dominant_slope * start_bar + c_median
    y_med_end = dominant_slope * end_bar + c_median

    # Convert timestamps to unix seconds for charting
    start_ts = int(times[start_bar].timestamp()) if hasattr(times[start_bar], "timestamp") else int(start_bar)
    end_ts = int(times[end_bar].timestamp()) if hasattr(times[end_bar], "timestamp") else int(end_bar)

    # Current price position relative to channel boundaries
    curr_upper = y_up_end
    curr_lower = y_low_end
    ch_height = max(0.01, curr_upper - curr_lower)
    pos_pct = round(((curr_p - curr_lower) / ch_height) * 100.0, 1)
    slope_pct = round(((y_med_end - y_med_start) / max(0.01, y_med_start)) * 100.0, 2)

    # Status classification
    if pos_pct <= 18:
        status = "TESTING LOWER SUPPORT (Demand Boundary - High Prob Bounce)"
    elif pos_pct >= 82:
        status = "TESTING UPPER RESISTANCE (Overhead Boundary - Supply Reversal)"
    elif 40 <= pos_pct <= 60:
        status = "AT 50% MEDIAN EQUILIBRIUM"
    elif pos_pct > 102:
        status = "BULLISH EXPANSION BREAKOUT"
    elif pos_pct < -2:
        status = "BEARISH EXPANSION BREAKDOWN"
    else:
        status = "INSIDE CHANNEL CORRIDOR"

    return {
        "active": True,
        "channel_type": channel_type,
        "orientation": orientation,
        "status": status,
        "slope": round(float(dominant_slope), 4),
        "slope_pct": slope_pct,
        "position_pct": pos_pct,
        "channel_height": round(float(ch_height), 2),
        "channel_height_pct": round(float((ch_height / curr_p) * 100.0), 2),
        "upper_line": {
            "start_time": start_ts,
            "start_price": round(float(y_up_start), 2),
            "end_time": end_ts,
            "end_price": round(float(y_up_end), 2)
        },
        "lower_line": {
            "start_time": start_ts,
            "start_price": round(float(y_low_start), 2),
            "end_time": end_ts,
            "end_price": round(float(y_low_end), 2)
        },
        "median_line": {
            "start_time": start_ts,
            "start_price": round(float(y_med_start), 2),
            "end_time": end_ts,
            "end_price": round(float(y_med_end), 2)
        }
    }


def calculate_algorithmic_trendlines(
    df: pd.DataFrame,
    swing_highs: list[dict],
    swing_lows: list[dict]
) -> dict[str, Any]:
    """Fit robust trendlines across recent swing points and calculate parallel channels."""
    result = {"support_line": None, "resistance_line": None, "parallel_channel": None}

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

    result["parallel_channel"] = calculate_algorithmic_parallel_channels(df, swing_highs, swing_lows)
    return result


def cluster_support_resistance_zones(
    df: pd.DataFrame,
    swing_highs: list[dict] = None,
    swing_lows: list[dict] = None,
    threshold_pct: float = 0.015,
    max_zones: int = 6
) -> list[dict[str, Any]]:
    """
    Cluster price action into sleek, institutional Support & Resistance (Demand & Supply)
    "thick line zones" rather than oversized screen-filling rectangles.

    Each zone is centered strictly around its touch-weighted mid_price, with a compact
    ribbon height (0.15% to 0.25% price band) and clear touch strength.
    """
    if df is None or len(df) < 5:
        return []

    current_price = float(df["Close"].iloc[-1])
    highs = df["High"].values
    lows = df["Low"].values
    closes = df["Close"].values
    n = len(df)

    # 1. Calibrate compact thick-line ribbon thickness using ATR
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(abs(highs[1:] - closes[:-1]), abs(lows[1:] - closes[:-1]))
    ) if n > 1 else np.array([current_price * 0.02])
    atr = float(np.mean(tr[-14:])) if len(tr) >= 14 else float(current_price * 0.02)
    if atr <= 0 or np.isnan(atr):
        atr = float(current_price * 0.015)

    # Sleek thick-line zone half-height: compact 0.12% - 0.25% band
    zone_half_height = max(current_price * 0.0012, atr * 0.06)
    cluster_threshold = max(current_price * 0.008, atr * 0.40)

    # 2. Extract multi-scale swing fractals (windows 2, 4, 8)
    all_points = []
    for w, weight in [(2, 1), (4, 2), (8, 3)]:
        if n > 2 * w:
            for i in range(w, n - w):
                if all(highs[i] >= highs[i - j] for j in range(1, w + 1)) and all(highs[i] >= highs[i + j] for j in range(1, w + 1)):
                    all_points.append({"price": float(highs[i]), "type": "high", "weight": weight, "bar": i})
                if all(lows[i] <= lows[i - j] for j in range(1, w + 1)) and all(lows[i] <= lows[i + j] for j in range(1, w + 1)):
                    all_points.append({"price": float(lows[i]), "type": "low", "weight": weight, "bar": i})

    # Include external swing points if provided
    if swing_highs:
        for p in swing_highs:
            all_points.append({"price": float(p["price"]), "type": "high", "weight": 2, "bar": p.get("bar_index", 0)})
    if swing_lows:
        for p in swing_lows:
            all_points.append({"price": float(p["price"]), "type": "low", "weight": 2, "bar": p.get("bar_index", 0)})

    if not all_points:
        return []

    # Sort all points by price
    all_points.sort(key=lambda x: x["price"])

    # 3. Cluster points into contiguous price levels
    clusters = []
    curr_cluster = [all_points[0]]

    for pt in all_points[1:]:
        prev_center = np.mean([p["price"] for p in curr_cluster])
        if abs(pt["price"] - prev_center) <= cluster_threshold:
            curr_cluster.append(pt)
        else:
            clusters.append(curr_cluster)
            curr_cluster = [pt]
    if curr_cluster:
        clusters.append(curr_cluster)

    # 4. Formulate sleek thick line zone boundaries centered at mid_price
    raw_zones = []
    for c in clusters:
        prices = [p["price"] for p in c]
        weights = sum(p["weight"] for p in c)
        types = set(p["type"] for p in c)
        is_flip = len(types) > 1

        mid_p = float(np.average(prices, weights=[p["weight"] for p in c]))
        # Compact thick-line boundary strictly centered around mid_p
        min_p = float(mid_p - zone_half_height)
        max_p = float(mid_p + zone_half_height)

        touches = len(c)
        if touches >= 4 or weights >= 6:
            strength = "MAJOR"
        elif touches >= 2 or weights >= 3:
            strength = "INTERMEDIATE"
        else:
            strength = "LOCAL"

        is_support = max_p <= current_price * 1.006
        z_type = "support" if is_support else "resistance"

        raw_zones.append({
            "type": z_type,
            "is_flip": is_flip,
            "min_price": round(min_p, 2),
            "max_price": round(max_p, 2),
            "mid_price": round(mid_p, 2),
            "touches": touches,
            "weight": weights,
            "strength": strength,
            "dist_pct": round(abs(mid_p - current_price) / current_price * 100, 2)
        })

    # 5. Separate into Demand (Support) and Supply (Resistance)
    demands = [z for z in raw_zones if z["type"] == "support"]
    supplies = [z for z in raw_zones if z["type"] == "resistance"]

    demands.sort(key=lambda z: z["mid_price"], reverse=True)
    supplies.sort(key=lambda z: z["mid_price"])

    # 6. Merge overlapping zones within each group to preserve sleek thick-line ribbons
    def merge_clean(zones_list, max_count=3):
        clean = []
        for z in zones_list:
            overlap = False
            for existing in clean:
                if abs(z["mid_price"] - existing["mid_price"]) <= (zone_half_height * 2.8):
                    overlap = True
                    existing["touches"] += z["touches"]
                    new_mid = round((existing["mid_price"] + z["mid_price"]) / 2.0, 2)
                    existing["mid_price"] = new_mid
                    existing["min_price"] = round(new_mid - zone_half_height, 2)
                    existing["max_price"] = round(new_mid + zone_half_height, 2)
                    if z["strength"] == "MAJOR":
                        existing["strength"] = "MAJOR"
                    if z.get("is_flip"):
                        existing["is_flip"] = True
                    break
            if not overlap:
                clean.append(z)
            if len(clean) >= max_count:
                break
        return clean

    clean_demands = merge_clean(demands, max_count=3)
    clean_supplies = merge_clean(supplies, max_count=3)

    # 7. Assign sleek TradingView labels
    for i, z in enumerate(clean_demands):
        is_imm = (i == 0)
        z["is_immediate"] = is_imm
        z["id"] = f"demand_{i+1}"
        if is_imm:
            z["label"] = f"Immediate Demand Zone ({z['touches']}x)"
        elif z["strength"] == "MAJOR":
            z["label"] = f"Major Institutional Demand ({z['touches']}x)"
        elif z.get("is_flip"):
            z["label"] = f"Key Polarity Demand Base ({z['touches']}x)"
        else:
            z["label"] = f"Structural Demand Zone ({z['touches']}x)"

    for i, z in enumerate(clean_supplies):
        is_imm = (i == 0)
        z["is_immediate"] = is_imm
        z["id"] = f"supply_{i+1}"
        if is_imm:
            z["label"] = f"Immediate Overhead Supply ({z['touches']}x)"
        elif z["strength"] == "MAJOR":
            z["label"] = f"Major Distribution Supply ({z['touches']}x)"
        elif z.get("is_flip"):
            z["label"] = f"Key Polarity Supply Wall ({z['touches']}x)"
        else:
            z["label"] = f"Structural Supply Zone ({z['touches']}x)"

    all_sr_zones = clean_demands + clean_supplies
    return all_sr_zones


# Alias for explicit caller naming
build_maximum_sr_zones = cluster_support_resistance_zones

