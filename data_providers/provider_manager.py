"""
Data Provider Manager - Gestor centralizado de proveedores de datos

Permite cambiar automáticamente entre proveedores según disponibilidad.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .interfaces.data_provider_interface import IDataProvider, DataProviderType, TimeFrame, MarketData
from .oanda_provider import OandaProvider
from utils.utils import Utils


class ProviderPriority(Enum):
    """Prioridades de proveedores."""
    PRIMARY = 1
    SECONDARY = 2
    FALLBACK = 3


class DataProviderManager:
    """Gestor que maneja múltiples proveedores de datos con failover automático."""
    
    def __init__(self):
        self.providers: Dict[DataProviderType, IDataProvider] = {}
        self.provider_priorities: Dict[DataProviderType, ProviderPriority] = {}
        self.active_provider: Optional[IDataProvider] = None
        
    def add_provider(
        self, 
        provider: IDataProvider, 
        priority: ProviderPriority = ProviderPriority.SECONDARY
    ) -> bool:
        """
        Agrega un proveedor al manager.
        
        Args:
            provider: Instancia del proveedor
            priority: Prioridad del proveedor
            
        Returns:
            True si se agregó correctamente
        """
        try:
            provider_type = provider.provider_type
            self.providers[provider_type] = provider
            self.provider_priorities[provider_type] = priority
            
            print(f"{Utils.dateprint()} - [ProviderManager] Agregado {provider_type.value} (prioridad: {priority.value})")
            return True
            
        except Exception as e:
            print(f"{Utils.dateprint()} - [ProviderManager] Error agregando proveedor: {e}")
            return False
    
    def initialize_providers(self) -> bool:
        """
        Inicializa y conecta todos los proveedores.
        
        Returns:
            True si al menos un proveedor se conectó
        """
        connected_providers = 0
        
        for provider_type, provider in self.providers.items():
            try:
                if provider.connect():
                    connected_providers += 1
                    print(f"{Utils.dateprint()} - [ProviderManager] ✅ {provider_type.value} conectado")
                else:
                    print(f"{Utils.dateprint()} - [ProviderManager] ❌ {provider_type.value} falló conexión")
            except Exception as e:
                print(f"{Utils.dateprint()} - [ProviderManager] Error conectando {provider_type.value}: {e}")
        
        if connected_providers > 0:
            self._select_active_provider()
            return True
        else:
            print(f"{Utils.dateprint()} - [ProviderManager] ❌ No hay proveedores disponibles")
            return False
    
    def _select_active_provider(self) -> Optional[IDataProvider]:
        """Selecciona el proveedor activo basado en prioridad y disponibilidad."""
        available_providers = [
            (priority, provider_type, provider)
            for provider_type, provider in self.providers.items()
            if provider.is_connected()
            for priority in [self.provider_priorities[provider_type]]
        ]
        
        if not available_providers:
            self.active_provider = None
            return None
        
        # Ordenar por prioridad (menor número = mayor prioridad)
        available_providers.sort(key=lambda x: x[0].value)
        
        _, provider_type, provider = available_providers[0]
        self.active_provider = provider
        
        print(f"{Utils.dateprint()} - [ProviderManager] Proveedor activo: {provider_type.value}")
        return self.active_provider
    
    def get_historical_data(
        self,
        symbol: str,
        timeframe: TimeFrame,
        count: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        fallback_enabled: bool = True
    ) -> Optional[MarketData]:
        """
        Obtiene datos históricos con failover automático.
        
        Args:
            symbol: Símbolo del instrumento
            timeframe: Timeframe
            count: Cantidad de velas
            start_time: Tiempo inicial
            end_time: Tiempo final
            fallback_enabled: Si usar failover automático
            
        Returns:
            MarketData o None si fallan todos los proveedores
        """
        if not self.active_provider:
            self._select_active_provider()
        
        if not self.active_provider:
            print(f"{Utils.dateprint()} - [ProviderManager] No hay proveedores disponibles")
            return None
        
        # Intentar con proveedor activo
        try:
            data = self.active_provider.get_historical_data(
                symbol, timeframe, count, start_time, end_time
            )
            if data:
                return data
        except Exception as e:
            print(f"{Utils.dateprint()} - [ProviderManager] Error en proveedor activo: {e}")
        
        # Failover a otros proveedores si está habilitado
        if fallback_enabled:
            return self._try_fallback_providers(
                "get_historical_data", symbol, timeframe, count, start_time, end_time
            )
        
        return None
    
    def get_current_price(self, symbol: str, fallback_enabled: bool = True) -> Optional[Dict[str, float]]:
        """
        Obtiene precio actual con failover automático.
        
        Args:
            symbol: Símbolo del instrumento
            fallback_enabled: Si usar failover automático
            
        Returns:
            Dict con precios o None
        """
        if not self.active_provider:
            self._select_active_provider()
        
        if not self.active_provider:
            return None
        
        # Intentar con proveedor activo
        try:
            price = self.active_provider.get_current_price(symbol)
            if price:
                return price
        except Exception as e:
            print(f"{Utils.dateprint()} - [ProviderManager] Error obteniendo precio: {e}")
        
        # Failover si está habilitado
        if fallback_enabled:
            return self._try_fallback_providers("get_current_price", symbol)
        
        return None
    
    def _try_fallback_providers(self, method_name: str, *args, **kwargs) -> Any:
        """
        Intenta ejecutar un método en proveedores de respaldo.
        
        Args:
            method_name: Nombre del método a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos nombrados
            
        Returns:
            Resultado del primer proveedor que funcione o None
        """
        # Obtener proveedores ordenados por prioridad (excluyendo el activo)
        fallback_providers = [
            (priority, provider_type, provider)
            for provider_type, provider in self.providers.items()
            if provider != self.active_provider and provider.is_connected()
            for priority in [self.provider_priorities[provider_type]]
        ]
        
        fallback_providers.sort(key=lambda x: x[0].value)
        
        for priority, provider_type, provider in fallback_providers:
            try:
                print(f"{Utils.dateprint()} - [ProviderManager] Intentando fallback: {provider_type.value}")
                
                method = getattr(provider, method_name)
                result = method(*args, **kwargs)
                
                if result:
                    print(f"{Utils.dateprint()} - [ProviderManager] ✅ Fallback exitoso: {provider_type.value}")
                    # Actualizar proveedor activo
                    self.active_provider = provider
                    return result
                    
            except Exception as e:
                print(f"{Utils.dateprint()} - [ProviderManager] Fallback falló {provider_type.value}: {e}")
                continue
        
        print(f"{Utils.dateprint()} - [ProviderManager] ❌ Todos los proveedores fallaron")
        return None
    
    def get_provider_status(self) -> Dict[str, Any]:
        """
        Obtiene estado de todos los proveedores.
        
        Returns:
            Dict con estado de cada proveedor
        """
        status = {
            "active_provider": self.active_provider.provider_type.value if self.active_provider else None,
            "providers": {}
        }
        
        for provider_type, provider in self.providers.items():
            status["providers"][provider_type.value] = {
                "connected": provider.is_connected(),
                "priority": self.provider_priorities[provider_type].value
            }
        
        return status
    
    def switch_provider(self, provider_type: DataProviderType) -> bool:
        """
        Cambia manualmente el proveedor activo.
        
        Args:
            provider_type: Tipo de proveedor a activar
            
        Returns:
            True si el cambio fue exitoso
        """
        if provider_type not in self.providers:
            print(f"{Utils.dateprint()} - [ProviderManager] Proveedor {provider_type.value} no encontrado")
            return False
        
        provider = self.providers[provider_type]
        
        if not provider.is_connected():
            print(f"{Utils.dateprint()} - [ProviderManager] Proveedor {provider_type.value} no conectado")
            return False
        
        self.active_provider = provider
        print(f"{Utils.dateprint()} - [ProviderManager] Proveedor cambiado a: {provider_type.value}")
        return True
    
    def disconnect_all(self) -> bool:
        """
        Desconecta todos los proveedores.
        
        Returns:
            True si todos se desconectaron correctamente
        """
        success = True
        
        for provider_type, provider in self.providers.items():
            try:
                if provider.disconnect():
                    print(f"{Utils.dateprint()} - [ProviderManager] {provider_type.value} desconectado")
                else:
                    print(f"{Utils.dateprint()} - [ProviderManager] Error desconectando {provider_type.value}")
                    success = False
            except Exception as e:
                print(f"{Utils.dateprint()} - [ProviderManager] Error desconectando {provider_type.value}: {e}")
                success = False
        
        self.active_provider = None
        return success


def create_default_manager() -> DataProviderManager:
    """
    Crea un manager con configuración por defecto.
    
    Returns:
        DataProviderManager configurado con Oanda
    """
    manager = DataProviderManager()
    
    # Agregar Oanda como proveedor principal
    oanda = OandaProvider()
    manager.add_provider(oanda, ProviderPriority.PRIMARY)
    
    return manager