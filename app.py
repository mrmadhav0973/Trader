"""
AlphaEdge Trader - Interactive Web Dashboard
Powered by Streamlit, Plotly, and the AlphaEdge Confluence Engine.
"""

import streamlit as st
import pandas as pd
from core.data import fetch_ohlcv, DEFAULT_WATCHLIST, normalize_symbol
from core.signals import analyze_symbol
from core.charting import create_analysis_chart

# Streamlit Page Config
st.set_page_config(
    page_title="AlphaEdge Pro - Algorithmic Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling according to UI/UX Pro Max and user theme specifications
def inject_custom_styles(theme: str):
    is_dark = theme == "Dark (Black & Grey)"

    if is_dark:
        bg_canvas = "#090B0E"
        bg_card = "#111620"
        border_col = "#212A38"
        text_primary = "#F8FAFC"
        text_muted = "#94A3B8"
        accent_navy = "#151B26"
        badge_bg = "#1E293B"
    else:
        # Light Theme (White & Navy Blue)
        bg_canvas = "#F4F7FC"
        bg_card = "#FFFFFF"
        border_col = "#E2E8F0"
        text_primary = "#0A192F"     # Deep Navy
        text_muted = "#475569"
        accent_navy = "#0A192F"      # Rich Navy Blue Card Accent
        badge_bg = "#E0E7FF"

    st.markdown(f"""
    <style>
        /* Base page styling */
        .stApp {{
            background-color: {bg_canvas};
            color: {text_primary};
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
        }}
        
        /* Metric and Card containers */
        div[data-testid="stMetric"] {{
            background-color: {bg_card};
            border: 1px solid {border_col};
            padding: 14px 18px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }}
        div[data-testid="stMetricLabel"] {{
            color: {text_muted} !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            text-transform: uppercase;
        }}
        div[data-testid="stMetricValue"] {{
            color: {text_primary} !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 20px !important;
            font-weight: 800 !important;
        }}
        
        /* Custom card container */
        .trade-card {{
            background-color: {bg_card};
            border: 1px solid {border_col};
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
        }}

        .blueprint-header {{
            font-size: 16px;
            font-weight: 800;
            color: {text_primary};
            margin-bottom: 12px;
        }}

        .confluence-badge-high {{
            background-color: rgba(16, 185, 129, 0.15);
            color: #10B981;
            padding: 4px 12px;
            border-radius: 999px;
            font-weight: 800;
            font-size: 13px;
            display: inline-block;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        
        .confluence-badge-mid {{
            background-color: rgba(245, 158, 11, 0.15);
            color: #F59E0B;
            padding: 4px 12px;
            border-radius: 999px;
            font-weight: 800;
            font-size: 13px;
            display: inline-block;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}

        /* Buttons */
        .stButton>button {{
            border-radius: 8px;
            font-weight: 700;
            transition: all 0.2s ease;
        }}
    </style>
    """, unsafe_allow_html=True)


# Initialize Session State
if "selected_symbol" not in st.session_state:
    st.session_state["selected_symbol"] = "TATAPOWER.NS"
if "capital" not in st.session_state:
    st.session_state["capital"] = 5000.0


# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.markdown("### ⚙️ Terminal Settings")

    # Theme Switcher
    theme_choice = st.radio(
        "Theme Mode",
        options=["Dark (Black & Grey)", "Light (White & Navy Blue)"],
        index=0,
        horizontal=True
    )
    selected_theme = "dark" if "Dark" in theme_choice else "light"

    st.markdown("---")

    # Dynamic Capital Controls (Default ₹5,000)
    st.markdown("### 💰 Capital Management")
    st.caption("Change capital dynamically. Risk is automatically sized to protect your funds.")

    col_c1, col_c2, col_c3 = st.columns(3)
    if col_c1.button("₹5,000"):
        st.session_state["capital"] = 5000.0
    if col_c2.button("₹10,000"):
        st.session_state["capital"] = 10000.0
    if col_c3.button("₹25,000"):
        st.session_state["capital"] = 25000.0

    capital_input = st.number_input(
        "Available Capital (₹)",
        min_value=500.0,
        max_value=10000000.0,
        value=float(st.session_state["capital"]),
        step=500.0
    )
    st.session_state["capital"] = capital_input

    risk_pct_input = st.slider(
        "Risk Per Trade (%)",
        min_value=0.5,
        max_value=5.0,
        value=2.0,
        step=0.5,
        help="Recommended: 2.0% max loss per trade to ensure long-term survivability."
    )
    risk_fraction = risk_pct_input / 100.0

    st.markdown("---")

    # Chart & Analysis Overlays
    st.markdown("### 🔍 Indicator & SMC Layers")
    show_trendlines = st.checkbox("Algorithmic Trendlines", value=True)
    show_zones = st.checkbox("Support / Resistance Zones", value=True)
    show_smc = st.checkbox("Fair Value Gaps & Sweeps", value=True)
    show_emas = st.checkbox("20 & 50 EMAs", value=True)
    show_trade_lines = st.checkbox("Trade Levels (Entry, SL, Targets)", value=True)

# Inject matching styles
inject_custom_styles(theme_choice)

# --- MAIN APP HEADER ---
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
    <div>
        <h1 style="margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;">
            AlphaEdge Pro <span style="font-size: 13px; padding: 2px 8px; border-radius: 4px; background: rgba(59, 130, 246, 0.15); color: #3B82F6; vertical-align: middle;">v2.0</span>
        </h1>
        <p style="margin: 0; font-size: 13px; color: #94A3B8;">Algorithmic Confluence Trading Terminal • Trendlines • Zones • SMC • ₹5,000 Risk Sizing</p>
    </div>
    <div style="text-align: right; background: {'#111620' if selected_theme == 'dark' else '#FFFFFF'}; border: 1px solid {'#212A38' if selected_theme == 'dark' else '#E2E8F0'}; padding: 8px 16px; border-radius: 8px;">
        <span style="font-size: 11px; text-transform: uppercase; color: #94A3B8; font-weight: 700;">Account Capital</span><br>
        <span style="font-family: monospace; font-size: 16px; font-weight: 800; color: #10B981;">₹{st.session_state['capital']:,.2f}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# TABS: 1. Active Analysis, 2. Market Screener
tab_chart, tab_screener = st.tabs(["📊 Technical Analysis & Execution", "⚡ 1-Click Market Screener"])


# ==============================================================================
# TAB 1: TECHNICAL ANALYSIS & EXECUTION
# ==============================================================================
with tab_chart:
    # Controls Toolbar
    col_t1, col_t2, col_t3 = st.columns([3, 2, 2])

    with col_t1:
        preset_sym = st.selectbox(
            "Quick Select Watchlist",
            options=DEFAULT_WATCHLIST,
            index=0
        )
    with col_t2:
        custom_sym = st.text_input("Or Enter Any Ticker (NSE / US / Crypto)", value="")
    with col_t3:
        timeframe = st.selectbox("Timeframe", options=["1d", "4h", "1h", "15m"], index=0)

    active_symbol = custom_sym.strip() if custom_sym.strip() else preset_sym
    normalized_sym = normalize_symbol(active_symbol)

    # Fetch Data & Run Analysis
    with st.spinner(f"Analyzing {normalized_sym} across structural, volume, and SMC models..."):
        try:
            df = fetch_ohlcv(normalized_sym, timeframe=timeframe)
            analysis = analyze_symbol(
                df,
                capital=st.session_state["capital"],
                risk_pct=risk_fraction
            )
            data_loaded = True
        except Exception as e:
            st.error(f"Error fetching data for {normalized_sym}: {str(e)}")
            data_loaded = False

    if data_loaded:
        risk_plan = analysis["risk_plan"]
        current_p = analysis["current_price"]
        confluence = analysis["confluence_score"]
        signal_type = analysis["signal_type"]

        # Top Metric Banner
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Current Price", f"₹{current_p:,.2f}")
        m2.metric("Signal Recommendation", signal_type)
        m3.metric("Confluence Score", f"{confluence}%", delta=analysis["signal_grade"])
        m4.metric("Position Size", f"{risk_plan['quantity']} Shares", f"₹{risk_plan['capital_deployed']:,.0f}")
        m5.metric("Max Capital Risk", f"-₹{risk_plan['max_loss']:,.2f}", f"{risk_plan['actual_risk_pct']:.1f}%")

        # Main Workspace: 2 Columns (Chart on Left, Execution Card on Right)
        col_chart, col_panel = st.columns([7, 3])

        with col_chart:
            # Render the Interactive Plotly Chart
            fig = create_analysis_chart(
                analysis=analysis,
                theme=selected_theme,
                show_trendlines=show_trendlines,
                show_zones=show_zones,
                show_smc=show_smc,
                show_emas=show_emas,
                show_trade_overlay=show_trade_lines
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})

        with col_panel:
            # Trade Execution Blueprint Box
            is_bullish = "BUY" in signal_type
            badge_class = "confluence-badge-high" if confluence >= 70 else "confluence-badge-mid"

            st.markdown(f"""
            <div class="trade-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div class="blueprint-header">Trade Execution Plan</div>
                    <span class="{badge_class}">{signal_type}</span>
                </div>
                <div style="font-size: 12px; margin-bottom: 16px;">
                    <strong>Asset:</strong> {normalized_sym} ({timeframe})<br>
                    <strong>Execution Type:</strong> Cash / Delivery (CNC)<br>
                    <strong>Confluence Quality:</strong> {confluence}% ({analysis['signal_grade']})
                </div>
            """, unsafe_allow_html=True)

            # Execution Prices Grid
            st.markdown("##### 🎯 Planned Price Targets")
            st.write(f"• **Buy Entry Range:** `₹{risk_plan['entry_price'] - (analysis['atr']*0.2):,.2f} – ₹{risk_plan['entry_price']:,.2f}`")
            st.write(f"• **Strict Stop Loss:** `₹{risk_plan['stop_loss']:,.2f}` (`-₹{risk_plan['risk_per_share']:.2f}` / share)")
            st.write(f"• **Target 1 (1:2 R:R):** `₹{risk_plan['target_1']:,.2f}` (`+₹{risk_plan['profit_target_1']:.0f}` gain)")
            st.write(f"• **Target 2 (1:3 R:R):** `₹{risk_plan['target_2']:,.2f}` (`+₹{risk_plan['profit_target_2']:.0f}` gain)")

            st.markdown("---")

            # Risk Sizing Breakdown
            st.markdown("##### 🛡️ ₹5,000 Capital Protection Engine")
            st.write(f"• **Recommended Buy:** **{risk_plan['quantity']} Shares**")
            st.write(f"• **Capital Required:** `₹{risk_plan['capital_deployed']:,.2f}`")
            st.write(f"• **Cash Buffer Remaining:** `₹{risk_plan['remaining_cash']:,.2f}`")
            st.write(f"• **Worst-Case Loss:** `₹{risk_plan['max_loss']:,.2f}` (Strictly ≤ {risk_pct_input}% of capital)")
            st.write(f"• **Expected Profit (Target 1):** `+₹{risk_plan['profit_target_1']:,.2f}` (`+{risk_plan['profit_pct_target_1']:.1f}%` on capital)")

            if risk_plan.get("is_oversized_risk"):
                st.warning("⚠️ Note: 1 share exceeds the strict 2% risk limit due to high share price.")
            elif not risk_plan.get("is_affordable"):
                st.error("❌ Share price exceeds total available capital. Increase capital or select lower-priced stocks.")

            st.markdown("</div>", unsafe_allow_html=True)

            # Confluence Checklist
            with st.expander("📋 Confluence Checklist Breakdown", expanded=True):
                for factor in analysis["confluence_factors"]:
                    icon = "✅" if factor["passed"] else "⚪"
                    st.write(f"{icon} **{factor['name']}:** {factor['detail']}")


# ==============================================================================
# TAB 2: 1-CLICK MARKET SCREENER
# ==============================================================================
with tab_screener:
    st.markdown("### ⚡ Live Confluence Screener")
    st.caption("Scans top Indian stocks on the Daily timeframe, calculates confluence scores, and finds the highest probability swing opportunities.")

    col_s1, col_s2 = st.columns([2, 5])
    with col_s1:
        run_scan = st.button("🚀 Run Live Market Scan", use_container_width=True)

    if run_scan:
        scan_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, sym in enumerate(DEFAULT_WATCHLIST):
            status_text.text(f"Scanning {sym} ({idx+1}/{len(DEFAULT_WATCHLIST)})...")
            try:
                s_df = fetch_ohlcv(sym, timeframe="1d")
                s_analysis = analyze_symbol(s_df, capital=st.session_state["capital"], risk_pct=risk_fraction)
                rp = s_analysis["risk_plan"]

                scan_results.append({
                    "Symbol": sym,
                    "Price (₹)": f"₹{s_analysis['current_price']:,.2f}",
                    "Signal": s_analysis["signal_type"],
                    "Grade": s_analysis["signal_grade"],
                    "Confluence Score": s_analysis["confluence_score"],
                    "Recommended Shares": rp["quantity"],
                    "Target 1 (₹)": f"₹{rp['target_1']:,.2f}",
                    "Stop Loss (₹)": f"₹{rp['stop_loss']:,.2f}",
                    "Max Risk (₹)": f"-₹{rp['max_loss']:,.0f}"
                })
            except Exception as e:
                continue
            progress_bar.progress((idx + 1) / len(DEFAULT_WATCHLIST))

        status_text.text("Market scan complete!")

        if scan_results:
            results_df = pd.DataFrame(scan_results)
            results_df.sort_values(by="Confluence Score", ascending=False, inplace=True)
            st.dataframe(
                results_df,
                use_container_width=True,
                hide_index=True
            )
            st.success(f"Successfully ranked {len(scan_results)} setups! Top opportunities are highlighted at the top.")
        else:
            st.warning("Could not complete scan. Please check your internet connection.")
