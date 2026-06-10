import unittest
import datetime
from mini_algo_trading.broker.mock_broker import MockBroker
from mini_algo_trading.models.position import Position

class TestMockBroker(unittest.TestCase):
    def setUp(self):
        self.broker = MockBroker(initial_balance=10000.0)
        self.now = datetime.datetime(2023, 1, 1, 9, 30)

    def test_place_long_order(self):
        # Place long order: buy 10 units of AAPL at $100
        # Cost = $1000, remaining balance should be $9000
        trade = self.broker.place_order(
            ticker="AAPL",
            direction="LONG",
            quantity=10,
            price=100.0,
            timestamp=self.now,
            stop_loss=95.0,
            take_profit=110.0
        )
        
        self.assertIsNotNone(trade)
        self.assertEqual(self.broker.get_balance(), 9000.0)
        self.assertIn("AAPL", self.broker.get_positions())
        
        pos = self.broker.get_positions()["AAPL"]
        self.assertEqual(pos.quantity, 10.0)
        self.assertEqual(pos.entry_price, 100.0)
        self.assertEqual(pos.stop_loss, 95.0)
        self.assertEqual(pos.take_profit, 110.0)

    def test_insufficient_funds(self):
        # Balance is 10000, try to buy 150 units at 100 (cost 15000)
        trade = self.broker.place_order(
            ticker="AAPL",
            direction="LONG",
            quantity=150,
            price=100.0,
            timestamp=self.now
        )
        self.assertNil = self.assertIsNone(trade)
        self.assertEqual(self.broker.get_balance(), 10000.0)
        self.assertEqual(len(self.broker.get_positions()), 0)

    def test_close_long_order(self):
        self.broker.place_order(
            ticker="AAPL",
            direction="LONG",
            quantity=10,
            price=100.0,
            timestamp=self.now
        )
        
        # Close position at $105
        # Proceeds should be $1050, final balance should be $9000 + $1050 = $10050
        # PnL = +$50
        closed_trade = self.broker.close_order(
            ticker="AAPL",
            price=105.0,
            timestamp=self.now + datetime.timedelta(days=1),
            reason="SIGNAL"
        )
        
        self.assertIsNotNone(closed_trade)
        self.assertEqual(self.broker.get_balance(), 10050.0)
        self.assertNotIn("AAPL", self.broker.get_positions())
        self.assertEqual(closed_trade.pnl, 50.0)
        self.assertEqual(closed_trade.pnl_pct, 0.05)
        self.assertEqual(closed_trade.status, "CLOSED")

    def test_stop_loss_trigger(self):
        self.broker.place_order(
            ticker="AAPL",
            direction="LONG",
            quantity=10,
            price=100.0,
            timestamp=self.now,
            stop_loss=95.0,
            take_profit=110.0
        )
        
        # Update price to $94 (breaches stop loss of 95)
        prices = {"AAPL": 94.0}
        closed_trades = self.broker.update_positions_and_check_stops(
            prices, 
            self.now + datetime.timedelta(hours=1)
        )
        
        self.assertEqual(len(closed_trades), 1)
        self.assertEqual(closed_trades[0].exit_reason, "SL")
        self.assertEqual(closed_trades[0].exit_price, 94.0)
        self.assertEqual(self.broker.get_balance(), 9000.0 + 940.0)  # 9940.0
        self.assertNotIn("AAPL", self.broker.get_positions())

    def test_place_short_order(self):
        # Place short order: sell 10 units of AAPL at $100
        # Cash increases by $1000, balance becomes $11000
        trade = self.broker.place_order(
            ticker="AAPL",
            direction="SHORT",
            quantity=10,
            price=100.0,
            timestamp=self.now,
            stop_loss=105.0,
            take_profit=90.0
        )
        
        self.assertIsNotNone(trade)
        self.assertEqual(self.broker.get_balance(), 11000.0)
        self.assertIn("AAPL", self.broker.get_positions())
        
        # Close short position at $95
        # We buy back at $950, final balance should be $11000 - $950 = $10050
        # PnL = +$50
        closed_trade = self.broker.close_order(
            ticker="AAPL",
            price=95.0,
            timestamp=self.now + datetime.timedelta(days=1),
            reason="SIGNAL"
        )
        
        self.assertIsNotNone(closed_trade)
        self.assertEqual(self.broker.get_balance(), 10050.0)
        self.assertEqual(closed_trade.pnl, 50.0)

if __name__ == "__main__":
    unittest.main()
