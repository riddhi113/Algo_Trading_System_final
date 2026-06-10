import pandas as pd
from typing import Dict, List, Tuple
from mini_algo_trading.broker.mock_broker import MockBroker
from mini_algo_trading.risk.risk_manager import RiskManager
from mini_algo_trading.models.trade import Trade
from mini_algo_trading.utils.logger import logger
from mini_algo_trading.utils.constants import CLOSE

class BacktestEngine:
    def __init__(
        self,
        df: pd.DataFrame,
        ticker: str,
        initial_capital: float = 100000.0,
        stop_loss_pct: float = None,
        take_profit_pct: float = None,
        risk_pct: float = None,
        allow_short: bool = False
    ):
        """
        Backtesting Engine to simulate trading strategies on historical data.

        Args:
            df (pd.DataFrame): Market DataFrame containing historical data and a 'Signal' column.
            ticker (str): The ticker symbol.
            initial_capital (float): Starting balance.
            stop_loss_pct (float, optional): Stop loss percentage.
            take_profit_pct (float, optional): Take profit percentage.
            risk_pct (float, optional): Risk percentage for position sizing.
            allow_short (bool): Whether to allow short selling. Default is False (Long-Only).
        """
        self.df = df
        self.ticker = ticker
        self.allow_short = allow_short
        
        # Initialize sub-modules
        self.broker = MockBroker(initial_balance=initial_capital)
        self.risk_manager = RiskManager(
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            risk_pct=risk_pct
        )
        
        # History tracking
        self.equity_curve: List[Dict] = []

    def run(self) -> Tuple[pd.DataFrame, List[Trade]]:
        """
        Executes the backtest simulation over the market data.

        Returns:
            Tuple[pd.DataFrame, List[Trade]]: (Equity Curve DataFrame, List of Trades)
        """
        logger.info(f"Starting backtest for {self.ticker} (Allow Short: {self.allow_short})...")
        
        if "Signal" not in self.df.columns:
            raise ValueError("DataFrame must contain a 'Signal' column to run the backtest.")

        for timestamp, row in self.df.iterrows():
            current_price = float(row[CLOSE])
            signal = str(row["Signal"]).upper()
            prices = {self.ticker: current_price}

            # 1. Update prices and check for SL / TP hits first
            self.broker.update_positions_and_check_stops(prices, timestamp)

            # Get active position
            active_positions = self.broker.get_positions()
            position = active_positions.get(self.ticker)

            # 2. Process signals
            if position is None:
                # No active position: Check for entries
                if signal == "BUY":
                    self._enter_position("LONG", current_price, timestamp)
                elif signal == "SELL" and self.allow_short:
                    self._enter_position("SHORT", current_price, timestamp)
            else:
                # Active position exists: Check for exits/reversals
                if position.direction == "LONG":
                    if signal == "SELL":
                        self.broker.close_order(self.ticker, current_price, timestamp, reason="SIGNAL")
                        # If shorting is allowed, we reverse the position immediately
                        if self.allow_short:
                            self._enter_position("SHORT", current_price, timestamp)
                elif position.direction == "SHORT":
                    if signal == "BUY":
                        self.broker.close_order(self.ticker, current_price, timestamp, reason="SIGNAL")
                        # Reverse to long
                        self._enter_position("LONG", current_price, timestamp)

            # 3. Record daily equity metrics
            equity = self.broker.get_equity(prices)
            self.equity_curve.append({
                "Date": timestamp,
                "Cash": self.broker.get_balance(),
                "Equity": equity,
                "Benchmark_Price": current_price
            })

        # 4. Clean up remaining open positions at the end of the data
        active_positions = self.broker.get_positions()
        if self.ticker in active_positions:
            last_timestamp = self.df.index[-1]
            last_price = float(self.df.loc[last_timestamp, CLOSE])
            logger.info(f"Closing outstanding position in {self.ticker} at end of data (Price: {last_price:.2f})")
            self.broker.close_order(self.ticker, last_price, last_timestamp, reason="END_OF_DATA")
            
            # Update the last entry in equity curve
            self.equity_curve[-1]["Cash"] = self.broker.get_balance()
            self.equity_curve[-1]["Equity"] = self.broker.get_balance()

        # Build equity curve DataFrame
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df.set_index("Date", inplace=True)
        
        # Calculate daily returns and benchmark returns for comparison
        equity_df["Strategy_Return"] = equity_df["Equity"].pct_change().fillna(0.0)
        equity_df["Benchmark_Return"] = equity_df["Benchmark_Price"].pct_change().fillna(0.0)
        
        # Calculate cumulative returns
        equity_df["Strategy_Cum_Return"] = (1 + equity_df["Strategy_Return"]).cumprod() - 1
        equity_df["Benchmark_Cum_Return"] = (1 + equity_df["Benchmark_Return"]).cumprod() - 1

        logger.info(f"Backtest complete. Final Equity: {self.broker.get_balance():.2f}")
        return equity_df, self.broker.get_order_history()

    def _enter_position(self, direction: str, price: float, timestamp: pd.Timestamp):
        """
        Helper to calculate stops, position size, and place an order.
        """
        # Calculate Stop Loss and Take Profit levels
        sl_price, tp_price = self.risk_manager.calculate_sl_tp(price, direction)
        
        # Calculate Position Size (Qty)
        qty = self.risk_manager.calculate_position_size(
            capital=self.broker.get_balance(),
            entry_price=price,
            stop_loss_price=sl_price
        )

        if qty > 0:
            self.broker.place_order(
                ticker=self.ticker,
                direction=direction,
                quantity=qty,
                price=price,
                timestamp=timestamp,
                stop_loss=sl_price,
                take_profit=tp_price
            )
