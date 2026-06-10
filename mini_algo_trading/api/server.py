"""
server.py — FastAPI backend for the Algo Trading System

Step 7 Implementation:
  ── Mock Broker API endpoints ────────────────────────────────────────────────
  POST /api/broker/order          → place_order()
  DELETE /api/broker/order/{ticker} → close_order()
  GET  /api/broker/positions      → get_positions()
  GET  /api/broker/balance        → get_balance()
  GET  /api/broker/history        → get_order_history()

  ── Authentication ────────────────────────────────────────────────────────────
  POST /api/auth/login            → Returns JWT token
  GET  /api/auth/me               → Returns current user info (token required)

  ── Backtest / Compare ───────────────────────────────────────────────────────
  POST /api/backtest              → Run backtest pipeline
  POST /api/compare               → Run MA vs MACD comparison

  ── WebSocket live feed ──────────────────────────────────────────────────────
  WS   /ws/live                   → Streams real-time simulated price ticks

  ── Static files ─────────────────────────────────────────────────────────────
  GET  /                          → login.html (served first)
  GET  /dashboard                 → index.html (protected by frontend token check)
"""

import os
import asyncio
import random
import math
import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import pandas as pd

from mini_algo_trading.data.loader import fetch_historical_data, load_market_data
from mini_algo_trading.strategies.moving_average import MovingAverageCrossover
from mini_algo_trading.strategies.macd import MACDStrategy
from mini_algo_trading.backtest.engine import BacktestEngine
from mini_algo_trading.metrics.performance import calculate_performance_metrics
from mini_algo_trading.broker.mock_broker import MockBroker
from mini_algo_trading.api.auth import authenticate_user, create_access_token, verify_token
from mini_algo_trading.utils.logger import logger

# ── App Init ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Algo Trading System API",
    description="Step 7 — Mock Broker API + WebSocket + JWT Auth",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global in-memory broker instance (shared across API calls) ────────────────
_broker = MockBroker(initial_balance=100_000.0)

# ── WebSocket connection manager ──────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info(f"WebSocket client connected. Total: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active)}")

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)

ws_manager = ConnectionManager()

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean_float(val) -> float:
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return 0.0
    return float(val)


def require_auth(authorization: str = Header(None)) -> dict:
    """Dependency: validates Bearer JWT from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token is expired or invalid")
    return payload


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str


@app.post("/api/auth/login", tags=["Auth"])
async def login(req: LoginRequest):
    """
    Authenticate user and return a JWT access token.
    Credentials: username=Admin, password=admin@123
    """
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    logger.info(f"User '{user['username']}' logged in successfully.")
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"],
    }


@app.post("/api/auth/register", tags=["Auth"])
async def register(req: RegisterRequest):
    """
    Register endpoint — in this demo, only Admin is supported.
    Returns an informational message.
    """
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    # In production: save to DB. For Step 7 demo, just acknowledge.
    return {
        "status": "info",
        "message": f"Account '{req.username}' registration received. Contact admin to activate."
    }


@app.get("/api/auth/me", tags=["Auth"])
async def get_me(current_user: dict = Depends(require_auth)):
    """Return info about the currently authenticated user."""
    return {"username": current_user.get("sub"), "role": current_user.get("role")}


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7 — MOCK BROKER API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class PlaceOrderRequest(BaseModel):
    ticker: str = Field(..., example="RELIANCE.NS")
    direction: str = Field(..., example="LONG", description="LONG or SHORT")
    quantity: float = Field(..., gt=0, example=10.0)
    price: float = Field(..., gt=0, example=2500.0)
    stop_loss: Optional[float] = Field(None, example=2400.0)
    take_profit: Optional[float] = Field(None, example=2700.0)


@app.get("/api/broker/balance", tags=["Broker"])
async def broker_get_balance(current_user: dict = Depends(require_auth)):
    """
    get_balance() — Return current available cash in the broker account.
    """
    balance = _broker.get_balance()
    equity = _broker.get_equity({})
    return {
        "cash_balance": round(balance, 2),
        "total_equity": round(equity, 2),
        "currency": "INR",
    }


@app.get("/api/broker/positions", tags=["Broker"])
async def broker_get_positions(current_user: dict = Depends(require_auth)):
    """
    get_positions() — Return all currently open positions.
    """
    positions = _broker.get_positions()
    result = []
    for ticker, pos in positions.items():
        result.append({
            "ticker": ticker,
            "direction": pos.direction,
            "quantity": round(pos.quantity, 4),
            "entry_price": round(pos.entry_price, 2),
            "current_price": round(pos.current_price, 2) if hasattr(pos, "current_price") else None,
            "unrealized_pnl": round(pos.unrealized_pnl, 2),
            "stop_loss": pos.stop_loss,
            "take_profit": pos.take_profit,
        })
    return {"open_positions": result, "count": len(result)}


@app.get("/api/broker/history", tags=["Broker"])
async def broker_get_order_history(current_user: dict = Depends(require_auth)):
    """
    get_order_history() — Return all trades (open and closed).
    """
    trades = _broker.get_order_history()
    result = []
    for t in trades:
        entry_date = t.entry_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(t.entry_date, (datetime.datetime, pd.Timestamp)) else str(t.entry_date)
        exit_date = t.exit_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(t.exit_date, (datetime.datetime, pd.Timestamp)) else (str(t.exit_date) if t.exit_date else None)
        result.append({
            "trade_id": t.trade_id,
            "ticker": t.ticker,
            "direction": t.direction,
            "quantity": round(t.quantity, 4),
            "entry_date": entry_date,
            "entry_price": round(t.entry_price, 2),
            "exit_date": exit_date,
            "exit_price": round(t.exit_price, 2) if t.exit_price else None,
            "pnl": round(t.pnl, 2),
            "pnl_pct": round(t.pnl_pct * 100, 2),
            "exit_reason": t.exit_reason,
            "status": t.status,
        })
    return {"order_history": result, "total": len(result)}


@app.post("/api/broker/order", tags=["Broker"])
async def broker_place_order(
    req: PlaceOrderRequest,
    current_user: dict = Depends(require_auth),
):
    """
    place_order() — Simulate placing a market order to open a new position.
    """
    trade = _broker.place_order(
        ticker=req.ticker,
        direction=req.direction,
        quantity=req.quantity,
        price=req.price,
        timestamp=datetime.datetime.now(),
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
    )
    if trade is None:
        raise HTTPException(
            status_code=400,
            detail=f"Order rejected — check balance, direction, or existing position for {req.ticker}.",
        )
    return {
        "status": "placed",
        "trade_id": trade.trade_id,
        "ticker": req.ticker,
        "direction": req.direction,
        "quantity": req.quantity,
        "entry_price": req.price,
        "cash_remaining": round(_broker.get_balance(), 2),
    }


@app.delete("/api/broker/order/{ticker}", tags=["Broker"])
async def broker_close_order(
    ticker: str,
    price: float,
    current_user: dict = Depends(require_auth),
):
    """
    close_order() — Close an active position for the given ticker at the given price.
    """
    trade = _broker.close_order(
        ticker=ticker,
        price=price,
        timestamp=datetime.datetime.now(),
        reason="MANUAL",
    )
    if trade is None:
        raise HTTPException(
            status_code=404,
            detail=f"No open position found for ticker: {ticker}",
        )
    return {
        "status": "closed",
        "trade_id": trade.trade_id,
        "ticker": ticker,
        "exit_price": price,
        "pnl": round(trade.pnl, 2),
        "pnl_pct": round(trade.pnl_pct * 100, 2),
        "cash_balance": round(_broker.get_balance(), 2),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET — LIVE PRICE FEED
# ═══════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/live")
async def websocket_live_feed(websocket: WebSocket):
    """
    WebSocket endpoint that streams simulated live price ticks every second.
    Sends JSON: { symbol, price, change, change_pct, volume, timestamp }
    """
    await ws_manager.connect(websocket)
    symbols = {
        "RELIANCE.NS": 2500.0,
        "^NSEI": 22500.0,
        "TCS.NS": 3800.0,
        "^NSEBANK": 48000.0,
    }
    try:
        while True:
            ticks = []
            for symbol, base_price in symbols.items():
                # Simulate a realistic random walk
                change_pct = random.uniform(-0.003, 0.003)
                new_price = round(base_price * (1 + change_pct), 2)
                symbols[symbol] = new_price
                change = round(new_price - base_price, 2)
                ticks.append({
                    "symbol": symbol,
                    "price": new_price,
                    "change": change,
                    "change_pct": round(change_pct * 100, 3),
                    "volume": random.randint(1000, 50000),
                    "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                })
            await websocket.send_json({"type": "tick", "data": ticks})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ═══════════════════════════════════════════════════════════════════════════════
# BACKTEST ENDPOINTS (existing, now require auth)
# ═══════════════════════════════════════════════════════════════════════════════

class BacktestRequest(BaseModel):
    ticker: str = Field("RELIANCE.NS")
    start_date: str = Field("2023-01-01")
    end_date: str = Field("2024-01-01")
    interval: str = Field("1d")
    initial_capital: float = Field(100000.0)
    stop_loss_pct: Optional[float] = Field(0.02)
    take_profit_pct: Optional[float] = Field(0.05)
    risk_pct: Optional[float] = Field(0.01)
    allow_short: bool = Field(False)
    strategy: str = Field("MA_Crossover")
    strategy_params: Dict[str, Any] = Field(
        default={"fast_period": 20, "slow_period": 50, "ma_type": "EMA"}
    )


def _run_backtest_logic(req: BacktestRequest):
    """Shared backtest logic used by both /api/backtest and /api/compare."""
    temp_dir = "data"
    os.makedirs(temp_dir, exist_ok=True)
    temp_csv = f"{temp_dir}/temp_api_{req.ticker}_{req.start_date}_{req.end_date}.csv"

    try:
        df = fetch_historical_data(
            ticker=req.ticker,
            start_date=req.start_date,
            end_date=req.end_date,
            interval=req.interval,
            output_path=temp_csv,
        )
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail=f"No data for: {req.ticker}")

        cleaned_df = load_market_data(temp_csv)

        if req.strategy == "MA_Crossover":
            fast = int(req.strategy_params.get("fast_period", 20))
            slow = int(req.strategy_params.get("slow_period", 50))
            ma_type = str(req.strategy_params.get("ma_type", "EMA"))
            if fast >= slow:
                raise HTTPException(status_code=400, detail="Fast MA must be < Slow MA")
            strategy = MovingAverageCrossover(fast_period=fast, slow_period=slow, ma_type=ma_type)
        elif req.strategy == "MACD":
            fast = int(req.strategy_params.get("fast_period", 12))
            slow = int(req.strategy_params.get("slow_period", 26))
            signal = int(req.strategy_params.get("signal_period", 9))
            if fast >= slow:
                raise HTTPException(status_code=400, detail="Fast EMA must be < Slow EMA")
            strategy = MACDStrategy(fast_period=fast, slow_period=slow, signal_period=signal)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown strategy: {req.strategy}")

        df_signals = strategy.generate_signals(cleaned_df)
        engine = BacktestEngine(
            df=df_signals,
            ticker=req.ticker,
            initial_capital=req.initial_capital,
            stop_loss_pct=req.stop_loss_pct if req.stop_loss_pct and req.stop_loss_pct > 0 else None,
            take_profit_pct=req.take_profit_pct if req.take_profit_pct and req.take_profit_pct > 0 else None,
            risk_pct=req.risk_pct if req.risk_pct and req.risk_pct > 0 else None,
            allow_short=req.allow_short,
        )
        equity_df, trades = engine.run()
        metrics = calculate_performance_metrics(equity_df, trades, req.initial_capital)

        # Build chart data
        chart_data = []
        for ts, row in df_signals.iterrows():
            date_str = ts.strftime("%Y-%m-%d") if isinstance(ts, (datetime.datetime, pd.Timestamp)) else str(ts)
            item = {
                "date": date_str,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
                "signal": str(row["Signal"]),
            }
            if req.strategy == "MA_Crossover":
                item["fast_ma"] = float(row["Fast_MA"]) if not pd.isna(row["Fast_MA"]) else None
                item["slow_ma"] = float(row["Slow_MA"]) if not pd.isna(row["Slow_MA"]) else None
            elif req.strategy == "MACD":
                item["macd_line"] = float(row["MACD_Line"]) if not pd.isna(row["MACD_Line"]) else None
                item["signal_line"] = float(row["Signal_Line"]) if not pd.isna(row["Signal_Line"]) else None
            chart_data.append(item)

        equity_curve = []
        for ts, row in equity_df.iterrows():
            date_str = ts.strftime("%Y-%m-%d") if isinstance(ts, (datetime.datetime, pd.Timestamp)) else str(ts)
            equity_curve.append({
                "date": date_str,
                "equity": float(row["Equity"]),
                "strategy_return": float(row["Strategy_Cum_Return"] * 100),
                "benchmark_return": float(row["Benchmark_Cum_Return"] * 100),
            })

        trade_logs = []
        for t in trades:
            entry_date = t.entry_date.strftime("%Y-%m-%d") if isinstance(t.entry_date, (datetime.datetime, pd.Timestamp)) else str(t.entry_date)
            exit_date = t.exit_date.strftime("%Y-%m-%d") if isinstance(t.exit_date, (datetime.datetime, pd.Timestamp)) else (str(t.exit_date) if t.exit_date else None)
            trade_logs.append({
                "trade_id": t.trade_id,
                "ticker": t.ticker,
                "direction": t.direction,
                "quantity": float(t.quantity),
                "entry_date": entry_date,
                "entry_price": float(t.entry_price),
                "exit_date": exit_date,
                "exit_price": float(t.exit_price) if t.exit_price else None,
                "pnl": float(t.pnl),
                "pnl_pct": float(t.pnl_pct * 100),
                "exit_reason": t.exit_reason,
                "status": t.status,
            })

        return df_signals, equity_df, metrics, trade_logs, equity_curve, chart_data

    finally:
        if os.path.exists(temp_csv):
            try:
                os.remove(temp_csv)
            except Exception:
                pass


@app.post("/api/backtest", tags=["Backtest"])
async def run_backtest(req: BacktestRequest, current_user: dict = Depends(require_auth)):
    try:
        _, _, metrics, trade_logs, equity_curve, chart_data = _run_backtest_logic(req)
        return {
            "status": "success",
            "ticker": req.ticker,
            "metrics": {
                "initial_capital": clean_float(metrics["initial_capital"]),
                "final_equity": clean_float(metrics["final_equity"]),
                "total_pnl": clean_float(metrics["total_pnl"]),
                "total_pnl_pct": clean_float(metrics["total_pnl_pct"] * 100),
                "benchmark_pnl_pct": clean_float(metrics["benchmark_pnl_pct"] * 100),
                "total_trades": int(metrics["total_trades"]),
                "winning_trades": int(metrics["winning_trades"]),
                "losing_trades": int(metrics["losing_trades"]),
                "win_rate": clean_float(metrics["win_rate"] * 100),
                "gross_profit": clean_float(metrics["gross_profit"]),
                "gross_loss": clean_float(metrics["gross_loss"]),
                "profit_factor": clean_float(metrics["profit_factor"]),
                "max_drawdown": clean_float(metrics["max_drawdown"] * 100),
                "sharpe_ratio": clean_float(metrics["sharpe_ratio"]),
            },
            "trades": trade_logs,
            "equity_curve": equity_curve,
            "chart_data": chart_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare", tags=["Backtest"])
async def run_comparison(req: BacktestRequest, current_user: dict = Depends(require_auth)):
    temp_dir = "data"
    os.makedirs(temp_dir, exist_ok=True)
    temp_csv = f"{temp_dir}/temp_compare_{req.ticker}_{req.start_date}_{req.end_date}.csv"

    try:
        df = fetch_historical_data(ticker=req.ticker, start_date=req.start_date, end_date=req.end_date, interval=req.interval, output_path=temp_csv)
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail=f"No data for: {req.ticker}")

        cleaned_df = load_market_data(temp_csv)

        ma_fast = int(req.strategy_params.get("ma_fast_period", 20))
        ma_slow = int(req.strategy_params.get("ma_slow_period", 50))
        strategy_ma = MovingAverageCrossover(fast_period=ma_fast, slow_period=ma_slow, ma_type=str(req.strategy_params.get("ma_type", "EMA")))
        df_ma = strategy_ma.generate_signals(cleaned_df)

        macd_fast = int(req.strategy_params.get("macd_fast_period", 12))
        macd_slow = int(req.strategy_params.get("macd_slow_period", 26))
        macd_signal = int(req.strategy_params.get("macd_signal_period", 9))
        strategy_macd = MACDStrategy(fast_period=macd_fast, slow_period=macd_slow, signal_period=macd_signal)
        df_macd = strategy_macd.generate_signals(cleaned_df)

        def run_engine(df_s):
            eng = BacktestEngine(df=df_s, ticker=req.ticker, initial_capital=req.initial_capital,
                stop_loss_pct=req.stop_loss_pct if req.stop_loss_pct and req.stop_loss_pct > 0 else None,
                take_profit_pct=req.take_profit_pct if req.take_profit_pct and req.take_profit_pct > 0 else None,
                risk_pct=req.risk_pct if req.risk_pct and req.risk_pct > 0 else None,
                allow_short=req.allow_short)
            eq, tr = eng.run()
            return eq, tr

        equity_ma, trades_ma = run_engine(df_ma)
        equity_macd, trades_macd = run_engine(df_macd)
        metrics_ma = calculate_performance_metrics(equity_ma, trades_ma, req.initial_capital)
        metrics_macd = calculate_performance_metrics(equity_macd, trades_macd, req.initial_capital)

        comparison_curve = []
        for ts in equity_ma.index:
            date_str = ts.strftime("%Y-%m-%d") if isinstance(ts, (datetime.datetime, pd.Timestamp)) else str(ts)
            row_ma = equity_ma.loc[ts]
            try:
                macd_ret = float(equity_macd.loc[ts]["Strategy_Cum_Return"] * 100)
            except KeyError:
                macd_ret = 0.0
            comparison_curve.append({
                "date": date_str,
                "ma_return": float(row_ma["Strategy_Cum_Return"] * 100),
                "macd_return": macd_ret,
                "benchmark_return": float(row_ma["Benchmark_Cum_Return"] * 100),
            })

        def fmt(m):
            return {
                "initial_capital": clean_float(m["initial_capital"]),
                "final_equity": clean_float(m["final_equity"]),
                "total_pnl": clean_float(m["total_pnl"]),
                "total_pnl_pct": clean_float(m["total_pnl_pct"] * 100),
                "benchmark_pnl_pct": clean_float(m["benchmark_pnl_pct"] * 100),
                "total_trades": int(m["total_trades"]),
                "winning_trades": int(m["winning_trades"]),
                "losing_trades": int(m["losing_trades"]),
                "win_rate": clean_float(m["win_rate"] * 100),
                "gross_profit": clean_float(m["gross_profit"]),
                "gross_loss": clean_float(m["gross_loss"]),
                "profit_factor": clean_float(m["profit_factor"]),
                "max_drawdown": clean_float(m["max_drawdown"] * 100),
                "sharpe_ratio": clean_float(m["sharpe_ratio"]),
            }

        return {"status": "success", "ticker": req.ticker, "ma_metrics": fmt(metrics_ma), "macd_metrics": fmt(metrics_macd), "comparison_curve": comparison_curve}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_csv):
            try:
                os.remove(temp_csv)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC FILE SERVING — login first, then dashboard
# ═══════════════════════════════════════════════════════════════════════════════

static_path = os.path.join(os.path.dirname(__file__), "static")

@app.get("/", include_in_schema=False)
async def serve_login():
    return FileResponse(os.path.join(static_path, "login.html"))

@app.get("/dashboard", include_in_schema=False)
async def serve_dashboard():
    return FileResponse(os.path.join(static_path, "index.html"))

if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")
