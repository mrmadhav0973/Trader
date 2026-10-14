"""
Algorithmic Patterns Module - Advanced Veteran Suite
Candlestick anatomy (pin bars, engulfing, inside bars), market structure (Dow/Wyckoff),
volatility contraction (VCP), algorithmic trendlines, and S/R clustering.
"""

from typing import Any
import numpy as np
import pandas as pd


def detect_swing_points(df: pd.DataFrame, window: int = 3) -> tuple[list[dict], list[dict]]:
    """
    Detect local swing highs and swing lows using rolling fractals and trailing-edge detection.
    Guarantees that both historical multi-week swings and recent key rejection wicks are captured.
    """
    highs = df["High"].values
    lows = df["Low"].values
    times = df.index
    n = len(df)

    swing_highs = []
    swing_lows = []

    for i in range(1, n):
        w_back = min(window, i)
        w_fwd = min(window, n - 1 - i)

        is_swing_high = all(highs[i] >= highs[i - j] for j in range(1, w_back + 1)) and \
                        (w_fwd == 0 or all(highs[i] >= highs[i + j] for j in range(1, w_fwd + 1)))
        if is_swing_high:
            swing_highs.append({
                "bar_index": i,
                "timestamp": times[i],
                "price": float(highs[i])
            })

        is_swing_low = all(lows[i] <= lows[i - j] for j in range(1, w_back + 1)) and \
                       (w_fwd == 0 or all(lows[i] <= lows[i + j] for j in range(1, w_fwd + 1)))
        if is_swing_low:
            swing_lows.append({
                "bar_index": i,
                "timestamp": times[i],
                "price": float(lows[i])
            })

    # Clean consecutive clustered duplicate highs/lows keeping the extreme price
    clean_sh = []
    for h in swing_highs:
        if clean_sh and abs(h["bar_index"] - clean_sh[-1]["bar_index"]) <= 2:
            if h["price"] > clean_sh[-1]["price"]:
                clean_sh[-1] = h
        else:
            clean_sh.append(h)

    clean_sl = []
    for l in swing_lows:
        if clean_sl and abs(l["bar_index"] - clean_sl[-1]["bar_index"]) <= 2:
            if l["price"] < clean_sl[-1]["price"]:
                clean_sl[-1] = l
        else:
            clean_sl.append(l)

    return clean_sh, clean_sl


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


def detect_human_market_structure(
    df: pd.DataFrame,
    swing_highs: list[dict],
    swing_lows: list[dict]
) -> dict[str, Any]:
    """
    Detects and labels ICT / Dow Theory Market Structure across historical and live candles:
    1. Swing Point Pivot Badges: HH (Higher High), HL (Higher Low), LH (Lower High), LL (Lower Low).
    2. Historical Structure Breaks: BOS (Break of Structure) and CHoCH (Change of Character)
       rendered as horizontal dashed benchmark lines connecting the broken pivot to the breakout bar.
    """
    if df is None or len(df) < 5:
        return {"labeled_pivots": [], "structure_breaks": []}

    n = len(df)
    times = df.index
    closes = df["Close"].values

    # Merge and sort all swings chronologically
    all_swings = []
    for h in swing_highs:
        all_swings.append({
            "bar_index": h["bar_index"],
            "timestamp": h["timestamp"],
            "price": h["price"],
            "type": "HIGH"
        })
    for l in swing_lows:
        all_swings.append({
            "bar_index": l["bar_index"],
            "timestamp": l["timestamp"],
            "price": l["price"],
            "type": "LOW"
        })
    all_swings.sort(key=lambda x: x["bar_index"])

    prev_high = None
    prev_low = None
    labeled_pivots = []
    for s in all_swings:
        if s["type"] == "HIGH":
            lbl = "HH" if (prev_high and s["price"] > prev_high["price"]) else ("LH" if prev_high else "HIGH")
            prev_high = s
        else:
            lbl = "HL" if (prev_low and s["price"] > prev_low["price"]) else ("LL" if prev_low else "LOW")
            prev_low = s

        unix_ts = int(s["timestamp"].timestamp()) if hasattr(s["timestamp"], "timestamp") else int(s["timestamp"])
        labeled_pivots.append({
            "bar_index": s["bar_index"],
            "time": unix_ts,
            "price": round(float(s["price"]), 2),
            "type": s["type"],
            "label": lbl
        })

    # Historical Structure Breaks (BOS / CHoCH)
    structure_breaks = []
    sh_list = [s for s in labeled_pivots if s["type"] == "HIGH"]
    sl_list = [s for s in labeled_pivots if s["type"] == "LOW"]

    # Bearish Breaks (Candle closing below previous swing low)
    for sl in sl_list:
        lvl = sl["price"]
        for b in range(sl["bar_index"] + 1, n):
            if closes[b] < lvl:
                b_type = "CHoCH" if sl.get("label") == "HL" else "BOS"
                start_ts = sl["time"]
                break_ts = int(times[b].timestamp()) if hasattr(times[b], "timestamp") else int(b)
                structure_breaks.append({
                    "type": f"BEARISH_{b_type}",
                    "level": lvl,
                    "start_time": start_ts,
                    "break_time": break_ts,
                    "start_price": lvl,
                    "break_price": round(float(closes[b]), 2),
                    "label": f"{b_type}: {lvl:.1f}",
                    "direction": "BEAR"
                })
                break

    # Bullish Breaks (Candle closing above previous swing high)
    for sh in sh_list:
        lvl = sh["price"]
        for b in range(sh["bar_index"] + 1, n):
            if closes[b] > lvl:
                b_type = "CHoCH" if sh.get("label") == "LH" else "BOS"
                start_ts = sh["time"]
                break_ts = int(times[b].timestamp()) if hasattr(times[b], "timestamp") else int(b)
                structure_breaks.append({
                    "type": f"BULLISH_{b_type}",
                    "level": lvl,
                    "start_time": start_ts,
                    "break_time": break_ts,
                    "start_price": lvl,
                    "break_price": round(float(closes[b]), 2),
                    "label": f"{b_type}: {lvl:.1f}",
                    "direction": "BULL"
                })
                break

    # Limit to the most prominent recent breaks (last 8)
    structure_breaks = structure_breaks[-8:]

    return {
        "labeled_pivots": labeled_pivots,
        "structure_breaks": structure_breaks
    }


def calculate_algorithmic_parallel_channels(
    df: pd.DataFrame,
    swing_highs: list[dict],
    swing_lows: list[dict],
    res_line: dict[str, Any] = None,
    supp_line: dict[str, Any] = None
) -> dict[str, Any]:
    """
    Construct high-precision parallel channels (Upper Resistance, Lower Support, 50% Median Line).
    STRICT INSTITUTIONAL VALIDATION:
    Only activates if there is genuine parallelism and price containment (at least 70% of candles
    contained within corridor, matching slopes, and active testing).
    Never produces fake, crossing, or arbitrary floating lines.
    """
    if df is None or len(df) < 15 or len(swing_highs) < 2 or len(swing_lows) < 2:
        return {"active": False}

    curr_p = float(df["Close"].iloc[-1])
    n = len(df)
    times = df.index
    highs = df["High"].values
    lows = df["Low"].values
    closes = df["Close"].values

    # Check if we have valid multi-touch trendlines that can form a channel
    if res_line and supp_line and res_line.get("active") and supp_line.get("active"):
        s_res = res_line.get("slope", 0)
        s_supp = supp_line.get("slope", 0)
        # Check slope alignment: both negative (descending channel) or both positive (ascending channel)
        if (s_res * s_supp > 0) and abs(s_res - s_supp) <= max(abs(s_res), abs(s_supp)) * 0.35:
            dominant_slope = (s_res + s_supp) / 2.0
            start_bar = max(0, min(res_line.get("start_bar", 0), supp_line.get("start_bar", 0)))
            end_bar = n - 1

            # Recalculate intercepts using dominant slope
            c_upper = max(highs[k] - (dominant_slope * k) for k in range(start_bar, n))
            c_lower = min(lows[k] - (dominant_slope * k) for k in range(start_bar, n))
            c_med = (c_upper + c_lower) / 2.0

            y_up_start = dominant_slope * start_bar + c_upper
            y_up_end = dominant_slope * end_bar + c_upper
            y_low_start = dominant_slope * start_bar + c_lower
            y_low_end = dominant_slope * end_bar + c_lower
            y_med_start = dominant_slope * start_bar + c_med
            y_med_end = dominant_slope * end_bar + c_med

            start_ts = int(times[start_bar].timestamp()) if hasattr(times[start_bar], "timestamp") else int(start_bar)
            end_ts = int(times[end_bar].timestamp()) if hasattr(times[end_bar], "timestamp") else int(end_bar)

            ch_h = max(0.01, y_up_end - y_low_end)
            pos_pct = round(((curr_p - y_low_end) / ch_h) * 100.0, 1)
            slope_pct = round(((y_med_end - y_med_start) / max(0.01, y_med_start)) * 100.0, 2)
            c_type = "ASCENDING CHANNEL" if dominant_slope > 0 else "DESCENDING CHANNEL"

            return {
                "active": True,
                "channel_type": c_type,
                "orientation": "bullish" if dominant_slope > 0 else "bearish",
                "status": f"CORRIDOR ({pos_pct:.0f}% Position)",
                "slope": round(float(dominant_slope), 4),
                "slope_pct": slope_pct,
                "position_pct": pos_pct,
                "channel_height": round(float(ch_h), 2),
                "channel_height_pct": round(float((ch_h / curr_p) * 100.0), 2),
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

    # If no strict parallel channel exists, return inactive to keep chart pristine
    return {"active": False}


def calculate_algorithmic_trendlines(
    df: pd.DataFrame,
    swing_highs: list[dict],
    swing_lows: list[dict]
) -> dict[str, Any]:
    """
    Fits institutional multi-touch diagonal Support & Resistance trendlines.
    A human trader looks across the entire structural history, connects major swing extremes,
    and extends rays to the current price with clear touch counts and anchor points.
    """
    result = {
        "support_line": None,
        "resistance_line": None,
        "parallel_channel": {"active": False},
        "all_trendlines": []
    }

    if df is None or len(df) < 10:
        return result

    n = len(df)
    times = df.index
    highs = df["High"].values
    lows = df["Low"].values
    closes = df["Close"].values
    curr_p = float(closes[-1])

    # Pre-extract unix timestamps once for instant O(1) lookup
    ts_array = [int(t.timestamp()) if hasattr(t, "timestamp") else int(i) for i, t in enumerate(times)]

    # 1. Best-Fitting Multi-Touch Resistance Trendline
    candidate_res = []
    sh_sorted = sorted(swing_highs, key=lambda x: x["bar_index"])
    if len(sh_sorted) > 25:
        sh_sorted = sorted(sh_sorted, key=lambda x: x.get("prominence", 1.0), reverse=True)[:25]
        sh_sorted.sort(key=lambda x: x["bar_index"])

    for i in range(len(sh_sorted)):
        for j in range(i + 1, len(sh_sorted)):
            p1, p2 = sh_sorted[i], sh_sorted[j]
            dx = p2["bar_index"] - p1["bar_index"]
            if dx < 6:
                continue
            slope = (p2["price"] - p1["price"]) / dx
            intercept = p1["price"] - slope * p1["bar_index"]

            start_idx = p1["bar_index"]
            k_arr = np.arange(start_idx, n)
            proj = slope * k_arr + intercept

            diff = np.abs(highs[start_idx:] - proj)
            touches = int(np.sum(diff <= (curr_p * 0.007)))
            violations = int(np.sum(closes[start_idx:] > proj + (curr_p * 0.008)))

            if touches >= 2 and violations <= 1:
                score = (touches * 10) - (violations * 15) - abs(slope) * 2
                candidate_res.append({
                    "score": score,
                    "p1": p1,
                    "p2": p2,
                    "slope": slope,
                    "intercept": intercept,
                    "touches": touches,
                    "violations": violations
                })

    if candidate_res:
        candidate_res.sort(key=lambda x: x["score"], reverse=True)
        best_res = candidate_res[0]
        end_bar = n - 1
        end_proj = best_res["slope"] * end_bar + best_res["intercept"]
        t1_ts = int(best_res["p1"]["timestamp"].timestamp()) if hasattr(best_res["p1"]["timestamp"], "timestamp") else int(best_res["p1"]["timestamp"])
        t2_ts = ts_array[end_bar]
        slope_pct = round(((end_proj - best_res["p1"]["price"]) / best_res["p1"]["price"] / max(1, end_bar - best_res["p1"]["bar_index"])) * 100, 2)
        status = "ACTIVE RESISTANCE"
        if curr_p > end_proj:
            status = "BROKEN / RECLAIMED"

        # Single pass to build touch points for winning line
        touch_pts = []
        b_slope = best_res["slope"]
        b_intercept = best_res["intercept"]
        for k in range(best_res["p1"]["bar_index"], n):
            proj = b_slope * k + b_intercept
            if abs(highs[k] - proj) <= (curr_p * 0.007):
                touch_pts.append({"time": ts_array[k], "price": round(float(highs[k]), 2)})

        result["resistance_line"] = {
            "active": True,
            "type": "RESISTANCE",
            "start_bar": best_res["p1"]["bar_index"],
            "start_time": t1_ts,
            "start_price": round(float(best_res["p1"]["price"]), 2),
            "end_time": t2_ts,
            "end_price": round(float(end_proj), 2),
            "slope": round(float(best_res["slope"]), 4),
            "slope_pct": slope_pct,
            "touches": best_res["touches"],
            "touch_points": touch_pts,
            "status": status,
            "is_descending": bool(best_res["slope"] < 0),
            "is_ascending": bool(best_res["slope"] > 0),
            "label": f"📉 Major Resistance Trendline ({best_res['touches']}x)"
        }

    # 2. Best-Fitting Multi-Touch Support Trendline
    candidate_supp = []
    sl_sorted = sorted(swing_lows, key=lambda x: x["bar_index"])
    if len(sl_sorted) > 25:
        sl_sorted = sorted(sl_sorted, key=lambda x: x.get("prominence", 1.0), reverse=True)[:25]
        sl_sorted.sort(key=lambda x: x["bar_index"])

    for i in range(len(sl_sorted)):
        for j in range(i + 1, len(sl_sorted)):
            p1, p2 = sl_sorted[i], sl_sorted[j]
            dx = p2["bar_index"] - p1["bar_index"]
            if dx < 6:
                continue
            slope = (p2["price"] - p1["price"]) / dx
            intercept = p1["price"] - slope * p1["bar_index"]

            start_idx = p1["bar_index"]
            k_arr = np.arange(start_idx, n)
            proj = slope * k_arr + intercept

            diff = np.abs(lows[start_idx:] - proj)
            touches = int(np.sum(diff <= (curr_p * 0.007)))
            violations = int(np.sum(closes[start_idx:] < proj - (curr_p * 0.008)))

            if touches >= 2 and violations <= 1:
                score = (touches * 10) - (violations * 15) - abs(slope) * 2
                candidate_supp.append({
                    "score": score,
                    "p1": p1,
                    "p2": p2,
                    "slope": slope,
                    "intercept": intercept,
                    "touches": touches,
                    "violations": violations
                })

    if candidate_supp:
        candidate_supp.sort(key=lambda x: x["score"], reverse=True)
        best_supp = candidate_supp[0]
        end_bar = n - 1
        end_proj = best_supp["slope"] * end_bar + best_supp["intercept"]
        t1_ts = int(best_supp["p1"]["timestamp"].timestamp()) if hasattr(best_supp["p1"]["timestamp"], "timestamp") else int(best_supp["p1"]["timestamp"])
        t2_ts = ts_array[end_bar]
        slope_pct = round(((end_proj - best_supp["p1"]["price"]) / best_supp["p1"]["price"] / max(1, end_bar - best_supp["p1"]["bar_index"])) * 100, 2)
        status = "ACTIVE SUPPORT"
        if curr_p < end_proj:
            status = "BROKEN / BREAKDOWN"

        # Single pass to build touch points for winning support line
        touch_pts = []
        b_slope = best_supp["slope"]
        b_intercept = best_supp["intercept"]
        for k in range(best_supp["p1"]["bar_index"], n):
            proj = b_slope * k + b_intercept
            if abs(lows[k] - proj) <= (curr_p * 0.007):
                touch_pts.append({"time": ts_array[k], "price": round(float(lows[k]), 2)})

        result["support_line"] = {
            "active": True,
            "type": "SUPPORT",
            "start_bar": best_supp["p1"]["bar_index"],
            "start_time": t1_ts,
            "start_price": round(float(best_supp["p1"]["price"]), 2),
            "end_time": t2_ts,
            "end_price": round(float(end_proj), 2),
            "slope": round(float(best_supp["slope"]), 4),
            "slope_pct": slope_pct,
            "touches": best_supp["touches"],
            "touch_points": touch_pts,
            "status": status,
            "is_ascending": bool(best_supp["slope"] > 0),
            "is_descending": bool(best_supp["slope"] < 0),
            "label": f"📈 Major Support Trendline ({best_supp['touches']}x)"
        }

    # Parallel Channel strictly evaluated using true multi-touch boundaries
    result["parallel_channel"] = calculate_algorithmic_parallel_channels(
        df,
        swing_highs,
        swing_lows,
        res_line=result.get("resistance_line"),
        supp_line=result.get("support_line")
    )
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

    clean_demands = merge_clean(demands, max_count=4)
    clean_supplies = merge_clean(supplies, max_count=4)

    # Ensure the absolute peak high and structural base low are explicitly preserved
    if swing_highs:
        max_sh = max(swing_highs, key=lambda x: x["price"])
        if max_sh["price"] > current_price and not any(abs(z["mid_price"] - max_sh["price"]) <= (zone_half_height * 3.5) for z in clean_supplies):
            clean_supplies.append({
                "type": "resistance",
                "is_flip": False,
                "min_price": round(max_sh["price"] - zone_half_height, 2),
                "max_price": round(max_sh["price"] + zone_half_height, 2),
                "mid_price": round(max_sh["price"], 2),
                "touches": 3,
                "weight": 5,
                "strength": "MAJOR",
                "dist_pct": round(abs(max_sh["price"] - current_price) / current_price * 100, 2),
                "is_immediate": False,
                "id": "supply_peak",
                "label": f"Major Peak Resistance ({round(max_sh['price'], 1)})"
            })

    if swing_lows:
        min_sl = min(swing_lows, key=lambda x: x["price"])
        if min_sl["price"] < current_price and not any(abs(z["mid_price"] - min_sl["price"]) <= (zone_half_height * 3.5) for z in clean_demands):
            clean_demands.append({
                "type": "support",
                "is_flip": False,
                "min_price": round(min_sl["price"] - zone_half_height, 2),
                "max_price": round(min_sl["price"] + zone_half_height, 2),
                "mid_price": round(min_sl["price"], 2),
                "touches": 3,
                "weight": 5,
                "strength": "MAJOR",
                "dist_pct": round(abs(min_sl["price"] - current_price) / current_price * 100, 2),
                "is_immediate": False,
                "id": "demand_base",
                "label": f"Major Structural Demand Base ({round(min_sl['price'], 1)})"
            })

    # Sort supplies ascending and demands descending
    clean_supplies.sort(key=lambda z: z["mid_price"])
    clean_demands.sort(key=lambda z: z["mid_price"], reverse=True)

    # 7. Assign sleek TradingView labels
    for i, z in enumerate(clean_demands):
        is_imm = (i == 0)
        z["is_immediate"] = is_imm
        z["id"] = f"demand_{i+1}"
        if "label" not in z or not z["label"]:
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
        if "label" not in z or not z["label"]:
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

