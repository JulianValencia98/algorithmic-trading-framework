from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Signal:
    """
    Modelo de una señal generada por una estrategia.
    Útil para análisis de señales vs ejecuciones.
    """
    id: Optional[int] = None
    bot_id: str = ""
    strategy_name: str = ""
    symbol: str = ""
    timeframe: str = ""
    
    # Señal
    signal_type: str = ""  # 'buy', 'sell', 'hold'
    generated_at: datetime = field(default_factory=datetime.now)
    
    # Precios al momento de la señal
    price_at_signal: float = 0.0
    
    # Si se ejecutó o no
    was_executed: bool = False
    execution_ticket: Optional[int] = None
    skip_reason: Optional[str] = None  # 'max_positions', 'market_closed', etc.
    
    # Contexto (para IA)
    indicators_snapshot: Optional[str] = None  # JSON con valores de indicadores
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'bot_id': self.bot_id,
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'signal_type': self.signal_type,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'price_at_signal': self.price_at_signal,
            'was_executed': self.was_executed,
            'execution_ticket': self.execution_ticket,
            'skip_reason': self.skip_reason,
            'indicators_snapshot': self.indicators_snapshot,
        }
