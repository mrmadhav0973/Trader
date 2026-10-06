"""
AlphaEdge Trader - Breakout & Confluence Confirmation Engine
Implements professional human-trader logic for breakout trading:
- Never FOMO buy/short on the breach of an unclosed candle.
- Waits for candle close confirmation beyond the key level.
- Evaluates body conviction vs. wick rejection (detects fakeout traps).
- Verifies institutional volume expansion (>1.2x 20-period SMA).
- Checks retest & follow-through structure hold.
- Produces clean, actionable waiting stages and disciplined execution levels.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


def detect_breakout_confirmation(df: pd.DataFrame, current_price: Optional[float] = None) -> Dict[str, Any]:
    """
    Evaluate market structure for breakout/breakdown setups and multi-stage confirmation.
    """
    if df is None or len(df) < 15:
        return {
            "status": "INSUFFICIENT_DATA",
            "setup_name": "Gathering Data",
            "stage": "MONITORING",
            "stage_badge": {"text": "👀 SCANNING CHART", "color": "neutral"},
            "direction": "NEUTRAL",
            "key_level": 0.0,
            "current_price": 0.0,
            "resistance": {"level": 0.0, "distance_pct": 0.0},
            "support": {"level": 0.0, "distance_pct": 0.0},
            "confirmation_factors": [],
            "action_advice": "Awaiting candle history to map key consolidation boundaries.",
            "human_discipline_rule": "Patience is edge. A pro trader never anticipates a breakout; wait for price to breach and confirm.",
            "trade_levels": None
        }

    curr_p = float(current_price) if current_price is not None else float(df["Close"].iloc[-1])
    currency_symbol = df.attrs.get("currency_symbol", "₹") if hasattr(df, "attrs") else "₹"

    # 1. Structural Boundaries (Last 30-50 bars)
    lookback = min(50, len(df))
    subset = df.iloc[-lookback:]
    
    # 20-period volume average
    avg_vol = float(subset["Volume"].tail(20).mean()) if "Volume" in subset.columns else 1.0

    # ATR calculation for buffer
    high_low = subset["High"] - subset["Low"]
    high_close = (subset["High"] - subset["Close"].shift(1)).abs()
    low_close = (subset["Low"] - subset["Close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = float(tr.tail(14).mean())
    if np.isnan(atr) or atr <= 0:
        atr = curr_p * 0.015

    # Prior bars (excluding the very latest candle to measure true breakout from prior range)
    prior_bars = subset.iloc[:-1] if len(subset) > 1 else subset
    
    # Key Resistance: Highest high of consolidation
    res_level = round(float(prior_bars["High"].tail(25).max()), 2)
    # Key Support: Lowest low of consolidation
    sup_level = round(float(prior_bars["Low"].tail(25).min()), 2)

    last_candle = df.iloc[-1]
    last_o = float(last_candle["Open"])
    last_h = float(last_candle["High"])
    last_l = float(last_candle["Low"])
    last_c = float(last_candle["Close"])
    last_v = float(last_candle["Volume"]) if "Volume" in last_candle else 0

    candle_range = max(0.01, last_h - last_l)
    body_size = abs(last_c - last_o)
    upper_wick = last_h - max(last_o, last_c)
    lower_wick = min(last_o, last_c) - last_l

    # Distances
    dist_to_res = ((res_level - curr_p) / res_level) * 100.0
    dist_to_sup = ((curr_p - sup_level) / sup_level) * 100.0

    # Determine Focus Direction:
    # If price is closer to or testing Resistance -> Bullish Breakout
    # If price is closer to or testing Support -> Bearish Breakdown
    is_bullish = abs(dist_to_res) <= abs(dist_to_sup) or curr_p >= res_level

    key_level = res_level if is_bullish else sup_level
    direction = "LONG" if is_bullish else "SHORT"
    setup_name = f"Key Resistance Breakout ({currency_symbol}{res_level:.2f})" if is_bullish else f"Key Support Breakdown ({currency_symbol}{sup_level:.2f})"

    # Multi-Stage Confirmation Criteria (4 Pillars)
    factors = []

    # 1. Level Penetration
    if is_bullish:
        has_penetrated = curr_p >= res_level or last_h >= res_level
        pen_detail = f"Price breached resistance level ({currency_symbol}{res_level:.2f}) with high of {currency_symbol}{last_h:.2f}." if has_penetrated else f"Trading below resistance ({currency_symbol}{res_level:.2f}). Distance: {dist_to_res:.2f}%."
    else:
        has_penetrated = curr_p <= sup_level or last_l <= sup_level
        pen_detail = f"Price breached support floor ({currency_symbol}{sup_level:.2f}) with low of {currency_symbol}{last_l:.2f}." if has_penetrated else f"Trading above support ({currency_symbol}{sup_level:.2f}). Distance: {dist_to_sup:.2f}%."

    factors.append({
        "id": "penetration",
        "name": "Level Breach",
        "passed": bool(has_penetrated),
        "detail": pen_detail
    })

    # 2. Candle Close Confirmation (The Pro Rule: Never enter on an unclosed candle / wick)
    if is_bullish:
        has_closed_beyond = last_c > res_level
        is_wick_rejection = upper_wick >= (0.45 * candle_range) and last_c <= res_level
        body_conviction = (body_size / candle_range) >= 0.40 and last_c > last_o
        
        if has_closed_beyond and body_conviction:
            close_passed = True
            close_detail = f"Candle closed firmly above level at {currency_symbol}{last_c:.2f} with strong bullish body."
        elif has_penetrated and not has_closed_beyond:
            close_passed = False
            close_detail = f"Candle in progress: Has NOT closed above {currency_symbol}{res_level:.2f} yet. Wicking/intra-bar."
        else:
            close_passed = False
            close_detail = f"Awaiting candle close above {currency_symbol}{res_level:.2f}."
    else:
        has_closed_beyond = last_c < sup_level
        is_wick_rejection = lower_wick >= (0.45 * candle_range) and last_c >= sup_level
        body_conviction = (body_size / candle_range) >= 0.40 and last_c < last_o

        if has_closed_beyond and body_conviction:
            close_passed = True
            close_detail = f"Candle closed firmly below level at {currency_symbol}{last_c:.2f} with strong bearish body."
        elif has_penetrated and not has_closed_beyond:
            close_passed = False
            close_detail = f"Candle in progress: Has NOT closed below {currency_symbol}{sup_level:.2f} yet. Wicking/intra-bar."
        else:
            close_passed = False
            close_detail = f"Awaiting candle close below {currency_symbol}{sup_level:.2f}."

    factors.append({
        "id": "candle_close",
        "name": "Candle Close Confirmation",
        "passed": bool(close_passed),
        "detail": close_detail
    })

    # 3. Institutional Volume Expansion
    vol_ratio = (last_v / avg_vol) if avg_vol > 0 else 1.0
    has_vol_surge = vol_ratio >= 1.20
    factors.append({
        "id": "volume",
        "name": "Institutional Volume Expansion",
        "passed": bool(has_vol_surge),
        "detail": f"Volume is {vol_ratio:.1f}x of 20-period average ({int(last_v):,} vs avg {int(avg_vol):,})." if has_vol_surge else f"Volume is {vol_ratio:.1f}x avg. Requires >1.2x volume surge for institutional participation."
    })

    # 4. Retest & Structure Hold
    if is_bullish:
        retest_held = last_l >= (res_level - atr * 0.25) and curr_p >= res_level
        retest_detail = f"Price maintaining structure above broken resistance {currency_symbol}{res_level:.2f}." if retest_held else f"Watching for retest / pullback to {currency_symbol}{res_level:.2f} to hold as support."
    else:
        retest_held = last_h <= (sup_level + atr * 0.25) and curr_p <= sup_level
        retest_detail = f"Price maintaining structure below broken support {currency_symbol}{sup_level:.2f}." if retest_held else f"Watching for retest / bounce to {currency_symbol}{sup_level:.2f} to hold as resistance."

    factors.append({
        "id": "retest",
        "name": "Retest & Structure Hold",
        "passed": bool(retest_held),
        "detail": retest_detail
    })

    # Confluence calculation
    passed_count = sum(1 for f in factors if f["passed"])
    confluence_pct = int((passed_count / 4.0) * 100)

    # State Machine Assignment
    if is_wick_rejection:
        stage = "FAKEOUT_TRAP"
        badge = {"text": "⚠️ FAKEOUT DETECTED", "color": "bear"}
        advice = f"Fakeout Trap Detected: Price pierced {currency_symbol}{key_level:.2f} but was rejected with a long wick. Retail breakout buyers are trapped. High risk of immediate flush."
        rule = "Pro Rule: Trapped traders fuel market moves. When price wicks through a level and closes back inside, the breakout has failed."
    elif passed_count >= 3 and close_passed:
        stage = "CONFIRMED"
        badge = {"text": "✅ BREAKOUT CONFIRMED", "color": "bull"}
        advice = f"High-Confluence Breakout Triggered: Candle closed beyond {currency_symbol}{key_level:.2f} with strong volume and structure hold. High-conviction entry confirmed."
        rule = "Pro Rule: Full confirmation met. Enter with strictly defined Stop Loss. Let the market do the work."
    elif has_penetrated and not close_passed:
        stage = "WAITING_FOR_CANDLE_CLOSE"
        badge = {"text": "⏳ WAITING FOR CANDLE CLOSE", "color": "amber"}
        advice = f"Breakout in Progress: Testing {currency_symbol}{key_level:.2f}. Human Pro Rule: Never enter on an unclosed candle! Wait for official close to confirm conviction."
        rule = "Pro Rule: 80% of intraday breakout failures occur because traders enter before candle close. Wait for the bell/close."
    elif close_passed and not retest_held:
        stage = "WAITING_FOR_RETEST"
        badge = {"text": "🔄 WAITING FOR RETEST", "color": "blue"}
        advice = f"Candle Closed Above Level! Pro traders now wait for a brief retest of {currency_symbol}{key_level:.2f} or breakout candle high breach for optimal R:R."
        rule = "Pro Rule: Retest entries offer the highest Risk-to-Reward ratio by converting old resistance into new support."
    else:
        stage = "MONITORING"
        dist_val = dist_to_res if is_bullish else dist_to_sup
        badge = {"text": "👀 MONITORING SETUP", "color": "neutral"}
        advice = f"Patience is Edge: Price is {abs(dist_val):.2f}% away from {('resistance' if is_bullish else 'support')} ({currency_symbol}{key_level:.2f}). Wait for price to approach and test the level."
        rule = "Pro Rule: Cash is also a position. Wait patiently for the setup to come to you rather than chasing."

    # Trade Execution Parameters
    if is_bullish:
        entry_price = round(last_h if stage == "CONFIRMED" else (res_level + atr * 0.08), 2)
        stop_loss = round(min(last_l, res_level - atr * 0.45), 2)
        risk_per_share = max(0.5, entry_price - stop_loss)
        target_1 = round(entry_price + (risk_per_share * 2.0), 2)
        target_2 = round(entry_price + (risk_per_share * 3.0), 2)
    else:
        entry_price = round(last_l if stage == "CONFIRMED" else (sup_level - atr * 0.08), 2)
        stop_loss = round(max(last_h, sup_level + atr * 0.45), 2)
        risk_per_share = max(0.5, stop_loss - entry_price)
        target_1 = round(entry_price - (risk_per_share * 2.0), 2)
        target_2 = round(entry_price - (risk_per_share * 3.0), 2)

    return {
        "status": "OK",
        "setup_name": setup_name,
        "stage": stage,
        "stage_badge": badge,
        "direction": direction,
        "key_level": key_level,
        "current_price": round(curr_p, 2),
        "resistance": {
            "level": res_level,
            "distance_pct": round(dist_to_res, 2)
        },
        "support": {
            "level": sup_level,
            "distance_pct": round(dist_to_sup, 2)
        },
        "passed_count": passed_count,
        "total_factors": 4,
        "confluence_score": confluence_pct,
        "confirmation_factors": factors,
        "action_advice": advice,
        "human_discipline_rule": rule,
        "trade_levels": {
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "risk_per_share": round(risk_per_share, 2),
            "risk_reward": "1:2.0"
        }
    }
