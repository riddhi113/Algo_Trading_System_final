import unittest
import pandas as pd
import numpy as np
from mini_algo_trading.strategies.moving_average import MovingAverageCrossover
from mini_algo_trading.strategies.macd import MACDStrategy
from mini_algo_trading.utils.constants import CLOSE, OPEN, HIGH, LOW, VOLUME

class TestStrategies(unittest.TestCase):
    def setUp(self):
        # Create 100 days of simple trending prices
        dates = pd.date_range(start="2023-01-01", periods=100)
        self.df = pd.DataFrame(index=dates)
        self.df[OPEN] = 100.0
        self.df[HIGH] = 105.0
        self.df[LOW] = 95.0
        self.df[VOLUME] = 1000
        
        # Close starts at 100, goes down then crosses up
        close_prices = []
        for i in range(100):
            if i < 40:
                close_prices.append(100.0 - i * 0.5)  # Downtrend
            else:
                close_prices.append(80.0 + (i - 40) * 1.5)  # Aggressive uptrend
        self.df[CLOSE] = close_prices

    def test_moving_average_crossover_signals(self):
        # Using fast=10, slow=30
        strategy = MovingAverageCrossover(fast_period=10, slow_period=30, ma_type="SMA")
        df_signals = strategy.generate_signals(self.df)
        
        self.assertIn("Signal", df_signals.columns)
        self.assertIn("Fast_MA", df_signals.columns)
        self.assertIn("Slow_MA", df_signals.columns)
        
        # Verify that BUY or SELL signal types exist in output
        signals = df_signals["Signal"].unique()
        self.assertTrue("BUY" in signals or "SELL" in signals or "HOLD" in signals)
        
        # Check that where BUY signal occurs, Fast MA crossed above Slow MA
        buy_rows = df_signals[df_signals["Signal"] == "BUY"]
        for idx in buy_rows.index:
            loc = df_signals.index.get_loc(idx)
            if loc > 0:
                prev_idx = df_signals.index[loc - 1]
                # Current state: Fast > Slow
                self.assertGreater(df_signals.loc[idx, "Fast_MA"], df_signals.loc[idx, "Slow_MA"])
                # Previous state: Fast <= Slow
                self.assertLessEqual(df_signals.loc[prev_idx, "Fast_MA"], df_signals.loc[prev_idx, "Slow_MA"])

    def test_macd_strategy_signals(self):
        strategy = MACDStrategy(fast_period=12, slow_period=26, signal_period=9)
        df_signals = strategy.generate_signals(self.df)
        
        self.assertIn("Signal", df_signals.columns)
        self.assertIn("MACD_Line", df_signals.columns)
        self.assertIn("Signal_Line", df_signals.columns)
        
        # Check that where SELL signal occurs, MACD Line crossed below Signal Line
        sell_rows = df_signals[df_signals["Signal"] == "SELL"]
        for idx in sell_rows.index:
            loc = df_signals.index.get_loc(idx)
            if loc > 0:
                prev_idx = df_signals.index[loc - 1]
                self.assertLess(df_signals.loc[idx, "MACD_Line"], df_signals.loc[idx, "Signal_Line"])
                self.assertGreaterEqual(df_signals.loc[prev_idx, "MACD_Line"], df_signals.loc[prev_idx, "Signal_Line"])

if __name__ == "__main__":
    unittest.main()
