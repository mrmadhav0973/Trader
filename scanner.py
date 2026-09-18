"""
AlphaEdge Trader - Command Line Scanner & Signal Generator
Quickly analyze single stocks or scan entire watchlists from your terminal.
"""

import argparse
import sys

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from core.data import fetch_ohlcv, DEFAULT_WATCHLIST, normalize_symbol
from core.signals import analyze_symbol

console = Console()


def print_symbol_analysis(symbol: str, capital: float = 5000.0, timeframe: str = "1d"):
    norm_sym = normalize_symbol(symbol)
    console.print(f"\n[bold cyan]Fetching & analyzing {norm_sym} ({timeframe})...[/bold cyan]")

    try:
        df = fetch_ohlcv(norm_sym, timeframe=timeframe)
        analysis = analyze_symbol(df, capital=capital, risk_pct=0.02)
    except Exception as e:
        console.print(f"[bold red]Error analyzing {norm_sym}: {e}[/bold red]")
        return

    risk = analysis["risk_plan"]
    p = analysis["current_price"]
    score = analysis["confluence_score"]
    sig = analysis["signal_type"]
    grade = analysis["signal_grade"]

    # Color tagging
    sig_color = "green" if "BUY" in sig else ("yellow" if "WATCH" in sig else "red")

    card_content = f"""
[bold white]CURRENT MARKET STATUS[/bold white]
• Asset: [bold yellow]{norm_sym}[/bold yellow] ({timeframe.upper()})
• Last Traded Price: [bold cyan]₹{p:,.2f}[/bold cyan]
• RSI (14): [magenta]{analysis['rsi']:.1f}[/magenta] | ATR: [blue]₹{analysis['atr']:.2f}[/blue]
• Signal: [bold {sig_color}]{sig} ({grade})[/bold {sig_color}]
• Confluence Match: [bold {sig_color}]{score}%[/bold {sig_color}]

[bold white]PLANNED TRADE EXECUTION BLUEPRINT[/bold white]
• Entry Price: [cyan]₹{risk['entry_price']:,.2f}[/cyan]
• Strict Stop Loss: [bold red]₹{risk['stop_loss']:,.2f}[/bold red] (Risk: ₹{risk['risk_per_share']:.2f}/share)
• Target 1 (1:2 R:R): [bold green]₹{risk['target_1']:,.2f}[/bold green] (+₹{risk['profit_target_1']:,.0f} profit)
• Target 2 (1:3 R:R): [bold green]₹{risk['target_2']:,.2f}[/bold green] (+₹{risk['profit_target_2']:,.0f} profit)

[bold white]CAPITAL & RISK MANAGEMENT (Capital: ₹{capital:,.0f})[/bold white]
• Recommended Buy: [bold yellow]{risk['quantity']} Shares[/bold yellow]
• Total Capital Deployed: [white]₹{risk['capital_deployed']:,.2f}[/white]
• Remaining Cash Buffer: [white]₹{risk['remaining_cash']:,.2f}[/white]
• Maximum Potential Loss: [bold red]-₹{risk['max_loss']:,.2f}[/bold red] (Strictly {risk['actual_risk_pct']:.1f}% of capital)
• Expected Gain (Target 1): [bold green]+₹{risk['profit_target_1']:,.2f}[/bold green] (+{risk['profit_pct_target_1']:.1f}%)
    """

    panel = Panel(
        card_content.strip(),
        title=f"[bold green]AlphaEdge Confluence Card - {norm_sym}[/bold green]",
        border_style="bright_blue"
    )
    console.print(panel)

    # Confluence Checklist Table
    table = Table(title="Confluence Verification Checklist", box=None)
    table.add_column("Factor", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Technical Details", style="white")

    for f in analysis["confluence_factors"]:
        status_text = "[bold green]PASS[/bold green]" if f["passed"] else "[dim red]WAIT[/dim red]"
        table.add_row(f["name"], status_text, f["detail"])

    console.print(table)


def run_batch_scan(capital: float = 5000.0, timeframe: str = "1d"):
    console.print(f"\n[bold yellow]⚡ Running AlphaEdge Screener across {len(DEFAULT_WATCHLIST)} Watchlist Stocks...[/bold yellow]\n")

    table = Table(title="Market Screener - Top Ranked Setups", show_lines=True)
    table.add_column("Rank", justify="center", style="bold")
    table.add_column("Symbol", style="cyan")
    table.add_column("Price (₹)", justify="right")
    table.add_column("Confluence", justify="center")
    table.add_column("Signal", justify="center")
    table.add_column("Shares (₹5k Cap)", justify="center")
    table.add_column("Stop Loss", justify="right")
    table.add_column("Target 1", justify="right")
    table.add_column("Max Risk", justify="right", style="red")

    results = []

    for sym in DEFAULT_WATCHLIST:
        try:
            df = fetch_ohlcv(sym, timeframe=timeframe)
            a = analyze_symbol(df, capital=capital, risk_pct=0.02)
            rp = a["risk_plan"]
            results.append({
                "sym": sym,
                "price": a["current_price"],
                "score": a["confluence_score"],
                "sig": a["signal_type"],
                "grade": a["signal_grade"],
                "shares": rp["quantity"],
                "sl": rp["stop_loss"],
                "t1": rp["target_1"],
                "risk": rp["max_loss"]
            })
        except Exception:
            continue

    # Sort by Confluence Score
    results.sort(key=lambda x: x["score"], reverse=True)

    for i, r in enumerate(results, start=1):
        color = "green" if "BUY" in r["sig"] else ("yellow" if "WATCH" in r["sig"] else "red")
        table.add_row(
            str(i),
            r["sym"],
            f"₹{r['price']:,.2f}",
            f"{r['score']}% ({r['grade']})",
            f"[{color}]{r['sig']}[/{color}]",
            str(r["shares"]),
            f"₹{r['sl']:,.2f}",
            f"₹{r['t1']:,.2f}",
            f"-₹{r['risk']:,.0f}"
        )

    console.print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AlphaEdge Trading Signal Scanner")
    parser.add_argument("--symbol", type=str, default="TATAPOWER.NS", help="Ticker symbol to analyze")
    parser.add_argument("--capital", type=float, default=5000.0, help="Trading capital in INR (default: 5000)")
    parser.add_argument("--timeframe", type=str, default="1d", help="Candle timeframe (15m, 1h, 4h, 1d)")
    parser.add_argument("--scan-all", action="store_true", help="Run batch scan on all watchlist stocks")

    args = parser.parse_args()

    if args.scan_all:
        run_batch_scan(capital=args.capital, timeframe=args.timeframe)
    else:
        print_symbol_analysis(symbol=args.symbol, capital=args.capital, timeframe=args.timeframe)
