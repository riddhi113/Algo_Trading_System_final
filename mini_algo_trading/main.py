import os
import argparse
import yaml
from mini_algo_trading.utils.logger import logger
from mini_algo_trading.data.loader import fetch_historical_data, load_market_data
from mini_algo_trading.strategies.moving_average import MovingAverageCrossover
from mini_algo_trading.strategies.macd import MACDStrategy
from mini_algo_trading.backtest.engine import BacktestEngine
from mini_algo_trading.metrics.performance import calculate_performance_metrics, print_performance_summary

def load_config(config_path: str) -> dict:
    """Loads configuration from YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Mini Algo Trading System")
    parser.add_argument("--config", type=str, default="mini_algo_trading/config/config.yaml", help="Path to config.yaml")
    parser.add_argument("--download", action="store_true", help="Force download of historical data from yfinance")
    args = parser.parse_args()

    logger.info("Initializing Mini Algo Trading System...")
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        data_cfg = config["data"]
        acc_cfg = config["account"]
        risk_cfg = config["risk"]
        bt_cfg = config["backtest"]
        active_strategy = config["active_strategy"]
        
        ticker = data_cfg["ticker"]
        start_date = data_cfg["start_date"]
        end_date = data_cfg["end_date"]
        interval = data_cfg["interval"]
        filepath = data_cfg["filepath"]

        # Ensure market data is available
        if args.download or not os.path.exists(filepath):
            logger.info(f"Market data file {filepath} not found or download forced. Fetching from yfinance...")
            fetch_historical_data(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                output_path=filepath
            )

        # Load and clean market data
        df = load_market_data(filepath)

        # Select and initialize Strategy
        if active_strategy == "MA_Crossover":
            strat_params = config["strategies"]["MA_Crossover"]
            strategy = MovingAverageCrossover(
                fast_period=strat_params["fast_period"],
                slow_period=strat_params["slow_period"],
                ma_type=strat_params["ma_type"]
            )
        elif active_strategy == "MACD":
            strat_params = config["strategies"]["MACD"]
            strategy = MACDStrategy(
                fast_period=strat_params["fast_period"],
                slow_period=strat_params["slow_period"],
                signal_period=strat_params["signal_period"]
            )
        else:
            raise ValueError(f"Unknown strategy selected: {active_strategy}")

        # Generate signals
        df_with_signals = strategy.generate_signals(df)

        # Run Backtest
        initial_capital = float(acc_cfg["initial_capital"])
        engine = BacktestEngine(
            df=df_with_signals,
            ticker=ticker,
            initial_capital=initial_capital,
            stop_loss_pct=risk_cfg.get("stop_loss_pct"),
            take_profit_pct=risk_cfg.get("take_profit_pct"),
            risk_pct=risk_cfg.get("risk_pct"),
            allow_short=bt_cfg.get("allow_short", False)
        )
        
        equity_df, trades = engine.run()

        # Calculate and Print Performance
        metrics = calculate_performance_metrics(equity_df, trades, initial_capital)
        print_performance_summary(metrics)

        # Print trade summary
        if trades:
            print("\nTRADE LOG:")
            print(f"{'Trade ID':<10} | {'Type':<5} | {'Qty':<10} | {'Entry':<8} | {'Exit':<8} | {'PnL (₹)':<10} | {'PnL (%)':<8} | {'Reason':<10}")
            print("-" * 85)
            for t in trades[:15]:  # Show first 15 trades
                pnl_str = f"{t.pnl:+.2f}" if t.status == "CLOSED" else "OPEN"
                pnl_pct_str = f"{t.pnl_pct*100:+.2f}%" if t.status == "CLOSED" else "OPEN"
                exit_price_str = f"{t.exit_price:.2f}" if t.exit_price else "OPEN"
                exit_reason = t.exit_reason if t.exit_reason else "N/A"
                print(f"{t.trade_id:<10} | {t.direction:<5} | {t.quantity:<10.2f} | {t.entry_price:<8.2f} | {exit_price_str:<8} | {pnl_str:<10} | {pnl_pct_str:<8} | {exit_reason:<10}")
            if len(trades) > 15:
                print(f"... and {len(trades) - 15} more trades.")
        else:
            print("\nNo trades executed during the backtest.")

    except Exception as e:
        logger.error(f"Error executing backtest pipeline: {e}", exc_info=True)

if __name__ == "__main__":
    main()
