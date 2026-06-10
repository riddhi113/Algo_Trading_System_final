import pandas as pd
import numpy as np
from mini_algo_trading.strategies.base_strategy import BaseStrategy
from mini_algo_trading.utils.logger import logger
from mini_algo_trading.utils.constants import CLOSE

class MovingAverageCrossover(BaseStrategy):
    def __init__(self, fast_period: int = 50, slow_period: int = 200, ma_type: str = "SMA"):
        """
        Moving Average Crossover Strategy.

        Args:
            fast_period (int): Lookback period for fast moving average.
            slow_period (int): Lookback period for slow moving average.
            ma_type (str): Type of moving average: 'SMA' or 'EMA'.
        """
        super().__init__(name=f"MA_Crossover_{fast_period}_{slow_period}")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.ma_type = ma_type.upper()

        if self.fast_period >= self.slow_period:
            raise ValueError("Fast period must be strictly smaller than slow period.")

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates buy/sell signals based on moving average crossovers.
        """
        logger.info(f"Generating signals using {self.name} ({self.ma_type})...")
        data = df.copy()

        # Calculate moving averages
        if self.ma_type == "EMA":
            data["Fast_MA"] = data[CLOSE].ewm(span=self.fast_period, adjust=False).mean()
            data["Slow_MA"] = data[CLOSE].ewm(span=self.slow_period, adjust=False).mean()
        else:  # Simple Moving Average (SMA)
            data["Fast_MA"] = data[CLOSE].rolling(window=self.fast_period).mean()
            data["Slow_MA"] = data[CLOSE].rolling(window=self.slow_period).mean()

        # Initialize signals to 'HOLD'
        data["Signal"] = "HOLD"

        # Find where Fast MA crosses above Slow MA (BUY signal)
        buy_cond = (data["Fast_MA"] > data["Slow_MA"]) & (data["Fast_MA"].shift(1) <= data["Slow_MA"].shift(1))
        # Find where Fast MA crosses below Slow MA (SELL signal)
        sell_cond = (data["Fast_MA"] < data["Slow_MA"]) & (data["Fast_MA"].shift(1) >= data["Slow_MA"].shift(1))

        # Assign signals
        data.loc[buy_cond, "Signal"] = "BUY"
        data.loc[sell_cond, "Signal"] = "SELL"

        # Log signal generation results
        total_buys = (data["Signal"] == "BUY").sum()
        total_sells = (data["Signal"] == "SELL").sum()
        logger.info(f"Signal generation complete. Found {total_buys} BUY signals and {total_sells} SELL signals.")

        return data
