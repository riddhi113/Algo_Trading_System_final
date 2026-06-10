import unittest
import pandas as pd
from mini_algo_trading.backtest.engine import BacktestEngine
from mini_algo_trading.utils.constants import CLOSE, OPEN, HIGH, LOW, VOLUME

class TestBacktestEngine(unittest.TestCase):
    def setUp(self):
        # Create a simple 10-day dataset
        dates = pd.date_range(start="2023-01-01", periods=10)
        self.df = pd.DataFrame(index=dates)
        self.df[OPEN] = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        self.df[HIGH] = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
        self.df[LOW] =  [99,  100, 101, 102, 103, 104, 105, 106, 107, 108]
        self.df[CLOSE] = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        self.df[VOLUME] = 1000
        
        # Signals: BUY on Day 3, SELL on Day 7
        self.df["Signal"] = "HOLD"
        self.df.iloc[2, self.df.columns.get_loc("Signal")] = "BUY"   # Index 2 (Day 3)
        self.df.iloc[6, self.df.columns.get_loc("Signal")] = "SELL"  # Index 6 (Day 7)

    def test_backtest_runs_successfully(self):
        engine = BacktestEngine(
            df=self.df,
            ticker="XYZ",
            initial_capital=10000.0,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            risk_pct=None
        )
        
        equity_df, trades = engine.run()
        
        # Verify output formats
        self.assertIsInstance(equity_df, pd.DataFrame)
        self.assertEqual(len(equity_df), 10)
        self.assertIn("Equity", equity_df.columns)
        self.assertIn("Cash", equity_df.columns)
        self.assertIn("Strategy_Cum_Return", equity_df.columns)
        
        # Should have exactly 1 trade completed (BUY on Day 3, SELL on Day 7)
        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertEqual(trade.ticker, "XYZ")
        self.assertEqual(trade.direction, "LONG")
        self.assertEqual(trade.entry_price, 102.0)  # Close on Day 3
        self.assertEqual(trade.exit_price, 106.0)   # Close on Day 7
        self.assertEqual(trade.exit_reason, "SIGNAL")
        self.assertEqual(trade.status, "CLOSED")
        
        # Realized PnL = (106 - 102) * Qty.
        # Qty = (10000 * 0.95) / 102 = 93.137
        # PnL = 4 * 93.137 = 372.55
        self.assertAlmostEqual(trade.pnl, 4.0 * trade.quantity, places=2)
        
        # Check cash and equity values
        self.assertAlmostEqual(equity_df["Equity"].iloc[-1], 10000.0 + trade.pnl, places=2)

    def test_force_close_at_end_of_data(self):
        # Trigger BUY on Day 3, but never signal SELL
        self.df["Signal"] = "HOLD"
        self.df.iloc[2, self.df.columns.get_loc("Signal")] = "BUY"
        
        engine = BacktestEngine(
            df=self.df,
            ticker="XYZ",
            initial_capital=10000.0
        )
        equity_df, trades = engine.run()
        
        # Check that the trade was forced closed at the final day's close price
        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertEqual(trade.status, "CLOSED")
        self.assertEqual(trade.exit_reason, "END_OF_DATA")
        self.assertEqual(trade.exit_price, 109.0)  # Close on last day

if __name__ == "__main__":
    unittest.main()
