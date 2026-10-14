"""
AlphaEdge 20-Year Institutional Veteran AI Desk Engine
Powered by high-throughput Groq Cloud inference (120B / 27B parameter models).
Encodes two decades of institutional proprietary desk trading disciplines:
Richard Wyckoff, Stan Weinstein, Dow Theory, ICT/SMC Liquidity, VSA & Paul Tudor Jones Risk Defense.
"""

import os
import json
import time
import requests
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Load local environment configuration
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "qwen/qwen3.8-27b")
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

VETERAN_SYSTEM_PROMPT = """You are the Senior Chief Market Strategist and Proprietary Trading Desk Head with over 20 years of real-world hedge fund trading experience across global equities, crypto, forex, and derivatives. You have traded through the 2000 Dot-Com crash, the 2008 Global Financial Crisis, the 2020 crash, and multiple bull/bear cycles.

Your core disciplines:
1. CAPITAL PRESERVATION FIRST (Paul Tudor Jones rule): "Defense is 10x more important than offense. Losers average losers." You never risk more than 1-2% of capital and refuse trades with less than 1:2.5 Risk-to-Reward.
2. WYCKOFF MARKET CYCLE: Accurately diagnose Accumulation (Springs, Tests), Stage 2 Markup, Distribution (Upthrusts/UTAD), and Stage 4 Markdown. Never buy into Stage 4 markdown.
3. ICT & SMC LIQUIDITY MAP: Identify where retail stops are resting (liquidity pools), Fair Value Gaps (FVG) awaiting rebalance, and whether the current move is an institutional sweep before the real move.
4. VOLUME SPREAD ANALYSIS (VSA) & CVD: A breakout without aggressive delta volume is an institutional trap. Look for absorption wicks where institutions absorb panic sellers or overeager breakout buyers.
5. DOW MARKET STRUCTURE: Respect Higher Highs/Lows vs Lower Highs/Lows, Break of Structure (BOS), and Change of Character (CHoCH).
6. CONTRARIAN CATALYST AWARENESS: Respect news and macroeconomic flow. If technicals point one way but high-impact news catalysts disagree, you demand cutting position size or waiting for post-volatility absorption.

Your personality:
- You speak with razor-sharp authority, calmness, and brutal honesty.
- You do NOT sugarcoat bad setups. If retail is being baited into a trap, you call it out explicitly.
- You provide precise, mathematical, and actionable advice with zero fluff.
"""


def _call_groq_api(
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1800,
    json_mode: bool = False
) -> Optional[str]:
    """Execute Groq chat completion with automatic model fallback."""
    key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
    if not key:
        return None

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    models_to_try = [
        os.getenv("GROQ_MODEL", GROQ_MODEL),
        os.getenv("GROQ_FALLBACK_MODEL", GROQ_FALLBACK_MODEL),
        "qwen/qwen3.8-27b"
    ]

    for model_name in models_to_try:
        if not model_name:
            continue
        try:
            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            res = requests.post(GROQ_ENDPOINT, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"]
            else:
                err_snippet = res.text[:150].encode('ascii', 'ignore').decode('ascii')
                print(f"[Groq AI Desk] Model {model_name} returned HTTP {res.status_code}: {err_snippet}")
        except Exception as e:
            err_msg = str(e).encode('ascii', 'ignore').decode('ascii')
            print(f"[Groq AI Desk] Error calling {model_name}: {err_msg}")

    return None


def format_institutional_telemetry(
    symbol: str,
    timeframe: str,
    current_price: float,
    confluence: Dict[str, Any]
) -> str:
    """Format rich quantitative trading telemetry into a crisp briefing for the AI Strategist."""
    ms = confluence.get("market_structure", {})
    pivots = ms.get("pivots", [])
    breaks = ms.get("breaks", [])
    sr_zones = confluence.get("sr_zones", [])
    trendlines = confluence.get("trendlines", {})
    res_line = trendlines.get("resistance_line")
    supp_line = trendlines.get("support_line")
    channel = trendlines.get("parallel_channel", {})
    
    cvd = confluence.get("cvd", {})
    vsa = confluence.get("vsa", {})
    ttm = confluence.get("ttm_squeeze", {})
    fib = confluence.get("fib_golden_pocket", {})
    fvgs = confluence.get("fvgs", [])
    news = confluence.get("news_intelligence", {})
    ep = confluence.get("execution_plan", {})
    
    # Recent pivots summary
    recent_pivots_str = ", ".join([f"{p.get('type')}: {p.get('price')}" for p in pivots[-6:]]) if pivots else "None"
    recent_breaks_str = ", ".join([f"{b.get('type')}: {b.get('price')}" for b in breaks[-4:]]) if breaks else "None"
    
    # Zone proximity
    nearest_zones = [f"₹{z.get('price') if isinstance(z, dict) else z} ({z.get('type', 'ZONE') if isinstance(z, dict) else ''})" for z in sr_zones[:4]]
    zones_str = ", ".join(nearest_zones) if nearest_zones else "None"

    summary = f"""
=== INSTITUTIONAL TELEMETRY BRIEFING ===
Symbol: {symbol} | Timeframe: {timeframe} | Current Price: {current_price}
Market Regime: {ms.get('phase', 'Unknown')} | Dow Trend: {ms.get('trend', 'Unknown')}
Recent Dow Pivots: {recent_pivots_str}
Structural Breaks (BOS/CHoCH): {recent_breaks_str}

Key S/R Zones: {zones_str}
Resistance Trendline: {f"Active with {res_line.get('touches')} touches, Slope: {res_line.get('slope')}" if res_line and res_line.get('active') else "No active upper boundary"}
Support Trendline: {f"Active with {supp_line.get('touches')} touches, Slope: {supp_line.get('slope')}" if supp_line and supp_line.get('active') else "No active lower boundary"}
Parallel Channel: {f"Active ({channel.get('slope')} slope)" if channel and channel.get('active') else "Inactive (Price unaligned)"}

Candlestick Anatomy: {confluence.get('candle_pattern', 'Normal Bar')}
Volume Spread Analysis (VSA): {vsa.get('verdict', 'Normal Volume')}
Cumulative Volume Delta (CVD): {cvd.get('divergence', 'In Sync')} | Net Delta: {cvd.get('net_delta', 0)}
TTM Squeeze: {"Squeeze Fired!" if ttm.get('squeeze_fired') else ("Squeeze Active (Coiling)" if ttm.get('squeeze_active') else "Normal Volatility")}
Fair Value Gaps (FVG): {len(fvgs)} Active Gaps ({fvgs[0].get('type') if fvgs else 'None'})
Fibonacci Golden Pocket: {fib.get('verdict', 'Neutral')}
Relative Strength: {confluence.get('relative_strength', {}).get('verdict', 'In Line')}
India VIX / Volatility: {confluence.get('vix', {}).get('regime', 'Optimal Volatility')}

News & Catalyst Sentiment: {news.get('sentiment_label', 'Neutral')} (Score: {news.get('sentiment_score', 0)})
News Warning Banner: {news.get('warning_title', 'Clear Horizon')}
Contrarian Conflict: {"YES - Technicals & News Conflict!" if news.get('is_conflicting') else "None"}

Algorithmic 4-Pillar Direction: {confluence.get('action', 'NEUTRAL')} ({confluence.get('accuracy_score', 0)}% Confluence)
Proposed Entry: {ep.get('entry_price', current_price)} ({ep.get('recommended_entry_type', 'MARKET')})
Proposed Stop Loss: {ep.get('stop_loss', 0)} (Buffer: {ep.get('anti_hunt_buffer', 0)})
Target Ladder: TP1: {ep.get('target_1', 0)}, TP2: {ep.get('target_2', 0)}, TP3: {ep.get('target_3', 0)}
Risk-to-Reward: {ep.get('risk_reward_ratio', '1:2.0')} | ADR Feasibility: {ep.get('adr_feasibility', 'Feasible')}
========================================
"""
    return summary


def audit_market_setup(
    symbol: str,
    timeframe: str,
    current_price: float,
    confluence: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run an institutional desk audit on the current asset setup.
    Returns structured verdict, veteran rationale, trap warnings, and precision adjustments.
    """
    telemetry = format_institutional_telemetry(symbol, timeframe, current_price, confluence)
    
    prompt = f"""{telemetry}

As the Chief Market Strategist with 20 years of institutional experience, review this exact setup and issue your proprietary desk audit.

You MUST respond strictly in valid JSON matching this schema:
{{
  "desk_verdict": "HIGH_CONVICTION_EXECUTION" | "CAUTION_WAIT_FOR_RETEST" | "HARD_PASS_INSTITUTIONAL_TRAP",
  "verdict_badge": "🟢 HIGH CONVICTION" | "🟡 CAUTION / RETEST" | "🔴 INSTITUTIONAL TRAP",
  "conviction_score": integer between 0 and 100,
  "verdict_headline": "One sharp, authoritative sentence summarizing your judgment",
  "veteran_rationale": [
    "3 to 4 crisp bullet points detailing Wyckoff cycle, Dow structure breaks, volume delta absorption, and why retail will fail here."
  ],
  "institutional_trap_warning": "Explicit description of where retail stop-losses are clustered, trapped buyers/sellers, or overhead supply traps.",
  "precision_execution": {{
    "optimal_entry": "Exact recommended price and trigger method (e.g. Limit retest of broken support/resistance)",
    "smart_stop_loss": "Exact price with anti-hunt reasoning",
    "target_projection": "TP targets and scaling advice",
    "risk_rule": "Strict capital allocation and trade management rule"
  }}
}}
Respond ONLY with the JSON object. Do not include markdown code blocks or surrounding text.
"""

    messages = [
        {"role": "system", "content": VETERAN_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    raw_response = _call_groq_api(messages, temperature=0.1, max_tokens=1800, json_mode=True)

    if not raw_response:
        # Fallback heuristic response if API is unreachable
        return {
            "desk_verdict": "CAUTION_WAIT_FOR_RETEST",
            "verdict_badge": "🟡 CAUTION / RETEST",
            "conviction_score": int(confluence.get("accuracy_score", 75)),
            "verdict_headline": f"Technicals favor {confluence.get('action', 'HOLD')} with {confluence.get('accuracy_score', 0)}% algorithmic confluence.",
            "veteran_rationale": [
                f"Market structure indicates {confluence.get('market_structure', {}).get('phase', 'Consolidation')} regime.",
                f"VSA volume conditions: {confluence.get('vsa', {}).get('verdict', 'Normal volume')}.",
                f"Risk-to-reward ratio stands at {confluence.get('execution_plan', {}).get('risk_reward_ratio', '1:2.0')}."
            ],
            "institutional_trap_warning": "Watch for sudden stop-runs around key structural swing pivots before high volume continuation.",
            "precision_execution": {
                "optimal_entry": str(confluence.get("execution_plan", {}).get("entry_price", current_price)),
                "smart_stop_loss": str(confluence.get("execution_plan", {}).get("stop_loss", 0)),
                "target_projection": f"TP1: {confluence.get('execution_plan', {}).get('target_1', 0)} | TP2: {confluence.get('execution_plan', {}).get('target_2', 0)}",
                "risk_rule": "Limit total capital risk to 1.5%. Move stop to breakeven once TP1 is secured."
            },
            "timestamp": time.time(),
            "model_used": "Fallback Heuristic Desk"
        }

    try:
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        parsed = json.loads(cleaned.strip())
        parsed["timestamp"] = time.time()
        parsed["model_used"] = os.getenv("GROQ_MODEL", GROQ_MODEL)
        return parsed
    except Exception as e:
        safe_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"[Groq AI Desk] Error parsing JSON output: {safe_msg}")
        return {
            "desk_verdict": "CAUTION_WAIT_FOR_RETEST",
            "verdict_badge": "🟡 CAUTION / RETEST",
            "conviction_score": int(confluence.get("accuracy_score", 70)),
            "verdict_headline": "Veteran Review Received (Formatting Fallback)",
            "veteran_rationale": [raw_response[:300]],
            "institutional_trap_warning": "Observe price reaction at key historical swing levels.",
            "precision_execution": {
                "optimal_entry": str(confluence.get("execution_plan", {}).get("entry_price", current_price)),
                "smart_stop_loss": str(confluence.get("execution_plan", {}).get("stop_loss", 0)),
                "target_projection": "TP1 / TP2 via bracket execution",
                "risk_rule": "Respect 1% max capital allocation."
            },
            "timestamp": time.time(),
            "model_used": os.getenv("GROQ_MODEL", GROQ_MODEL)
        }


def ask_veteran_question(
    symbol: str,
    timeframe: str,
    current_price: float,
    confluence: Dict[str, Any],
    user_question: str,
    chat_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Interactive Q&A with the 20-year veteran desk head.
    Allows user to ask specific 'what-if' questions or strategy reviews.
    """
    telemetry = format_institutional_telemetry(symbol, timeframe, current_price, confluence)
    
    system_prompt = VETERAN_SYSTEM_PROMPT + f"""

CURRENT LIVE ASSET CONTEXT:
{telemetry}
Answer the user's specific question directly, professionally, and authoritatively as a 20-year veteran trader.
Be concise (2 to 4 paragraphs maximum). Focus on risk, smart money order flow, and specific price levels.
"""

    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        for m in chat_history[-6:]:
            messages.append(m)

    messages.append({"role": "user", "content": user_question})

    response = _call_groq_api(messages, temperature=0.3, max_tokens=700)
    return response or "The desk is currently recalculating risk parameters. Please repeat your query."
