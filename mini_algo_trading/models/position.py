from typing import Optional

class Position:
    def __init__(
        self,
        ticker: str,
        quantity: float,
        entry_price: float,
        direction: str = "LONG",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        """
        Represents an active trading position.

        Args:
            ticker (str): The ticker symbol.
            quantity (float): Number of shares/units held. Must be > 0.
            entry_price (float): The purchase price.
            direction (str): 'LONG' or 'SHORT'. Default is 'LONG'.
            stop_loss (float, optional): Price at which to exit to limit loss.
            take_profit (float, optional): Price at which to exit to lock in profit.
        """
        if quantity <= 0:
            raise ValueError("Position quantity must be greater than zero.")
        if entry_price <= 0:
            raise ValueError("Position entry price must be greater than zero.")
        if direction not in ("LONG", "SHORT"):
            raise ValueError("Direction must be 'LONG' or 'SHORT'.")

        self.ticker = ticker
        self.quantity = quantity
        self.entry_price = entry_price
        self.direction = direction
        self.current_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    @property
    def unrealized_pnl(self) -> float:
        """
        Calculates the unrealized profit or loss based on current_price.
        """
        if self.direction == "LONG":
            return (self.current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - self.current_price) * self.quantity

    def update_price(self, new_price: float):
        """
        Updates the current market price of the position.
        """
        if new_price <= 0:
            raise ValueError("Updated price must be positive.")
        self.current_price = new_price

    def check_risk_violation(self) -> Optional[str]:
        """
        Checks if the current price has breached the stop loss or take profit.
        Returns 'SL' if stop loss breached, 'TP' if take profit breached, otherwise None.
        """
        if self.direction == "LONG":
            if self.stop_loss is not None and self.current_price <= self.stop_loss:
                return "SL"
            if self.take_profit is not None and self.current_price >= self.take_profit:
                return "TP"
        else:
            if self.stop_loss is not None and self.current_price >= self.stop_loss:
                return "SL"
            if self.take_profit is not None and self.current_price <= self.take_profit:
                return "TP"
        return None

    def __repr__(self) -> str:
        return (f"Position({self.direction} {self.quantity} {self.ticker} @ "
                f"Entry: {self.entry_price:.2f}, Current: {self.current_price:.2f}, "
                f"PnL: {self.unrealized_pnl:+.2f}, SL: {self.stop_loss}, TP: {self.take_profit})")
