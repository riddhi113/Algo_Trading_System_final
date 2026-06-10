from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies strategy logic to the input market data DataFrame.
        Must return a copy/modified DataFrame with a 'Signal' column containing
        'BUY', 'SELL', or 'HOLD'.
        
        Args:
            df (pd.DataFrame): Dataframe containing historical OHLCV data.

        Returns:
            pd.DataFrame: Dataframe with technical indicators and a 'Signal' column.
        """
        pass
