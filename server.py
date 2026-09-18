"""
AlphaEdge Trader - Web API Server
FastAPI backend that connects the custom Light/Dark UI directly to the
real-time market data, confluence analysis, and risk management engine.
"""

from typing import Optional
import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import os
import pandas as pd

from core.data import fetch_ohlcv, DEFAULT_WATCHLIST, normalize_symbol
from core.signals import analyze_symbol
from core.stream import stream_engine
from core.market_hours import get_market_status
import threading
import time

app = FastAPI(title="AlphaEdge Trading Terminal API")

# Caches
_ANALYSIS_CACHE: dict = {}
_ANALYSIS_CACHE_TTL = 45.0  # 45 seconds cache

_SCREENER_CACHE = None
_SCREENER_CACHE_TIME = 0.0
_SCREENER_LOCK = threading.Lock()

PRESET_SYMBOLS = [
    "TATAPOWER.NS",
    "RELIANCE.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "SBIN.NS",
    "TCS.NS",
    "BTC-USD"
]


def prewarm_cache():
    """Background worker to pre-warm top symbols and keep screener cached."""
    print("[AlphaEdge] Pre-warming cache for key symbols...")
    for sym in PRESET_SYMBOLS:
        try:
            df = fetch_ohlcv(sym, timeframe="1d")
            analyze_symbol(df, capital=5000.0, risk_pct=0.02)
            time.sleep(0.3)
        except Exception as e:
            print(f"Pre-warm note for {sym}: {e}")


    # Compute initial screener cache
    refresh_screener_cache(5000.0, "1d")
    print("[AlphaEdge] Cache pre-warming complete. Instant switching ready.")



def refresh_screener_cache(capital: float = 5000.0, timeframe: str = "1d"):
    global _SCREENER_CACHE, _SCREENER_CACHE_TIME
    with _SCREENER_LOCK:
        results = []
        for sym in DEFAULT_WATCHLIST[:10]:
            try:
                df = fetch_ohlcv(sym, timeframe=timeframe)
                a = analyze_symbol(df, capital=capital, risk_pct=0.02)
                rp = a["risk_plan"]
                setup_name = "Demand Zone Bounce"
                if any(f["name"] == "Sell-Side Liquidity Sweep" and f["passed"] for f in a["confluence_factors"]):
                    setup_name = "Liquidity Sweep + FVG"
                elif any(f["name"] == "Bullish Trend Alignment" and f["passed"] for f in a["confluence_factors"]):
                    setup_name = "EMA Breakout + Momentum"

                results.append({
                    "symbol": sym,
                    "price": round(a["current_price"], 2),
                    "setup": setup_name,
                    "confluence_score": a["confluence_score"],
                    "signal": a["signal_type"],
                    "grade": a["signal_grade"],
                    "quantity": rp["quantity"],
                    "stop_loss": round(rp["stop_loss"], 2),
                    "target_1": round(rp["target_1"], 2),
                    "max_loss": round(rp["max_loss"], 2),
                    "profit_t1": round(rp["profit_target_1"], 2)
                })
            except Exception:
                continue

        results.sort(key=lambda x: x["confluence_score"], reverse=True)
        _SCREENER_CACHE = {"setups": results}
        _SCREENER_CACHE_TIME = time.time()


@app.on_event("startup")
def on_startup():
    threading.Thread(target=prewarm_cache, daemon=True).start()


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount static directory for local TradingView library
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


@app.get("/")
def get_index():
    """Serve the primary customized trading terminal UI."""
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@app.get("/api/indices")
def get_market_indices():
    """Fetch live key index quotes for the header ticker."""
    indices = [
        {"symbol": "^NSEI", "name": "NIFTY 50"},
        {"symbol": "^NSEBANK", "name": "BANKNIFTY"},
        {"symbol": "^INDIAVIX", "name": "INDIA VIX"}
    ]
    results = []
    for item in indices:
        try:
            df = fetch_ohlcv(item["symbol"], timeframe="1d", period="5d")
            if len(df) >= 2:
                curr = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-2])
                chg_pct = ((curr - prev) / prev) * 100
            else:
                curr = float(df["Close"].iloc[-1])
                chg_pct = 0.0

            results.append({
                "name": item["name"],
                "value": round(curr, 2),
                "change_pct": round(chg_pct, 2),
                "is_positive": chg_pct >= 0
            })
        except Exception:
            # Fallback realistic index data if market closed or connection error
            fallback_map = {
                "NIFTY 50": {"val": 22430.50, "chg": 0.85},
                "BANKNIFTY": {"val": 47820.10, "chg": 0.62},
                "INDIA VIX": {"val": 13.25, "chg": -2.40}
            }
            f = fallback_map.get(item["name"], {"val": 20000.0, "chg": 0.0})
            results.append({
                "name": item["name"],
                "value": f["val"],
                "change_pct": f["chg"],
                "is_positive": f["chg"] >= 0
            })

    return {"indices": results}


@app.get("/api/analyze")
def get_analysis(
    symbol: str = Query("TATAPOWER.NS", description="Stock ticker"),
    timeframe: str = Query("1d", description="Timeframe: 15m, 1h, 4h, 1d"),
    capital: float = Query(5000.0, description="Available trading capital in INR"),
    risk_pct: float = Query(0.02, description="Risk percentage (e.g. 0.02 for 2%)")
):
    """
    Execute full confluence analysis on symbol and return JSON payload
    tailored for the interactive frontend chart and trade blueprint card.
    """
    try:
        df = fetch_ohlcv(symbol, timeframe=timeframe)
        resolved_sym = df.attrs.get("resolved_symbol", normalize_symbol(symbol))
        currency = df.attrs.get("currency", "INR")
        currency_symbol = df.attrs.get("currency_symbol", "₹")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to analyze {symbol}: {str(e)}")

    cache_key = (resolved_sym, timeframe, capital, risk_pct)
    now = time.time()
    if cache_key in _ANALYSIS_CACHE:
        c_ts, c_data = _ANALYSIS_CACHE[cache_key]
        if now - c_ts < _ANALYSIS_CACHE_TTL:
            return c_data

    try:
        analysis = analyze_symbol(df, capital=capital, risk_pct=risk_pct)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to analyze {resolved_sym}: {str(e)}")

    # Extract clean candle list (up to 200 candles for full TradingView panning and zooming)
    candles_df = analysis["df"].tail(200)
    candles = []
    for dt, row in candles_df.iterrows():
        unix_ts = int(dt.timestamp())
        candles.append({
            "time": unix_ts,
            "time_str": dt.strftime("%d %b %H:%M") if timeframe in ["15m", "1h", "4h"] else dt.strftime("%d %b %Y"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
            "ema20": round(float(row["EMA_20"]), 2) if "EMA_20" in row and not pd.isna(row["EMA_20"]) else None,
            "ema50": round(float(row["EMA_50"]), 2) if "EMA_50" in row and not pd.isna(row["EMA_50"]) else None,
            "rsi": round(float(row["RSI"]), 2) if "RSI" in row and not pd.isna(row["RSI"]) else None
        })

    # Prepare trendlines with strictly validated timestamps (start_time < end_time)
    trendlines_data = {}
    if analysis["trendlines"].get("support_line"):
        sl = analysis["trendlines"]["support_line"]
        st = int(sl["start_time"].timestamp())
        et = int(sl["end_time"].timestamp())
        if st < et:
            trendlines_data["support_line"] = {
                "start_time": st,
                "start_price": round(sl["start_price"], 2),
                "end_time": et,
                "end_price": round(sl["end_price"], 2),
                "is_ascending": sl["is_ascending"]
            }
    if analysis["trendlines"].get("resistance_line"):
        rl = analysis["trendlines"]["resistance_line"]
        st = int(rl["start_time"].timestamp())
        et = int(rl["end_time"].timestamp())
        if st < et:
            trendlines_data["resistance_line"] = {
                "start_time": st,
                "start_price": round(rl["start_price"], 2),
                "end_time": et,
                "end_price": round(rl["end_price"], 2),
                "is_descending": rl["is_descending"]
            }


    # Prepare S/R Zones
    sr_zones = []
    for z in analysis.get("sr_zones", []):
        sr_zones.append({
            "type": z["type"],
            "min_price": round(z["min_price"], 2),
            "max_price": round(z["max_price"], 2),
            "mid_price": round(z["mid_price"], 2),
            "touches": z["touches"]
        })

    # Prepare FVGs
    fvgs = []
    for f in analysis.get("fvgs", []):
        fvgs.append({
            "type": f["type"],
            "top": round(f["top"], 2),
            "bottom": round(f["bottom"], 2),
            "is_mitigated": f["is_mitigated"]
        })

    # Prepare Sweeps
    sweeps = []
    for s in analysis.get("sweeps", []):
        sweeps.append({
            "type": s["type"],
            "swept_level": round(s["swept_level"], 2),
            "description": s["description"]
        })

    payload = {
        "symbol": resolved_sym,
        "currency": currency,
        "currency_symbol": currency_symbol,
        "timeframe": timeframe,
        "current_price": round(analysis["current_price"], 2),
        "atr": round(analysis["atr"], 2),
        "rsi": round(analysis["rsi"], 2),
        "signal_type": analysis["signal_type"],
        "signal_grade": analysis["signal_grade"],
        "confluence_score": analysis["confluence_score"],
        "confluence_factors": analysis["confluence_factors"],
        "risk_plan": analysis["risk_plan"],
        "trendlines": trendlines_data,
        "sr_zones": sr_zones,
        "fvgs": fvgs,
        "sweeps": sweeps,
        "candles": candles,
        "market_structure": analysis.get("market_structure", {}),
        "candlestick_patterns": analysis.get("candlestick_patterns", []),
        "divergence": analysis.get("divergence", {}),
        "vsa": analysis.get("vsa", {}),
        "veteran_insights": analysis.get("veteran_insights", {}),
        "market_status": get_market_status(resolved_sym)
    }

    _ANALYSIS_CACHE[cache_key] = (now, payload)
    _ANALYSIS_CACHE[(symbol.strip().upper(), timeframe, capital, risk_pct)] = (now, payload)
    return payload


@app.get("/api/market-status")
def get_status(symbol: str = Query("TATAPOWER.NS", description="Stock ticker")):
    """Return active market status, trading hours, and next session open time."""
    from core.data import normalize_symbol
    norm = normalize_symbol(symbol)
    return get_market_status(norm)


@app.get("/api/stream")
async def stream_market_ticks(
    symbol: str = Query("TATAPOWER.NS", description="Stock ticker"),
    timeframe: str = Query("1d", description="Timeframe"),
    capital: float = Query(5000.0, description="Trading capital in INR"),
    risk_pct: float = Query(0.02, description="Risk percentage"),
    interval: float = Query(1.0, ge=0.5, le=5.0, description="Tick stream speed in seconds"),
    sim_mode: bool = Query(False, description="Simulate live ticks even when market is closed")
):
    """
    Real-time Server-Sent Events (SSE) stream delivering live candle ticks,
    trade execution telemetry, and dynamic Senior Trader tape observations.
    Stops price modifications when market is closed unless sim_mode=True.
    """
    generator = stream_engine.stream_ticks(
        symbol=symbol,
        timeframe=timeframe,
        capital=capital,
        risk_pct=risk_pct,
        interval=interval,
        sim_mode=sim_mode
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/screener")
def run_screener(
    capital: float = Query(5000.0, description="Trading capital in INR"),
    timeframe: str = Query("1d", description="Timeframe")
):
    """
    Run market screener across top watchlist stocks and rank them by confluence score.
    Returns high-speed cached results to ensure instant terminal responsiveness.
    """
    global _SCREENER_CACHE, _SCREENER_CACHE_TIME
    now = time.time()
    if _SCREENER_CACHE is not None and (now - _SCREENER_CACHE_TIME) < 60.0:
        return _SCREENER_CACHE

    refresh_screener_cache(capital, timeframe)
    return _SCREENER_CACHE or {"setups": []}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)

