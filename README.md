# Mini Algo Trading System

## Overview
This is a mini algorithmic trading system built with Python and FastAPI. It includes a backtesting pipeline and a web dashboard to visualize trading results, metrics, and logs.

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/riddhi113/Algo_Trading_System_final.git
   cd Algo_Trading_System_final
   ```

2. **Run the setup script:**
   This will create a Python virtual environment and install all necessary dependencies.
   ```bash
   bash setup.sh
   ```

## Running the Project

To run the backtest and start the dashboard server, simply execute:
```bash
./run.sh
```

**What this does:**
1. Runs the backtesting pipeline (using historical data).
2. Starts the FastAPI server to serve the results and the web dashboard.

**View the Dashboard:**
Once the server is running, open your web browser and go to:
[http://127.0.0.1:8080](http://127.0.0.1:8080)

To stop the server, press `Ctrl+C` in your terminal.

## Using the Dashboard
- **Asset Configuration:** Select different strategies or parameters in the left sidebar.
- **Run Backtest:** Click the "Run Backtest" button in the sidebar to execute a backtest with your selected parameters.
- **Charts and Logs:** The main view will display the Candlestick Chart with trades, Performance Curve, and a detailed Trade Log.
