"""
mock_broker.py — Step 7: Mock Broker API

Methods implemented (Step 7 specification):
  - place_order()         : Simulate placing a buy/sell order
  - close_order()         : Close an active position
  - get_positions()       : Return all currently open positions
  - get_balance()         : Return current available cash balance
  - get_order_history()   : Return full history of all trades

Technical expectations met:
  - Modular and clean architecture (single-responsibility per method)
  - Proper error handling (guard clauses, validation, returns None on failure)
  - Logging system (structured logs via shared logger utility)
  - Type hints throughout (PEP 484 compliant)
  - Configuration-driven initial balance via __init__ parameter
"""

import datetime
from typing import Dict, List, Optional
from mini_algo_trading.models.position import Position
from mini_algo_trading.models.trade import Trade
from mini_algo_trading.utils.logger import logger


class MockBroker:
    """
    Simulates a brokerage account for algorithmic trading backtests.

    Tracks cash balance, open positions, and full order history.
    Supports LONG and SHORT directions with stop-loss / take-profit management.
    """

    def __init__(self, initial_balance: float = 100_000.0) -> None:
        """
        Initialise the broker with a starting cash balance.

        Args:
            initial_balance: Starting capital in the account (default ₹1,00,000).
        """
        self.cash: float = initial_balance
        self.initial_balance: float = initial_balance
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self._trade_counter: int = 1

    # ── Step 7 Method 1 ────────────────────────────────────────────────────────
    def get_balance(self) -> float:
        """
        Return the current available cash balance.

        Returns:
            float: Available cash in the account.
        """
        logger.debug(f"get_balance() → ₹{self.cash:,.2f}")
        return self.cash

    # ── Step 7 Method 2 ────────────────────────────────────────────────────────
    def get_positions(self) -> Dict[str, Position]:
        """
        Return all currently open positions keyed by ticker symbol.

        Returns:
            Dict[str, Position]: Map of ticker → open Position object.
        """
        logger.debug(f"get_positions() → {len(self.positions)} open position(s)")
        return self.positions

    # ── Step 7 Method 3 ────────────────────────────────────────────────────────
    def get_order_history(self) -> List[Trade]:
        """
        Return the complete order history (both open and closed trades).

        Returns:
            List[Trade]: All trades placed since broker initialisation.
        """
        logger.debug(f"get_order_history() → {len(self.trades)} total trade(s)")
        return self.trades

    # ── Step 7 Method 4 ────────────────────────────────────────────────────────
    def place_order(
        self,
        ticker: str,
        direction: str,
        quantity: float,
        price: float,
        timestamp: datetime.datetime,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Optional[Trade]:
        """
        Simulate placing a market order to open a new position.

        Validates inputs, checks available balance, and records both the
        Trade and Position. Pyramiding (adding to existing positions) is
        not supported — a new order is rejected if a position already exists.

        Args:
            ticker:      Asset symbol (e.g. "RELIANCE.NS").
            direction:   "LONG" (buy) or "SHORT" (sell).
            quantity:    Number of units to trade (must be > 0).
            price:       Execution price per unit (must be > 0).
            timestamp:   Datetime of the order.
            stop_loss:   Optional stop-loss price level.
            take_profit: Optional take-profit price level.

        Returns:
            Trade if successfully placed, None on rejection.
        """
        # ── Input validation ──────────────────────────────────────────────────
        if quantity <= 0 or price <= 0:
            logger.error(
                f"place_order() rejected — invalid params: qty={quantity}, price={price}"
            )
            return None

        if direction not in ("LONG", "SHORT"):
            logger.error(f"place_order() rejected — unknown direction: '{direction}'")
            return None

        # ── Prevent pyramiding ────────────────────────────────────────────────
        if ticker in self.positions:
            logger.warning(
                f"place_order() skipped — position already open for {ticker}. "
                "Pyramiding is not supported."
            )
            return None

        cost: float = quantity * price

        # ── Balance check & cash adjustment ──────────────────────────────────
        if direction == "LONG":
            if cost > self.cash:
                logger.warning(
                    f"place_order() rejected — insufficient cash. "
                    f"Required: ₹{cost:,.2f}, Available: ₹{self.cash:,.2f}"
                )
                return None
            self.cash -= cost

        elif direction == "SHORT":
            # Margin requirement: need at least the transaction value as collateral
            if cost > self.cash:
                logger.warning(
                    f"place_order() rejected — insufficient margin. "
                    f"Required: ₹{cost:,.2f}, Available: ₹{self.cash:,.2f}"
                )
                return None
            self.cash += cost  # Short sale proceeds credited

        # ── Create Trade record ───────────────────────────────────────────────
        trade_id = f"T_{self._trade_counter:05d}"
        self._trade_counter += 1

        trade = Trade(
            trade_id=trade_id,
            ticker=ticker,
            direction=direction,
            quantity=quantity,
            entry_date=timestamp,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self.trades.append(trade)

        # ── Create Position record ────────────────────────────────────────────
        position = Position(
            ticker=ticker,
            quantity=quantity,
            entry_price=price,
            direction=direction,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self.positions[ticker] = position

        logger.info(
            f"ORDER PLACED: {trade_id} | {direction} {quantity:.4f} {ticker} "
            f"@ ₹{price:.2f} | Cash: ₹{self.cash:,.2f}"
        )
        return trade

    # ── Step 7 Method 5 ────────────────────────────────────────────────────────
    def close_order(
        self,
        ticker: str,
        price: float,
        timestamp: datetime.datetime,
        reason: str = "SIGNAL",
    ) -> Optional[Trade]:
        """
        Simulate closing an active position at the given price.

        Calculates realized PnL, returns cash to the account, and marks
        the corresponding Trade record as CLOSED.

        Args:
            ticker:    Asset symbol of the position to close.
            price:     Exit execution price per unit.
            timestamp: Datetime of the close event.
            reason:    Reason for closing ("SIGNAL", "SL", "TP", "EXPIRY").

        Returns:
            The closed Trade if successful, None if no active position exists.
        """
        # ── Guard: position must exist ─────────────────────────────────────────
        if ticker not in self.positions:
            logger.warning(
                f"close_order() skipped — no active position found for {ticker}."
            )
            return None

        position: Position = self.positions.pop(ticker)
        position.update_price(price)

        # ── Cash settlement ───────────────────────────────────────────────────
        if position.direction == "LONG":
            # Sell holdings: receive quantity × exit price
            self.cash += position.quantity * price
        elif position.direction == "SHORT":
            # Buy-back to cover short: pay quantity × exit price
            self.cash -= position.quantity * price

        # ── Close Trade record ────────────────────────────────────────────────
        for trade in self.trades:
            if trade.ticker == ticker and trade.status == "OPEN":
                trade.close_trade(timestamp, price, reason)
                logger.info(
                    f"ORDER CLOSED: {trade.trade_id} | {position.direction} "
                    f"{position.quantity:.4f} {ticker} closed @ ₹{price:.2f} "
                    f"| PnL: {trade.pnl:+.2f} ({trade.pnl_pct * 100:+.2f}%) "
                    f"| Reason: {reason} | Cash: ₹{self.cash:,.2f}"
                )
                return trade

        logger.error(
            f"close_order() — position for {ticker} existed but no OPEN trade record found."
        )
        return None

    # ── Internal helper (not part of Step 7 spec, supports backtest engine) ────
    def get_equity(self, current_prices: Dict[str, float]) -> float:
        """
        Return total account equity (cash + unrealized PnL of open positions).

        Args:
            current_prices: Map of ticker → current market price.

        Returns:
            float: Total account value at current prices.
        """
        unrealized: float = 0.0
        for ticker, pos in self.positions.items():
            if ticker in current_prices:
                pos.update_price(current_prices[ticker])
            unrealized += pos.unrealized_pnl
        return self.cash + unrealized

    def update_positions_and_check_stops(
        self,
        current_prices: Dict[str, float],
        timestamp: datetime.datetime,
    ) -> List[Trade]:
        """
        Update all open positions with the latest prices and trigger
        stop-loss / take-profit closes where levels are breached.

        Args:
            current_prices: Map of ticker → current market price.
            timestamp:      Current bar datetime.

        Returns:
            List[Trade]: Trades auto-closed due to risk violation this bar.
        """
        closed_trades: List[Trade] = []
        for ticker in list(self.positions.keys()):
            if ticker not in current_prices:
                continue

            price: float = current_prices[ticker]
            pos: Position = self.positions[ticker]
            pos.update_price(price)

            violation: Optional[str] = pos.check_risk_violation()
            if violation:
                logger.info(
                    f"Risk violation ({violation}) triggered for {ticker} at ₹{price:.2f}"
                )
                closed = self.close_order(ticker, price, timestamp, reason=violation)
                if closed:
                    closed_trades.append(closed)

        return closed_trades
