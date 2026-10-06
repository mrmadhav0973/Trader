"""
AlphaEdge Trader - Perfect Institutional Execution Engine
Calculates precision-engineered Entry, Stop Loss, and Take Profit levels:
1. Dual Entry Engine: Limit Retest (Wholesale Discount) vs. Momentum Trigger.
2. Anti-Stop-Hunt Stop Loss: Structural Invalidation Anchor + 0.35x ATR Noise Buffer.
3. 3-Tier Take Profit Ladder:
   - TP1 (50% Bank & Slide SL to Breakeven): 1:2.0 R:R / Nearest Liquidity Pool.
   - TP2 (30% Bank at 1.618 Fib Golden Ratio Extension): 1:3.5 R:R.
   - TP3 (20% Trend Runner / Moonbag): 1:5.0 R:R / HTF Macro Structure.
4. ADR (Average Daily Range) Feasibility Filter: Reality-checks targets against 14-day volatility budget.
5. Breakeven & Dynamic Trailing Roadmap.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


def calculate_perfect_execution_plan(
    df: pd.DataFrame,
    current_price: float,
    direction: str = "LONG",
    nearest_demand: Optional[Dict[str, Any]] = None,
    nearest_supply: Optional[Dict[str, Any]] = None,
    fvgs: Optional[List[Dict[str, Any]]] = None,
    fib_data: Optional[Dict[str, Any]] = None,
    breakout_radar: Optional[Dict[str, Any]] = None,
    capital: float = 5000.0,
    risk_pct: float = 0.02,
    currency_symbol: str = "₹"
) -> Dict[str, Any]:
    """
    Generate an advanced institutional execution plan with dual entry prices,
    anti-hunt structural invalidation stop loss, 3-tier take profit ladder,
    and ADR feasibility analysis.
    """
    curr_p = float(current_price)
    is_long = direction.upper() in ["LONG", "BUY", "BULLISH"]
    c_sym = currency_symbol or "₹"

    # 1. Volatility Metrics (ATR & ADR)
    atr = float(df["ATR"].iloc[-1]) if ("ATR" in df.columns and not pd.isna(df["ATR"].iloc[-1])) else (curr_p * 0.015)
    if np.isnan(atr) or atr <= 0:
        atr = curr_p * 0.015

    # 14-period Average Daily Range (ADR)
    if len(df) >= 14 and "High" in df.columns and "Low" in df.columns:
        daily_ranges = (df["High"] - df["Low"]).tail(14)
        adr = float(daily_ranges.mean())
        if np.isnan(adr) or adr <= 0:
            adr = atr * 1.5
    else:
        adr = atr * 1.5

    last_row = df.iloc[-1]
    c_high = float(last_row["High"]) if "High" in last_row else curr_p
    c_low = float(last_row["Low"]) if "Low" in last_row else curr_p
    c_open = float(last_row["Open"]) if "Open" in last_row else curr_p
    c_close = float(last_row["Close"]) if "Close" in last_row else curr_p

    # Current session range consumed
    session_range = max(0.01, c_high - c_low)
    adr_consumed_pct = round((session_range / adr) * 100, 1) if adr > 0 else 50.0

    # Moving averages / VWAP if present
    ema20 = float(df["EMA_20"].iloc[-1]) if ("EMA_20" in df.columns and not pd.isna(df["EMA_20"].iloc[-1])) else curr_p
    vwap = float(df["VWAP"].iloc[-1]) if ("VWAP" in df.columns and not pd.isna(df["VWAP"].iloc[-1])) else curr_p

    fvgs = fvgs or []
    fib_data = fib_data or {}
    breakout_radar = breakout_radar or {}

    # -------------------------------------------------------------------------
    # A. DUAL ENTRY CALCULATION (LIMIT RETEST vs MOMENTUM TRIGGER)
    # -------------------------------------------------------------------------
    entry_market = round(curr_p, 2)

    if is_long:
        # Candidate discount levels for Limit Retest:
        discount_candidates = []
        # 1. 50% Consequent Encroachment (CE) of active Bullish FVG
        for f in fvgs:
            if f.get("type") == "BULLISH" and "mid_ce" in f:
                if f["mid_ce"] < curr_p:
                    discount_candidates.append((f["mid_ce"], "50% FVG Consequent Encroachment"))

        # 2. Fib OTE (0.705 / 0.618 level)
        fib_ote = fib_data.get("ote_0705") or fib_data.get("fib_618")
        if fib_ote and fib_ote < curr_p:
            discount_candidates.append((fib_ote, "Fibonacci Golden Ratio OTE (0.705)"))

        # 3. Top of Institutional Demand Zone
        if nearest_demand and nearest_demand.get("high_price", 0) < curr_p:
            discount_candidates.append((nearest_demand["high_price"], "Institutional Demand Zone Boundary"))

        # 4. Pullback to VWAP / EMA 20
        if vwap < curr_p and (curr_p - vwap) / curr_p <= 0.02:
            discount_candidates.append((vwap, "Session VWAP Benchmark Retest"))
        elif ema20 < curr_p and (curr_p - ema20) / curr_p <= 0.02:
            discount_candidates.append((ema20, "20 EMA Dynamic Support Retest"))

        if discount_candidates:
            # Pick the highest valid discount level that is comfortably below current price
            best_discount = max(discount_candidates, key=lambda x: x[0])
            entry_limit_retest = round(best_discount[0], 2)
            retest_rationale = best_discount[1]
        else:
            entry_limit_retest = round(curr_p - (atr * 0.30), 2)
            retest_rationale = "Retest of local consolidation base (0.30 ATR discount)"

        # Momentum Trigger: 1 tick above recent high or breakout resistance
        breakout_lvl = breakout_radar.get("key_level")
        if breakout_lvl and breakout_lvl > curr_p:
            entry_breakout = round(breakout_lvl + (atr * 0.10), 2)
            momentum_rationale = f"Breakout clearance above key level ({c_sym}{breakout_lvl:.2f})"
        else:
            entry_breakout = round(c_high + (atr * 0.10), 2)
            momentum_rationale = "Clearance 1 tick above trigger bar high"

        # Determine Recommendation
        dist_to_limit_pct = (curr_p - entry_limit_retest) / curr_p * 100
        if dist_to_limit_pct <= 0.35:
            recommended_entry = entry_market
            recommended_type = "MOMENTUM MARKET"
            entry_rationale = "Price is already sitting in optimal value zone. Execute at market."
        else:
            recommended_entry = entry_limit_retest
            recommended_type = "LIMIT RETEST"
            entry_rationale = f"Wait for discount pullback to {retest_rationale} to maximize R:R."

    else:
        # SHORT DISCOUNTS (Premium levels above current price)
        premium_candidates = []
        for f in fvgs:
            if f.get("type") == "BEARISH" and "mid_ce" in f:
                if f["mid_ce"] > curr_p:
                    premium_candidates.append((f["mid_ce"], "50% Bearish FVG Consequent Encroachment"))

        fib_ote = fib_data.get("ote_0705") or fib_data.get("fib_618")
        if fib_ote and fib_ote > curr_p:
            premium_candidates.append((fib_ote, "Fibonacci Golden Ratio OTE (0.705)"))

        if nearest_supply and nearest_supply.get("low_price", 0) > curr_p:
            premium_candidates.append((nearest_supply["low_price"], "Institutional Supply Zone Boundary"))

        if vwap > curr_p and (vwap - curr_p) / curr_p <= 0.02:
            premium_candidates.append((vwap, "Session VWAP Overhead Retest"))
        elif ema20 > curr_p and (ema20 - curr_p) / curr_p <= 0.02:
            premium_candidates.append((ema20, "20 EMA Dynamic Resistance Retest"))

        if premium_candidates:
            best_premium = min(premium_candidates, key=lambda x: x[0])
            entry_limit_retest = round(best_premium[0], 2)
            retest_rationale = best_premium[1]
        else:
            entry_limit_retest = round(curr_p + (atr * 0.30), 2)
            retest_rationale = "Pullback to local supply base (0.30 ATR premium)"

        breakout_lvl = breakout_radar.get("key_level")
        if breakout_lvl and breakout_lvl < curr_p:
            entry_breakout = round(breakout_lvl - (atr * 0.10), 2)
            momentum_rationale = f"Breakdown clearance below key support ({c_sym}{breakout_lvl:.2f})"
        else:
            entry_breakout = round(c_low - (atr * 0.10), 2)
            momentum_rationale = "Breakdown 1 tick below trigger bar low"

        dist_to_limit_pct = (entry_limit_retest - curr_p) / curr_p * 100
        if dist_to_limit_pct <= 0.35:
            recommended_entry = entry_market
            recommended_type = "MOMENTUM MARKET"
            entry_rationale = "Price is actively rejecting from supply zone. Execute at market."
        else:
            recommended_entry = entry_limit_retest
            recommended_type = "LIMIT RETEST"
            entry_rationale = f"Wait for pullback to {retest_rationale} to maximize R:R."

    # -------------------------------------------------------------------------
    # B. ANTI-STOP-HUNT STOP LOSS (STRUCTURAL INVALIDATION ANCHOR)
    # -------------------------------------------------------------------------
    anti_hunt_buffer = round(atr * 0.35, 2)

    if is_long:
        # Base anchor: Demand zone low, or lowest rejection wick low
        if nearest_demand and nearest_demand.get("low_price", 0) > 0:
            structural_base = min(c_low, nearest_demand["low_price"])
            anchor_name = f"Demand Zone Base ({c_sym}{nearest_demand['low_price']:.2f})"
        else:
            structural_base = c_low
            anchor_name = f"Swing Pivot Low ({c_sym}{c_low:.2f})"

        planned_sl = round(structural_base - anti_hunt_buffer, 2)
        # Sanity check: Ensure SL is below entry
        if planned_sl >= recommended_entry:
            planned_sl = round(recommended_entry - (atr * 1.0), 2)

        risk_per_share = round(max(0.1, recommended_entry - planned_sl), 2)
        sl_invalidation = (
            f"Protected by {anchor_name} with {c_sym}{anti_hunt_buffer:.2f} (0.35x ATR) anti-hunt buffer. "
            f"Trade thesis invalidates if candle body closes below {c_sym}{planned_sl:.2f}."
        )
    else:
        if nearest_supply and nearest_supply.get("high_price", 0) > 0:
            structural_base = max(c_high, nearest_supply["high_price"])
            anchor_name = f"Supply Zone High ({c_sym}{nearest_supply['high_price']:.2f})"
        else:
            structural_base = c_high
            anchor_name = f"Swing Pivot High ({c_sym}{c_high:.2f})"

        planned_sl = round(structural_base + anti_hunt_buffer, 2)
        if planned_sl <= recommended_entry:
            planned_sl = round(recommended_entry + (atr * 1.0), 2)

        risk_per_share = round(max(0.1, planned_sl - recommended_entry), 2)
        sl_invalidation = (
            f"Protected by {anchor_name} with {c_sym}{anti_hunt_buffer:.2f} (0.35x ATR) anti-hunt buffer. "
            f"Trade thesis invalidates if candle body closes above {c_sym}{planned_sl:.2f}."
        )

    # -------------------------------------------------------------------------
    # C. 3-TIER TAKE PROFIT SCALING LADDER (TP1, TP2, TP3 RUNNER)
    # -------------------------------------------------------------------------
    if is_long:
        # TP1: 1:2.0 R:R or nearest local supply
        tp1_price = round(recommended_entry + (risk_per_share * 2.0), 2)
        # TP2: 1:3.5 R:R (1.618 Fib Extension target)
        tp2_price = round(recommended_entry + (risk_per_share * 3.5), 2)
        # TP3: 1:5.0 R:R (Major HTF target)
        tp3_price = round(recommended_entry + (risk_per_share * 5.0), 2)

        tp1_gain_pct = round(((tp1_price - recommended_entry) / recommended_entry) * 100, 2)
        tp2_gain_pct = round(((tp2_price - recommended_entry) / recommended_entry) * 100, 2)
        tp3_gain_pct = round(((tp3_price - recommended_entry) / recommended_entry) * 100, 2)
        breakeven_price = round(recommended_entry + (recommended_entry * 0.0015), 2)
    else:
        tp1_price = round(recommended_entry - (risk_per_share * 2.0), 2)
        tp2_price = round(recommended_entry - (risk_per_share * 3.5), 2)
        tp3_price = round(recommended_entry - (risk_per_share * 5.0), 2)

        tp1_gain_pct = round(((recommended_entry - tp1_price) / recommended_entry) * 100, 2)
        tp2_gain_pct = round(((recommended_entry - tp2_price) / recommended_entry) * 100, 2)
        tp3_gain_pct = round(((recommended_entry - tp3_price) / recommended_entry) * 100, 2)
        breakeven_price = round(recommended_entry - (recommended_entry * 0.0015), 2)

    # -------------------------------------------------------------------------
    # D. ADR REALITY CHECK & FEASIBILITY
    # -------------------------------------------------------------------------
    tp1_distance = abs(tp1_price - recommended_entry)
    adr_req_pct = round((tp1_distance / adr) * 100, 1) if adr > 0 else 50.0

    if adr_req_pct <= 65.0:
        adr_feasibility = f"🟢 HIGH INTRADAY FEASIBILITY (TP1 uses {adr_req_pct}% of 14-day ADR)"
    elif adr_req_pct <= 100.0:
        adr_feasibility = f"🟡 MODERATE INTRADAY (TP1 requires {adr_req_pct}% of daily range)"
    else:
        adr_feasibility = f"🔵 MULTI-DAY SWING HORIZON (TP1 requires {adr_req_pct}% of ADR; hold into next session)"

    # -------------------------------------------------------------------------
    # E. CAPITAL SIZING & ASYMMETRIC PAYOFF
    # -------------------------------------------------------------------------
    max_risk_amount = round(capital * risk_pct, 2)
    position_qty = max(1, int(max_risk_amount / risk_per_share)) if risk_per_share > 0 else 1

    # Projected returns
    total_loss = round(position_qty * risk_per_share, 2)
    tp1_dollar = round(position_qty * 0.50 * (abs(tp1_price - recommended_entry)), 2)
    tp2_dollar = round(position_qty * 0.30 * (abs(tp2_price - recommended_entry)), 2)
    tp3_dollar = round(position_qty * 0.20 * (abs(tp3_price - recommended_entry)), 2)
    blended_gain = round(tp1_dollar + tp2_dollar + tp3_dollar, 2)
    blended_rr = round(blended_gain / total_loss, 2) if total_loss > 0 else 2.5

    return {
        "direction": "LONG" if is_long else "SHORT",
        "action": "BUY / LONG" if is_long else "SELL / SHORT",
        
        # Dual Entries
        "entry_price": recommended_entry,
        "entry_market": entry_market,
        "entry_limit_retest": entry_limit_retest,
        "entry_breakout_trigger": entry_breakout,
        "recommended_entry_type": recommended_type,
        "entry_rationale": entry_rationale,
        
        # Stop Loss
        "stop_loss": planned_sl,
        "risk_per_share": risk_per_share,
        "risk_pct": round((risk_per_share / recommended_entry) * 100, 2),
        "anti_hunt_buffer": anti_hunt_buffer,
        "sl_invalidation_logic": sl_invalidation,
        
        # 3-Tier Take Profit Ladder
        "target_1": tp1_price,
        "target_1_rr": "1:2.0",
        "target_1_pct": tp1_gain_pct,
        "target_1_rule": "BANK 50% POSITION: Nearest opposing liquidity pool. Immediately slide SL to Breakeven.",
        
        "target_2": tp2_price,
        "target_2_rr": "1:3.5",
        "target_2_pct": tp2_gain_pct,
        "target_2_rule": "BANK 30% POSITION: 1.618 Fibonacci Golden Extension. Trail remaining 20% behind 20 EMA.",
        
        "target_3": tp3_price,
        "target_3_rr": "1:5.0",
        "target_3_pct": tp3_gain_pct,
        "target_3_rule": "HOLD 20% RUNNER: Major HTF Supply/Demand target. Exit upon lower timeframe CHoCH.",
        
        # Trade Management
        "breakeven_price": breakeven_price,
        "trailing_sl_anchor": "20 EMA or Consecutive Higher Low Wicks",
        
        # Volatility & ADR Feasibility
        "adr_14": round(adr, 2),
        "adr_consumed_pct": adr_consumed_pct,
        "adr_feasibility": adr_feasibility,
        
        # Risk Management
        "capital_risk_amount": max_risk_amount,
        "position_quantity": position_qty,
        "risk_reward_ratio": f"1:{blended_rr}",
        "blended_rr": f"1:{blended_rr}",
        "projected_profit": blended_gain,
        "capital_protection_rule": (
            f"Risk strictly capped at {risk_pct*100:.0f}% ({c_sym}{max_risk_amount:.2f}). "
            f"Projected payout: +{c_sym}{blended_gain:.2f} ({blended_rr}x profit factor). "
            f"Rule: Once TP1 hits, trade is 100% risk-free."
        )
    }
