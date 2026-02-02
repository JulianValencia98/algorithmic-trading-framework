from strategies.strategy_base import StrategyBase
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple

class SimpleTimeStrategy(StrategyBase):
    """
    Strategy that opens a buy position, keeps it open for 20 minutes, closes it, and immediately opens another buy.
    Continuous loop: buy -> wait 20 min -> close -> buy again.
    Magic Number: 1
    
    Risk Management:
    - Fixed lot size: 0.05
    - Fixed SL: 100 pips
    - Fixed TP: 300 pips
    """

    def __init__(self):
        super().__init__()
        self.magic_number = 1  # Unique identifier for this strategy
        self.last_signal_time = None
        self.position_open_time = None
        self.has_position = False
        
        # Strategy-specific risk parameters
        self.fixed_lot = 0.05
        self.sl_pips = 100.0
        self.tp_pips = 300.0

    def generate_signal(self, data: pd.DataFrame, current_index: int) -> str:
        """
        Generate buy signal initially, then check if 2 minutes have passed to close and reopen.
        """
        if current_index >= len(data):
            return 'hold'
        
        # Use 'time' column if it exists, otherwise use index
        if 'time' in data.columns:
            current_time = data.iloc[current_index]['time']
        else:
            current_time = data.index[current_index]
        
        # If no position, open a buy immediately
        if not self.has_position:
            self.has_position = True
            self.position_open_time = current_time
            self.last_signal_time = current_time
            return 'buy'
        
        # If position is open, check if 2 minutes have passed
        if self.has_position and self.position_open_time is not None:
            # Calculate time difference (handle both datetime and int timestamps)
            if isinstance(current_time, int) or isinstance(current_time, float):
                time_diff_seconds = current_time - (self.position_open_time if isinstance(self.position_open_time, (int, float)) else self.position_open_time.timestamp())
            else:
                time_diff_seconds = (current_time - self.position_open_time).total_seconds()
            
            # After 20 minutes (1200 seconds), close and immediately reopen
            if time_diff_seconds >= 1200:  # 1200 seconds = 20 minutes
                self.position_open_time = current_time
                self.last_signal_time = current_time
                return 'buy'
        
        return 'hold'

    def get_parameters(self) -> dict:
        return {
            'strategy_name': 'SimpleTimeStrategy',
            'magic_number': self.magic_number,
            'description': 'Opens buy position, waits 20 min, closes and reopens',
            
            # Símbolos soportados por esta estrategia
            'symbols': ['EURUSD', 'GBPUSD', 'USDJPY'],  # Símbolos principales
            
            # Position Management
            'close_before_open': False,  # No cerrar posiciones existentes
            'max_open_positions': 1,      # Solo 1 posición a la vez
        }
    
    def calculate_position_size(self, symbol: str, equity: float, entry_price: float) -> float:
        """
        Returns fixed lot size for this strategy.
        """
        return self.fixed_lot
    
    def calculate_sl_tp(self, symbol: str, action: str, entry_price: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate SL/TP based on fixed pips.
        """
        pip_size = self.get_pip_size(symbol)
        if pip_size <= 0:
            return None, None
        
        if action.lower() == 'buy':
            sl = entry_price - (self.sl_pips * pip_size)
            tp = entry_price + (self.tp_pips * pip_size)
        else:  # sell
            sl = entry_price + (self.sl_pips * pip_size)
            tp = entry_price - (self.tp_pips * pip_size)
        
        return sl, tp