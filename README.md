# ⚡ AlphaEdge — 20-Year Veteran AI Trading Terminal

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mrmadhav0973/Trader/blob/main/AlphaEdge_Colab.ipynb)

AlphaEdge is an institutional-grade algorithmic trading analysis terminal built with the voice, mental models, and risk management of a **20+ Year Senior Veteran Trader**.

---

## 🚀 1-Click Run on Google Colab (Zero Load on PC)

Run the entire system in the cloud with **12 GB RAM on Google Cloud for FREE**:

1. Click the **[Open In Colab](https://colab.research.google.com/github/mrmadhav0973/Trader/blob/main/AlphaEdge_Colab.ipynb)** badge above.
2. Click **Runtime** → **Run all** (`Ctrl + F9`).
3. Click the generated **`loca.lt`** link to access your live terminal.

---

## 🧠 Core Features

* **20-Year Veteran Multi-Layer Confluence Engine:**
  * Market Regime & Wyckoff Stages (Stage 1 Accumulation, Stage 2 Markup, Stage 3 Distribution, Stage 4 Markdown).
  * Institutional Support & Resistance Clusters with touch-count weighting.
  * Candlestick Anatomy: Pin Bars, Hammers, Shooting Stars, Engulfing bars, and Inside-Bar Volatility Coils.
  * Volume Spread Analysis (VSA): Supply absorption, volume dry-up, Bollinger bandwidth squeezes.
  * Smart Money Concepts (SMC): Liquidity sweeps and Fair Value Gaps (FVGs).
  * Momentum & RSI Divergences (Bullish & Bearish regular divergences).
  * Algorithmic Dynamic Trendlines.

* **Multi-Market Support:**
  * **NSE & BSE (Indian Equities):** Nifty 50, Tata Power, Reliance, HDFC Bank, etc.
  * **US Equities:** NVDA, TSLA, AAPL, MSFT, AMZN, PLTR, etc.
  * **24/7 Crypto:** BTC-USD, ETH-USD, SOL-USD, AVAX-USD, LINK-USD, DOGE-USD.

* **TradingView Native Interactive Charting:**
  * Real-time candlestick charts with pan, zoom, auto-fit, and fullscreen.
  * Demand / Supply zone overlays, Entry, Stop Loss, Target 1, and Target 2 lines.

* **Real-time Tape & WebSocket Streaming:**
  * Real-time price ticks and automated breakeven stop loss trailing.

---

## 💻 Local Installation (Optional)

```bash
git clone https://github.com/mrmadhav0973/Trader.git
cd Trader
pip install -r requirements.txt
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```
Open `http://localhost:8000` in your browser.
