"""
Market Data Retrieval Module
Fetches, cleans, and standardizes OHLCV candlestick data from Yahoo Finance.
"""

from typing import Optional
import pandas as pd
import yfinance as yf

import time

# Common Indian Equities Watchlist (NSE)
DEFAULT_WATCHLIST = [
    "TATAPOWER.NS",
    "TCS.NS",
    "RELIANCE.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "ITC.NS",
    "LT.NS",
    "BHARTIARTL.NS",
    "BAJFINANCE.NS",
    "ADANIENT.NS",
    "SUNPHARMA.NS",
    "TITAN.NS"
]

# In-memory OHLCV Cache: (symbol, timeframe, period) -> (timestamp, df)
_OHLCV_CACHE: dict = {}
CACHE_TTL_SECONDS = 60.0  # 1 minute fresh cache

# Common US / Global tickers (no exchange suffix on Yahoo Finance)
COMMON_US_TICKERS = {
    "AAPL", "MSFT", "GOOG", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX",
    "AMD", "INTC", "PLTR", "COIN", "BABA", "UBER", "DIS", "PYPL", "CRM",
    "ORCL", "CSCO", "QCOM", "ADBE", "SPY", "QQQ", "DIA", "IWM", "V", "MA",
    "JPM", "BAC", "WMT", "COST", "KO", "PEP", "XOM", "CVX", "NKE", "BA",
    "IBM", "SHOP", "SNOW", "SQ", "ROKU", "SOFI", "ARM", "SMCI", "AVGO", "MSTR",
    "HDB", "IBN"
}

# Crypto shortcuts
CRYPTO_MAP = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "DOGE": "DOGE-USD",
    "XRP": "XRP-USD",
    "BNB": "BNB-USD",
    "ADA": "ADA-USD",
    "AVAX": "AVAX-USD",
    "DOT": "DOT-USD",
    "LINK": "LINK-USD"
}

# Index shortcuts
INDEX_MAP = {
    "NIFTY": "^NSEI",
    "NIFTY50": "^NSEI",
    "NIFTY 50": "^NSEI",
    "^NSEI": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "BANK NIFTY": "^NSEBANK",
    "^NSEBANK": "^NSEBANK",
    "VIX": "^INDIAVIX",
    "INDIAVIX": "^INDIAVIX",
    "^INDIAVIX": "^INDIAVIX",
    "SPX": "^GSPC",
    "SP500": "^GSPC",
    "S&P500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW": "^DJI"
}


def resolve_candidates(symbol: str) -> list[str]:
    """
    Generate prioritized candidate tickers for Yahoo Finance.
    Handles Indian equities (.NS, .BO), US/Global equities (raw),
    Crypto (-USD), and Major Indices (^).
    """
    sym = symbol.strip().upper()
    if sym in INDEX_MAP:
        return [INDEX_MAP[sym]]
    if sym in CRYPTO_MAP:
        return [CRYPTO_MAP[sym]]

    # If the user already provided an explicit exchange or asset suffix
    if any(c in sym for c in [".", "-", "=", "^"]):
        return [sym]

    # If known popular US equity / ETF
    if sym in COMMON_US_TICKERS:
        return [sym, f"{sym}.NS"]

    # For general bare tickers: try Indian NSE first, then raw US/global, then BSE
    return [f"{sym}.NS", sym, f"{sym}.BO"]


def normalize_symbol(symbol: str) -> str:
    """
    Standardize ticker symbol into the most probable single candidate.
    """
    candidates = resolve_candidates(symbol)
    return candidates[0]


def get_symbol_currency(symbol: str) -> tuple[str, str]:
    """
    Returns (currency_code, currency_symbol) e.g. ('USD', '$') or ('INR', '₹').
    """
    sym = symbol.upper()
    if sym.endswith(".NS") or sym.endswith(".BO") or sym in ["^NSEI", "^NSEBANK", "^INDIAVIX"]:
        return "INR", "₹"
    return "USD", "$"


def fetch_ohlcv(
    symbol: str,
    timeframe: str = "1d",
    period: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch OHLCV candlestick data using yfinance with multi-market resolution.

    Args:
        symbol: Ticker symbol (e.g., 'AAPL', 'RELIANCE', 'TATAPOWER.NS', 'BTC-USD').
        timeframe: Bar timeframe ('15m', '1h', '4h', '1d', '1wk').
        period: History period ('1mo', '3mo', '6mo', '1y', '2y'). If None, selected automatically.

    Returns:
        pd.DataFrame: Cleaned OHLCV dataframe with attrs['resolved_symbol'], attrs['currency'], attrs['currency_symbol'].
    """
    candidates = resolve_candidates(symbol)

    if period is None:
        if timeframe in ["1m"]:
            period = "5d"
        elif timeframe in ["3m", "5m", "15m"]:
            period = "1mo"
        elif timeframe in ["1h", "60m"]:
            period = "6mo"
        else:
            period = "1y"

    now = time.time()

    # Check cache for any matching candidate or raw symbol
    for cand in [symbol.strip().upper()] + candidates:
        cache_key = (cand, timeframe, period)
        if cache_key in _OHLCV_CACHE:
            cached_ts, cached_df = _OHLCV_CACHE[cache_key]
            if now - cached_ts < CACHE_TTL_SECONDS:
                return cached_df.copy()

    # yfinance interval mapping
    interval_map = {
        "1m": "1m",
        "3m": "1m",  # Will resample to 3min
        "5m": "5m",
        "15m": "15m",
        "1h": "60m",
        "4h": "60m",  # yfinance doesn't have native 4h, we fetch 1h and resample
        "1d": "1d",
        "1wk": "1wk"
    }
    fetch_interval = interval_map.get(timeframe, "1d")

    df = None
    matched_candidate = None

    # Try each candidate in prioritized order
    for cand in candidates:
        try:
            ticker = yf.Ticker(cand)
            for attempt in range(2):
                try:
                    df = ticker.history(period=period, interval=fetch_interval)
                    if df is not None and not df.empty and len(df) >= 5:
                        break
                except Exception:
                    pass
                time.sleep(0.3)

            # Fallback to 6mo if 1y was throttled
            if (df is None or df.empty or len(df) < 5) and period == "1y":
                try:
                    df = ticker.history(period="6mo", interval=fetch_interval)
                except Exception:
                    pass

            if df is not None and not df.empty and len(df) >= 5:
                matched_candidate = cand
                break
        except Exception:
            continue

    if df is None or df.empty or len(df) < 5 or not matched_candidate:
        raise ValueError(f"Could not retrieve sufficient data for symbol '{symbol}'. Checked candidates: {', '.join(candidates)}.")

    # Clean columns
    df = df.reset_index()

    # Handle multi-level columns if returned
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    # Find date column
    date_col = "Date" if "Date" in df.columns else "Datetime"
    if date_col not in df.columns:
        date_col = df.columns[0]

    df.rename(columns={
        date_col: "Datetime",
        "Open": "Open",
        "High": "High",
        "Low": "Low",
        "Close": "Close",
        "Volume": "Volume"
    }, inplace=True)

    df["Datetime"] = pd.to_datetime(df["Datetime"])
    df.set_index("Datetime", inplace=True)

    # Resample if requested (4h or 3m)
    if timeframe == "4h":
        df = df.resample("4h").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()
    elif timeframe == "3m":
        df = df.resample("3min").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna()

    # Drop any zero volume or NaN rows
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[df["Close"] > 0]
    df.sort_index(inplace=True)

    # Attach currency and resolved symbol metadata
    currency, curr_sym = get_symbol_currency(matched_candidate)
    df.attrs["resolved_symbol"] = matched_candidate
    df.attrs["currency"] = currency
    df.attrs["currency_symbol"] = curr_sym

    # Store in cache under both candidate and requested symbol
    _OHLCV_CACHE[(matched_candidate, timeframe, period)] = (now, df)
    _OHLCV_CACHE[(symbol.strip().upper(), timeframe, period)] = (now, df)

    return df.copy()


