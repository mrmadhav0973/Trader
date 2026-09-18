"""
AlphaEdge Trader - Market Hours & Exchange Session Engine
Accurately detects whether exchanges (NSE/BSE, NYSE/NASDAQ, CME Commodities, Crypto)
are currently in regular trading hours, pre-market, after-hours, or closed on weekends.
"""

import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any

from core.data import COMMON_US_TICKERS, CRYPTO_MAP, COMMODITY_MAP, INDEX_MAP

# Exchange Timezones
TZ_IST = ZoneInfo("Asia/Kolkata")
TZ_ET = ZoneInfo("America/New_York")
TZ_UTC = ZoneInfo("UTC")


def get_asset_category(symbol: str) -> str:
    """
    Categorize symbol into: 'crypto', 'commodities', 'stocks', or 'indices'.
    """
    sym = symbol.strip().upper()
    if sym.endswith("-USD") or sym in CRYPTO_MAP or sym in ["BTC", "ETH", "SOL", "DOGE", "XRP", "BNB", "ADA", "AVAX", "LINK", "NEAR", "SUI", "LTC"]:
        return "crypto"
    if sym.endswith("=F") or sym.endswith(".MCX") or sym in COMMODITY_MAP or sym in ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "BZ=F"]:
        return "commodities"
    if sym.startswith("^") or sym in INDEX_MAP:
        return "indices"
    return "stocks"


def get_market_status(symbol: str) -> Dict[str, Any]:
    """
    Determine if the market for the given symbol is currently OPEN or CLOSED.
    
    Returns a dictionary containing:
        - symbol: str
        - category: str ("crypto", "commodities", "stocks", "indices")
        - is_open: bool
        - market: str ("NSE/BSE (India)", "NYSE/NASDAQ (US)", "CME/NYMEX (Commodities)", "Crypto 24/7")
        - status: str ("OPEN", "CLOSED")
        - status_label: str ("MARKET OPEN", "MARKET CLOSED", "24/7 LIVE")
        - session_hours: str (human readable session timings)
        - reason: str (detailed explanation)
        - next_event: str (e.g. "Opens Tomorrow at 09:15 AM IST")
    """
    sym = symbol.strip().upper()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    category = get_asset_category(sym)

    # 1. Crypto Assets (BTC-USD, ETH-USD, etc.) - 24/7/365
    if category == "crypto":
        return {
            "symbol": sym,
            "category": "crypto",
            "market": "Crypto 24/7",
            "is_open": True,
            "status": "OPEN",
            "status_label": "24/7 LIVE",
            "session_hours": "Continuous 24/7/365",
            "reason": "Cryptocurrency markets operate continuously without closing.",
            "next_event": "24/7 Continuous Trading"
        }

    # 2. Commodity Futures (CME / NYMEX: =F, or MCX India: .MCX)
    if category == "commodities":
        if sym.endswith(".MCX"):
            now_ist = now_utc.astimezone(TZ_IST)
            weekday = now_ist.weekday()  # 0=Mon, 4=Fri, 5=Sat, 6=Sun
            hour_min = (now_ist.hour, now_ist.minute)
            is_weekday = weekday < 5
            is_session = (9, 0) <= hour_min < (23, 30)
            is_open = is_weekday and is_session
            return {
                "symbol": sym,
                "category": "commodities",
                "market": "MCX (India Commodities)",
                "is_open": is_open,
                "status": "OPEN" if is_open else "CLOSED",
                "status_label": "MARKET OPEN" if is_open else "MARKET CLOSED",
                "session_hours": "09:00 - 23:30 IST",
                "reason": "MCX Commodity session is active." if is_open else ("Weekend: MCX is closed." if not is_weekday else "MCX session is closed."),
                "next_event": "Closes at 23:30 IST" if is_open else "Opens next weekday at 09:00 IST"
            }
        else:
            # CME / NYMEX Globex Commodity Futures (GC=F, CL=F, SI=F, NG=F, HG=F, BZ=F)
            now_et = now_utc.astimezone(TZ_ET)
            weekday = now_et.weekday()  # 0=Mon, 4=Fri, 5=Sat, 6=Sun
            hour_min = (now_et.hour, now_et.minute)
            
            if weekday == 4 and hour_min >= (17, 0):  # Friday after 17:00 ET
                is_open = False
                reason = "Weekend: CME commodity futures closed until Sunday 18:00 ET."
                next_event = "Opens Sunday at 18:00 ET"
            elif weekday == 5:  # Saturday
                is_open = False
                reason = "Weekend: CME commodity futures are closed."
                next_event = "Opens Sunday at 18:00 ET"
            elif weekday == 6:  # Sunday
                if hour_min < (18, 0):
                    is_open = False
                    reason = "Weekend: CME commodity futures open at 18:00 ET."
                    next_event = "Opens today at 18:00 ET"
                else:
                    is_open = True
                    reason = "CME Globex commodity session is active."
                    next_event = "Daily break tomorrow at 17:00 ET"
            else:  # Monday to Thursday
                if (17, 0) <= hour_min < (18, 0):
                    is_open = False
                    reason = "Daily maintenance break: CME futures reopen at 18:00 ET."
                    next_event = "Reopens today at 18:00 ET"
                else:
                    is_open = True
                    reason = "CME Globex commodity session is active."
                    next_event = "Daily break at 17:00 ET" if hour_min < (17, 0) else "Closes tomorrow at 17:00 ET"

            return {
                "symbol": sym,
                "category": "commodities",
                "market": "CME/NYMEX (Commodities)",
                "is_open": is_open,
                "status": "OPEN" if is_open else "CLOSED",
                "status_label": "MARKET OPEN" if is_open else "MARKET CLOSED",
                "session_hours": "Sun 18:00 ET - Fri 17:00 ET (23h/day)",
                "reason": reason,
                "next_event": next_event
            }

    # 3. US Equities (NYSE / NASDAQ) - Mon-Fri 09:30 to 16:00 ET (19:00 to 01:30 IST)
    is_us = (
        sym in COMMON_US_TICKERS or
        (not sym.endswith(".NS") and not sym.endswith(".BO") and not sym.startswith("^NSE") and not sym.startswith("^INDIA") and not sym.endswith(".MCX") and not sym.endswith("=F"))
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
                "category": "stocks",
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
                "category": "stocks",
                "market": "NYSE/NASDAQ (US)",
                "is_open": False,
                "status": "CLOSED",
                "status_label": "MARKET CLOSED",
                "session_hours": "09:30 - 16:00 ET (19:00 - 01:30 IST)",
                "reason": reason,
                "next_event": f"Opens {next_day} at 09:30 AM ET (07:00 PM IST)"
            }

    # 4. Indian Equities & Indices (NSE / BSE) - Mon-Fri 09:15 to 15:30 IST
    now_ist = now_utc.astimezone(TZ_IST)
    weekday = now_ist.weekday()
    hour_min = (now_ist.hour, now_ist.minute)
    
    is_weekday = weekday < 5
    is_session = (9, 15) <= hour_min < (15, 30)
    is_open = is_weekday and is_session

    if is_open:
        return {
            "symbol": sym,
            "category": "stocks" if not sym.startswith("^") else "indices",
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
            "category": "stocks" if not sym.startswith("^") else "indices",
            "market": "NSE/BSE (India)",
            "is_open": False,
            "status": "CLOSED",
            "status_label": "MARKET CLOSED",
            "session_hours": "09:15 - 15:30 IST",
            "reason": reason,
            "next_event": f"Opens {next_day} at 09:15 AM IST"
        }
