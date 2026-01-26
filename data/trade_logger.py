"""
Trade Logger Service

Servicio que registra todas las operaciones de trading en la base de datos.
Diseñado para ser inyectado en SimpleTradingDirector.
"""
from datetime import datetime
from typing import Optional
import json

from data.models.trade import Trade, TradeStatus
from data.models.signal import Signal
from data.repositories.trade_repository import TradeRepository
from utils.utils import Utils


class TradeLogger:
    """
    Servicio para registrar trades y señales.
    Proporciona métodos simples para logging desde SimpleTradingDirector.
    Crea una base de datos separada para cada cuenta de MT5.
    """
    
    def __init__(self, account_id: int = None, repository: Optional[TradeRepository] = None):
        """
        Inicializa el Trade Logger.
        
        Args:
            account_id: ID de la cuenta MT5 (para crear DB por cuenta)
            repository: Repositorio de trades (si no se proporciona, crea uno nuevo)
        """
        self.account_id = account_id
        self.repository = repository or TradeRepository(account_id=account_id)
        
        if account_id:
            print(f"{Utils.dateprint()} - [TradeLogger] Database: trades_account_{account_id}.db")
    
    def log_trade_opened(
        self,
        ticket: int,
        magic_number: int,
        bot_id: str,
        strategy_name: str,
        symbol: str,
        action: str,
        volume: float,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        signal_data: Optional[dict] = None,
        market_context: Optional[dict] = None
    ) -> int:
        """
        Registra la apertura de un trade.
        
        Args:
            ticket: Ticket de MT5
            magic_number: Magic number de la estrategia
            bot_id: ID del bot
            strategy_name: Nombre de la estrategia
            symbol: Símbolo operado
            action: 'buy' o 'sell'
            volume: Lotes
            entry_price: Precio de entrada
            sl_price: Stop Loss
            tp_price: Take Profit
            signal_data: Datos de la señal (opcional, para AI)
            market_context: Contexto de mercado (opcional, para AI)
            
        Returns:
            ID del trade en la base de datos
        """
        trade = Trade(
            ticket=ticket,
            magic_number=magic_number,
            bot_id=bot_id,
            strategy_name=strategy_name,
            symbol=symbol,
            action=action,
            volume=volume,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            opened_at=datetime.now(),
            status=TradeStatus.OPENED,
            signal_data=json.dumps(signal_data) if signal_data else None,
            market_context=json.dumps(market_context) if market_context else None,
        )
        
        trade_id = self.repository.save_trade(trade)
        print(f"{Utils.dateprint()} - [TradeLogger] Trade #{ticket} logged (ID: {trade_id})")
        
        return trade_id
    
    def log_trade_closed(
        self,
        ticket: int,
        exit_price: float,
        profit: float,
        close_reason: str = "manual",
        commission: float = 0.0,
        swap: float = 0.0
    ) -> bool:
        """
        Registra el cierre de un trade.
        
        Args:
            ticket: Ticket de MT5
            exit_price: Precio de salida
            profit: Profit/pérdida
            close_reason: Razón del cierre ('sl', 'tp', 'manual', 'signal')
            commission: Comisión
            swap: Swap
            
        Returns:
            True si se actualizó correctamente
        """
        trade = self.repository.get_trade_by_ticket(ticket)
        
        if not trade:
            print(f"{Utils.dateprint()} - [TradeLogger] WARNING: Trade #{ticket} not found in database")
            return False
        
        # Calcular pips de profit
        profit_pips = self._calculate_profit_pips(
            trade.symbol, trade.action, trade.entry_price, exit_price
        )
        
        trade.exit_price = exit_price
        trade.profit = profit
        trade.profit_pips = profit_pips
        trade.commission = commission
        trade.swap = swap
        trade.closed_at = datetime.now()
        trade.status = TradeStatus.CLOSED
        trade.close_reason = close_reason
        
        success = self.repository.update_trade(trade)
        
        if success:
            emoji = "✅" if profit > 0 else "❌"
            print(f"{Utils.dateprint()} - [TradeLogger] {emoji} Trade #{ticket} closed: ${profit:.2f} ({profit_pips:.1f} pips)")
        
        return success
    
    def log_signal(
        self,
        bot_id: str,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        signal_type: str,
        price_at_signal: float,
        was_executed: bool = False,
        execution_ticket: Optional[int] = None,
        skip_reason: Optional[str] = None,
        indicators_snapshot: Optional[dict] = None
    ) -> int:
        """
        Registra una señal generada.
        
        Args:
            bot_id: ID del bot
            strategy_name: Nombre de la estrategia
            symbol: Símbolo
            timeframe: Timeframe
            signal_type: 'buy', 'sell', 'hold'
            price_at_signal: Precio cuando se generó la señal
            was_executed: Si se ejecutó o no
            execution_ticket: Ticket si se ejecutó
            skip_reason: Razón si no se ejecutó
            indicators_snapshot: Estado de indicadores
            
        Returns:
            ID de la señal en la base de datos
        """
        signal = Signal(
            bot_id=bot_id,
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            signal_type=signal_type,
            generated_at=datetime.now(),
            price_at_signal=price_at_signal,
            was_executed=was_executed,
            execution_ticket=execution_ticket,
            skip_reason=skip_reason,
            indicators_snapshot=json.dumps(indicators_snapshot) if indicators_snapshot else None,
        )
        
        return self.repository.save_signal(signal)
    
    def _calculate_profit_pips(
        self, 
        symbol: str, 
        action: str, 
        entry_price: float, 
        exit_price: float
    ) -> float:
        """Calcula el profit en pips."""
        # Determinar tamaño de pip basado en símbolo
        if "JPY" in symbol:
            pip_size = 0.01
        elif "XAU" in symbol or "GOLD" in symbol:
            pip_size = 0.1
        else:
            pip_size = 0.0001
        
        if action.lower() == "buy":
            pips = (exit_price - entry_price) / pip_size
        else:
            pips = (entry_price - exit_price) / pip_size
        
        return round(pips, 1)
    
    # ==================== QUERY METHODS ====================
    
    def get_open_trades(self, bot_id: Optional[str] = None):
        """Obtiene trades abiertos."""
        return self.repository.get_open_trades(bot_id)
    
    def get_bot_history(self, bot_id: str, limit: int = 100):
        """Obtiene historial de trades de un bot."""
        return self.repository.get_trades_by_bot(bot_id, limit)
    
    def get_bot_stats(self, bot_id: str) -> dict:
        """Obtiene estadísticas de un bot."""
        return self.repository.get_bot_stats(bot_id)
    
    def get_all_stats(self):
        """Obtiene estadísticas de todos los bots."""
        return self.repository.get_all_bots_stats()
    
    def get_recent_signals(self, bot_id: str, limit: int = 50):
        """Obtiene señales recientes de un bot."""
        return self.repository.get_signals_by_bot(bot_id, limit)
