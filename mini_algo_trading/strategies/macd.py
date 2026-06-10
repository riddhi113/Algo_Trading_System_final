import pandas as pd
from mini_algo_trading.strategies.base_strategy import BaseStrategy
from mini_algo_trading.utils.logger import logger
from mini_algo_trading.utils.constants import CLOSE

class MACDStrategy(BaseStrategy):
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        MACD Crossover Strategy.

        Args:
            fast_period (int): Lookback period for fast EMA (default 12).
            slow_period (int): Lookback period for slow EMA (default 26).
            signal_period (int): Lookback period for MACD Signal Line EMA (default 9).
        """
        super().__init__(name=f"MACD_{fast_period}_{slow_period}_{signal_period}")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

        if self.fast_period >= self.slow_period:
            raise ValueError("Fast period must be strictly smaller than slow period.")

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates buy/sell signals based on MACD Line crossing the Signal Line.
        """
        logger.info(f"Generating signals using {self.name}...")
        data = df.copy()

        # Calculate EMAs
        fast_ema = data[CLOSE].ewm(span=self.fast_period, adjust=False).mean()
        slow_ema = data[CLOSE].ewm(span=self.slow_period, adjust=False).mean()

        # Calculate MACD Line and Signal Line
        data["MACD_Line"] = fast_ema - slow_ema
        data["Signal_Line"] = data["MACD_Line"].ewm(span=self.signal_period, adjust=False).mean()
        data["MACD_Hist"] = data["MACD_Line"] - data["Signal_Line"]

        # Initialize signals to 'HOLD'
        data["Signal"] = "HOLD"

        # Find where MACD crosses above Signal Line (BUY signal)
        buy_cond = (data["MACD_Line"] > data["Signal_Line"]) & (data["MACD_Line"].shift(1) <= data["Signal_Line"].shift(1))
        # Find where MACD crosses below Signal Line (SELL signal)
        sell_cond = (data["MACD_Line"] < data["Signal_Line"]) & (data["MACD_Line"].shift(1) >= data["Signal_Line"].shift(1))

        # Assign signals
        data.loc[buy_cond, "Signal"] = "BUY"
        data.loc[sell_cond, "Signal"] = "SELL"

        # Log signal generation results
        total_buys = (data["Signal"] == "BUY").sum()
        total_sells = (data["Signal"] == "SELL").sum()
        logger.info(f"Signal generation complete. Found {total_buys} BUY signals and {total_sells} SELL signals.")

        return data
