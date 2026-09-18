"""
Risk Management & Capital Position Sizing Module
Dynamically sizes positions to strictly enforce the user's risk ceiling (e.g. 2% on ₹5,000 capital).
"""

from typing import Any
import math


def calculate_position_sizing(
    capital: float,
    entry_price: float,
    stop_loss: float,
    risk_percentage: float = 0.02,
    reward_ratios: tuple[float, float] = (2.0, 3.0)
) -> dict[str, Any]:
    """
    Calculate precise position sizing and risk metrics.

    Args:
        capital: Total trading capital available (default ₹5,000).
        entry_price: Planned entry price.
        stop_loss: Planned stop loss price.
        risk_percentage: Maximum capital to risk on this trade (0.02 = 2%).
        reward_ratios: Tuple of risk-to-reward multipliers for targets (e.g. 2.0 and 3.0).

    Returns:
        dict containing quantity, capital deployed, max loss, and target levels.
    """
    if capital <= 0:
        raise ValueError("Capital must be positive.")
    if entry_price <= 0 or stop_loss <= 0:
        raise ValueError("Entry and Stop Loss prices must be positive.")

    is_long = entry_price > stop_loss
    risk_per_share = abs(entry_price - stop_loss)

    if risk_per_share == 0:
        raise ValueError("Entry price and Stop Loss cannot be identical.")

    # Max rupee loss permitted
    max_risk_allowed = capital * risk_percentage

    # Calculate share quantities
    shares_by_risk = math.floor(max_risk_allowed / risk_per_share)
    shares_by_capital = math.floor(capital / entry_price)

    # Position size is capped by both risk ceiling and total capital
    quantity = min(shares_by_risk, shares_by_capital)

    if quantity < 1:
        # Check if 1 share is affordable
        if entry_price <= capital:
            quantity = 1
            is_oversized_risk = (quantity * risk_per_share) > max_risk_allowed
        else:
            quantity = 0
            is_oversized_risk = False
    else:
        is_oversized_risk = False

    capital_deployed = quantity * entry_price
    remaining_cash = max(0.0, capital - capital_deployed)
    actual_max_loss = quantity * risk_per_share
    actual_risk_pct = (actual_max_loss / capital) * 100 if capital > 0 else 0

    # Target calculations
    r1, r2 = reward_ratios
    if is_long:
        target_1 = entry_price + (r1 * risk_per_share)
        target_2 = entry_price + (r2 * risk_per_share)
    else:
        target_1 = entry_price - (r1 * risk_per_share)
        target_2 = entry_price - (r2 * risk_per_share)

    profit_target_1 = quantity * abs(target_1 - entry_price)
    profit_target_2 = quantity * abs(target_2 - entry_price)

    profit_pct_target_1 = (profit_target_1 / capital) * 100 if capital > 0 else 0
    profit_pct_target_2 = (profit_target_2 / capital) * 100 if capital > 0 else 0

    return {
        "capital": capital,
        "risk_percentage": risk_percentage * 100,
        "entry_price": round(entry_price, 2),
        "stop_loss": round(stop_loss, 2),
        "risk_per_share": round(risk_per_share, 2),
        "target_1": round(target_1, 2),
        "target_2": round(target_2, 2),
        "quantity": int(quantity),
        "capital_deployed": round(capital_deployed, 2),
        "remaining_cash": round(remaining_cash, 2),
        "max_loss": round(actual_max_loss, 2),
        "actual_risk_pct": round(actual_risk_pct, 2),
        "profit_target_1": round(profit_target_1, 2),
        "profit_target_2": round(profit_target_2, 2),
        "profit_pct_target_1": round(profit_pct_target_1, 2),
        "profit_pct_target_2": round(profit_pct_target_2, 2),
        "is_oversized_risk": is_oversized_risk,
        "is_affordable": quantity > 0
    }
