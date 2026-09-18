"""
AlphaEdge Trader - Market Hours & Exchange Session Engine
Accurately detects whether exchanges (NSE/BSE, NYSE/NASDAQ, Crypto)
are currently in regular trading hours, pre-market, after-hours, or closed on weekends.
"""

import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any

from core.data import COMMON_US_TICKERS, CRYPTO_MAP

# Exchange Timezones
TZ_IST = ZoneInfo("Asia/Kolkata")
TZ_ET = ZoneInfo("America/New_York")
TZ_UTC = ZoneInfo("UTC")


def get_market_status(symbol: str) -> Dict[str, Any]:
    """
    Determine if the market for the given symbol is currently OPEN or CLOSED.
    
    Returns a dictionary containing:
        - is_open: bool
        - market: str ("NSE/BSE (India)", "NYSE/NASDAQ (US)", "Crypto 24/7")
        - status: str ("OPEN", "CLOSED")
        - status_label: str ("MARKET OPEN", "MARKET CLOSED", "24/7 LIVE")
        - session_hours: str (human readable session timings)
        - reason: str (detailed explanation)
        - next_event: str (e.g. "Opens Tomorrow at 09:15 AM IST")
    """
    sym = symbol.strip().upper()
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    # 1. Crypto Assets (BTC-USD, ETH-USD, etc.) - 24/7/365
    if sym.endswith("-USD") or sym in CRYPTO_MAP or sym in ["BTC", "ETH", "SOL", "DOGE", "XRP"]:
        return {
            "symbol": sym,
            "market": "Crypto 24/7",
            "is_open": True,
            "status": "OPEN",
            "status_label": "24/7 LIVE",
            "session_hours": "Continuous 24/7/365",
            "reason": "Cryptocurrency markets operate continuously without closing.",
            "next_event": "24/7 Continuous Trading"
        }

    # 2. US Equities (NYSE / NASDAQ) - Mon-Fri 09:30 to 16:00 ET (19:00 to 01:30 IST)
    is_us = (
        sym in COMMON_US_TICKERS or
        (not sym.endswith(".NS") and not sym.endswith(".BO") and not sym.startswith("^NSE") and not sym.startswith("^INDIA"))
    )
    if is_us:
        now_et = now_utc.astimezone(TZ_ET)
        weekday = now_et.weekday()  # 0=Monday, 4=Friday, 5=Sat, 6=Sun
        hour_min = (now_et.hour, now_et.minute)
        
        is_weekday = weekday < 5
        is_session = (9, 30) <= hour_min < (16, 0)
        is_open = is_weekday and is_session

        if is_open:
            return {
                "symbol": sym,
                "market": "NYSE/NASDAQ (US)",
                "is_open": True,
                "status": "OPEN",
                "status_label": "MARKET OPEN",
                "session_hours": "09:30 - 16:00 ET (19:00 - 01:30 IST)",
                "reason": "Regular US equity session is active.",
                "next_event": "Closes today at 16:00 ET"
            }
        else:
            if not is_weekday:
                next_day = "Monday"
            else:
                next_day = "Tomorrow" if hour_min >= (16, 0) else "Today"
            
            if not is_weekday:
                reason = "Weekend: US exchanges are closed."
            elif hour_min < (9, 30):
                reason = "Pre-market: US regular session opens at 09:30 ET (07:00 PM IST)."
            else:
                reason = "After-hours: Regular session closed at 16:00 ET."

            return {
                "symbol": sym,
                "market": "NYSE/NASDAQ (US)",
                "is_open": False,
                "status": "CLOSED",
                "status_label": "MARKET CLOSED",
                "session_hours": "09:30 - 16:00 ET (19:00 - 01:30 IST)",
                "reason": reason,
                "next_event": f"Opens {next_day} at 09:30 AM ET (07:00 PM IST)"
            }

    # 3. Indian Equities & Indices (NSE / BSE) - Mon-Fri 09:15 to 15:30 IST
    now_ist = now_utc.astimezone(TZ_IST)
    weekday = now_ist.weekday()
    hour_min = (now_ist.hour, now_ist.minute)
    
    is_weekday = weekday < 5
    is_session = (9, 15) <= hour_min < (15, 30)
    is_open = is_weekday and is_session

    if is_open:
        return {
            "symbol": sym,
            "market": "NSE/BSE (India)",
            "is_open": True,
            "status": "OPEN",
            "status_label": "MARKET OPEN",
            "session_hours": "09:15 - 15:30 IST",
            "reason": "Regular NSE/BSE trading session is active.",
            "next_event": "Closes today at 15:30 IST"
        }
    else:
        if not is_weekday:
            next_day = "Monday"
        else:
            next_day = "Tomorrow" if hour_min >= (15, 30) else "Today"
            
        if not is_weekday:
            reason = "Weekend: Indian equity markets are closed."
        elif hour_min < (9, 15):
            reason = "Pre-market: NSE session opens at 09:15 AM IST."
        else:
            reason = "After-hours: Regular NSE session closed at 15:30 IST."

        return {
            "symbol": sym,
            "market": "NSE/BSE (India)",
            "is_open": False,
            "status": "CLOSED",
            "status_label": "MARKET CLOSED",
            "session_hours": "09:15 - 15:30 IST",
            "reason": reason,
            "next_event": f"Opens {next_day} at 09:15 AM IST"
        }
