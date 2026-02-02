from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import MetaTrader5 as mt5

class StrategyBase(ABC):
    """
    Abstract base class for trading strategies.
    Each strategy is fully autonomous: it controls signal generation,
    position sizing, and SL/TP calculation.
    
    The framework only orchestrates execution - the strategy decides everything.
    
    Required methods to implement:
    - generate_signal(): Returns 'buy', 'sell', or 'hold'
    - get_parameters(): Returns strategy configuration
    - calculate_position_size(): Returns lot size for the trade
    - calculate_sl_tp(): Returns (sl_price, tp_price) tuple
    
    Position Management (in get_parameters):
    - close_before_open: bool (True = close existing before opening new)
    - max_open_positions: int (max simultaneous positions if close_before_open=False)
    """
    
    def __init__(self):
        self.magic_number = None  # Must be set by child class

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame, current_index: int) -> str:
        """
        Generate trading signal based on data.
        Returns: 'buy', 'sell', 'hold'
        """
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """
        Return strategy configuration parameters.
        
        Required keys:
        - close_before_open: bool
        - max_open_positions: int
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, symbol: str, equity: float, entry_price: float) -> float:
        """
        Calculate position size (lots) for the trade.
        
        Args:
            symbol: Trading symbol
            equity: Current account equity
            entry_price: Expected entry price
        
        Returns:
            Position size in lots
        """
        pass
    
    @abstractmethod
    def calculate_sl_tp(self, symbol: str, action: str, entry_price: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate Stop Loss and Take Profit prices.
        
        Args:
            symbol: Trading symbol
            action: 'buy' or 'sell'
            entry_price: Entry price for the trade
        
        Returns:
            Tuple of (sl_price, tp_price). Use None for no SL or TP.
        """
        pass
    
    def get_magic_number(self) -> int:
        """
        Return the unique magic number for this strategy.
        """
        if self.magic_number is None:
            raise ValueError(f"Magic number not set for strategy {self.__class__.__name__}")
        return self.magic_number
    
    def should_close_before_open(self) -> bool:
        """
        Returns True if existing positions should be closed before opening new ones.
        """
        params = self.get_parameters()
        return params.get('close_before_open', True)
    
    def get_max_open_positions(self) -> int:
        """
        Returns maximum number of simultaneous positions allowed.
        """
        params = self.get_parameters()
        return params.get('max_open_positions', 1)
    
    # ========== HELPER METHODS FOR CHILD CLASSES ==========
    
    @staticmethod
    def get_pip_size(symbol: str) -> float:
        """
        Helper: Get pip size for a symbol.
        Uses symbol search to handle suffixes correctly.
        """
        try:
            # Try to find symbol info with potential suffix
            info = None
            
            # First try direct lookup
            info = mt5.symbol_info(symbol)
            
            # If not found, try common suffixes
            if info is None:
                suffixes = ['.sml', '.raw', 'c', 'm', '', '.ecn', '.pro']
                for suffix in suffixes:
                    test_symbol = symbol + suffix
                    info = mt5.symbol_info(test_symbol)
                    if info is not None:
                        break
            
            if info is None:
                print(f"Warning: Symbol {symbol} not found for pip size calculation")
                # Return default pip size based on symbol type
                if 'JPY' in symbol:
                    return 0.01  # JPY pairs typically have 2 decimal places
                else:
                    return 0.0001  # Most major pairs have 4 decimal places
            
            # Calculate pip size based on digits
            if info.digits in (3, 5):
                return info.point * 10
            return info.point
            
        except Exception as e:
            print(f"Error calculating pip size for {symbol}: {e}")
            # Return conservative default
            if 'JPY' in symbol:
                return 0.01
            else:
                return 0.0001
    
    @staticmethod
    def get_symbol_info(symbol: str):
        """
        Helper: Get MT5 symbol info.
        """
        return mt5.symbol_info(symbol)
    
    @staticmethod
    def pips_to_price(entry_price: float, pips: float, action: str, pip_size: float) -> float:
        """
        Helper: Convert pips to price level.
        
        Args:
            entry_price: Entry price
            pips: Number of pips
            action: 'buy' or 'sell'
            pip_size: Size of one pip
        
        Returns:
            Price level
        """
        if action.lower() == 'buy':
            return entry_price + (pips * pip_size)
        else:
            return entry_price - (pips * pip_size)