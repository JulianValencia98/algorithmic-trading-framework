"""
Event Bus - Sistema de eventos pub/sub

Permite desacoplar componentes del framework mediante eventos.
Los componentes pueden publicar eventos y otros pueden suscribirse a ellos.
"""
from typing import Callable, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading


class EventType(Enum):
    """Tipos de eventos del framework."""
    # Trading events
    SIGNAL_GENERATED = "signal_generated"
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    TRADE_MODIFIED = "trade_modified"
    
    # Bot lifecycle events
    BOT_STARTED = "bot_started"
    BOT_STOPPED = "bot_stopped"
    BOT_PAUSED = "bot_paused"
    BOT_RESUMED = "bot_resumed"
    BOT_ERROR = "bot_error"
    
    # Market events
    MARKET_OPENED = "market_opened"
    MARKET_CLOSED = "market_closed"
    
    # System events
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"


@dataclass
class Event:
    """Representa un evento del sistema."""
    event_type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""  # Bot ID o componente que generó el evento


# Type alias para callbacks
EventCallback = Callable[[Event], None]


class EventBus:
    """
    Bus de eventos singleton para comunicación entre componentes.
    Thread-safe para uso con múltiples bots.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el bus de eventos."""
        if self._initialized:
            return
        
        self._subscribers: Dict[EventType, List[EventCallback]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._lock = threading.Lock()
        self._initialized = True
    
    def subscribe(self, event_type: EventType, callback: EventCallback):
        """
        Suscribe un callback a un tipo de evento.
        
        Args:
            event_type: Tipo de evento a escuchar
            callback: Función a llamar cuando ocurra el evento
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: EventCallback):
        """
        Desuscribe un callback de un tipo de evento.
        
        Args:
            event_type: Tipo de evento
            callback: Función a remover
        """
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                except ValueError:
                    pass  # Callback no estaba suscrito
    
    def publish(self, event: Event):
        """
        Publica un evento a todos los suscriptores.
        
        Args:
            event: Evento a publicar
        """
        with self._lock:
            # Guardar en historial
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]
            
            # Obtener copia de suscriptores
            callbacks = self._subscribers.get(event.event_type, []).copy()
        
        # Llamar callbacks fuera del lock para evitar deadlocks
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event callback: {e}")
    
    def emit(self, event_type: EventType, data: Dict[str, Any], source: str = ""):
        """
        Método de conveniencia para emitir eventos.
        
        Args:
            event_type: Tipo de evento
            data: Datos del evento
            source: Origen del evento
        """
        event = Event(event_type=event_type, data=data, source=source)
        self.publish(event)
    
    def get_recent_events(self, event_type: EventType = None, limit: int = 50) -> List[Event]:
        """
        Obtiene eventos recientes del historial.
        
        Args:
            event_type: Filtrar por tipo (None = todos)
            limit: Número máximo de eventos
            
        Returns:
            Lista de eventos
        """
        with self._lock:
            if event_type:
                events = [e for e in self._event_history if e.event_type == event_type]
            else:
                events = self._event_history.copy()
        
        return events[-limit:]
    
    def clear_history(self):
        """Limpia el historial de eventos."""
        with self._lock:
            self._event_history.clear()
    
    def clear_subscribers(self):
        """Limpia todos los suscriptores."""
        with self._lock:
            self._subscribers.clear()


# Instancia global del EventBus
event_bus = EventBus()


# ==================== HELPER FUNCTIONS ====================

def on_signal_generated(
    bot_id: str,
    strategy_name: str,
    symbol: str,
    signal_type: str,
    price: float,
    **kwargs
):
    """Helper para emitir evento de señal generada."""
    # Verificar pausa global antes de emitir
    try:
        from utils.global_state import global_state
        if global_state.should_skip_action("event"):
            return  # Saltar evento si está pausado globalmente
    except ImportError:
        pass  # Continuar si no está disponible global_state
    
    event_bus.emit(
        EventType.SIGNAL_GENERATED,
        {
            'bot_id': bot_id,
            'strategy_name': strategy_name,
            'symbol': symbol,
            'signal_type': signal_type,
            'price': price,
            **kwargs
        },
        source=bot_id
    )


def on_trade_opened(
    bot_id: str,
    ticket: int,
    symbol: str,
    action: str,
    volume: float,
    price: float,
    sl: float,
    tp: float,
    **kwargs
):
    """Helper para emitir evento de trade abierto."""
    # Verificar pausa global antes de emitir
    try:
        from utils.global_state import global_state
        if global_state.should_skip_action("event"):
            return  # Saltar evento si está pausado globalmente
    except ImportError:
        pass  # Continuar si no está disponible global_state
    
    event_bus.emit(
        EventType.TRADE_OPENED,
        {
            'bot_id': bot_id,
            'ticket': ticket,
            'symbol': symbol,
            'action': action,
            'volume': volume,
            'price': price,
            'sl': sl,
            'tp': tp,
            **kwargs
        },
        source=bot_id
    )


def on_trade_closed(
    bot_id: str,
    ticket: int,
    symbol: str,
    profit: float,
    close_reason: str,
    **kwargs
):
    """Helper para emitir evento de trade cerrado."""
    # Verificar pausa global antes de emitir
    try:
        from utils.global_state import global_state
        if global_state.should_skip_action("event"):
            return  # Saltar evento si está pausado globalmente
    except ImportError:
        pass  # Continuar si no está disponible global_state
    
    event_bus.emit(
        EventType.TRADE_CLOSED,
        {
            'bot_id': bot_id,
            'ticket': ticket,
            'symbol': symbol,
            'profit': profit,
            'close_reason': close_reason,
            **kwargs
        },
        source=bot_id
    )


def on_bot_status_change(bot_id: str, status: str, **kwargs):
    """Helper para emitir eventos de cambio de estado del bot."""
    event_map = {
        'started': EventType.BOT_STARTED,
        'stopped': EventType.BOT_STOPPED,
        'paused': EventType.BOT_PAUSED,
        'resumed': EventType.BOT_RESUMED,
        'error': EventType.BOT_ERROR,
    }
    
    event_type = event_map.get(status)
    if event_type:
        event_bus.emit(event_type, {'bot_id': bot_id, **kwargs}, source=bot_id)
