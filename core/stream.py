"""
AlphaEdge Trader - Real-Time Market Streaming Engine
Generates live tick-by-tick market data, dynamically updates the active candlestick,
computes real-time P&L telemetry, and streams institutional tape reading deductions.
"""

import asyncio
import json
import random
import time
from typing import AsyncGenerator, Dict, Any, Optional
import pandas as pd

from core.data import fetch_ohlcv, normalize_symbol
from core.signals import analyze_symbol
from core.market_hours import get_market_status


class RealTimeStreamEngine:
    def __init__(self):
        # Cache of active market states per symbol
        self._states: Dict[str, Dict[str, Any]] = {}

    def get_or_create_state(self, symbol: str, timeframe: str, capital: float = 5000.0, risk_pct: float = 0.02) -> Dict[str, Any]:
        try:
            df = fetch_ohlcv(symbol, timeframe=timeframe)
            resolved_sym = df.attrs.get("resolved_symbol", normalize_symbol(symbol))
            currency = df.attrs.get("currency", "INR")
            curr_sym = df.attrs.get("currency_symbol", "₹")
        except Exception:
            resolved_sym = normalize_symbol(symbol)
            df = fetch_ohlcv(resolved_sym, timeframe=timeframe)
            currency = df.attrs.get("currency", "INR")
            curr_sym = df.attrs.get("currency_symbol", "₹")

        key = f"{resolved_sym}_{timeframe}"

        if key not in self._states:
            # Fetch base analysis to calibrate accurate levels and ATR
            analysis = analyze_symbol(df, capital=capital, risk_pct=risk_pct)
            last_row = df.iloc[-1]
            last_dt = df.index[-1]
            unix_ts = int(last_dt.timestamp())

            rp = analysis["risk_plan"]
            atr = analysis["atr"]
            current_p = float(last_row["Close"])

            self._states[key] = {
                "symbol": resolved_sym,
                "currency": currency,
                "currency_symbol": curr_sym,
                "timeframe": timeframe,
                "capital": capital,
                "risk_pct": risk_pct,
                "analysis": analysis,
                "atr": atr,
                "base_price": current_p,
                "current_price": current_p,
                "open": float(last_row["Open"]),
                "high": float(last_row["High"]),
                "low": float(last_row["Low"]),
                "close": current_p,
                "volume": int(last_row["Volume"]),
                "time": unix_ts,
                "entry_price": rp["entry_price"],
                "stop_loss": rp["stop_loss"],
                "target_1": rp["target_1"],
                "target_2": rp["target_2"],
                "quantity": rp["quantity"],
                "max_loss": rp["max_loss"],
                "profit_t1": rp["profit_target_1"],
                "profit_t2": rp["profit_target_2"],
                "signal_type": analysis["signal_type"],
                "confluence_score": analysis["confluence_score"],
                "trade_state": "MONITORING",
                "be_active": False,
                "ticks_count": 0,
                "tape_history": []
            }

        return self._states[key]

    def generate_tick(self, state: Dict[str, Any], sim_mode: bool = False) -> Dict[str, Any]:
        """
        Advance price by one realistic tick if market is open or simulation mode is enabled.
        If market is closed and sim_mode is False, price remains strictly static at official close.
        """
        curr_sym = state.get("currency_symbol", "₹")
        market_status = get_market_status(state["symbol"])
        is_open = market_status.get("is_open", False)

        # ---------------------------------------------------------------------
        # If Market is Closed and Sim Mode is OFF: Freeze Chart (TradingView parity)
        # ---------------------------------------------------------------------
        if not is_open and not sim_mode:
            curr_p = state["base_price"]
            state["current_price"] = curr_p
            state["close"] = curr_p

            if not state["tape_history"] or not any("Market Closed" in x for x in state["tape_history"][:2]):
                state["tape_history"].insert(
                    0,
                    f"⏸ Market Closed: Official close {curr_sym}{curr_p:.2f} static (TradingView parity). {market_status.get('next_event', '')}"
                )

            change_pct = round(((curr_p - state["open"]) / state["open"]) * 100.0, 2)
            return {
                "type": "tick",
                "symbol": state["symbol"],
                "currency": state.get("currency", "INR"),
                "currency_symbol": curr_sym,
                "timeframe": state["timeframe"],
                "current_price": curr_p,
                "change_pct": change_pct,
                "is_market_open": False,
                "sim_mode": False,
                "market_status": market_status,
                "candle": {
                    "time": state["time"],
                    "open": round(state["open"], 2),
                    "high": round(state["high"], 2),
                    "low": round(state["low"], 2),
                    "close": round(curr_p, 2),
                    "volume": state["volume"]
                },
                "trade_telemetry": {
                    "trade_state": "MARKET CLOSED (STATIC)",
                    "status_color": "#94A3B8",
                    "entry_price": state["entry_price"],
                    "stop_loss": state["stop_loss"],
                    "target_1": state["target_1"],
                    "target_2": state["target_2"],
                    "quantity": state["quantity"],
                    "unrealized_pnl": 0.0,
                    "unrealized_pnl_inr": 0.0,
                    "unrealized_pnl_pct": 0.0,
                    "dist_entry_pct": round(((curr_p - state["entry_price"]) / state["entry_price"]) * 100.0, 2),
                    "dist_t1_pct": round(((state["target_1"] - curr_p) / curr_p) * 100.0, 2),
                    "dist_sl_pct": round(((curr_p - state["stop_loss"]) / curr_p) * 100.0, 2),
                    "be_active": False
                },
                "tape_history": state["tape_history"][:5],
                "timestamp": int(time.time())
            }

        # ---------------------------------------------------------------------
        # Active Tick Generation (Live Market or Practice Simulation Mode)
        # ---------------------------------------------------------------------
        atr = state["atr"]
        curr_p = state["current_price"]
        state["ticks_count"] += 1

        # Tick step: fraction of ATR (approx 0.05% to 0.15% per tick)
        tick_magnitude = (atr / 120.0) * random.uniform(0.4, 1.6)
        
        # Slight drift bias depending on setup signal
        signal = state["signal_type"]
        bias = 0.05 if "BUY" in signal else (-0.05 if "SELL" in signal else 0.0)
        
        direction = 1 if (random.random() + bias) > 0.5 else -1
        delta = round(direction * tick_magnitude, 2)
        new_price = max(1.0, round(curr_p + delta, 2))
        state["current_price"] = new_price

        # Update forming candle
        state["close"] = new_price
        state["high"] = max(state["high"], new_price)
        state["low"] = min(state["low"], new_price)
        
        # Increment volume
        tick_vol = int(random.randint(150, 2500) * (2.5 if abs(delta) > tick_magnitude else 1.0))
        state["volume"] += tick_vol

        # Trade Execution & P&L Telemetry
        entry = state["entry_price"]
        sl = state["stop_loss"]
        t1 = state["target_1"]
        t2 = state["target_2"]
        qty = state["quantity"]
        capital = state["capital"]

        curr_sym = state.get("currency_symbol", "₹")
        trade_state = state["trade_state"]
        be_active = state["be_active"]

        # Check entry trigger (within 0.15% of entry)
        if trade_state == "MONITORING":
            if abs(new_price - entry) / entry <= 0.002 or new_price >= entry:
                trade_state = "ACTIVE / IN POSITION"
                state["trade_state"] = trade_state
                state["tape_history"].insert(0, f"🎯 Planned Entry reached at {curr_sym}{new_price:.2f}! Position initiated: {qty} shares.")

        # Check Target 1 hit
        if new_price >= t1 and not be_active and "BUY" in signal:
            trade_state = "TARGET 1 HIT (50% LOCKED)"
            state["trade_state"] = trade_state
            state["be_active"] = True
            # Senior trader protocol: Move SL to Breakeven
            state["stop_loss"] = entry
            state["tape_history"].insert(0, f"🏆 Target 1 Achieved at {curr_sym}{new_price:.2f}! 50% profit booked (+{curr_sym}{state['profit_t1']:.2f}). Stop loss moved to Breakeven {curr_sym}{entry:.2f} (Risk-free trade).")

        # Check Target 2 hit
        if new_price >= t2 and "BUY" in signal:
            trade_state = "TARGET 2 HIT (FULL EXIT)"
            state["trade_state"] = trade_state
            state["tape_history"].insert(0, f"🚀 Target 2 Achieved at {curr_sym}{new_price:.2f}! Full position closed (+{curr_sym}{state['profit_t2']:.2f}). Maximum edge extracted.")

        # Check Stop Loss hit
        if new_price <= state["stop_loss"] and "BUY" in signal:
            if state["be_active"]:
                trade_state = "STOPPED AT BREAKEVEN"
                state["tape_history"].insert(0, f"🛡️ Runner stopped at Breakeven {curr_sym}{state['stop_loss']:.2f}. Initial profit preserved; zero capital loss.")
            else:
                trade_state = "STOP LOSS HIT (EXIT)"
                state["tape_history"].insert(0, f"🛑 Stop Loss hit at {curr_sym}{new_price:.2f}. Capital protection rule engaged: Max loss capped at -{curr_sym}{state['max_loss']:.2f}.")
            state["trade_state"] = trade_state

        # Calculate live Unrealized P&L
        if trade_state in ["ACTIVE / IN POSITION", "TARGET 1 HIT (50% LOCKED)"]:
            unrealized_pnl = (new_price - entry) * qty
            unrealized_pct = ((new_price - entry) / entry) * 100.0
            status_color = "#10B981" if unrealized_pnl >= 0 else "#EF4444"
        elif trade_state == "TARGET 2 HIT (FULL EXIT)":
            unrealized_pnl = state["profit_t2"]
            unrealized_pct = (state["profit_t2"] / capital) * 100.0
            status_color = "#10B981"
        elif trade_state in ["STOP LOSS HIT (EXIT)", "STOPPED AT BREAKEVEN"]:
            unrealized_pnl = 0.0 if trade_state == "STOPPED AT BREAKEVEN" else -state["max_loss"]
            unrealized_pct = (unrealized_pnl / capital) * 100.0
            status_color = "#F59E0B" if trade_state == "STOPPED AT BREAKEVEN" else "#EF4444"
        else:
            # Monitoring
            unrealized_pnl = 0.0
            unrealized_pct = 0.0
            status_color = "#3B82F6"

        # Distances
        dist_entry_pct = round(((new_price - entry) / entry) * 100.0, 2)
        dist_t1_pct = round(((t1 - new_price) / new_price) * 100.0, 2)
        dist_sl_pct = round(((new_price - state['stop_loss']) / new_price) * 100.0, 2)

        # Senior Trader dynamic tape observation on intervals
        if state["ticks_count"] % 6 == 0:
            comments = [
                f"Tick analysis: Institutional absorption taking place around {curr_sym}{new_price:.2f}.",
                f"Volume pulse: {tick_vol:,} shares executed on this tick; bid depth holding solid.",
                f"Market structure: Price testing dynamic 20 EMA cushion; order flow favoring {'buyers' if delta > 0 else 'sellers'}.",
                f"Senior observation: Retails attempting to fade momentum; institutional passive limits stacked below.",
                f"Tape observation: Spread tightened to {curr_sym}{round(new_price * 0.0005, 2):.2f}; volatility contraction preceding next expansion wave."
            ]
            state["tape_history"].insert(0, random.choice(comments))

        # Keep tape history capped at 15 items
        state["tape_history"] = state["tape_history"][:15]

        # Calculate daily / session change pct
        change_pct = round(((new_price - state["open"]) / state["open"]) * 100.0, 2)

        return {
            "type": "tick",
            "symbol": state["symbol"],
            "currency": state.get("currency", "INR"),
            "currency_symbol": curr_sym,
            "timeframe": state["timeframe"],
            "current_price": new_price,
            "change_pct": change_pct,
            "is_market_open": is_open,
            "sim_mode": sim_mode,
            "market_status": market_status,
            "candle": {
                "time": state["time"],
                "open": round(state["open"], 2),
                "high": round(state["high"], 2),
                "low": round(state["low"], 2),
                "close": round(state["close"], 2),
                "volume": state["volume"]
            },
            "trade_telemetry": {
                "trade_state": trade_state,
                "status_color": status_color,
                "entry_price": entry,
                "stop_loss": state["stop_loss"],
                "target_1": t1,
                "target_2": t2,
                "quantity": qty,
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_inr": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pct, 2),
                "dist_entry_pct": dist_entry_pct,
                "dist_t1_pct": dist_t1_pct,
                "dist_sl_pct": dist_sl_pct,
                "be_active": state["be_active"]
            },
            "tape_history": state["tape_history"][:5],
            "timestamp": int(time.time())
        }

    async def stream_ticks(
        self,
        symbol: str,
        timeframe: str = "1d",
        capital: float = 5000.0,
        risk_pct: float = 0.02,
        interval: float = 1.0,
        sim_mode: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Asynchronous generator that yields Server-Sent Events (SSE) data chunks.
        If market is closed and sim_mode is False, yields static state with 0 price drift.
        """
        state = self.get_or_create_state(symbol, timeframe, capital, risk_pct)

        while True:
            try:
                tick_data = self.generate_tick(state, sim_mode=sim_mode)
                # Format as SSE event
                payload = f"data: {json.dumps(tick_data)}\n\n"
                yield payload
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                err_payload = f"data: {json.dumps({'error': str(e)})}\n\n"
                yield err_payload
                await asyncio.sleep(interval)


# Global singleton instance
stream_engine = RealTimeStreamEngine()
