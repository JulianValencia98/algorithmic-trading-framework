from strategies.strategy_base import StrategyBase
import pandas as pd
import numpy as np
from typing import Optional, Tuple


class MeanReversionBBStrategy(StrategyBase):
    """
    Mean Reversion Strategy using Bollinger Bands with multiple confirmations.
    
    Features:
    - Bollinger Bands for entry signals
    - RSI confirmation (optional)
    - Trend filter with EMA (optional)
    - Volume confirmation (optional)
    - Squeeze detection (optional)
    - ATR-based dynamic SL/TP
    
    Magic Number: 10
    
    All parameters are configurable via __init__.
    """

    def __init__(
        self,
        # === IDENTIFICACIÓN ===
        magic_number: int = 10,
        
        # === SÍMBOLOS ===
        symbols: list = None,
        
        # === BOLLINGER BANDS ===
        bb_period: int = 20,
        bb_std: float = 2.5,  # Más amplio = menos señales, más confiables
        
        # === RSI FILTER ===
        use_rsi: bool = True,
        rsi_period: int = 14,
        rsi_oversold: int = 25,  # Más estricto (antes 30)
        rsi_overbought: int = 75,  # Más estricto (antes 70)
        
        # === TREND FILTER ===
        use_trend_filter: bool = True,
        trend_ema_period: int = 50,
        trend_tolerance: float = 0.02,  # 2% tolerance
        
        # === VOLUME FILTER ===
        use_volume_filter: bool = False,
        volume_period: int = 20,
        volume_factor: float = 1.5,
        
        # === SQUEEZE DETECTION ===
        use_squeeze_filter: bool = True,  # Activado - evita entrar en baja volatilidad
        squeeze_lookback: int = 50,
        squeeze_threshold: float = 0.8,
        
        # === RISK MANAGEMENT ===
        risk_percent: float = 1.0,
        use_atr_sl_tp: bool = True,
        atr_period: int = 14,
        sl_atr_mult: float = 1.5,
        tp_atr_mult: float = 3.0,  # Aumentado de 2.0 a 3.0 para mejor R:R
        
        # Fallback fixed pips (when ATR not used)
        sl_pips: float = 30.0,
        tp_pips: float = 60.0,
        
        # === POSITION MANAGEMENT ===
        close_before_open: bool = True,
        max_open_positions: int = 1,
    ):
        super().__init__()
        
        # Identification
        self.magic_number = magic_number
        self.symbols = symbols if symbols else ['GBPUSD']  # GBPUSD optimizado para mean reversion
        
        # Bollinger Bands
        self.bb_period = bb_period
        self.bb_std = bb_std
        
        # RSI Filter
        self.use_rsi = use_rsi
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        
        # Trend Filter
        self.use_trend_filter = use_trend_filter
        self.trend_ema_period = trend_ema_period
        self.trend_tolerance = trend_tolerance
        
        # Volume Filter
        self.use_volume_filter = use_volume_filter
        self.volume_period = volume_period
        self.volume_factor = volume_factor
        
        # Squeeze Detection
        self.use_squeeze_filter = use_squeeze_filter
        self.squeeze_lookback = squeeze_lookback
        self.squeeze_threshold = squeeze_threshold
        
        # Risk Management
        self.risk_percent = risk_percent
        self.use_atr_sl_tp = use_atr_sl_tp
        self.atr_period = atr_period
        self.sl_atr_mult = sl_atr_mult
        self.tp_atr_mult = tp_atr_mult
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        
        # Position Management
        self._close_before_open = close_before_open
        self._max_open_positions = max_open_positions
        
        # Internal state (calculated during generate_signal)
        self.current_atr = None
        self.current_bb_width = None

    def generate_signal(self, data: pd.DataFrame, current_index: int) -> str:
        """
        Generate trading signal based on Bollinger Bands with optional confirmations.
        
        Returns: 'buy', 'sell', or 'hold'
        """
        min_required = max(self.bb_period, self.rsi_period, self.trend_ema_period, self.atr_period) + 10
        
        if current_index < min_required:
            return 'hold'
        
        # Get data slice up to current index
        close = data['close'].iloc[:current_index + 1]
        high = data['high'].iloc[:current_index + 1]
        low = data['low'].iloc[:current_index + 1]
        
        current_price = close.iloc[-1]
        
        # === CALCULATE BOLLINGER BANDS ===
        sma = close.rolling(window=self.bb_period).mean()
        std = close.rolling(window=self.bb_period).std()
        
        upper_band = sma + (self.bb_std * std)
        lower_band = sma - (self.bb_std * std)
        
        current_sma = sma.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        
        # Store BB width for squeeze detection
        self.current_bb_width = (current_upper - current_lower) / current_sma
        
        # === CALCULATE ATR ===
        self.current_atr = self._calculate_atr(high, low, close)
        
        # === CHECK SQUEEZE (if enabled) ===
        if self.use_squeeze_filter:
            bb_width_series = (upper_band - lower_band) / sma
            avg_width = bb_width_series.rolling(self.squeeze_lookback).mean().iloc[-1]
            
            if self.current_bb_width < avg_width * self.squeeze_threshold:
                # In squeeze - avoid trading
                return 'hold'
        
        # === CHECK VOLUME (if enabled) ===
        if self.use_volume_filter and 'tick_volume' in data.columns:
            volume = data['tick_volume'].iloc[:current_index + 1]
            avg_volume = volume.rolling(self.volume_period).mean().iloc[-1]
            current_volume = volume.iloc[-1]
            
            if current_volume < avg_volume * self.volume_factor:
                return 'hold'
        
        # === CALCULATE RSI (if enabled) ===
        rsi_ok_buy = True
        rsi_ok_sell = True
        
        if self.use_rsi:
            current_rsi = self._calculate_rsi(close)
            rsi_ok_buy = current_rsi < self.rsi_oversold
            rsi_ok_sell = current_rsi > self.rsi_overbought
        
        # === CHECK TREND (if enabled) ===
        trend_ok_buy = True
        trend_ok_sell = True
        
        if self.use_trend_filter:
            ema_trend = close.ewm(span=self.trend_ema_period, adjust=False).mean().iloc[-1]
            
            # For buy: price should be near or above EMA (uptrend context)
            trend_ok_buy = current_price > ema_trend * (1 - self.trend_tolerance)
            # For sell: price should be near or below EMA (downtrend context)
            trend_ok_sell = current_price < ema_trend * (1 + self.trend_tolerance)
        
        # === GENERATE SIGNALS ===
        # BUY: Price at lower band + RSI oversold + Uptrend context
        if current_price <= current_lower:
            if rsi_ok_buy and trend_ok_buy:
                return 'buy'
        
        # SELL: Price at upper band + RSI overbought + Downtrend context
        if current_price >= current_upper:
            if rsi_ok_sell and trend_ok_sell:
                return 'sell'
        
        return 'hold'

    def _calculate_rsi(self, close: pd.Series) -> float:
        """Calculate RSI indicator."""
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]

    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> float:
        """Calculate ATR (Average True Range)."""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        # Use numpy maximum instead of concat for better performance
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        atr = tr.rolling(window=self.atr_period).mean()
        
        return atr.iloc[-1]

    def get_parameters(self) -> dict:
        """Return strategy configuration parameters."""
        return {
            'strategy_name': 'MeanReversionBB',
            'magic_number': self.magic_number,
            'description': 'Mean Reversion with Bollinger Bands and multiple confirmations',
            
            # Supported symbols
            'symbols': self.symbols,
            
            # Position Management
            'close_before_open': self._close_before_open,
            'max_open_positions': self._max_open_positions,
            
            # Strategy parameters (for logging/debugging)
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'use_rsi': self.use_rsi,
            'use_trend_filter': self.use_trend_filter,
            'use_volume_filter': self.use_volume_filter,
            'use_squeeze_filter': self.use_squeeze_filter,
            'risk_percent': self.risk_percent,
        }

    def calculate_position_size(self, symbol: str, equity: float, entry_price: float) -> float:
        """
        Calculate position size based on risk percentage.
        
        Uses ATR-based SL to calculate proper position size.
        """
        risk_amount = equity * (self.risk_percent / 100)
        
        pip_size = self.get_pip_size(symbol)
        symbol_info = self.get_symbol_info(symbol)
        
        if symbol_info is None or pip_size <= 0:
            return 0.01  # Minimum fallback
        
        # Calculate SL in pips
        if self.use_atr_sl_tp and self.current_atr is not None:
            sl_distance = self.current_atr * self.sl_atr_mult
            sl_pips = sl_distance / pip_size
        else:
            sl_pips = self.sl_pips
        
        # Calculate lot size
        # pip_value = contract_size * pip_size (per lot)
        pip_value = symbol_info.trade_contract_size * pip_size
        
        if sl_pips > 0 and pip_value > 0:
            volume = risk_amount / (sl_pips * pip_value)
        else:
            volume = 0.01
        
        # Clamp to valid range
        volume = max(symbol_info.volume_min, min(volume, symbol_info.volume_max))
        
        # Round to step
        volume_step = symbol_info.volume_step
        volume = round(volume / volume_step) * volume_step
        
        return round(volume, 2)

    def calculate_sl_tp(self, symbol: str, action: str, entry_price: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate Stop Loss and Take Profit prices.
        
        Uses ATR-based dynamic levels or fixed pips.
        """
        pip_size = self.get_pip_size(symbol)
        
        if pip_size <= 0:
            return None, None
        
        # Determine SL/TP distances
        if self.use_atr_sl_tp and self.current_atr is not None:
            sl_distance = self.current_atr * self.sl_atr_mult
            tp_distance = self.current_atr * self.tp_atr_mult
        else:
            sl_distance = self.sl_pips * pip_size
            tp_distance = self.tp_pips * pip_size
        
        # Calculate prices based on action
        if action.lower() == 'buy':
            sl = entry_price - sl_distance
            tp = entry_price + tp_distance
        else:  # sell
            sl = entry_price + sl_distance
            tp = entry_price - tp_distance
        
        # Round to symbol's digit precision
        symbol_info = self.get_symbol_info(symbol)
        if symbol_info:
            digits = symbol_info.digits
            sl = round(sl, digits)
            tp = round(tp, digits)
        
        return (sl, tp)

    def get_config_summary(self) -> str:
        """Return a human-readable summary of current configuration."""
        filters = []
        if self.use_rsi:
            filters.append(f"RSI({self.rsi_period})")
        if self.use_trend_filter:
            filters.append(f"EMA({self.trend_ema_period})")
        if self.use_volume_filter:
            filters.append(f"Volume({self.volume_factor}x)")
        if self.use_squeeze_filter:
            filters.append("Squeeze")
        
        sl_tp_mode = "ATR-dynamic" if self.use_atr_sl_tp else "Fixed pips"
        
        return (
            f"MeanReversionBB [Magic: {self.magic_number}]\n"
            f"  BB: period={self.bb_period}, std={self.bb_std}\n"
            f"  Filters: {', '.join(filters) if filters else 'None'}\n"
            f"  Risk: {self.risk_percent}% per trade\n"
            f"  SL/TP: {sl_tp_mode}"
        )


# === PRESET CONFIGURATIONS ===

def create_conservative_strategy() -> MeanReversionBBStrategy:
    """Conservative configuration - fewer trades, higher win rate."""
    return MeanReversionBBStrategy(
        magic_number=11,
        bb_period=20,
        bb_std=2.5,  # Wider bands = fewer signals
        use_rsi=True,
        rsi_oversold=25,
        rsi_overbought=75,
        use_trend_filter=True,
        use_volume_filter=True,
        use_squeeze_filter=True,
        risk_percent=0.5,  # Lower risk
        sl_atr_mult=2.0,
        tp_atr_mult=1.5,
    )


def create_aggressive_strategy() -> MeanReversionBBStrategy:
    """Aggressive configuration - more trades, higher risk."""
    return MeanReversionBBStrategy(
        magic_number=12,
        bb_period=14,
        bb_std=1.5,  # Tighter bands = more signals
        use_rsi=True,
        rsi_oversold=35,
        rsi_overbought=65,
        use_trend_filter=False,  # Trade against trend too
        use_volume_filter=False,
        use_squeeze_filter=False,
        risk_percent=2.0,  # Higher risk
        sl_atr_mult=1.0,
        tp_atr_mult=3.0,
    )


def create_scalping_strategy() -> MeanReversionBBStrategy:
    """Scalping configuration - fast timeframes, tight stops."""
    return MeanReversionBBStrategy(
        magic_number=13,
        bb_period=10,
        bb_std=1.5,
        use_rsi=True,
        rsi_period=7,
        rsi_oversold=30,
        rsi_overbought=70,
        use_trend_filter=False,
        use_volume_filter=False,
        use_squeeze_filter=False,
        risk_percent=0.5,
        use_atr_sl_tp=False,
        sl_pips=15.0,
        tp_pips=20.0,
    )
