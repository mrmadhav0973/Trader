"""
Scalping Mastery Engine - High-Frequency Institutional Micro-Trading Module
Evaluates sub-minute and intraday micro-structure (1m, 3m, 5m, 15m) using
Session VWAP, 9/21 EMA ribbons, order flow velocity, tape pressure, and tight invalidations.
"""

from typing import Any
import pandas as pd


def analyze_scalp_setup(
    df: pd.DataFrame,
    candlestick_patterns: list[dict[str, Any]],
    sweeps: list[dict[str, Any]],
    fvgs: list[dict[str, Any]],
    capital: float = 5000.0,
    risk_pct: float = 0.015
) -> dict[str, Any]:
    """
    Perform deep institutional scalping analysis on micro-timeframe data.
    Returns scalping archetype, tape order flow pressure, tight risk blueprint, and scratch rules.
    """
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = float(last["Close"])
    vwap = float(last.get("VWAP", price))
    vwap_up = float(last.get("VWAP_Upper", vwap * 1.005))
    vwap_low = float(last.get("VWAP_Lower", vwap * 0.995))
    ema9 = float(last.get("EMA_9", price))
    ema21 = float(last.get("EMA_21", price))
    rsi7 = float(last.get("RSI_7", 50.0))
    micro_atr = float(last.get("Micro_ATR", price * 0.003))
    vol_vel = float(last.get("Volume_Velocity", 1.0))
    buy_pct = float(last.get("Buy_Pressure_Pct", 50.0))
    curr_sym = df.attrs.get("currency_symbol", "₹") if hasattr(df, "attrs") else "₹"

    has_pin = any("Pin Bar" in p["name"] or "Hammer" in p["name"] for p in candlestick_patterns)
    has_engulf = any("Engulfing" in p["name"] for p in candlestick_patterns)
    has_sweep = len(sweeps) > 0

    scalp_score = 40
    factors = []
    archetype = "Micro Range Scalp (Standard Execution)"
    bias = "WATCH"

    # 1. Check Archetype 1: VWAP Bounce / Reclaim
    dist_to_vwap_pct = abs(price - vwap) / vwap
    if dist_to_vwap_pct <= 0.0025 and (price >= vwap or has_pin):
        archetype = "VWAP Dynamic Reclaim & Bounce"
        scalp_score += 25
        factors.append("Price testing & holding institutional Session VWAP")
        bias = "LONG SCALP"
    elif price > vwap and ema9 > ema21:
        # Archetype 2: 9/21 EMA Momentum Burst
        archetype = "9/21 EMA Micro-Trend Momentum Surge"
        scalp_score += 25
        factors.append("9 EMA leading 21 EMA in clean expansion")
        bias = "LONG SCALP"
    elif has_sweep:
        # Archetype 3: Session Liquidity Grab
        archetype = "Micro Liquidity Sweep & Spring"
        scalp_score += 25
        factors.append("Recent swing low swept for retail stops")
        bias = "LONG SCALP"
    elif price <= vwap_low and rsi7 <= 25:
        # Archetype 4: Mean Reversion Exhaustion Fade
        archetype = "Lower VWAP Band Mean Reversion Snap"
        scalp_score += 25
        factors.append("Oversold exhaustion touching -1.5 StdDev VWAP band")
        bias = "LONG SCALP"

    # 2. Tape Velocity & Delta Pressure Evaluation
    if buy_pct >= 65.0:
        scalp_score += 15
        factors.append(f"Strong Buyer Dominance ({buy_pct:.0f}% Buy Delta)")
    elif buy_pct <= 35.0:
        scalp_score -= 10
        factors.append(f"Seller Pressure Dominant ({100 - buy_pct:.0f}% Sell Delta)")

    if vol_vel >= 1.5:
        scalp_score += 15
        factors.append(f"High Volume Velocity ({vol_vel:.1f}x surge)")

    if has_pin or has_engulf:
        scalp_score += 10
        factors.append("Decisive rejection candle printed on micro timeframe")

    # Score Clamping & Grade
    scalp_score = min(98, max(15, scalp_score))
    if scalp_score >= 75:
        scalp_grade = "A+ Scalp"
        if bias == "WATCH": bias = "LONG SCALP"
    elif scalp_score >= 55:
        scalp_grade = "B Scalp"
        if bias == "WATCH": bias = "LONG SCALP"
    else:
        scalp_grade = "Standby"
        bias = "CHOPPY / NO TRADE"

    # 3. Micro-Stop Loss & Execution Blueprint
    # For scalping, risk is strictly micro-capped (0.2% to 0.7%)
    trigger_low = float(last["Low"])
    risk_distance = max(micro_atr * 0.8, price * 0.0025)
    scalp_sl = round(min(trigger_low - (0.2 * micro_atr), price - risk_distance), 2)
    if scalp_sl >= price or (price - scalp_sl) > (price * 0.008):
        scalp_sl = round(price * 0.995, 2)  # Strict 0.5% max scalp risk

    actual_risk_per_unit = max(0.01, price - scalp_sl)
    scalp_t1 = round(price + (1.5 * actual_risk_per_unit), 2)
    scalp_t2 = round(price + (2.5 * actual_risk_per_unit), 2)

    risk_pct_val = (actual_risk_per_unit / price) * 100
    t1_pct_val = ((scalp_t1 - price) / price) * 100

    # Share sizing for scalping
    max_scalp_risk = capital * risk_pct
    scalp_shares = max(1, int(max_scalp_risk / actual_risk_per_unit)) if actual_risk_per_unit > 0 else 1

    # Scalper Protocol
    min_entry = round(price * 0.999, 2)
    max_entry = round(price * 1.001, 2)

    return {
        "scalp_bias": bias,
        "scalp_grade": scalp_grade,
        "scalp_score": scalp_score,
        "archetype": archetype,
        "factors": factors,
        "order_flow": {
            "buy_pressure_pct": buy_pct,
            "sell_pressure_pct": round(100.0 - buy_pct, 1),
            "volume_velocity": vol_vel,
            "velocity_label": "SURGING 🔥" if vol_vel >= 1.5 else ("ACTIVE" if vol_vel >= 1.0 else "DRYING UP 💤")
        },
        "blueprint": {
            "entry": round(price, 2),
            "entry_range": f"{curr_sym}{min_entry} – {curr_sym}{max_entry}",
            "stop_loss": scalp_sl,
            "target_1": scalp_t1,
            "target_2": scalp_t2,
            "risk_pct": round(risk_pct_val, 2),
            "target_1_pct": round(t1_pct_val, 2),
            "risk_reward": "1:1.5",
            "quantity": scalp_shares,
            "currency_symbol": curr_sym
        },
        "vwap_benchmark": {
            "vwap": round(vwap, 2),
            "upper_band": round(vwap_up, 2),
            "lower_band": round(vwap_low, 2),
            "dist_pct": round(dist_to_vwap_pct * 100, 2),
            "position": "Above VWAP (Bullish Bias)" if price >= vwap else "Below VWAP (Discount Bias)"
        },
        "time_horizon": "Expected hold: 3 to 15 minutes",
        "scratch_rule": "Strict Invalidation: If price fails to push into green within 4 candles, exit immediately at breakeven. Never turn a fast scalp into a lingering hope trade."
    }
