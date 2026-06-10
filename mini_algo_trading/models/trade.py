import datetime
from typing import Optional

class Trade:
    def __init__(
        self,
        trade_id: str,
        ticker: str,
        direction: str,
        quantity: float,
        entry_date: datetime.datetime,
        entry_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        """
        Represents a completed or active trade execution.
        """
        self.trade_id = trade_id
        self.ticker = ticker
        self.direction = direction
        self.quantity = quantity
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        
        # Exit details
        self.exit_date: Optional[datetime.datetime] = None
        self.exit_price: Optional[float] = None
        self.exit_reason: Optional[str] = None  # "SIGNAL", "SL", "TP", "FORCE_CLOSE"
        
        # Financial metrics
        self.pnl: float = 0.0
        self.pnl_pct: float = 0.0
        self.status: str = "OPEN"  # "OPEN" or "CLOSED"

    def close_trade(self, exit_date: datetime.datetime, exit_price: float, reason: str):
        """
        Closes the trade, calculates realized PnL and percentage returns.
        """
        if self.status == "CLOSED":
            raise ValueError(f"Trade {self.trade_id} is already closed.")
        if exit_price <= 0:
            raise ValueError("Exit price must be positive.")

        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_reason = reason
        self.status = "CLOSED"

        # Calculate realized PnL
        if self.direction == "LONG":
            self.pnl = (self.exit_price - self.entry_price) * self.quantity
            self.pnl_pct = (self.exit_price - self.entry_price) / self.entry_price
        else:
            self.pnl = (self.entry_price - self.exit_price) * self.quantity
            self.pnl_pct = (self.entry_price - self.exit_price) / self.entry_price

    def __repr__(self) -> str:
        if self.status == "OPEN":
            return (f"Trade(ID: {self.trade_id}, Ticker: {self.ticker}, Direction: {self.direction}, "
                    f"Qty: {self.quantity}, Entry: {self.entry_price:.2f} on {self.entry_date}, Status: OPEN)")
        else:
            return (f"Trade(ID: {self.trade_id}, Ticker: {self.ticker}, Direction: {self.direction}, "
                    f"Qty: {self.quantity}, Entry: {self.entry_price:.2f}, Exit: {self.exit_price:.2f}, "
                    f"PnL: {self.pnl:+.2f} ({self.pnl_pct*100:+.2f}%), Reason: {self.exit_reason})")
