import logging
import os
import sys

def setup_logger(name="algo_trading", log_file="algo_trading.log", level=logging.INFO):
    """
    Sets up a logger that outputs to both console and a log file.
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if setup_logger is called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Formatters
    log_format = "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    try:
        # Create directory for log file if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to set up file logging: {e}", file=sys.stderr)

    return logger

# Create a default system-wide logger
logger = setup_logger()
