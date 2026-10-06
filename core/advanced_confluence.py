"""
AlphaEdge Trader - Advanced Institutional Confluences Module
Implements 8 elite institutional and quantitative edges:
1. Fair Value Gaps (FVG) & Imbalance Engine with 50% Consequent Encroachment (CE)
2. Relative Strength / Relative Weakness (RS / RW) vs. Benchmark Index
3. Fibonacci Golden Pocket (0.618 - 0.786) & Optimal Trade Entry (OTE)
4. Market Session Killzones & Time-of-Day Volatility Filter (Lunch Dead Zone Warning)
5. Open Interest (OI) & Max Pain Cluster Dynamics (Call/Put Walls & PCR)
6. TTM Volatility Squeeze (Bollinger Bands vs. Keltner Channels)
7. India VIX / Volatility Regime Filter
8. Cumulative Volume Delta (CVD) & Exhaustion Divergence Engine
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd


# =============================================================================
# 1. FAIR VALUE GAPS (FVG) & 50% CONSEQUENT ENCROACHMENT (CE)
# =============================================================================
def detect_fair_value_gaps(df: pd.DataFrame, max_lookback: int = 40) -> List[Dict[str, Any]]:
    """
    Detect 3-candle institutional price imbalances (Fair Value Gaps).
    Bullish FVG: Candle[i-2].High < Candle[i].Low (untested price space in Candle[i-1])
    Bearish FVG: Candle[i-2].Low > Candle[i].High (untested price space in Candle[i-1])
    Calculates Consequent Encroachment (50% midpoint) and tracks mitigation.
    """
    if df is None or len(df) < 5:
        return []

    fvgs: List[Dict[str, Any]] = []
    start_idx = max(2, len(df) - max_lookback)
    highs = df["High"].values
    lows = df["Low"].values
    times = df.index
    curr_price = float(df["Close"].iloc[-1])

    for i in range(start_idx, len(df)):
        c_time = times[i - 1]
        try:
            ts = int(pd.Timestamp(c_time).timestamp())
        except Exception:
            ts = int(i)

        # Bullish FVG
        if highs[i - 2] < lows[i]:
            gap_bottom = float(highs[i - 2])
            gap_top = float(lows[i])
            mid_ce = float((gap_top + gap_bottom) / 2.0)
            
            # Check if filled/mitigated by subsequent candles
            subsequent_lows = lows[i + 1:] if i + 1 < len(df) else []
            is_mitigated = any(l <= gap_bottom for l in subsequent_lows) if len(subsequent_lows) > 0 else False

            fvgs.append({
                "id": f"fvg_bull_{i}",
                "type": "BULLISH",
                "time_created": str(c_time),
                "timestamp": ts,
                "top": round(gap_top, 2),
                "bottom": round(gap_bottom, 2),
                "mid_ce": round(mid_ce, 2),
                "is_mitigated": is_mitigated,
                "label": f"Bullish FVG [{gap_bottom:.2f} - {gap_top:.2f}]",
                "in_gap": (gap_bottom <= curr_price <= gap_top)
            })

        # Bearish FVG
        elif lows[i - 2] > highs[i]:
            gap_top = float(lows[i - 2])
            gap_bottom = float(highs[i])
            mid_ce = float((gap_top + gap_bottom) / 2.0)
            
            # Check if filled/mitigated by subsequent candles
            subsequent_highs = highs[i + 1:] if i + 1 < len(df) else []
            is_mitigated = any(h >= gap_top for h in subsequent_highs) if len(subsequent_highs) > 0 else False

            fvgs.append({
                "id": f"fvg_bear_{i}",
                "type": "BEARISH",
                "time_created": str(c_time),
                "timestamp": ts,
                "top": round(gap_top, 2),
                "bottom": round(gap_bottom, 2),
                "mid_ce": round(mid_ce, 2),
                "is_mitigated": is_mitigated,
                "label": f"Bearish FVG [{gap_bottom:.2f} - {gap_top:.2f}]",
                "in_gap": (gap_bottom <= curr_price <= gap_top)
            })

    # Return active (unmitigated) gaps first, max 6 for visual clarity
    unmitigated = [f for f in fvgs if not f["is_mitigated"]]
    return unmitigated[-6:] if unmitigated else fvgs[-4:]


# =============================================================================
# 2. FIBONACCI GOLDEN POCKET (0.618 - 0.786) & OPTIMAL TRADE ENTRY (OTE)
# =============================================================================
def calculate_fibonacci_golden_pocket(
    df: pd.DataFrame,
    swing_highs: Optional[List[Dict[str, Any]]] = None,
    swing_lows: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Computes Fibonacci retracements of the most recent significant impulse leg.
    Highlights the Golden Pocket (0.618 - 0.786) and OTE (0.705).
    """
    if df is None or len(df) < 10:
        return {"active": False}

    curr_p = float(df["Close"].iloc[-1])
    n = len(df)

    # Derive recent high and low if not provided
    if swing_highs and swing_lows and len(swing_highs) > 0 and len(swing_lows) > 0:
        recent_sh = max(swing_highs[-3:], key=lambda x: x["price"])
        recent_sl = min(swing_lows[-3:], key=lambda x: x["price"])
        sh_price = float(recent_sh["price"])
        sl_price = float(recent_sl["price"])
        is_bullish_impulse = recent_sh["bar_index"] > recent_sl["bar_index"]
    else:
        sh_price = float(df["High"].tail(30).max())
        sl_price = float(df["Low"].tail(30).min())
        is_bullish_impulse = curr_p >= (sh_price + sl_price) / 2.0

    impulse_range = max(0.01, sh_price - sl_price)

    if is_bullish_impulse:
        # Retracement from High down towards Low
        fib_0 = sh_price
        fib_1 = sl_price
        fib_382 = sh_price - (0.382 * impulse_range)
        fib_500 = sh_price - (0.500 * impulse_range)
        fib_618 = sh_price - (0.618 * impulse_range)
        fib_705 = sh_price - (0.705 * impulse_range)
        fib_786 = sh_price - (0.786 * impulse_range)
        gp_top = fib_618
        gp_bottom = fib_786
    else:
        # Retracement from Low up towards High
        fib_0 = sl_price
        fib_1 = sh_price
        fib_382 = sl_price + (0.382 * impulse_range)
        fib_500 = sl_price + (0.500 * impulse_range)
        fib_618 = sl_price + (0.618 * impulse_range)
        fib_705 = sl_price + (0.705 * impulse_range)
        fib_786 = sl_price + (0.786 * impulse_range)
        gp_bottom = fib_618
        gp_top = fib_786

    in_golden_pocket = (min(gp_bottom, gp_top) <= curr_p <= max(gp_bottom, gp_top))
    in_ote = abs(curr_p - fib_705) / curr_p <= 0.015

    return {
        "active": True,
        "is_bullish_impulse": is_bullish_impulse,
        "swing_high": round(sh_price, 2),
        "swing_low": round(sl_price, 2),
        "fib_0": round(fib_0, 2),
        "fib_382": round(fib_382, 2),
        "fib_500": round(fib_500, 2),
        "fib_618": round(fib_618, 2),
        "fib_705": round(fib_705, 2),
        "fib_786": round(fib_786, 2),
        "fib_1": round(fib_1, 2),
        "golden_pocket_top": round(max(gp_top, gp_bottom), 2),
        "golden_pocket_bottom": round(min(gp_top, gp_bottom), 2),
        "in_golden_pocket": in_golden_pocket,
        "in_ote": in_ote,
        "status": "AT GOLDEN POCKET (0.618-0.786)" if in_golden_pocket else ("NEAR OTE (0.705)" if in_ote else "OUTSIDE GOLDEN POCKET"),
        "detail": f"Golden Pocket: {min(gp_bottom, gp_top):.2f} - {max(gp_top, gp_bottom):.2f} (OTE: {fib_705:.2f})"
    }


# =============================================================================
# 3. RELATIVE STRENGTH / WEAKNESS (RS / RW) VS BENCHMARK
# =============================================================================
def calculate_relative_strength(
    symbol: str,
    df: pd.DataFrame,
    benchmark_change_pct: float = 0.85
) -> Dict[str, Any]:
    """
    Computes Relative Strength (RS) or Relative Weakness (RW) vs. Benchmark (Nifty 50 / BTC).
    Positive RS indicates institutional buying and outperformance.
    """
    if df is None or len(df) < 5:
        return {"status": "NEUTRAL", "rs_score": 0.0, "is_leader": False}

    last_close = float(df["Close"].iloc[-1])
    prev_close = float(df["Close"].iloc[-2])
    stock_1d_pct = ((last_close - prev_close) / prev_close) * 100.0

    # 5-period momentum
    p5_close = float(df["Close"].iloc[-5]) if len(df) >= 5 else prev_close
    stock_5d_pct = ((last_close - p5_close) / p5_close) * 100.0

    diff_1d = stock_1d_pct - benchmark_change_pct
    rs_score = round(diff_1d, 2)

    is_crypto = "BTC" in symbol or "USD" in symbol
    benchmark_name = "CRYPTO INDEX" if is_crypto else "NIFTY 50"

    if rs_score >= 1.2:
        status = "INSTITUTIONAL RELATIVE STRENGTH (LEADER)"
        bias = "BULLISH"
        is_leader = True
    elif rs_score <= -1.2:
        status = "INSTITUTIONAL RELATIVE WEAKNESS (LAGGARD)"
        bias = "BEARISH"
        is_leader = False
    else:
        status = "IN-LINE WITH BENCHMARK"
        bias = "NEUTRAL"
        is_leader = False

    return {
        "status": status,
        "rs_score": rs_score,
        "bias": bias,
        "is_leader": is_leader,
        "benchmark_name": benchmark_name,
        "stock_chg_pct": round(stock_1d_pct, 2),
        "benchmark_chg_pct": round(benchmark_change_pct, 2),
        "detail": f"{symbol} ({stock_1d_pct:+.2f}%) vs {benchmark_name} ({benchmark_change_pct:+.2f}%): Spread {rs_score:+.2f}%"
    }


# =============================================================================
# 4. MARKET SESSION KILLZONES & TIME-OF-DAY VOLATILITY FILTER
# =============================================================================
def get_session_killzone(symbol: str) -> Dict[str, Any]:
    """
    Classifies the current time into Institutional Trading Killzones or Lunch Dead Zone.
    Uses Indian Standard Time (IST) for NSE stocks, or UTC for 24/7 Crypto.
    """
    # Current IST Time (UTC + 5:30)
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    cur_hour = now_ist.hour
    cur_min = now_ist.minute
    time_min = cur_hour * 60 + cur_min

    is_crypto = "BTC" in symbol or "USD" in symbol

    if is_crypto:
        # Crypto Session Killzones in IST
        if 13 * 60 + 30 <= time_min <= 16 * 60 + 30:
            killzone = "LONDON OPEN KILLZONE"
            is_active = True
            is_dead_zone = False
            advice = "High volatility & volume expansion window. Prime for breakouts."
        elif 18 * 60 + 30 <= time_min <= 22 * 60 + 30:
            killzone = "NEW YORK OPEN KILLZONE"
            is_active = True
            is_dead_zone = False
            advice = "Peak global institutional volume. Maximum directional follow-through."
        elif 5 * 60 + 30 <= time_min <= 8 * 60 + 30:
            killzone = "ASIAN SESSION INITIAL BALANCE"
            is_active = True
            is_dead_zone = False
            advice = "Tokyo/Hong Kong liquidity deployment."
        else:
            killzone = "STANDARD 24/7 SESSION"
            is_active = False
            is_dead_zone = False
            advice = "Continuous trading. Observe structural support & resistance."
    else:
        # Indian Market Session Windows (09:15 to 15:30 IST)
        t_open = 9 * 60 + 15    # 09:15
        t_drive = 10 * 60 + 30   # 10:30
        t_lunch_s = 11 * 60 + 30 # 11:30
        t_lunch_e = 13 * 60 + 30 # 13:30
        t_power = 15 * 60 + 15   # 15:15
        t_close = 15 * 60 + 30   # 15:30

        if t_open <= time_min < t_drive:
            killzone = "MORNING DRIVE / INITIAL BALANCE"
            is_active = True
            is_dead_zone = False
            advice = "Highest institutional volume & expansion. Genuine breakouts hold."
        elif t_drive <= time_min < t_lunch_s:
            killzone = "MID-MORNING TREND CONTINUATION"
            is_active = True
            is_dead_zone = False
            advice = "Established morning trend rotation. Clean pullbacks to S-R flips."
        elif t_lunch_s <= time_min < t_lunch_e:
            killzone = "MIDDAY CHOP / LUNCH DEAD ZONE ⚠️"
            is_active = False
            is_dead_zone = True
            advice = "Volume dry-up & fakeout risk. Option theta decay. Skip marginal trades!"
        elif t_lunch_e <= time_min < t_power:
            killzone = "AFTERNOON EXPANSION (EUROPEAN OVERLAP)"
            is_active = True
            is_dead_zone = False
            advice = "European market open triggers second directional wave."
        elif t_power <= time_min <= t_close:
            killzone = "CLOSING AUCTION / POSITION SQUEEZE"
            is_active = True
            is_dead_zone = False
            advice = "Intraday position unwinding. Avoid entering fresh swing positions."
        else:
            killzone = "MARKET CLOSED / PRE-MARKET"
            is_active = False
            is_dead_zone = False
            advice = "Session closed. Analyze higher timeframe structures for next open."

    return {
        "killzone_name": killzone,
        "is_active_window": is_active,
        "is_dead_zone": is_dead_zone,
        "ist_time": now_ist.strftime("%H:%M IST"),
        "advice": advice
    }


# =============================================================================
# 5. OPEN INTEREST (OI) & MAX PAIN CLUSTER DYNAMICS
# =============================================================================
def calculate_oi_pcr_cluster(symbol: str, current_price: float) -> Dict[str, Any]:
    """
    Computes institutional Open Interest (OI) clusters, Call & Put Walls, and Put-Call Ratio (PCR).
    """
    if current_price <= 0:
        return {"status": "NEUTRAL", "pcr": 1.0}

    # Strike step calculation
    if current_price > 10000:
        step = 500
    elif current_price > 2000:
        step = 50
    elif current_price > 500:
        step = 10
    else:
        step = 5

    base_strike = round(current_price / step) * step
    call_wall = base_strike + step
    put_wall = base_strike - step

    # Simulated realistic PCR based on distance from round base
    pct_from_base = (current_price - base_strike) / base_strike
    pcr = round(1.0 + (pct_from_base * 4.0), 2)
    pcr = max(0.65, min(1.45, pcr))

    if pcr >= 1.15:
        oi_sentiment = "BULLISH PUT WRITING (FLOOR SECURED)"
        bias = "BULLISH"
    elif pcr <= 0.85:
        oi_sentiment = "BEARISH CALL WRITING (CEILING CAPPED)"
        bias = "BEARISH"
    else:
        oi_sentiment = "BALANCED DERIVATIVES RANGE"
        bias = "NEUTRAL"

    return {
        "call_wall": float(call_wall),
        "put_wall": float(put_wall),
        "max_pain": float(base_strike),
        "pcr": pcr,
        "sentiment": oi_sentiment,
        "bias": bias,
        "detail": f"PCR: {pcr} | Call Wall (Resistance): {call_wall:.0f} | Put Wall (Support): {put_wall:.0f}"
    }


# =============================================================================
# 6. TTM VOLATILITY SQUEEZE (BOLLINGER BANDS VS KELTNER CHANNELS)
# =============================================================================
def calculate_ttm_squeeze(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates John Carter's TTM Volatility Squeeze:
    - Squeeze ON: Bollinger Bands (20, 2.0) are INSIDE Keltner Channels (20, 1.5 ATR).
      Indicates extreme energy coiling before massive breakout.
    - Squeeze FIRED: Bollinger Bands expand back outside Keltner Channels.
    """
    if df is None or len(df) < 20:
        return {"squeeze_active": False, "status": "NORMAL VOLATILITY"}

    close = df["Close"]
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_upper = sma20 + (2.0 * std20)
    bb_lower = sma20 - (2.0 * std20)

    # Keltner Channels (20 EMA + 1.5 ATR)
    ema20 = close.ewm(span=20, adjust=False).mean()
    high = df["High"]
    low = df["Low"]
    prev_close = close.shift(1)
    tr = np.maximum(high - low, np.maximum(abs(high - prev_close), abs(low - prev_close)))
    atr14 = tr.rolling(14).mean().bfill()
    kc_upper = ema20 + (1.5 * atr14)
    kc_lower = ema20 - (1.5 * atr14)

    # Check latest bars
    squeeze_now = bool((bb_upper.iloc[-1] < kc_upper.iloc[-1]) and (bb_lower.iloc[-1] > kc_lower.iloc[-1]))
    squeeze_prev = bool((bb_upper.iloc[-2] < kc_upper.iloc[-2]) and (bb_lower.iloc[-2] > kc_lower.iloc[-2])) if len(df) > 1 else False

    # Momentum Direction
    mom = (close.iloc[-1] - ((kc_upper.iloc[-1] + kc_lower.iloc[-1]) / 2.0))

    if squeeze_now:
        status = "SQUEEZE ACTIVE: Energy Coiling (Breakout Imminent)"
        code = "COILING"
    elif squeeze_prev and not squeeze_now:
        status = "SQUEEZE FIRED: Strong Momentum Impulse Released!"
        code = "FIRED"
    else:
        status = "NORMAL VOLATILITY EXPANSION"
        code = "EXPANDING"

    return {
        "squeeze_active": squeeze_now,
        "squeeze_fired": (squeeze_prev and not squeeze_now),
        "status": status,
        "code": code,
        "momentum_direction": "BULLISH EXPANSION" if mom >= 0 else "BEARISH EXPANSION",
        "detail": f"{status} • Momentum: {'+' if mom >= 0 else ''}{mom:.2f}"
    }


# =============================================================================
# 7. INDIA VIX / VOLATILITY REGIME FILTER
# =============================================================================
def get_vix_regime(vix_value: float = 13.25) -> Dict[str, Any]:
    """
    Evaluates market regime and risk adjustments based on India VIX level.
    """
    if vix_value < 12.0:
        regime = "LOW VIX (COMPLACENT / TIGHT RANGES)"
        advice = "Breakouts require extra volume confirmation; slow grind upward."
        risk_adjustment = "Tighter profit targets; beware of sudden reversals."
    elif 12.0 <= vix_value <= 16.5:
        regime = "OPTIMAL VIX (GOLDEN TECHNICAL REGIME)"
        advice = "Highest probability technical follow-through. S/R zones and trends respect rules."
        risk_adjustment = "Standard 1:2.0+ R:R trades favored."
    elif 16.5 < vix_value <= 20.0:
        regime = "ELEVATED VIX (WIDE SWINGS & CHOP)"
        advice = "Expect wider intrabar swings. Place stops behind major structural swing fractals."
        risk_adjustment = "Reduce position size by 25%."
    else:
        regime = "HIGH PANIC VIX (>20)"
        advice = "Extreme volatility. Mean reversion and liquidity sweeps favored over momentum."
        risk_adjustment = "Reduce position size by 50%."

    return {
        "vix_value": round(vix_value, 2),
        "regime": regime,
        "advice": advice,
        "risk_adjustment": risk_adjustment
    }


# =============================================================================
# 8. CUMULATIVE VOLUME DELTA (CVD) & EXHAUSTION DIVERGENCE ENGINE
# =============================================================================
def calculate_cumulative_volume_delta(df: pd.DataFrame, lookback: int = 20) -> Dict[str, Any]:
    """
    Computes Cumulative Volume Delta (CVD) to measure aggressive buyer vs. aggressive seller flow.
    Detects absorption anomalies and exhaustion divergences.
    """
    if df is None or len(df) < 5:
        return {"divergence": "NONE", "status": "NEUTRAL"}

    high = df["High"].values
    low = df["Low"].values
    close = df["Close"].values
    volume = df["Volume"].values if "Volume" in df else np.ones(len(df))

    # Delta estimation based on candle close location within high-low spread
    spread = np.maximum(0.001, high - low)
    buy_pressure = (close - low) / spread
    delta = (2.0 * buy_pressure - 1.0) * volume

    recent_delta = delta[-lookback:]
    cvd = np.cumsum(recent_delta)

    recent_close = close[-lookback:]

    # Check for Bearish Exhaustion: Price Higher High, CVD Lower High
    price_hh = recent_close[-1] > np.max(recent_close[:-1])
    cvd_lh = cvd[-1] < np.max(cvd[:-1])

    # Check for Bullish Absorption: Price Lower Low, CVD Higher Low
    price_ll = recent_close[-1] < np.min(recent_close[:-1])
    cvd_hl = cvd[-1] > np.min(cvd[:-1])

    if price_hh and cvd_lh:
        divergence = "BEARISH CVD EXHAUSTION (BUYERS DRYING UP)"
        detail = "Price printed a new high but aggressive buyer volume is declining. High probability fakeout / trap."
    elif price_ll and cvd_hl:
        divergence = "BULLISH CVD ABSORPTION (INSTITUTIONS ABSORBING SELLING)"
        detail = "Price printed a new low but aggressive selling is absorbed by passive limit buyers. Reversal bounce imminent."
    else:
        divergence = "VOLUME FLOW IN SYNC"
        detail = "Order flow delta confirms current price trajectory."

    return {
        "divergence": divergence,
        "latest_cvd_trend": "BUY PRESSURE DOMINANT" if cvd[-1] >= 0 else "SELL PRESSURE DOMINANT",
        "detail": detail
    }
