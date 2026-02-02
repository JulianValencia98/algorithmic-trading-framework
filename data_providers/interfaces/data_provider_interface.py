"""
Data Provider Interface - Abstracción para múltiples fuentes de datos

Permite usar diferentes proveedores (MT5, Oanda, Investing.com, etc.)
de forma intercambiable en el framework.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from datetime import datetime
from enum import Enum


class DataProviderType(Enum):
    """Tipos de proveedores de datos."""
    MT5 = "mt5"
    OANDA = "oanda"
    INVESTING = "investing"
    ALPHA_VANTAGE = "alpha_vantage"
    YAHOO = "yahoo"


class TimeFrame(Enum):
    """Timeframes estandarizados."""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"


class MarketData:
    """Estructura estandarizada para datos de mercado."""
    def __init__(
        self,
        symbol: str,
        timeframe: TimeFrame,
        data: pd.DataFrame,
        provider: DataProviderType,
        last_update: datetime
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.data = data
        self.provider = provider
        self.last_update = last_update
        
    def validate(self) -> bool:
        """Valida que los datos tengan las columnas requeridas."""
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        return all(col in self.data.columns for col in required_cols)


class IDataProvider(ABC):
    """Interface para proveedores de datos."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Establece conexión con el proveedor."""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Cierra conexión con el proveedor."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Verifica si está conectado."""
        pass
    
    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        timeframe: TimeFrame,
        count: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Optional[MarketData]:
        """Obtiene datos históricos."""
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """Obtiene precio actual (bid/ask)."""
        pass
    
    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Obtiene información del símbolo."""
        pass
    
    @abstractmethod
    def get_available_symbols(self) -> List[str]:
        """Lista símbolos disponibles."""
        pass
    
    @abstractmethod
    def is_market_open(self, symbol: str) -> bool:
        """Verifica si el mercado está abierto."""
        pass
    
    @property
    @abstractmethod
    def provider_type(self) -> DataProviderType:
        """Tipo de proveedor."""
        pass