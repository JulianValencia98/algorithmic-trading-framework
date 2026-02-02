# Data Providers Package
"""
Sistema de proveedores de datos para el framework de trading.

Permite obtener datos de múltiples fuentes (MetaTrader5, Oanda, etc.)
con failover automático y gestión centralizada.
"""

from .interfaces.data_provider_interface import (
    IDataProvider, 
    DataProviderType, 
    TimeFrame, 
    MarketData
)
from .oanda_provider import OandaProvider
from .provider_manager import DataProviderManager, ProviderPriority, create_default_manager

__all__ = [
    "IDataProvider",
    "DataProviderType", 
    "TimeFrame",
    "MarketData",
    "OandaProvider",
    "DataProviderManager",
    "ProviderPriority",
    "create_default_manager"
]