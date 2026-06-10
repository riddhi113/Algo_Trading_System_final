# Standard DataFrame Columns
DATE = "Date"
OPEN = "Open"
HIGH = "High"
LOW = "Low"
CLOSE = "Close"
VOLUME = "Volume"
ADJ_CLOSE = "Adj Close"

# Required columns for strategies and backtester
REQUIRED_COLUMNS = [DATE, OPEN, HIGH, LOW, CLOSE, VOLUME]

# Default parameters
DEFAULT_CONFIG_PATH = "config/config.yaml"
DEFAULT_DATA_DIR = "data"
DEFAULT_MARKET_DATA_FILE = "data/market_data.csv"
