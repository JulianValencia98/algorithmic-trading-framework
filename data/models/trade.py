from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TradeStatus(Enum):
    """Estado del trade."""
    OPENED = "opened"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class Trade:
    """
    Modelo de un trade ejecutado.
    Almacena toda la información relevante para análisis posterior.
    """
    # Identificación
    id: Optional[int] = None
    ticket: Optional[int] = None
    magic_number: int = 0
    bot_id: str = ""
    strategy_name: str = ""
    
    # Trade info
    symbol: str = ""
    action: str = ""  # 'buy' or 'sell'
    volume: float = 0.0
    
    # Precios
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    sl_price: Optional[float] = None
    tp_price: Optional[float] = None
    
    # Resultados
    profit: Optional[float] = None
    profit_pips: Optional[float] = None
    commission: Optional[float] = None
    swap: Optional[float] = None
    
    # Tiempos
    opened_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    
    # Estado
    status: TradeStatus = TradeStatus.OPENED
    close_reason: Optional[str] = None  # 'sl', 'tp', 'manual', 'signal', 'error'
    
    # Contexto adicional (para IA futura)
    signal_data: Optional[str] = None  # JSON con datos de la señal
    market_context: Optional[str] = None  # JSON con contexto del mercado
    
    def to_dict(self) -> dict:
        """Convierte el trade a diccionario para serialización."""
        return {
            'id': self.id,
            'ticket': self.ticket,
            'magic_number': self.magic_number,
            'bot_id': self.bot_id,
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'action': self.action,
            'volume': self.volume,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'sl_price': self.sl_price,
            'tp_price': self.tp_price,
            'profit': self.profit,
            'profit_pips': self.profit_pips,
            'commission': self.commission,
            'swap': self.swap,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'status': self.status.value,
            'close_reason': self.close_reason,
            'signal_data': self.signal_data,
            'market_context': self.market_context,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Trade':
        """Crea un Trade desde un diccionario."""
        return cls(
            id=data.get('id'),
            ticket=data.get('ticket'),
            magic_number=data.get('magic_number', 0),
            bot_id=data.get('bot_id', ''),
            strategy_name=data.get('strategy_name', ''),
            symbol=data.get('symbol', ''),
            action=data.get('action', ''),
            volume=data.get('volume', 0.0),
            entry_price=data.get('entry_price', 0.0),
            exit_price=data.get('exit_price'),
            sl_price=data.get('sl_price'),
            tp_price=data.get('tp_price'),
            profit=data.get('profit'),
            profit_pips=data.get('profit_pips'),
            commission=data.get('commission'),
            swap=data.get('swap'),
            opened_at=datetime.fromisoformat(data['opened_at']) if data.get('opened_at') else datetime.now(),
            closed_at=datetime.fromisoformat(data['closed_at']) if data.get('closed_at') else None,
            status=TradeStatus(data.get('status', 'opened')),
            close_reason=data.get('close_reason'),
            signal_data=data.get('signal_data'),
            market_context=data.get('market_context'),
        )
