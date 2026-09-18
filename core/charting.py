"""
Interactive Charting Module
Builds multi-pane Plotly figures rendering candlesticks, trendlines, S/R zones,
FVG boxes, trade markers, volume, and RSI in Light & Dark modes.
"""

from typing import Any
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_analysis_chart(
    analysis: dict[str, Any],
    theme: str = "dark",
    show_trendlines: bool = True,
    show_zones: bool = True,
    show_smc: bool = True,
    show_emas: bool = True,
    show_trade_overlay: bool = True
) -> go.Figure:
    """
    Generate an interactive Plotly chart with all analytical layers.

    Args:
        analysis: Dictionary returned by core.signals.analyze_symbol.
        theme: 'dark' (Black & Grey) or 'light' (White & Navy Blue).
        show_trendlines: Toggle algorithmic trendlines.
        show_zones: Toggle horizontal S/R zones.
        show_smc: Toggle FVG boxes and liquidity sweep points.
        show_emas: Toggle 20 & 50 EMA lines.
        show_trade_overlay: Toggle Entry, Stop Loss, and Target lines.

    Returns:
        plotly.graph_objects.Figure
    """
    df = analysis["df"].copy()
    risk_plan = analysis.get("risk_plan", {})
    trendlines = analysis.get("trendlines", {})
    sr_zones = analysis.get("sr_zones", [])
    fvgs = analysis.get("fvgs", [])
    sweeps = analysis.get("sweeps", [])

    is_dark = theme.lower() == "dark"

    # Color Palette Tokens
    bg_canvas = "#090B0E" if is_dark else "#FFFFFF"
    grid_color = "#18202C" if is_dark else "#F1F5F9"
    text_color = "#F8FAFC" if is_dark else "#0A192F"
    text_muted = "#94A3B8" if is_dark else "#64748B"

    bull_color = "#10B981"
    bear_color = "#EF4444"
    ema20_color = "#3B82F6"
    ema50_color = "#F59E0B"
    trendline_color = "#00E5FF" if is_dark else "#1E3A8A"
    curr_sym = df.attrs.get("currency_symbol", "₹") if hasattr(df, "attrs") else "₹"

    # Create 3-row subplot: 1. Main Candlestick (65%), 2. Volume (15%), 3. RSI (20%)
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.65, 0.15, 0.20],
        subplot_titles=("", "Volume", "RSI (14)")
    )

    # 1. Candlestick Chart (Row 1)
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="OHLC",
            increasing_line_color=bull_color,
            decreasing_line_color=bear_color,
            increasing_fillcolor=bull_color,
            decreasing_fillcolor=bear_color
        ),
        row=1,
        col=1
    )

    # 2. EMAs
    if show_emas:
        if "EMA_20" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["EMA_20"],
                    name="20 EMA",
                    line=dict(color=ema20_color, width=1.8)
                ),
                row=1,
                col=1
            )
        if "EMA_50" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["EMA_50"],
                    name="50 EMA",
                    line=dict(color=ema50_color, width=1.5, dash="dot")
                ),
                row=1,
                col=1
            )

    # 3. Algorithmic Trendlines
    if show_trendlines:
        supp = trendlines.get("support_line")
        if supp:
            fig.add_trace(
                go.Scatter(
                    x=[supp["start_time"], supp["end_time"]],
                    y=[supp["start_price"], supp["end_price"]],
                    mode="lines+text",
                    name="Support Trendline",
                    line=dict(color=trendline_color, width=2, dash="dash"),
                    text=["", "Dynamic Support"],
                    textposition="top right",
                    textfont=dict(size=10, color=trendline_color)
                ),
                row=1,
                col=1
            )

        res = trendlines.get("resistance_line")
        if res:
            fig.add_trace(
                go.Scatter(
                    x=[res["start_time"], res["end_time"]],
                    y=[res["start_price"], res["end_price"]],
                    mode="lines+text",
                    name="Resistance Trendline",
                    line=dict(color="#DC2626" if not is_dark else "#F87171", width=2, dash="dash"),
                    text=["", "Dynamic Resistance"],
                    textposition="bottom right",
                    textfont=dict(size=10, color="#EF4444")
                ),
                row=1,
                col=1
            )

    # 4. Support & Resistance Shaded Zones
    if show_zones:
        start_x = df.index[max(0, len(df) - 60)]
        end_x = df.index[-1]
        for zone in sr_zones[:4]:
            is_sup = zone["type"] == "support"
            fill = "rgba(16, 185, 129, 0.15)" if is_sup else "rgba(239, 68, 68, 0.12)"
            line_col = bull_color if is_sup else bear_color

            fig.add_shape(
                type="rect",
                x0=start_x,
                x1=end_x,
                y0=zone["min_price"],
                y1=zone["max_price"],
                fillcolor=fill,
                line=dict(color=line_col, width=1, dash="dot"),
                row=1,
                col=1
            )
            fig.add_annotation(
                x=start_x,
                y=zone["mid_price"],
                text=f"{'DEMAND' if is_sup else 'SUPPLY'} ZONE ({curr_sym}{zone['mid_price']:.1f})",
                showarrow=False,
                xanchor="left",
                font=dict(size=9, color=line_col),
                row=1,
                col=1
            )

    # 5. Smart Money Concepts (FVG & Sweeps)
    if show_smc:
        for fvg in fvgs:
            if not fvg["is_mitigated"]:
                is_bull_fvg = fvg["type"] == "bullish"
                fvg_fill = "rgba(59, 130, 246, 0.2)" if is_bull_fvg else "rgba(245, 158, 11, 0.2)"
                fvg_line = ema20_color if is_bull_fvg else ema50_color

                fig.add_shape(
                    type="rect",
                    x0=fvg["time_created"],
                    x1=df.index[-1],
                    y0=fvg["bottom"],
                    y1=fvg["top"],
                    fillcolor=fvg_fill,
                    line=dict(color=fvg_line, width=1),
                    row=1,
                    col=1
                )

        # Liquidity sweeps
        for sw in sweeps:
            fig.add_annotation(
                x=sw["time"],
                y=sw.get("sweep_wick_low", sw.get("sweep_wick_high")),
                text="⚡ Sweep",
                showarrow=True,
                arrowhead=2,
                arrowcolor="#F59E0B",
                font=dict(size=9, color="#F59E0B"),
                row=1,
                col=1
            )

    # 6. Trade Execution Blueprint Lines (Entry, SL, Targets)
    if show_trade_overlay and risk_plan:
        entry = risk_plan["entry_price"]
        sl = risk_plan["stop_loss"]
        t1 = risk_plan["target_1"]
        t2 = risk_plan["target_2"]

        last_bars_x = df.index[-min(25, len(df))]
        future_x = df.index[-1]

        # Entry Line (Blue)
        fig.add_shape(
            type="line",
            x0=last_bars_x, x1=future_x,
            y0=entry, y1=entry,
            line=dict(color="#3B82F6", width=2.5),
            row=1, col=1
        )
        fig.add_annotation(
            x=future_x, y=entry,
            text=f" ENTRY: {curr_sym}{entry:.2f}",
            showarrow=False, xanchor="left",
            font=dict(color="#FFF", size=10),
            bgcolor="#3B82F6", borderpad=3,
            row=1, col=1
        )

        # Stop Loss Line (Red dashed)
        fig.add_shape(
            type="line",
            x0=last_bars_x, x1=future_x,
            y0=sl, y1=sl,
            line=dict(color="#EF4444", width=2, dash="dash"),
            row=1, col=1
        )
        fig.add_annotation(
            x=future_x, y=sl,
            text=f" SL: {curr_sym}{sl:.2f} (-{curr_sym}{risk_plan['max_loss']:.0f})",
            showarrow=False, xanchor="left",
            font=dict(color="#FFF", size=10),
            bgcolor="#EF4444", borderpad=3,
            row=1, col=1
        )

        # Target 1 (Green dashed)
        fig.add_shape(
            type="line",
            x0=last_bars_x, x1=future_x,
            y0=t1, y1=t1,
            line=dict(color="#10B981", width=2, dash="dash"),
            row=1, col=1
        )
        fig.add_annotation(
            x=future_x, y=t1,
            text=f" T1: {curr_sym}{t1:.2f} (+{curr_sym}{risk_plan['profit_target_1']:.0f})",
            showarrow=False, xanchor="left",
            font=dict(color="#FFF", size=10),
            bgcolor="#10B981", borderpad=3,
            row=1, col=1
        )

        # Target 2 (Green dotted)
        fig.add_shape(
            type="line",
            x0=last_bars_x, x1=future_x,
            y0=t2, y1=t2,
            line=dict(color="#059669", width=1.5, dash="dot"),
            row=1, col=1
        )
        fig.add_annotation(
            x=future_x, y=t2,
            text=f" T2: {curr_sym}{t2:.2f} (+{curr_sym}{risk_plan['profit_target_2']:.0f})",
            showarrow=False, xanchor="left",
            font=dict(color="#FFF", size=10),
            bgcolor="#059669", borderpad=3,
            row=1, col=1
        )

    # 7. Volume Bars (Row 2)
    vol_colors = [bull_color if c >= o else bear_color for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="Volume",
            marker=dict(color=vol_colors, opacity=0.7)
        ),
        row=2,
        col=1
    )
    if "Volume_SMA_20" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Volume_SMA_20"],
                name="Vol SMA (20)",
                line=dict(color="#94A3B8", width=1.2)
            ),
            row=2,
            col=1
        )

    # 8. RSI Subplot (Row 3)
    if "RSI" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["RSI"],
                name="RSI (14)",
                line=dict(color="#8B5CF6", width=1.8)
            ),
            row=3,
            col=1
        )
        # 70 & 30 Lines
        fig.add_shape(
            type="line",
            x0=df.index[0], x1=df.index[-1],
            y0=70, y1=70,
            line=dict(color=text_muted, width=1, dash="dot"),
            row=3, col=1
        )
        fig.add_shape(
            type="line",
            x0=df.index[0], x1=df.index[-1],
            y0=30, y1=30,
            line=dict(color=text_muted, width=1, dash="dot"),
            row=3, col=1
        )

    # Global Layout Styling
    fig.update_layout(
        template="plotly_dark" if is_dark else "plotly_white",
        paper_bgcolor=bg_canvas,
        plot_bgcolor=bg_canvas,
        font=dict(family="Plus Jakarta Sans, sans-serif", color=text_color),
        margin=dict(l=40, r=90, t=30, b=30),
        height=720,
        showlegend=False,
        xaxis=dict(
            gridcolor=grid_color,
            rangeslider=dict(visible=False),
            showline=True,
            linecolor=grid_color
        ),
        yaxis=dict(
            gridcolor=grid_color,
            showline=True,
            linecolor=grid_color,
            side="right"
        ),
        xaxis2=dict(gridcolor=grid_color),
        yaxis2=dict(gridcolor=grid_color, side="right"),
        xaxis3=dict(gridcolor=grid_color),
        yaxis3=dict(gridcolor=grid_color, side="right", range=[10, 90])
    )

    return fig
