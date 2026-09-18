"""
Confluence Signal Generation Module - 20-Year Veteran Trader Engine
Evaluates market regime, candlestick anatomy, volume spread analysis (VSA),
divergences, trapped traders, and SMC to produce veteran-grade tape reading and trade blueprints.
"""

from typing import Any
import pandas as pd

from .indicators import add_all_indicators, detect_rsi_divergences
from .patterns import (
    detect_swing_points,
    calculate_algorithmic_trendlines,
    cluster_support_resistance_zones,
    analyze_candlestick_anatomy,
    analyze_market_structure
)
from .smc import detect_fair_value_gaps, detect_liquidity_sweeps
from .risk import calculate_position_sizing


def generate_veteran_commentary(
    symbol: str,
    price: float,
    market_structure: dict[str, Any],
    candlestick_patterns: list[dict[str, Any]],
    divergence: dict[str, Any],
    vsa: dict[str, Any],
    sweeps: list[dict[str, Any]],
    fvgs: list[dict[str, Any]],
    confluence_score: int,
    signal_type: str,
    risk_plan: dict[str, Any],
    currency_symbol: str = "₹"
) -> dict[str, Any]:
    """
    Synthesize all technical layers into the voice and analysis of a senior trader
    with 20+ years of active market experience across all trading styles (Scalp, Swing, Position, Wyckoff, SMC).
    """
    curr_sym = currency_symbol
    regime = market_structure["regime"]
    bias = market_structure["bias"]

    # 1. Multi-Style Perspective & Archetype Matching
    has_sweep = len(sweeps) > 0
    has_pin_bar = any("Pin Bar" in p["name"] or "Hammer" in p["name"] for p in candlestick_patterns)
    has_engulfing = any("Engulfing" in p["name"] for p in candlestick_patterns)
    is_squeeze = vsa.get("is_squeeze", False)

    if has_sweep and has_pin_bar:
        archetype = "Institutional Liquidity Grab & Spring (Wyckoff Shakeout)"
        trapped_traders = "Retail breakout sellers who shorted the breakdown are trapped. When price reclaimed the demand level, their buy-stop orders became rocket fuel for our long entry."
        wisdom = "In my 20+ years trading these markets, the cleanest moves always happen right after retail gets aggressively trapped on a fake breakdown. Never short into strong demand when the wick rejects it."
    elif "STAGE 2" in regime and has_engulfing:
        archetype = "High-Tight Momentum Expansion"
        trapped_traders = "Sellers fighting the trend are getting run over. Momentum buyers and institutional algos are in complete control of the order book."
        wisdom = "Over 20+ years of tape reading, I've learned that a Stage 2 markup with expanding volume is where accounts are made. Don't overthink it or try to call tops—ride the 20 EMA train until proven wrong."
    elif is_squeeze:
        archetype = "Volatility Contraction Pattern (VCP Coiling)"
        trapped_traders = "Floating supply has completely dried up. Both bulls and bears are coiled in tight range, anticipating an aggressive directional expansion."
        wisdom = "Volatility always cycles from low volatility to high volatility. When Bollinger bandwidth compresses to multi-month lows, the ensuing breakout is explosive. Be positioned before the herd notices."
    elif "STAGE 4" in regime:
        archetype = "Bearish Markdown Exhaustion / Counter-Trend Trap"
        trapped_traders = "Underwater dip-buyers holding heavy bags from higher levels. Every counter-trend bounce faces a wall of overhead retail supply eager to break even."
        wisdom = "The number one account killer I've witnessed over two decades is trying to catch falling knives in Stage 4 distributions. The market doesn't care how 'cheap' a stock looks. Capital preservation is your supreme duty."
    else:
        archetype = "Mean Reversion Value Play at Key Structural Pivot"
        trapped_traders = "Choppy sideways balance; liquidity pools rest cleanly above the swing highs and below the swing lows."
        wisdom = "When the market lacks a trending edge, amateur traders churn their accounts to zero on fees and false starts. A seasoned trader knows that cash is a legitimate, high-yielding position."

    # 2. Multi-Style Operational Perspectives
    multi_style = {
        "scalper_view": (
            f"Immediate tape action: Price is hovering at {curr_sym}{price:.2f}. "
            f"{'Wick rejection confirmed buyers are stepping in on low timeframe pullbacks.' if has_pin_bar else 'Order book spread is balanced; wait for an intraday volume burst.'}"
        ),
        "swing_trader_view": (
            f"Multi-day swing setup: Confluence rating is {confluence_score}%. "
            f"{'Optimal risk-to-reward window with clear structural invalidation.' if confluence_score >= 60 else 'Insufficient multi-day momentum; risk of choppy sideways decay.'}"
        ),
        "position_trader_view": (
            f"Macro stage context: Stock is classified in **{regime}**. "
            f"{'Long-term accumulation/markup base intact.' if 'STAGE 2' in regime or 'STAGE 1' in regime else 'Macro trend remains unfavorable for multi-month holding.'}"
        )
    }

    # 3. Tape Reading Synthesized Notes
    notes = []
    notes.append(f"• **Market Cycle Context:** Currently operating in a **{regime}** ({bias}).")

    if candlestick_patterns:
        latest_pattern = candlestick_patterns[-1]
        notes.append(f"• **Candle Anatomy & Order Flow:** {latest_pattern['name']} detected — {latest_pattern['detail']}")
    else:
        notes.append("• **Candle Anatomy:** Balanced bar ranges without extreme wick rejection; price respecting institutional moving averages.")

    if divergence["bullish_divergence"]:
        notes.append(f"• **Momentum Divergence:** ⚡ {divergence['detail']} — internal selling momentum is decaying while price holds support.")
    elif divergence["bearish_divergence"]:
        notes.append(f"• **Momentum Divergence:** ⚠️ {divergence['detail']} — buyers failing to push fresh momentum into highs.")

    if vsa.get("absorption"):
        notes.append("• **Tape Reading (VSA):** High turnover with narrow price spread indicates **institutional absorption** of floating supply.")
    elif vsa.get("dry_up"):
        notes.append("• **Tape Reading (VSA):** Low volume pullback confirms that sellers lack aggressive inventory to push price lower.")

    if has_sweep:
        last_sweep = sweeps[-1]
        notes.append(f"• **Smart Money Footprint:** {last_sweep['description']}. Retail stops were hunted.")

    # 4. Strict Professional Trade Management Protocol
    if "BUY" in signal_type:
        entry_p = risk_plan['entry_price']
        min_entry = entry_p * 0.998
        max_entry = entry_p * 1.002
        management = (
            f"**Execution Blueprint:** Enter within the defined range `{curr_sym}{min_entry:.2f} – {curr_sym}{max_entry:.2f}`. "
            f"Hard Stop Loss strictly at `{curr_sym}{risk_plan['stop_loss']:.2f}` (if price closes below this, the technical premise is dead—exit immediately with zero hesitation). "
            f"**Take 50% profit off the table at Target 1 (`{curr_sym}{risk_plan['target_1']:.2f}`)** and immediately trail your Stop Loss to Breakeven (`{curr_sym}{risk_plan['entry_price']:.2f}`). "
            f"Let the remaining 50% position ride along the 20 EMA up to Target 2 (`{curr_sym}{risk_plan['target_2']:.2f}`). Never turn a green trade into a red trade."
        )
    else:
        management = (
            "**Execution Blueprint:** Sit tight in cash. The market is not presenting an asymmetric risk-reward setup right now. "
            "Professional traders spend 80% of their time waiting for the market to hand them high-probability edges. Protect your capital and wait for the setup to come to you."
        )

    return {
        "strategy_archetype": archetype,
        "trapped_traders": trapped_traders,
        "senior_trader_wisdom": wisdom,
        "multi_style": multi_style,
        "veteran_notes": "\n\n".join(notes),
        "trade_management_protocol": management
    }


def analyze_symbol(
    df: pd.DataFrame,
    capital: float = 5000.0,
    risk_pct: float = 0.02
) -> dict[str, Any]:
    """
    Perform deep veteran trader multi-layer confluence analysis on a symbol.
    """
    df = add_all_indicators(df)
    curr_sym = df.attrs.get("currency_symbol", "₹") if hasattr(df, "attrs") else "₹"
    last_bar = df.iloc[-1]
    current_price = float(last_bar["Close"])
    atr = float(last_bar["ATR"])

    # 1. Structural Patterns & Market Structure
    swing_highs, swing_lows = detect_swing_points(df, window=4)
    trendlines = calculate_algorithmic_trendlines(df, swing_highs, swing_lows)
    sr_zones = cluster_support_resistance_zones(df, swing_highs, swing_lows)
    market_structure = analyze_market_structure(df, swing_highs, swing_lows)
    candlestick_patterns = analyze_candlestick_anatomy(df, lookback=5)

    # 2. Smart Money Concepts
    fvgs = detect_fair_value_gaps(df)
    sweeps = detect_liquidity_sweeps(df, swing_highs, swing_lows)

    # 3. Advanced Indicator Insights
    divergence = detect_rsi_divergences(df, swing_highs, swing_lows)
    vsa = {
        "absorption": bool(last_bar.get("VSA_Absorption", False)),
        "dry_up": bool(last_bar.get("Volume_DryUp", False)),
        "is_squeeze": bool(last_bar.get("BB_Squeeze", False)),
        "vol_ratio": float(last_bar.get("Volume_Ratio", 1.0))
    }

    # 4. Multi-Dimensional Confluence Scoring
    confluence_factors = []
    confluence_score = 0

    # Layer 1: Market Structure & Moving Average Ribbon
    ema20 = float(last_bar["EMA_20"])
    ema50 = float(last_bar["EMA_50"])
    ema200 = float(last_bar["EMA_200"])

    if "STAGE 2" in market_structure["regime"]:
        confluence_score += 20
        confluence_factors.append({
            "name": "Market Structure (Wyckoff)",
            "detail": f"{market_structure['regime']} (HH/HL confirmed, Price > 20 > 50 > 200 EMA)",
            "passed": True
        })
    elif "STAGE 1" in market_structure["regime"]:
        confluence_score += 15
        confluence_factors.append({
            "name": "Market Structure (Wyckoff)",
            "detail": f"{market_structure['regime']} (Base building, demand absorbing floating supply)",
            "passed": True
        })
    else:
        confluence_factors.append({
            "name": "Market Structure",
            "detail": f"{market_structure['regime']} — {market_structure['regime_description']}",
            "passed": False
        })

    # Layer 2: Demand Zone & Structure Support
    closest_support = None
    support_zones = [z for z in sr_zones if z["type"] == "support" and z["max_price"] <= current_price * 1.015]
    if support_zones:
        closest_support = max(support_zones, key=lambda z: z["mid_price"])
        dist_pct = abs(current_price - closest_support["max_price"]) / current_price
        if dist_pct <= 0.025:
            confluence_score += 20
            confluence_factors.append({
                "name": "Institutional Demand Zone",
                "detail": f"Price testing cluster demand ({curr_sym}{closest_support['min_price']:.1f} - {curr_sym}{closest_support['max_price']:.1f}) with {closest_support['touches']} historical touches",
                "passed": True
            })
        else:
            confluence_factors.append({
                "name": "Demand Zone Proximity",
                "detail": f"Nearest support at {curr_sym}{closest_support['mid_price']:.1f} ({dist_pct*100:.1f}% below current price)",
                "passed": False
            })
    else:
        confluence_factors.append({
            "name": "Demand Zone",
            "detail": "Price in intermediate vacuum; no high-probability cluster immediately below",
            "passed": False
        })

    # Layer 3: Candlestick Anatomy (Wick Rejection / Takeover)
    if candlestick_patterns:
        latest_p = candlestick_patterns[-1]
        if "bullish" in latest_p["type"] or "compression" in latest_p["type"]:
            confluence_score += 15
            confluence_factors.append({
                "name": "Candlestick Anatomy",
                "detail": f"{latest_p['name']}: {latest_p['detail']}",
                "passed": True
            })
        else:
            confluence_factors.append({
                "name": "Candlestick Anatomy",
                "detail": f"{latest_p['name']}: {latest_p['detail']}",
                "passed": False
            })
    else:
        confluence_factors.append({
            "name": "Candlestick Anatomy",
            "detail": "Standard bar range without clear rejection wick",
            "passed": False
        })

    # Layer 4: Volume Spread Analysis (VSA) & Squeeze
    if vsa["absorption"]:
        confluence_score += 15
        confluence_factors.append({
            "name": "Volume Spread Analysis",
            "detail": "Institutional Absorption: heavy turnover on tight spread prevents downward slide",
            "passed": True
        })
    elif vsa["vol_ratio"] >= 1.4:
        confluence_score += 12
        confluence_factors.append({
            "name": "Volume Expansion",
            "detail": f"Volume spike {vsa['vol_ratio']:.1f}x above 20-period moving average",
            "passed": True
        })
    elif vsa["dry_up"]:
        confluence_score += 10
        confluence_factors.append({
            "name": "Volume Spread Analysis",
            "detail": f"Supply Dry-Up: Low turnover ({vsa['vol_ratio']:.1f}x) confirms sellers are exhausted",
            "passed": True
        })
    else:
        confluence_factors.append({
            "name": "Volume Characteristics",
            "detail": f"Volume is average ({vsa['vol_ratio']:.1f}x), no clear institutional signature",
            "passed": False
        })

    # Layer 5: Smart Money Concepts & Divergence
    recent_bull_fvg = [f for f in fvgs if f["type"] == "bullish" and not f["is_mitigated"]]
    has_sweep = any(s["type"] == "bullish_sweep" for s in sweeps)

    if has_sweep or divergence["bullish_divergence"]:
        confluence_score += 15
        detail = "Sell-side Liquidity swept (stop-hunt trap)" if has_sweep else divergence["detail"]
        confluence_factors.append({
            "name": "Smart Money / Divergence",
            "detail": detail,
            "passed": True
        })
    elif recent_bull_fvg:
        confluence_score += 10
        confluence_factors.append({
            "name": "Fair Value Gap (FVG)",
            "detail": f"Untested bullish imbalance at {curr_sym}{recent_bull_fvg[-1]['bottom']:.1f} - {curr_sym}{recent_bull_fvg[-1]['top']:.1f}",
            "passed": True
        })
    else:
        confluence_factors.append({
            "name": "SMC & Divergence",
            "detail": "No unmitigated imbalance or sweep on recent bars",
            "passed": False
        })

    # Layer 6: Dynamic Trendline Support
    supp_line = trendlines.get("support_line")
    if supp_line and supp_line["is_ascending"]:
        proj = supp_line["end_price"]
        if abs(current_price - proj) / current_price <= 0.03:
            confluence_score += 15
            confluence_factors.append({
                "name": "Dynamic Trendline Support",
                "detail": f"Ascending trendline holding firmly at {curr_sym}{proj:.2f}",
                "passed": True
            })
        else:
            confluence_factors.append({
                "name": "Trendline Alignment",
                "detail": f"Support line projected at {curr_sym}{proj:.2f}",
                "passed": False
            })
    else:
        confluence_factors.append({
            "name": "Trendline Alignment",
            "detail": "Trendline structure neutral or descending",
            "passed": False
        })

    # Signal Classification
    final_score = min(100, confluence_score)
    if final_score >= 75:
        signal_type = "STRONG BUY"
        signal_grade = "Grade A+"
    elif final_score >= 55:
        signal_type = "BUY"
        signal_grade = "Grade B"
    elif final_score <= 35:
        signal_type = "AVOID / SELL"
        signal_grade = "Grade D"
    else:
        signal_type = "NEUTRAL / WATCH"
        signal_grade = "Grade C"

    # Stop Loss & Target Sizing
    entry_price = current_price
    if closest_support:
        stop_loss = closest_support["min_price"] - (0.5 * atr)
    else:
        stop_loss = entry_price - (1.5 * atr)

    if stop_loss >= entry_price or (entry_price - stop_loss) < (0.005 * entry_price):
        stop_loss = entry_price * 0.975

    # Position sizing calculation
    risk_plan = calculate_position_sizing(
        capital=capital,
        entry_price=entry_price,
        stop_loss=stop_loss,
        risk_percentage=risk_pct,
        reward_ratios=(2.0, 3.0)
    )

    # 5. Generate Veteran Commentary & Playbook
    veteran_insights = generate_veteran_commentary(
        symbol=df.index.name or "Stock",
        price=current_price,
        market_structure=market_structure,
        candlestick_patterns=candlestick_patterns,
        divergence=divergence,
        vsa=vsa,
        sweeps=sweeps,
        fvgs=fvgs,
        confluence_score=final_score,
        signal_type=signal_type,
        risk_plan=risk_plan,
        currency_symbol=curr_sym
    )

    return {
        "df": df,
        "current_price": current_price,
        "atr": atr,
        "rsi": float(last_bar["RSI"]),
        "signal_type": signal_type,
        "signal_grade": signal_grade,
        "confluence_score": final_score,
        "confluence_factors": confluence_factors,
        "trendlines": trendlines,
        "sr_zones": sr_zones,
        "fvgs": fvgs,
        "sweeps": sweeps,
        "risk_plan": risk_plan,
        "market_structure": market_structure,
        "candlestick_patterns": candlestick_patterns,
        "divergence": divergence,
        "vsa": vsa,
        "veteran_insights": veteran_insights
    }
