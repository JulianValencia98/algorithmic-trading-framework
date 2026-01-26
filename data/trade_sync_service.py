"""
Trade Sync Service

Sincroniza los trades de la base de datos con el historial de MT5.
Se ejecuta periódicamente para mantener la DB actualizada.
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, List
import MetaTrader5 as mt5

from data.models.trade import Trade, TradeStatus
from data.repositories.trade_repository import TradeRepository
from utils.utils import Utils


class TradeSyncService:
    """
    Servicio que sincroniza trades con el historial de MT5.
    Lee el historial de la cuenta y actualiza la base de datos.
    """
    
    # Mapeo de magic numbers a nombres de estrategia
    MAGIC_TO_STRATEGY = {
        1: 'SimpleTimeStrategy',
        2: 'SimpleTimeStrategyGBP',
        3: 'SimpleTimeStrategyXAU',
    }
    
    def __init__(
        self, 
        repository: TradeRepository,
        sync_interval_minutes: int = 30,
        history_days: int = 7
    ):
        """
        Inicializa el servicio de sincronización.
        
        Args:
            repository: Repositorio de trades
            sync_interval_minutes: Intervalo de sincronización en minutos
            history_days: Días de historial a consultar
        """
        self.repository = repository
        self.sync_interval = sync_interval_minutes * 60  # Convertir a segundos
        self.history_days = history_days
        
        self._stop_event = threading.Event()
        self._sync_thread: Optional[threading.Thread] = None
        self._last_sync: Optional[datetime] = None
    
    def start(self):
        """Inicia el servicio de sincronización en background."""
        if self._sync_thread and self._sync_thread.is_alive():
            print(f"{Utils.dateprint()} - [TradeSyncService] Already running")
            return
        
        self._stop_event.clear()
        self._sync_thread = threading.Thread(
            target=self._sync_loop,
            daemon=True,
            name="TradeSyncService"
        )
        self._sync_thread.start()
        print(f"{Utils.dateprint()} - [TradeSyncService] Started (sync every {self.sync_interval // 60} min)")
    
    def stop(self):
        """Detiene el servicio de sincronización."""
        self._stop_event.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        print(f"{Utils.dateprint()} - [TradeSyncService] Stopped")
    
    def sync_now(self):
        """Ejecuta una sincronización inmediata."""
        print(f"{Utils.dateprint()} - [TradeSyncService] Manual sync started...")
        self._sync_with_mt5()
    
    def _sync_loop(self):
        """Loop principal de sincronización."""
        # Sync inicial
        self._sync_with_mt5()
        
        while not self._stop_event.is_set():
            # Esperar el intervalo
            self._stop_event.wait(self.sync_interval)
            
            if not self._stop_event.is_set():
                self._sync_with_mt5()
    
    def _sync_with_mt5(self):
        """Sincroniza los trades con el historial de MT5."""
        try:
            from_date = datetime.now() - timedelta(days=self.history_days)
            
            # Obtener historial de deals (operaciones cerradas)
            deals = mt5.history_deals_get(from_date, datetime.now())
            
            if deals is None:
                print(f"{Utils.dateprint()} - [TradeSyncService] No deals found in history")
                return
            
            # Procesar deals
            synced_count = 0
            updated_count = 0
            
            # Agrupar deals por position_id para obtener trades completos
            positions = self._group_deals_by_position(deals)
            
            for position_id, position_deals in positions.items():
                result = self._process_position(position_id, position_deals)
                if result == 'new':
                    synced_count += 1
                elif result == 'updated':
                    updated_count += 1
            
            self._last_sync = datetime.now()
            print(f"{Utils.dateprint()} - [TradeSyncService] Sync complete: {synced_count} new, {updated_count} updated")
            
        except Exception as e:
            print(f"{Utils.dateprint()} - [TradeSyncService] ERROR: {e}")
    
    def _group_deals_by_position(self, deals) -> dict:
        """Agrupa deals por position_id."""
        positions = {}
        
        for deal in deals:
            deal_dict = deal._asdict()
            pos_id = deal_dict.get('position_id', 0)
            
            if pos_id == 0:
                continue
                
            if pos_id not in positions:
                positions[pos_id] = []
            positions[pos_id].append(deal_dict)
        
        return positions
    
    def _process_position(self, position_id: int, deals: List[dict]) -> str:
        """
        Procesa una posición y sus deals.
        
        Returns:
            'new' si se creó nuevo, 'updated' si se actualizó, 'skip' si no hubo cambios
        """
        if not deals:
            return 'skip'
        
        # Ordenar deals por tiempo para determinar entrada/salida correctamente
        # El primer deal (más antiguo) es la entrada, el último es la salida
        sorted_deals = sorted(deals, key=lambda d: d.get('time', 0))
        
        entry_deal = sorted_deals[0]  # Primer deal = entrada
        exit_deal = sorted_deals[-1] if len(sorted_deals) > 1 else None  # Último deal = salida
        
        # Si solo hay un deal, es una posición abierta
        if len(sorted_deals) == 1:
            exit_deal = None
        
        # Obtener ticket del deal de entrada (usar order o position_id)
        ticket = entry_deal.get('order', position_id)
        
        # Verificar si ya existe en la base de datos
        existing_trade = self.repository.get_trade_by_ticket(ticket)
        
        if existing_trade:
            # Si existe y está abierto pero hay deal de salida, actualizar
            if existing_trade.status == TradeStatus.OPENED and exit_deal:
                return self._update_trade_from_exit(existing_trade, exit_deal)
            return 'skip'
        else:
            # Crear nuevo trade
            return self._create_trade_from_deals(entry_deal, exit_deal)
    
    def _create_trade_from_deals(self, entry_deal: dict, exit_deal: dict = None) -> str:
        """Crea un nuevo trade desde los deals de MT5."""
        try:
            # Determinar action
            deal_type = entry_deal.get('type', 0)
            action = 'buy' if deal_type == 0 else 'sell'  # 0=BUY, 1=SELL
            
            # Determinar status
            status = TradeStatus.CLOSED if exit_deal else TradeStatus.OPENED
            
            # Calcular profit
            profit = 0.0
            exit_price = None
            closed_at = None
            
            if exit_deal:
                profit = exit_deal.get('profit', 0.0)
                exit_price = exit_deal.get('price', 0.0)
                exit_time = exit_deal.get('time', 0)
                if exit_time:
                    closed_at = datetime.fromtimestamp(exit_time)
            
            # Obtener nombre de estrategia desde magic number
            magic = entry_deal.get('magic', 0)
            strategy_name = self.MAGIC_TO_STRATEGY.get(magic, f'Unknown_M{magic}')
            
            # Detectar close_reason desde el comment del deal de salida
            close_reason = None
            if exit_deal:
                exit_comment = exit_deal.get('comment', '').lower()
                if '[tp' in exit_comment:
                    close_reason = 'tp'
                elif '[sl' in exit_comment:
                    close_reason = 'sl'
                else:
                    close_reason = 'synced'
            
            # Crear trade
            trade = Trade(
                ticket=entry_deal.get('order', entry_deal.get('position_id')),
                magic_number=magic,
                bot_id=self._get_bot_id_from_deal(entry_deal),
                strategy_name=strategy_name,
                symbol=entry_deal.get('symbol', ''),
                action=action,
                volume=entry_deal.get('volume', 0.0),
                entry_price=entry_deal.get('price', 0.0),
                exit_price=exit_price,
                sl_price=None,  # No disponible en historial
                tp_price=None,  # No disponible en historial
                profit=profit,
                profit_pips=self._calculate_pips(
                    entry_deal.get('symbol', ''),
                    action,
                    entry_deal.get('price', 0.0),
                    exit_price or 0.0
                ) if exit_price else None,
                commission=entry_deal.get('commission', 0.0) + (exit_deal.get('commission', 0.0) if exit_deal else 0.0),
                swap=entry_deal.get('swap', 0.0) + (exit_deal.get('swap', 0.0) if exit_deal else 0.0),
                opened_at=datetime.fromtimestamp(entry_deal.get('time', 0)),
                closed_at=closed_at,
                status=status,
                close_reason=close_reason,
            )
            
            self.repository.save_trade(trade)
            return 'new'
            
        except Exception as e:
            print(f"{Utils.dateprint()} - [TradeSyncService] Error creating trade: {e}")
            return 'skip'
    
    def _update_trade_from_exit(self, trade: Trade, exit_deal: dict) -> str:
        """Actualiza un trade existente con datos de cierre."""
        try:
            trade.exit_price = exit_deal.get('price', 0.0)
            trade.profit = exit_deal.get('profit', 0.0)
            trade.profit_pips = self._calculate_pips(
                trade.symbol,
                trade.action,
                trade.entry_price,
                trade.exit_price
            )
            trade.commission = (trade.commission or 0) + exit_deal.get('commission', 0.0)
            trade.swap = (trade.swap or 0) + exit_deal.get('swap', 0.0)
            trade.closed_at = datetime.fromtimestamp(exit_deal.get('time', 0))
            trade.status = TradeStatus.CLOSED
            
            # Detectar close_reason desde el comment
            exit_comment = exit_deal.get('comment', '').lower()
            if '[tp' in exit_comment:
                trade.close_reason = 'tp'
            elif '[sl' in exit_comment:
                trade.close_reason = 'sl'
            else:
                trade.close_reason = 'synced'
            
            self.repository.update_trade(trade)
            return 'updated'
            
        except Exception as e:
            print(f"{Utils.dateprint()} - [TradeSyncService] Error updating trade: {e}")
            return 'skip'
    
    def _get_bot_id_from_deal(self, deal: dict) -> str:
        """Intenta determinar el bot_id desde el deal."""
        magic = deal.get('magic', 0)
        symbol = deal.get('symbol', 'UNKNOWN')
        comment = deal.get('comment', '')
        
        # Intentar extraer del comment o crear uno genérico
        if comment and 'FWK' in comment:
            return f"Synced_{symbol}_M{magic}"
        
        return f"Synced_{symbol}_M{magic}"
    
    def _calculate_pips(self, symbol: str, action: str, entry: float, exit: float) -> float:
        """Calcula pips de profit."""
        if not entry or not exit:
            return 0.0
        
        # Determinar tamaño de pip
        if "JPY" in symbol:
            pip_size = 0.01
        elif "XAU" in symbol or "GOLD" in symbol:
            pip_size = 0.1
        else:
            pip_size = 0.0001
        
        if action.lower() == "buy":
            pips = (exit - entry) / pip_size
        else:
            pips = (entry - exit) / pip_size
        
        return round(pips, 1)
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """Retorna el tiempo de la última sincronización."""
        return self._last_sync
