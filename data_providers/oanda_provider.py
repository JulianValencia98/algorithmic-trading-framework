"""
Oanda Data Provider - Integración con Oanda API v20

Requiere cuenta Oanda y API token.
Documentación: https://developer.oanda.com/rest-live-v20/introduction/
"""
import requests
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import time
import os
from dotenv import load_dotenv

from .interfaces.data_provider_interface import IDataProvider, DataProviderType, TimeFrame, MarketData
from utils.utils import Utils


class OandaProvider(IDataProvider):
    """Proveedor de datos para Oanda API v20."""
    
    # Mapeo de timeframes a formato Oanda
    TIMEFRAME_MAP = {
        TimeFrame.M1: "M1",
        TimeFrame.M5: "M5", 
        TimeFrame.M15: "M15",
        TimeFrame.M30: "M30",
        TimeFrame.H1: "H1",
        TimeFrame.H4: "H4",
        TimeFrame.D1: "D",
        TimeFrame.W1: "W",
        TimeFrame.MN1: "M"
    }
    
    def __init__(self, account_id: Optional[str] = None, api_token: Optional[str] = None):
        """
        Inicializa el proveedor Oanda.
        
        Args:
            account_id: ID de cuenta Oanda
            api_token: Token de API Oanda
        """
        load_dotenv()
        
        self.account_id = account_id or os.getenv("OANDA_ACCOUNT_ID")
        self.api_token = api_token or os.getenv("OANDA_API_TOKEN")
        self.environment = os.getenv("OANDA_ENVIRONMENT", "practice")  # practice o trade
        
        # URLs según entorno
        if self.environment == "trade":
            self.api_url = "https://api-fxtrade.oanda.com"
            self.stream_url = "https://stream-fxtrade.oanda.com"
        else:
            self.api_url = "https://api-fxpractice.oanda.com"
            self.stream_url = "https://stream-fxpractice.oanda.com"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        self._connected = False
        self._last_request_time = 0
        self._rate_limit_delay = 0.1  # 100ms entre requests
    
    def _rate_limit(self):
        """Implementa rate limiting simple."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
        self._last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Hace request con rate limiting y manejo de errores."""
        self._rate_limit()
        
        try:
            url = f"{self.api_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"{Utils.dateprint()} - [Oanda] API error: {e}")
            return None
    
    def connect(self) -> bool:
        """Verifica credenciales y conecta con Oanda."""
        try:
            # Test de conectividad obteniendo info de cuenta
            result = self._make_request(f"v3/accounts/{self.account_id}")
            if result and "account" in result:
                self._connected = True
                print(f"{Utils.dateprint()} - [Oanda] Conectado - Cuenta: {self.account_id} ({self.environment})")
                return True
            else:
                print(f"{Utils.dateprint()} - [Oanda] Error: Credenciales inválidas")
                return False
        except Exception as e:
            print(f"{Utils.dateprint()} - [Oanda] Error conectando: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Desconecta de Oanda."""
        self._connected = False
        print(f"{Utils.dateprint()} - [Oanda] Desconectado")
        return True
    
    def is_connected(self) -> bool:
        """Verifica conexión con Oanda."""
        return self._connected
    
    def get_historical_data(
        self,
        symbol: str,
        timeframe: TimeFrame,
        count: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Optional[MarketData]:
        """Obtiene datos históricos de Oanda."""
        if not self._connected:
            print(f"{Utils.dateprint()} - [Oanda] No conectado")
            return None
        
        # Convertir símbolo a formato Oanda (ej: EURUSD -> EUR_USD)
        oanda_symbol = self._convert_symbol_to_oanda(symbol)
        oanda_timeframe = self.TIMEFRAME_MAP.get(timeframe, "H1")
        
        params = {
            "granularity": oanda_timeframe,
            "count": min(count, 5000)  # Límite de Oanda
        }
        
        # Agregar rango de tiempo si se especifica
        if start_time:
            params["from"] = start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if end_time:
            params["to"] = end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        print(f"{Utils.dateprint()} - [Oanda] Solicitando datos: {symbol} {timeframe.value} x{count}")
        
        result = self._make_request(f"v3/instruments/{oanda_symbol}/candles", params)
        
        if not result or "candles" not in result:
            print(f"{Utils.dateprint()} - [Oanda] No se obtuvieron datos para {symbol}")
            return None
        
        # Convertir a DataFrame
        candles = []
        for candle in result["candles"]:
            if candle.get("complete", True):  # Solo velas completas
                mid = candle["mid"]
                candles.append({
                    "time": pd.to_datetime(candle["time"]),
                    "Open": float(mid["o"]),
                    "High": float(mid["h"]),
                    "Low": float(mid["l"]),
                    "Close": float(mid["c"]),
                    "Volume": int(candle["volume"])
                })
        
        if not candles:
            print(f"{Utils.dateprint()} - [Oanda] Sin velas completas para {symbol}")
            return None
        
        df = pd.DataFrame(candles)
        df.set_index("time", inplace=True)
        df.sort_index(inplace=True)
        
        print(f"{Utils.dateprint()} - [Oanda] ✅ Obtenidas {len(df)} velas de {symbol}")
        
        return MarketData(
            symbol=symbol,
            timeframe=timeframe,
            data=df,
            provider=DataProviderType.OANDA,
            last_update=datetime.now()
        )
    
    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """Obtiene precio actual de Oanda."""
        if not self._connected:
            return None
        
        oanda_symbol = self._convert_symbol_to_oanda(symbol)
        result = self._make_request(f"v3/instruments/{oanda_symbol}/candles", {
            "count": 1,
            "granularity": "S5"  # 5 segundos para precio más reciente
        })
        
        if not result or not result.get("candles"):
            return None
        
        candle = result["candles"][-1]
        if "mid" in candle:
            mid = candle["mid"]
            price = float(mid["c"])
            
            # Obtener spread aproximado
            spread = self._get_spread(oanda_symbol)
            half_spread = spread / 2
            
            return {
                "bid": price - half_spread,
                "ask": price + half_spread,
                "price": price
            }
        
        return None
    
    def _get_spread(self, oanda_symbol: str) -> float:
        """Obtiene spread aproximado del instrumento."""
        try:
            result = self._make_request(f"v3/instruments/{oanda_symbol}/candles", {
                "count": 1,
                "granularity": "M1"
            })
            
            if result and "candles" in result and result["candles"]:
                candle = result["candles"][0]
                if "bid" in candle and "ask" in candle:
                    bid_close = float(candle["bid"]["c"])
                    ask_close = float(candle["ask"]["c"])
                    return ask_close - bid_close
            
            # Spreads por defecto según tipo de instrumento
            if "_" in oanda_symbol:  # Forex
                major_pairs = ["EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD", "USD_CAD", "NZD_USD"]
                if oanda_symbol in major_pairs:
                    return 0.00020  # 2 pips para mayores
                else:
                    return 0.00050  # 5 pips para menores
            else:
                return 0.01  # Spread por defecto para otros instrumentos
        except:
            return 0.00020  # Fallback conservador
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Obtiene información del instrumento desde Oanda."""
        if not self._connected:
            return None
        
        oanda_symbol = self._convert_symbol_to_oanda(symbol)
        result = self._make_request(f"v3/instruments/{oanda_symbol}")
        
        if result and "instruments" in result and result["instruments"]:
            instrument = result["instruments"][0]
            return {
                "symbol": symbol,
                "name": instrument.get("displayName", symbol),
                "pip_location": instrument.get("pipLocation", -4),
                "trade_units_precision": instrument.get("tradeUnitsPrecision", 1),
                "minimum_trade_size": instrument.get("minimumTradeSize", "1"),
                "maximum_trade_size": instrument.get("maximumTradeSize", "100000000"),
                "provider": "Oanda"
            }
        
        return None
    
    def get_available_symbols(self) -> List[str]:
        """Obtiene lista de instrumentos disponibles en Oanda."""
        if not self._connected:
            return []
        
        result = self._make_request(f"v3/accounts/{self.account_id}/instruments")
        
        if not result or "instruments" not in result:
            return []
        
        symbols = []
        for instrument in result["instruments"]:
            # Convertir de formato Oanda a estándar (EUR_USD -> EURUSD)
            oanda_name = instrument["name"]
            standard_name = oanda_name.replace("_", "")
            symbols.append(standard_name)
        
        print(f"{Utils.dateprint()} - [Oanda] Disponibles {len(symbols)} instrumentos")
        return symbols
    
    def is_market_open(self, symbol: str) -> bool:
        """
        Verifica si el mercado está abierto para un símbolo.
        
        Nota: Oanda no proporciona esta info directamente,
        así que verificamos si podemos obtener precio actual.
        """
        price = self.get_current_price(symbol)
        return price is not None
    
    @property
    def provider_type(self) -> DataProviderType:
        """Tipo de proveedor."""
        return DataProviderType.OANDA
    
    def _convert_symbol_to_oanda(self, symbol: str) -> str:
        """
        Convierte símbolo estándar a formato Oanda.
        
        Ejemplos:
        EURUSD -> EUR_USD
        GBPUSD -> GBP_USD
        XAUUSD -> XAU_USD
        """
        # Mapeo de símbolos especiales
        special_symbols = {
            "XAUUSD": "XAU_USD",
            "XAGUSD": "XAG_USD",
            "US30": "US30_USD",
            "SPX500": "SPX500_USD",
            "NAS100": "NAS100_USD",
            "DE30": "DE30_EUR",
            "UK100": "UK100_GBP",
            "JP225": "JP225_USD"
        }
        
        if symbol in special_symbols:
            return special_symbols[symbol]
        
        # Para pares de forex estándar de 6 caracteres
        if len(symbol) == 6 and symbol.isalpha():
            return f"{symbol[:3]}_{symbol[3:]}"
        
        # Fallback: devolver tal como está
        return symbol
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión y retorna información detallada.
        
        Returns:
            Dict con información de la prueba de conexión
        """
        if not self.api_token or not self.account_id:
            return {
                "success": False,
                "error": "API token o account ID no configurados",
                "account_id": self.account_id,
                "environment": self.environment
            }
        
        try:
            result = self._make_request(f"v3/accounts/{self.account_id}")
            
            if result and "account" in result:
                account = result["account"]
                return {
                    "success": True,
                    "account_id": account.get("id"),
                    "currency": account.get("currency"),
                    "balance": float(account.get("balance", 0)),
                    "unrealized_pl": float(account.get("unrealizedPL", 0)),
                    "open_positions": account.get("openPositionCount", 0),
                    "environment": self.environment,
                    "api_url": self.api_url
                }
            else:
                return {
                    "success": False,
                    "error": "Respuesta inválida del servidor",
                    "environment": self.environment
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "environment": self.environment
            }