"""
Data Manager para Backtesting - Integra múltiples fuentes de datos

Permite obtener datos históricos desde Oanda, MetaTrader5 u otros proveedores
para realizar backtesting con datos de alta calidad.
"""
import os
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Importaciones de data providers
from data_providers import OandaProvider, TimeFrame as ProviderTimeFrame
from data_providers.interfaces.data_provider_interface import DataProviderType

# Importación de MetaTrader5 para fallback
try:
    import MetaTrader5 as mt5
    from Easy_Trading import BasicTrading
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

from utils.utils import Utils


class BacktestDataManager:
    """
    Gestor de datos para backtesting que puede usar múltiples fuentes.
    
    Prioridad:
    1. Oanda (más confiable para datos históricos)
    2. MetaTrader5 (fallback si Oanda no está disponible)
    """
    
    # Mapeo de timeframes string a enum
    TIMEFRAME_MAP = {
        'M1': ProviderTimeFrame.M1,
        'M5': ProviderTimeFrame.M5,
        'M15': ProviderTimeFrame.M15,
        'M30': ProviderTimeFrame.M30,
        'H1': ProviderTimeFrame.H1,
        'H4': ProviderTimeFrame.H4,
        'D1': ProviderTimeFrame.D1,
        'W1': ProviderTimeFrame.W1,
        'MN1': ProviderTimeFrame.MN1
    }
    
    # Mapeo para MT5 (fallback)
    MT5_TIMEFRAME_MAP = {
        'M1': mt5.TIMEFRAME_M1 if MT5_AVAILABLE else None,
        'M5': mt5.TIMEFRAME_M5 if MT5_AVAILABLE else None,
        'M15': mt5.TIMEFRAME_M15 if MT5_AVAILABLE else None,
        'M30': mt5.TIMEFRAME_M30 if MT5_AVAILABLE else None,
        'H1': mt5.TIMEFRAME_H1 if MT5_AVAILABLE else None,
        'H4': mt5.TIMEFRAME_H4 if MT5_AVAILABLE else None,
        'D1': mt5.TIMEFRAME_D1 if MT5_AVAILABLE else None,
        'W1': mt5.TIMEFRAME_W1 if MT5_AVAILABLE else None,
        'MN1': mt5.TIMEFRAME_MN1 if MT5_AVAILABLE else None
    }
    
    def __init__(self, preferred_provider: str = "oanda"):
        """
        Inicializa el gestor de datos.
        
        Args:
            preferred_provider: "oanda" o "mt5"
        """
        self.preferred_provider = preferred_provider.lower()
        self.oanda_provider: Optional[OandaProvider] = None
        self.mt5_basic_trading: Optional[BasicTrading] = None
        
        # Inicializar proveedores
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Inicializa los proveedores disponibles."""
        
        # Intentar inicializar Oanda
        try:
            self.oanda_provider = OandaProvider()
            if self.oanda_provider.connect():
                print(f"{Utils.dateprint()} - [BacktestDataManager] ✅ Oanda conectado")
            else:
                print(f"{Utils.dateprint()} - [BacktestDataManager] ❌ Oanda no disponible")
                self.oanda_provider = None
        except Exception as e:
            print(f"{Utils.dateprint()} - [BacktestDataManager] Error inicializando Oanda: {e}")
            self.oanda_provider = None
        
        # Intentar inicializar MT5 como fallback
        if MT5_AVAILABLE:
            try:
                self.mt5_basic_trading = BasicTrading()
                print(f"{Utils.dateprint()} - [BacktestDataManager] ✅ MT5 disponible como fallback")
            except Exception as e:
                print(f"{Utils.dateprint()} - [BacktestDataManager] Error inicializando MT5: {e}")
                self.mt5_basic_trading = None
    
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        count: int = 1000,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Obtiene datos históricos usando el proveedor preferido.
        
        Args:
            symbol: Símbolo del instrumento (ej: EURUSD, XAUUSD)
            timeframe: Timeframe string (M1, M5, H1, H4, D1, etc.)
            count: Número de velas a obtener
            start_date: Fecha inicial (opcional)
            end_date: Fecha final (opcional)
            
        Returns:
            DataFrame con columnas OHLCV o None si falla
        """
        print(f"{Utils.dateprint()} - [BacktestDataManager] Obteniendo datos {symbol} {timeframe} x{count}")
        
        # Determinar proveedor a usar
        provider_order = self._get_provider_order()
        
        for provider in provider_order:
            try:
                data = None
                
                if provider == "oanda" and self.oanda_provider:
                    data = self._get_data_from_oanda(symbol, timeframe, count, start_date, end_date)
                elif provider == "mt5" and self.mt5_basic_trading:
                    data = self._get_data_from_mt5(symbol, timeframe, count)
                
                if data is not None and not data.empty:
                    print(f"{Utils.dateprint()} - [BacktestDataManager] ✅ Datos obtenidos desde {provider.upper()}: {len(data)} velas")
                    return data
                    
            except Exception as e:
                print(f"{Utils.dateprint()} - [BacktestDataManager] Error con {provider}: {e}")
                continue
        
        print(f"{Utils.dateprint()} - [BacktestDataManager] ❌ No se pudieron obtener datos de ningún proveedor")
        return None
    
    def _get_provider_order(self) -> list:
        """Determina el orden de proveedores a intentar."""
        if self.preferred_provider == "oanda":
            return ["oanda", "mt5"]
        else:
            return ["mt5", "oanda"]
    
    def _get_data_from_oanda(
        self,
        symbol: str,
        timeframe: str,
        count: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """Obtiene datos desde Oanda."""
        
        # Convertir timeframe string a enum
        tf_enum = self.TIMEFRAME_MAP.get(timeframe.upper())
        if not tf_enum:
            print(f"{Utils.dateprint()} - [BacktestDataManager] Timeframe {timeframe} no soportado")
            return None
        
        try:
            market_data = self.oanda_provider.get_historical_data(
                symbol=symbol,
                timeframe=tf_enum,
                count=min(count, 5000),  # Límite de Oanda
                start_time=start_date,
                end_time=end_date
            )
            
            if market_data and market_data.data is not None:
                # Asegurar que el DataFrame tenga las columnas correctas
                df = market_data.data.copy()
                
                # Renombrar columnas si es necesario para compatibilidad
                column_mapping = {
                    'open': 'Open',
                    'high': 'High', 
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                }
                
                for old_col, new_col in column_mapping.items():
                    if old_col in df.columns and new_col not in df.columns:
                        df[new_col] = df[old_col]
                
                # Verificar columnas requeridas
                required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                if all(col in df.columns for col in required_cols):
                    return df[required_cols]
                else:
                    print(f"{Utils.dateprint()} - [BacktestDataManager] Columnas faltantes en datos de Oanda")
                    return None
            
        except Exception as e:
            print(f"{Utils.dateprint()} - [BacktestDataManager] Error obteniendo datos de Oanda: {e}")
            return None
    
    def _get_data_from_mt5(self, symbol: str, timeframe: str, count: int) -> Optional[pd.DataFrame]:
        """Obtiene datos desde MetaTrader5."""
        
        if not self.mt5_basic_trading:
            return None
        
        # Convertir timeframe a MT5
        mt5_tf = self.MT5_TIMEFRAME_MAP.get(timeframe.upper())
        if not mt5_tf:
            print(f"{Utils.dateprint()} - [BacktestDataManager] Timeframe {timeframe} no soportado en MT5")
            return None
        
        try:
            data = self.mt5_basic_trading._get_data_for_bt(mt5_tf, symbol, count)
            return data
        except Exception as e:
            print(f"{Utils.dateprint()} - [BacktestDataManager] Error obteniendo datos de MT5: {e}")
            return None
    
    def get_provider_status(self) -> Dict[str, bool]:
        """Obtiene el estado de los proveedores."""
        return {
            "oanda": self.oanda_provider is not None and self.oanda_provider.is_connected(),
            "mt5": self.mt5_basic_trading is not None,
            "preferred": self.preferred_provider
        }
    
    def cleanup(self):
        """Limpia recursos."""
        try:
            if self.oanda_provider:
                self.oanda_provider.disconnect()
            if self.mt5_basic_trading:
                self.mt5_basic_trading.shutdown()
        except Exception as e:
            print(f"{Utils.dateprint()} - [BacktestDataManager] Error en cleanup: {e}")


def get_backtest_data(
    symbol: str,
    timeframe: str,
    count: int = 1000,
    preferred_provider: str = "oanda",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Optional[pd.DataFrame]:
    """
    Función helper para obtener datos de backtesting.
    
    Args:
        symbol: Símbolo del instrumento
        timeframe: Timeframe (M1, M5, H1, etc.)
        count: Número de velas
        preferred_provider: "oanda" o "mt5"
        start_date: Fecha inicial (opcional)
        end_date: Fecha final (opcional)
        
    Returns:
        DataFrame con datos OHLCV o None
    """
    manager = BacktestDataManager(preferred_provider=preferred_provider)
    
    try:
        data = manager.get_historical_data(symbol, timeframe, count, start_date, end_date)
        return data
    finally:
        manager.cleanup()


if __name__ == "__main__":
    # Test del data manager
    print("=== TEST BACKTEST DATA MANAGER ===")
    
    # Crear manager con Oanda como preferido
    manager = BacktestDataManager(preferred_provider="oanda")
    
    # Mostrar estado de proveedores
    status = manager.get_provider_status()
    print(f"Estado de proveedores: {status}")
    
    # Obtener datos de prueba
    data = manager.get_historical_data("EURUSD", "H1", count=100)
    
    if data is not None:
        print(f"\n✅ Datos obtenidos: {len(data)} velas")
        print(f"Rango: {data.index[0]} a {data.index[-1]}")
        print(f"Último Close: {data['Close'].iloc[-1]}")
        print("\nPrimeras 3 velas:")
        print(data.head(3))
    else:
        print("\n❌ No se pudieron obtener datos")
    
    # Cleanup
    manager.cleanup()
    print("\n=== FIN TEST ===")