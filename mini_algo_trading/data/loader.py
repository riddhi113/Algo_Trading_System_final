import os
import sys

# Ensure the project root is in sys.path when running as a standalone script
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import yfinance as yf
from typing import Optional, Dict
from mini_algo_trading.utils.logger import logger
from mini_algo_trading.utils.constants import REQUIRED_COLUMNS, DATE, OPEN, HIGH, LOW, CLOSE, VOLUME

def fetch_historical_data(
    ticker: str,
    start_date: str,
    end_date: str,
    interval: str = "1d",
    output_path: Optional[str] = None
) -> Optional[pd.DataFrame]:

    logger.info(f"Fetching data for {ticker} from {start_date} to {end_date} (Interval: {interval})...")

    try:
        df = yf.download(ticker, start=start_date, end=end_date, interval=interval,
                         progress=False, auto_adjust=True)

        if df.empty:
            logger.error(f"No data returned for ticker '{ticker}' in the specified range.")
            return None

        df = df.reset_index()

        #Validation

        # 1. Flatten multi-level columns 
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        # 2. Standardize column names to constants
        date_col = "Datetime" if "Datetime" in df.columns else "Date"
        df = df.rename(columns={date_col: DATE})

        col_mapping = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower == "open":
                col_mapping[col] = OPEN
            elif col_lower == "high":
                col_mapping[col] = HIGH
            elif col_lower == "low":
                col_mapping[col] = LOW
            elif col_lower == "close":
                col_mapping[col] = CLOSE
            elif col_lower == "volume":
                col_mapping[col] = VOLUME
        df = df.rename(columns=col_mapping)

        # 3. Keep only standard OHLCV columns that exist
        keep_cols = [DATE, OPEN, HIGH, LOW, CLOSE, VOLUME]
        df = df[[c for c in keep_cols if c in df.columns]]

        # 4. Parse and sort by date
        df[DATE] = pd.to_datetime(df[DATE])
        df = df.set_index(DATE).sort_index()

        # 5. Cast price/volume columns to numeric
        for col in [OPEN, HIGH, LOW, CLOSE]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if VOLUME in df.columns:
            df[VOLUME] = pd.to_numeric(df[VOLUME], errors="coerce")

        # 6. Handle missing values — drop rows where Open or Close is NaN, ffill rest
        critical_cols = [c for c in [OPEN, CLOSE] if c in df.columns]
        before = len(df)
        df = df.dropna(subset=critical_cols)
        other_cols = [c for c in [HIGH, LOW, VOLUME] if c in df.columns]
        if other_cols:
            df[other_cols] = df[other_cols].ffill().bfill()
        after = len(df)
        if before != after:
            logger.warning(f"Dropped {before - after} row(s) with missing Open/Close values.")

        # 7. Fix High/Low logic violations (High < Close or Low > Open, etc.)
        violations = df[
            (df[HIGH] < df[OPEN]) | (df[HIGH] < df[CLOSE]) |
            (df[LOW] > df[OPEN]) | (df[LOW] > df[CLOSE])
        ]
        if not violations.empty:
            logger.warning(
                f"Detected {len(violations)} row(s) with illogical High/Low prices. Correcting."
            )
            df[HIGH] = df[[OPEN, HIGH, LOW, CLOSE]].max(axis=1)
            df[LOW]  = df[[OPEN, HIGH, LOW, CLOSE]].min(axis=1)

        logger.info(f"Data validated and cleaned. Total rows: {len(df)}")

        # Save to CSV
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            df.to_csv(output_path)
            logger.info(f"Successfully saved historical data to {output_path}")

        return df

    except Exception as e:
        logger.error(f"An error occurred while fetching data from yfinance: {e}", exc_info=True)
        return None


def load_market_data(filepath: str) -> pd.DataFrame:
    """
    Loads market data from a CSV, validates it, handles missing/invalid values,
    and returns a clean, structured pandas DataFrame.

    Args:
        filepath (str): The path to the CSV file.

    Returns:
        pd.DataFrame: Cleaned and validated DataFrame with Date/Datetime as Index.
    """
    logger.info(f"Loading market data from {filepath}...")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Market data file not found at: {filepath}")

    # Load the CSV
    df = pd.read_csv(filepath)
    
    # 1. Validate Column Names (Case-insensitive check and conversion)
    df.columns = [col.strip() for col in df.columns]
    
    # Check if we have Date/Datetime column
    date_col = None
    for name in [DATE, "Datetime", "date", "datetime", "Timestamp", "timestamp"]:
        if name in df.columns:
            date_col = name
            break
            
    if not date_col:
        # Check if index is already datetime
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
            date_col = "index"
        else:
            raise ValueError(f"No valid Date/Datetime column found. Available columns: {list(df.columns)}")

    # Standardize column mapping to expected constants (e.g. Open, High, Low, Close, Volume)
    col_mapping = {}
    for col in df.columns:
        col_lower = col.lower()
        if col_lower == "open":
            col_mapping[col] = OPEN
        elif col_lower == "high":
            col_mapping[col] = HIGH
        elif col_lower == "low":
            col_mapping[col] = LOW
        elif col_lower in ["close", "adj close"]:
            # Prioritize 'Close' if both exist, or Map close
            if col_lower == "close":
                col_mapping[col] = CLOSE
        elif col_lower == "volume":
            col_mapping[col] = VOLUME

    # Apply mapping
    df = df.rename(columns=col_mapping)
    
    # Ensure Date column is named exactly as the DATE constant
    if date_col != DATE:
        df = df.rename(columns={date_col: DATE})

    # 2. Check for required columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in market data: {missing_cols}")

    # 3. Format Date/Datetime index
    try:
        df[DATE] = pd.to_datetime(df[DATE])
    except Exception as e:
        raise ValueError(f"Failed to parse dates in '{DATE}' column: {e}")

    df = df.set_index(DATE)
    df = df.sort_index()

    # 4. Handle Missing Values
    # Check for NaN count
    nan_counts = df[REQUIRED_COLUMNS[1:]].isna().sum()
    if nan_counts.sum() > 0:
        logger.warning(f"Missing values detected in data: \n{nan_counts}")
        # Drop rows where critical columns (Open, Close) are completely missing
        critical_cols = [OPEN, CLOSE]
        df = df.dropna(subset=critical_cols)
        
        # Forward fill and backward fill other columns (High, Low, Volume)
        df = df.ffill().bfill()
        logger.info("Missing values handled using forward and backward fill.")

    # 5. Data Type Casting and Validations
    for col in [OPEN, HIGH, LOW, CLOSE]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[VOLUME] = pd.to_numeric(df[VOLUME], errors="coerce")

    # Drop any remaining rows that couldn't be converted to numeric
    before_drop = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS[1:])
    after_drop = len(df)
    if before_drop != after_drop:
        logger.warning(f"Dropped {before_drop - after_drop} row(s) containing non-numeric values.")

    # 6. Logical Consistency Checks (High >= Low, High >= Open/Close, Low <= Open/Close)
    # Ensure all prices are positive
    invalid_prices = df[(df[OPEN] <= 0) | (df[HIGH] <= 0) | (df[LOW] <= 0) | (df[CLOSE] <= 0)]
    if not invalid_prices.empty:
        logger.warning(f"Detected {len(invalid_prices)} row(s) with non-positive prices. Dropping these rows.")
        df = df[(df[OPEN] > 0) & (df[HIGH] > 0) & (df[LOW] > 0) & (df[CLOSE] > 0)]

    # Fix price logic violations (sometimes yfinance data has minor noise where High is slightly lower than Close/Open)
    # We will adjust High to be the max, and Low to be the min of all four prices
    violations = df[(df[HIGH] < df[OPEN]) | (df[HIGH] < df[CLOSE]) | (df[LOW] > df[OPEN]) | (df[LOW] > df[CLOSE])]
    if not violations.empty:
        logger.warning(f"Detected {len(violations)} row(s) with illogical High/Low prices (e.g. High < Close). Correcting them.")
        df[HIGH] = df[[OPEN, HIGH, LOW, CLOSE]].max(axis=1)
        df[LOW] = df[[OPEN, HIGH, LOW, CLOSE]].min(axis=1)

    logger.info(f"Market data loaded successfully. Total rows: {len(df)}")
    return df


# Run this file directly to download multiple tickers into one combined CSV.

if __name__ == "__main__":

    TICKERS = {
        "Reliance":  "RELIANCE.NS",
        "Nifty":     "^NSEI",
        "BankNifty": "^NSEBANK",
        "TCS":       "TCS.NS",
        "HDFC":      "HDFCBANK.NS",
    }
    START_DATE  = "2023-01-01"
    END_DATE    = "2024-01-01"
    INTERVAL    = "1d"
    OUTPUT_PATH = "data/all_market_data.csv"

    print("=" * 55)
    print("  Multi-Ticker Data Downloader")
    print("=" * 55)

    all_frames = []
    for name, symbol in TICKERS.items():
        df = fetch_historical_data(
            ticker=symbol,
            start_date=START_DATE,
            end_date=END_DATE,
            interval=INTERVAL,
            output_path=None
        )
        if df is not None and not df.empty:
            df = df.reset_index()
            df[DATE] = pd.to_datetime(df[DATE]).dt.date
            df.insert(1, "Ticker", name)
            df.insert(2, "Symbol", symbol)
            all_frames.append(df)

    if all_frames:
        combined_df = pd.concat(all_frames, ignore_index=True)
        combined_df = combined_df.sort_values([DATE, "Ticker"]).reset_index(drop=True)
        os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)
        combined_df.to_csv(OUTPUT_PATH, index=False)
        print(f"\nSaved to: {OUTPUT_PATH}")
        print(f"Total rows: {len(combined_df)}")
        print("\nRows per ticker:")
        print(combined_df.groupby("Ticker").size().to_string())
        print("\nPreview (first 8 rows):")
        print(combined_df.head(8).to_string(index=False))
    else:
        print("Download failed. Check the logs above for errors.")
