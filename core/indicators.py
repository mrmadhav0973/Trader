"""
Technical Indicators Module - Advanced Veteran Suite
Computes EMAs, RSI, MACD, ATR, Bollinger Bands, Volume Spread Analysis (VSA),
Volume Spikes, and RSI Divergences.
"""

from typing import Any
import numpy as np
import pandas as pd


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI) using Wilder's smoothing."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).copy()
    loss = (-delta.where(delta < 0, 0.0)).copy()

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    for i in range(period, len(series)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def calculate_macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD line, Signal line, and Histogram."""
    fast_ema = calculate_ema(series, fast)
    slow_ema = calculate_ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = calculate_ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR)."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()

    for i in range(period, len(df)):
        atr.iloc[i] = (atr.iloc[i - 1] * (period - 1) + tr.iloc[i]) / period

    return atr.bfill()


def calculate_bollinger_bands(
    series: pd.Series,
    period: int = 20,
    num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands (Upper, Middle, Lower) and Bandwidth.
    """
    mid = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std()
    upper = mid + (num_std * std)
    lower = mid - (num_std * std)
    bandwidth = (upper - lower) / mid.replace(0, np.nan)
    return upper.bfill(), mid.bfill(), lower.bfill(), bandwidth.bfill()


def calculate_vwap(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Session Volume Weighted Average Price (VWAP) and ±1.5 StdDev Bands.
    Anchored daily for intraday data, or uses rolling calculation for multi-day.
    """
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    volume = df["Volume"].replace(0, 1.0)
    tp_vol = typical_price * volume

    # Group by date if DatetimeIndex
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
        dates = df.index.date
        cum_tp_vol = tp_vol.groupby(dates).cumsum()
        cum_vol = volume.groupby(dates).cumsum()
    else:
        cum_tp_vol = tp_vol.cumsum()
        cum_vol = volume.cumsum()

    vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    vwap = vwap.bfill().ffill()

    # VWAP Variance & Standard Deviation
    dev = (typical_price - vwap) ** 2
    dev_vol = dev * volume
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
        cum_dev = dev_vol.groupby(df.index.date).cumsum()
    else:
        cum_dev = dev_vol.cumsum()
    vwap_std = np.sqrt(cum_dev / cum_vol.replace(0, np.nan)).fillna(0.0)

    upper_band = vwap + (1.5 * vwap_std)
    lower_band = vwap - (1.5 * vwap_std)
    return vwap, upper_band, lower_band


def detect_rsi_divergences(
    df: pd.DataFrame,
    swing_highs: list[dict],
    swing_lows: list[dict]
) -> dict[str, Any]:
    """
    Detect Regular and Hidden RSI Divergences:
    - Bullish Regular: Price makes Lower Low, RSI makes Higher Low (Reversal signal).
    - Bearish Regular: Price makes Higher High, RSI makes Lower High (Exhaustion signal).
    """
    bullish_div = False
    bearish_div = False
    detail = "No active divergence"
    curr_sym = df.attrs.get("currency_symbol", "") if hasattr(df, "attrs") else ""

    if len(swing_lows) >= 2:
        l1, l2 = swing_lows[-2], swing_lows[-1]
        p1, p2 = l1["price"], l2["price"]
        r1 = df["RSI"].iloc[l1["bar_index"]]
        r2 = df["RSI"].iloc[l2["bar_index"]]

        # Bullish Regular Divergence: Price Lower Low, RSI Higher Low
        if p2 < p1 and r2 > r1 and abs(l2["bar_index"] - (len(df) - 1)) <= 15:
            bullish_div = True
            detail = f"Bullish RSI Divergence: Price Lower Low ({curr_sym}{p2:.1f} < {curr_sym}{p1:.1f}) but RSI Higher Low ({r2:.1f} > {r1:.1f})"

    if len(swing_highs) >= 2:
        h1, h2 = swing_highs[-2], swing_highs[-1]
        p1, p2 = h1["price"], h2["price"]
        r1 = df["RSI"].iloc[h1["bar_index"]]
        r2 = df["RSI"].iloc[h2["bar_index"]]

        # Bearish Regular Divergence: Price Higher High, RSI Lower High
        if p2 > p1 and r2 < r1 and abs(h2["bar_index"] - (len(df) - 1)) <= 15:
            bearish_div = True
            detail = f"Bearish RSI Divergence: Price Higher High ({curr_sym}{p2:.1f} > {curr_sym}{p1:.1f}) but RSI Lower High ({r2:.1f} < {r1:.1f})"

    return {
        "bullish_divergence": bullish_div,
        "bearish_divergence": bearish_div,
        "detail": detail
    }


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute and attach full institutional indicators to the DataFrame.
    """
    df = df.copy()

    # Moving Average Ribbon
    df["EMA_20"] = calculate_ema(df["Close"], 20)
    df["EMA_50"] = calculate_ema(df["Close"], 50)
    df["EMA_200"] = calculate_ema(df["Close"], 200) if len(df) >= 200 else calculate_ema(df["Close"], min(len(df), 100))

    # RSI & Momentum
    df["RSI"] = calculate_rsi(df["Close"], 14)
    macd, signal, hist = calculate_macd(df["Close"], 12, 26, 9)
    df["MACD"] = macd
    df["MACD_Signal"] = signal
    df["MACD_Hist"] = hist

    # Volatility & Bollinger Bands
    df["ATR"] = calculate_atr(df, 14)
    bb_up, bb_mid, bb_low, bb_width = calculate_bollinger_bands(df["Close"], 20, 2.0)
    df["BB_Upper"] = bb_up
    df["BB_Middle"] = bb_mid
    df["BB_Lower"] = bb_low
    df["BB_Bandwidth"] = bb_width

    # Volatility Squeeze (Bandwidth in lowest 20th percentile)
    rolling_min_bw = df["BB_Bandwidth"].rolling(window=50, min_periods=20).min()
    df["BB_Squeeze"] = df["BB_Bandwidth"] <= (rolling_min_bw * 1.25)

    # Volume Spread Analysis (VSA)
    df["Volume_SMA_20"] = df["Volume"].rolling(window=20, min_periods=5).mean()
    df["Volume_Ratio"] = df["Volume"] / df["Volume_SMA_20"].replace(0, np.nan)
    df["Volume_Spike"] = df["Volume_Ratio"] >= 1.5

    # Scalping Micro-Indicators & Fast Ribbon
    df["EMA_9"] = calculate_ema(df["Close"], 9)
    df["EMA_21"] = calculate_ema(df["Close"], 21)
    df["RSI_7"] = calculate_rsi(df["Close"], 7)
    df["Micro_ATR"] = calculate_atr(df, 5)

    # Session VWAP and Standard Deviation Bands
    vwap, vwap_up, vwap_low = calculate_vwap(df)
    df["VWAP"] = vwap
    df["VWAP_Upper"] = vwap_up
    df["VWAP_Lower"] = vwap_low

    # Order Flow Velocity & Tape Pressure Gauge
    vol_sma_5 = df["Volume"].rolling(window=5, min_periods=2).mean().replace(0, 1.0)
    df["Volume_Velocity"] = (df["Volume"] / vol_sma_5).fillna(1.0).round(2)

    bull_force = (df["Close"] - df["Low"]) * df["Volume"]
    bear_force = (df["High"] - df["Close"]) * df["Volume"]
    total_force = (bull_force + bear_force).replace(0, 1.0)
    df["Buy_Pressure_Pct"] = ((bull_force / total_force) * 100).fillna(50.0).clip(5, 95).round(1)

    # Absorption: High volume + narrow candle spread (smart money absorbing selling)
    candle_spread = df["High"] - df["Low"]
    avg_spread = candle_spread.rolling(window=20, min_periods=5).mean()
    df["VSA_Absorption"] = (df["Volume_Ratio"] >= 1.4) & (candle_spread < avg_spread * 0.8)

    # Volume Dry-up: Low volume pullback
    df["Volume_DryUp"] = df["Volume_Ratio"] <= 0.65

    return df
