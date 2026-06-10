from typing import Optional, Tuple
from mini_algo_trading.utils.logger import logger

class RiskManager:
    def __init__(
        self,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        risk_pct: Optional[float] = None,
        max_capital_allocation_pct: float = 0.95
    ):
        """
        Risk Manager to manage stop-loss, take-profit, and position sizing.

        Args:
            stop_loss_pct (float, optional): Stop loss percentage (e.g. 0.02 for 2%).
            take_profit_pct (float, optional): Take profit percentage (e.g. 0.05 for 5%).
            risk_pct (float, optional): Percentage of account equity to risk per trade (e.g. 0.01 for 1%).
            max_capital_allocation_pct (float): Max percentage of account equity allocated to a single trade.
        """
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.risk_pct = risk_pct
        self.max_capital_allocation_pct = max_capital_allocation_pct

    def calculate_sl_tp(self, entry_price: float, direction: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculates absolute price levels for stop loss and take profit.

        Returns:
            Tuple[Optional[float], Optional[float]]: (stop_loss_price, take_profit_price)
        """
        stop_loss_price = None
        take_profit_price = None

        if direction == "LONG":
            if self.stop_loss_pct is not None:
                stop_loss_price = entry_price * (1.0 - self.stop_loss_pct)
            if self.take_profit_pct is not None:
                take_profit_price = entry_price * (1.0 + self.take_profit_pct)
        elif direction == "SHORT":
            if self.stop_loss_pct is not None:
                stop_loss_price = entry_price * (1.0 + self.stop_loss_pct)
            if self.take_profit_pct is not None:
                take_profit_price = entry_price * (1.0 - self.take_profit_pct)

        return stop_loss_price, take_profit_price

    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: Optional[float] = None
    ) -> float:
        """
        Calculates position size (quantity of shares/units to buy).
        If risk_pct and stop_loss_price are defined, uses risk-based sizing.
        Otherwise, sizes based on max capital allocation.
        """
        if entry_price <= 0:
            return 0.0

        # Maximum capital we can spend on this trade
        max_spending = capital * self.max_capital_allocation_pct

        if self.risk_pct is not None and stop_loss_price is not None:
            # Risk-based sizing: Quantity = (Capital * Risk%) / (Entry Price - Stop Loss Price)
            risk_amount = capital * self.risk_pct
            risk_per_unit = abs(entry_price - stop_loss_price)

            if risk_per_unit > 0:
                qty = risk_amount / risk_per_unit
                # Ensure we don't exceed max spending limits
                if (qty * entry_price) > max_spending:
                    qty = max_spending / entry_price
                    logger.debug(f"Risk-based quantity capped by max spending limit. Qty: {qty:.4f}")
                return float(qty)

        # Fallback: allocate max capital allocation percentage to this trade
        qty = max_spending / entry_price
        logger.debug(f"Default capital allocation sizing used. Qty: {qty:.4f}")
        return float(qty)
