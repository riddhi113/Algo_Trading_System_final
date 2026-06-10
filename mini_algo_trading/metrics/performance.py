import pandas as pd
import numpy as np
from typing import List, Dict, Any
from mini_algo_trading.models.trade import Trade
from mini_algo_trading.utils.logger import logger

def calculate_performance_metrics(
    equity_df: pd.DataFrame,
    trades: List[Trade],
    initial_capital: float
) -> Dict[str, Any]:
    """
    Computes performance metrics from the backtest results.

    Args:
        equity_df (pd.DataFrame): DataFrame containing the daily account equity curve.
        trades (List[Trade]): List of all executed trades.
        initial_capital (float): Starting balance.

    Returns:
        Dict[str, Any]: Dictionary containing calculated performance metrics.
    """
    # 1. Basic Trade Metrics
    closed_trades = [t for t in trades if t.status == "CLOSED"]
    num_trades = len(closed_trades)
    
    winning_trades = [t for t in closed_trades if t.pnl > 0]
    losing_trades = [t for t in closed_trades if t.pnl < 0]
    num_wins = len(winning_trades)
    num_losses = len(losing_trades)
    
    win_rate = num_wins / num_trades if num_trades > 0 else 0.0

    # PnL calculations
    gross_profit = sum(t.pnl for t in winning_trades)
    gross_loss = sum(abs(t.pnl) for t in losing_trades)
    
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 1.0)
    
    total_pnl = equity_df["Equity"].iloc[-1] - initial_capital
    total_pnl_pct = total_pnl / initial_capital

    # 2. Maximum Drawdown (Peak to Trough)
    equity = equity_df["Equity"]
    cumulative_max = equity.cummax()
    drawdown = (equity - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()  # Will be a negative percentage (e.g. -0.15)
    
    # 3. Sharpe Ratio (Annualized)
    # Standard formula assumes 252 trading days per year
    daily_returns = equity_df["Strategy_Return"]
    mean_daily_return = daily_returns.mean()
    std_daily_return = daily_returns.std()
    
    if std_daily_return > 0:
        sharpe_ratio = (mean_daily_return / std_daily_return) * np.sqrt(252)
    else:
        sharpe_ratio = 0.0

    # 4. Benchmark performance
    benchmark_pnl_pct = equity_df["Benchmark_Cum_Return"].iloc[-1] if not equity_df.empty else 0.0

    metrics = {
        "initial_capital": initial_capital,
        "final_equity": equity_df["Equity"].iloc[-1] if not equity_df.empty else initial_capital,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "benchmark_pnl_pct": benchmark_pnl_pct,
        "total_trades": num_trades,
        "winning_trades": num_wins,
        "losing_trades": num_losses,
        "win_rate": win_rate,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio
    }
    
    return metrics

def print_performance_summary(metrics: Dict[str, Any]):
    """
    Utility to print a well-formatted summary of performance metrics.
    """
    border = "=" * 50
    header = f"{'BACKTEST PERFORMANCE SUMMARY':^50}"
    
    summary = f"""
{border}
{header}
{border}
Initial Capital:         ₹{metrics['initial_capital']:,.2f}
Final Equity:            ₹{metrics['final_equity']:,.2f}
Net Profit/Loss:         ₹{metrics['total_pnl']:+,.2f} ({metrics['total_pnl_pct']*100:+.2f}%)
Benchmark Return:        {metrics['benchmark_pnl_pct']*100:+.2f}%

Total Executed Trades:   {metrics['total_trades']}
  - Winning Trades:      {metrics['winning_trades']}
  - Losing Trades:       {metrics['losing_trades']}
Win Rate:                {metrics['win_rate']*100:.2f}%
Gross Profit:            ₹{metrics['gross_profit']:,.2f}
Gross Loss:              ₹{metrics['gross_loss']:,.2f}
Profit Factor:           {metrics['profit_factor']:.2f}

Max Drawdown:            {metrics['max_drawdown']*100:.2f}%
Sharpe Ratio (Ann.):     {metrics['sharpe_ratio']:.2f}
{border}
"""
    print(summary)
