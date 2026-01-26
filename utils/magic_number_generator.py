"""
Magic Number Generator for Trading Framework

Generates unique magic numbers for each bot based on:
- Strategy base number (e.g., SimpleTimeStrategy = 1)
- Symbol suffix (e.g., EURUSD = .1, GBPUSD = .2)
- Timeframe suffix (additional decimal)

Example: SimpleTimeStrategy (1) + EURUSD (.1) + M5 (.01) = 1.11
         SimpleTimeStrategy (1) + GBPUSD (.2) + M1 (.00) = 1.20

This allows identifying the strategy, symbol, and timeframe from the magic number.
"""

import MetaTrader5 as mt5
from typing import Dict


class MagicNumberGenerator:
    """
    Generates unique magic numbers for trading bots.
    Format: BASE.SYMBOL_TIMEFRAME
    """
    
    # Mapping de símbolos a sufijos (0.1, 0.2, 0.3, etc.)
    SYMBOL_MAP: Dict[str, int] = {
        'EURUSD': 1,
        'GBPUSD': 2,
        'USDJPY': 3,
        'USDCHF': 4,
        'AUDUSD': 5,
        'USDCAD': 6,
        'NZDUSD': 7,
        'EURGBP': 8,
        'EURJPY': 9,
        'GBPJPY': 10,
        'GOLD': 11,
        'XAUUSD': 11,  # Alias para GOLD
        'SILVER': 12,
        'XAGUSD': 12,  # Alias para SILVER
        'US30': 13,
        'US100': 14,
        'US500': 15,
        'ETHUSD': 17,
    }
    
    # Mapping de timeframes a sufijos adicionales (0.00, 0.01, 0.02, etc.)
    TIMEFRAME_MAP: Dict[int, int] = {
        mt5.TIMEFRAME_M1: 0,
        mt5.TIMEFRAME_M5: 1,
        mt5.TIMEFRAME_M15: 2,
        mt5.TIMEFRAME_M30: 3,
        mt5.TIMEFRAME_H1: 4,
        mt5.TIMEFRAME_H4: 5,
        mt5.TIMEFRAME_D1: 6,
        mt5.TIMEFRAME_W1: 7,
        mt5.TIMEFRAME_MN1: 8,
    }
    
    @staticmethod
    def generate(strategy_base: int, symbol: str, timeframe: int) -> int:
        """
        Genera un magic number único basado en estrategia, símbolo y timeframe.
        
        Args:
            strategy_base: Número base de la estrategia (1, 2, 3, etc.)
            symbol: Símbolo de trading (e.g., 'EURUSD', 'GBPUSD')
            timeframe: Timeframe MT5 (e.g., mt5.TIMEFRAME_M1, mt5.TIMEFRAME_H1)
        
        Returns:
            Magic number único como entero
        
        Example:
            >>> MagicNumberGenerator.generate(1, 'EURUSD', mt5.TIMEFRAME_M1)
            110  # Representa: Strategy 1 + EURUSD (1) + M1 (0)
            
            >>> MagicNumberGenerator.generate(1, 'GBPUSD', mt5.TIMEFRAME_M5)
            121  # Representa: Strategy 1 + GBPUSD (2) + M5 (1)
        """
        # Obtener sufijo del símbolo
        symbol_suffix = MagicNumberGenerator.SYMBOL_MAP.get(symbol.upper(), 99)
        
        # Obtener sufijo del timeframe
        timeframe_suffix = MagicNumberGenerator.TIMEFRAME_MAP.get(timeframe, 9)
        
        # Construir magic number: BASE * 100 + SYMBOL * 10 + TIMEFRAME
        magic_number = (strategy_base * 100) + (symbol_suffix * 10) + timeframe_suffix
        
        return magic_number
    
    @staticmethod
    def parse(magic_number: int) -> Dict[str, int]:
        """
        Parsea un magic number para extraer sus componentes.
        
        Args:
            magic_number: Magic number a parsear
        
        Returns:
            Diccionario con 'strategy_base', 'symbol_code', 'timeframe_code'
        
        Example:
            >>> MagicNumberGenerator.parse(110)
            {'strategy_base': 1, 'symbol_code': 1, 'timeframe_code': 0}
        """
        strategy_base = magic_number // 100
        remainder = magic_number % 100
        symbol_code = remainder // 10
        timeframe_code = remainder % 10
        
        return {
            'strategy_base': strategy_base,
            'symbol_code': symbol_code,
            'timeframe_code': timeframe_code
        }
    
    @staticmethod
    def add_symbol(symbol: str, code: int):
        """
        Agrega un nuevo símbolo al mapeo (para símbolos personalizados).
        
        Args:
            symbol: Nombre del símbolo
            code: Código único (1-99)
        """
        if code < 1 or code > 99:
            raise ValueError("Symbol code must be between 1 and 99")
        
        MagicNumberGenerator.SYMBOL_MAP[symbol.upper()] = code
    
    @staticmethod
    def get_symbol_name(code: int) -> str:
        """
        Obtiene el nombre del símbolo a partir de su código.
        
        Args:
            code: Código del símbolo
        
        Returns:
            Nombre del símbolo o 'UNKNOWN' si no existe
        """
        for symbol, symbol_code in MagicNumberGenerator.SYMBOL_MAP.items():
            if symbol_code == code:
                return symbol
        return 'UNKNOWN'
    
    @staticmethod
    def get_timeframe_name(code: int) -> str:
        """
        Obtiene el nombre del timeframe a partir de su código.
        
        Args:
            code: Código del timeframe
        
        Returns:
            Nombre del timeframe o 'UNKNOWN' si no existe
        """
        timeframe_names = {
            0: 'M1',
            1: 'M5',
            2: 'M15',
            3: 'M30',
            4: 'H1',
            5: 'H4',
            6: 'D1',
            7: 'W1',
            8: 'MN1',
        }
        return timeframe_names.get(code, 'UNKNOWN')
