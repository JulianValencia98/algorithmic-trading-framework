import threading
import time
from typing import Dict, Optional
from datetime import datetime

import MetaTrader5 as mt5

from Easy_Trading import BasicTrading
from trading_director.simple_trading_director import SimpleTradingDirector
from strategies.strategy_base import StrategyBase
from data.trade_logger import TradeLogger
from data.trade_sync_service import TradeSyncService
from events.event_bus import on_bot_status_change
from utils.utils import Utils


class BotConfig:
    """Configuración para un bot individual."""
    
    @staticmethod
    def _get_timeframe_name(timeframe: int) -> str:
        """Convierte el código de timeframe MT5 a nombre legible."""
        timeframe_map = {
            mt5.TIMEFRAME_M1: 'M1',
            mt5.TIMEFRAME_M5: 'M5',
            mt5.TIMEFRAME_M15: 'M15',
            mt5.TIMEFRAME_M30: 'M30',
            mt5.TIMEFRAME_H1: 'H1',
            mt5.TIMEFRAME_H4: 'H4',
            mt5.TIMEFRAME_D1: 'D1',
            mt5.TIMEFRAME_W1: 'W1',
            mt5.TIMEFRAME_MN1: 'MN1',
        }
        return timeframe_map.get(timeframe, str(timeframe))
    
    def __init__(
        self,
        strategy: StrategyBase,
        symbol: str,
        timeframe: int,
        interval_seconds: int = 60,
        data_points: int = 100,
        bot_id: Optional[str] = None
    ):
        self.strategy = strategy
        self.symbol = symbol
        self.timeframe = timeframe
        self.interval_seconds = interval_seconds
        self.data_points = data_points
        
        # Generar bot_id automáticamente si no se proporciona
        if bot_id is None:
            strategy_name = strategy.__class__.__name__.replace('Strategy', '')
            timeframe_name = self._get_timeframe_name(timeframe)
            self.bot_id = f"{strategy_name}_{symbol}_{timeframe_name}"
        else:
            self.bot_id = bot_id
        
        # Usar el magic number de la estrategia
        self.magic_number = strategy.get_magic_number()


class AppDirector:
    """
    Director de aplicación que maneja múltiples bots de trading simultáneamente.
    Cada bot corre en su propio thread y puede ser pausado/reanudado individualmente.
    
    El AppDirector solo orquesta - cada estrategia decide su propio sizing y SL/TP.
    Crea una base de datos separada para cada cuenta de MT5.
    Sincroniza trades con historial de MT5 cada 10 minutos.
    """
    
    def __init__(
        self,
        basic_trading: BasicTrading,
        notification_service=None,
        trade_logger: Optional[TradeLogger] = None,
        sync_interval_minutes: int = 10
    ):
        self.basic_trading = basic_trading
        self.notification_service = notification_service
        
        # Obtener account ID para crear DB específica por cuenta
        account_id = self._get_account_id()
        self.trade_logger = trade_logger or TradeLogger(account_id=account_id)
        
        # Crear servicio de sincronización con historial MT5
        self.trade_sync_service = TradeSyncService(
            repository=self.trade_logger.repository,
            sync_interval_minutes=sync_interval_minutes,
            history_days=7
        )
        
        # Diccionario de bots activos: bot_id -> (thread, stop_event, director, config)
        self.active_bots: Dict[str, dict] = {}
        self.lock = threading.Lock()
    
    def _get_account_id(self) -> Optional[int]:
        """Obtiene el número de cuenta MT5."""
        try:
            import MetaTrader5 as mt5
            account_info = mt5.account_info()
            if account_info:
                return account_info.login  # Número de cuenta real
            return None
        except Exception as e:
            print(f"{Utils.dateprint()} - WARNING: Could not get account ID: {e}")
            return None
    
    def add_bot(self, bot_config: BotConfig) -> bool:
        """
        Agrega y arranca un nuevo bot.
        
        Args:
            bot_config: Configuración del bot a agregar
            
        Returns:
            True si se agregó exitosamente, False si ya existe
        """
        with self.lock:
            # Si es el primer bot, iniciar el servicio de sincronización
            is_first_bot = len(self.active_bots) == 0
            
            # Verificar si ya existe un bot con el mismo bot_id
            if bot_config.bot_id in self.active_bots:
                print(f"{Utils.dateprint()} - ERROR: Bot '{bot_config.bot_id}' ya existe.")
                return False
            
            # Verificar si ya existe un bot con el mismo magic_number
            for existing_bot_id, bot_info in self.active_bots.items():
                if bot_info['config'].magic_number == bot_config.magic_number:
                    print(f"{Utils.dateprint()} - ERROR: Ya existe un bot con el mismo magic number ({bot_config.magic_number}).")
                    print(f"  Bot existente: '{existing_bot_id}'")
                    print(f"  Nuevo bot:     '{bot_config.bot_id}'")
                    print(f"  Cada estrategia debe tener un magic number único.")
                    return False
            
            # Verificar si el mercado está abierto para el símbolo
            market_open = self.basic_trading.is_market_open(bot_config.symbol)
            if not market_open:
                print(f"{Utils.dateprint()} - ⚠️  WARNING: Mercado CERRADO para '{bot_config.symbol}'.")
                print(f"    El bot '{bot_config.bot_id}' esperará a que el mercado abra para operar.")
            else:
                print(f"{Utils.dateprint()} - ✅ Mercado ABIERTO para '{bot_config.symbol}'.")
            
            # Crear director para este bot
            director = SimpleTradingDirector(
                self.basic_trading,
                bot_config.strategy,
                notification_service=self.notification_service,
                magic_number=bot_config.magic_number,
                trade_logger=self.trade_logger,
                bot_id=bot_config.bot_id
            )
            
            # Crear eventos para controlar el thread
            stop_event = threading.Event()  # Para detener completamente (solo al salir)
            pause_event = threading.Event()  # Para pausar/reanudar
            pause_event.set()  # Iniciar en estado "running" (no pausado)
            
            # Crear y arrancar thread
            thread = threading.Thread(
                target=self._run_bot,
                args=(bot_config, director, stop_event, pause_event),
                daemon=True,
                name=f"Bot-{bot_config.bot_id}"
            )
            
            self.active_bots[bot_config.bot_id] = {
                'thread': thread,
                'stop_event': stop_event,
                'pause_event': pause_event,
                'director': director,
                'config': bot_config,
                'status': 'starting'
            }
            
            thread.start()
            print(f"{Utils.dateprint()} - Bot '{bot_config.bot_id}' iniciado: {bot_config.symbol} {bot_config.timeframe} (Magic: {bot_config.magic_number})")
            
            # Iniciar servicio de sincronización después de agregar el primer bot
            if is_first_bot:
                self.trade_sync_service.start()
            
            return True
    
    def _run_bot(self, config: BotConfig, director: SimpleTradingDirector, stop_event: threading.Event, pause_event: threading.Event):
        """
        Función que ejecuta el loop de un bot individual con soporte de pausa.
        
        Args:
            config: Configuración del bot
            director: Director de trading para este bot
            stop_event: Evento para señalar detención completa
            pause_event: Evento para pausar/reanudar (set = running, clear = paused)
        """
        iteration = 0
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        with self.lock:
            if config.bot_id in self.active_bots:
                self.active_bots[config.bot_id]['status'] = 'running'
        
        print(f"{Utils.dateprint()} - [{config.bot_id}] Iniciando loop - {config.symbol} {config.timeframe} (Magic: {config.magic_number})")
        
        while not stop_event.is_set():
            # Esperar si está pausado
            pause_event.wait()  # Bloquea hasta que pause_event.set() sea llamado
            
            # Verificar nuevamente si se debe detener después de reanudar
            if stop_event.is_set():
                break
            
            iteration += 1
            
            try:
                # Health check: verificar conexión MT5
                if not self.basic_trading.check_connection():
                    print(f"{Utils.dateprint()} - [{config.bot_id}] WARNING: MT5 connection lost. Attempting to reconnect...")
                    if self.basic_trading.reconnect():
                        print(f"{Utils.dateprint()} - [{config.bot_id}] MT5 reconnected successfully.")
                        consecutive_errors = 0
                    else:
                        print(f"{Utils.dateprint()} - [{config.bot_id}] ERROR: Failed to reconnect to MT5.")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            print(f"{Utils.dateprint()} - [{config.bot_id}] CRITICAL: Too many consecutive errors. Stopping bot.")
                            break
                        time.sleep(10)
                        continue
                
                # Verificar si el mercado está abierto antes de ejecutar
                if not self.basic_trading.is_market_open(config.symbol):
                    # Solo mostrar mensaje cada 5 iteraciones para no saturar el log
                    if iteration == 1 or iteration % 5 == 0:
                        print(f"{Utils.dateprint()} - [{config.bot_id}] 🕐 Mercado cerrado para {config.symbol}. Esperando...")
                    # Actualizar status a 'waiting_market'
                    with self.lock:
                        if config.bot_id in self.active_bots:
                            self.active_bots[config.bot_id]['status'] = 'waiting_market'
                    # Esperar el intervalo antes de verificar de nuevo (no saltar con continue)
                    for _ in range(config.interval_seconds):
                        if stop_event.is_set() or not pause_event.is_set():
                            break
                        time.sleep(1)
                    continue  # Saltar a la siguiente iteración después de esperar
                
                # Restaurar status a 'running' si estaba esperando
                with self.lock:
                    if config.bot_id in self.active_bots and self.active_bots[config.bot_id]['status'] == 'waiting_market':
                        self.active_bots[config.bot_id]['status'] = 'running'
                        print(f"{Utils.dateprint()} - [{config.bot_id}] ✅ Mercado abierto. Reanudando operaciones.")
                
                # Ejecutar estrategia
                director.run_strategy(
                    config.symbol,
                    config.timeframe,
                    config.data_points
                )
                consecutive_errors = 0  # Reset error counter on success
                
            except Exception as e:
                consecutive_errors += 1
                print(f"{Utils.dateprint()} - [{config.bot_id}] ERROR in iteration {iteration} ({consecutive_errors}/{max_consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"{Utils.dateprint()} - [{config.bot_id}] CRITICAL: Too many consecutive errors. Stopping bot.")
                    break
                
                time.sleep(5)  # Espera breve antes de reintentar
            
            # Esperar el intervalo configurado (con chequeo de eventos cada segundo)
            for _ in range(config.interval_seconds):
                if stop_event.is_set() or not pause_event.is_set():
                    break
                time.sleep(1)
        
        print(f"{Utils.dateprint()} - [{config.bot_id}] Detenido después de {iteration} iteraciones.")
        
        with self.lock:
            if config.bot_id in self.active_bots:
                self.active_bots[config.bot_id]['status'] = 'stopped'
    
    def pause_bot(self, bot_id: str) -> bool:
        """
        Pausa un bot específico.
        
        Args:
            bot_id: ID del bot a pausar
            
        Returns:
            True si se pausó exitosamente, False si no existe o ya está pausado
        """
        with self.lock:
            if bot_id not in self.active_bots:
                print(f"{Utils.dateprint()} - ERROR: Bot '{bot_id}' no existe.")
                return False
            
            bot_info = self.active_bots[bot_id]
            
            if bot_info['status'] == 'paused':
                print(f"{Utils.dateprint()} - Bot '{bot_id}' ya está pausado.")
                return True
            
            # Pausar el bot
            bot_info['pause_event'].clear()  # Pausar
            bot_info['status'] = 'paused'
            print(f"{Utils.dateprint()} - Bot '{bot_id}' pausado.")
            
            # Emit event
            on_bot_status_change(bot_id, 'paused')
        
        return True
    
    def resume_bot(self, bot_id: str) -> bool:
        """
        Reanuda un bot pausado.
        
        Args:
            bot_id: ID del bot a reanudar
            
        Returns:
            True si se reanudó exitosamente, False si no existe o no está pausado
        """
        with self.lock:
            if bot_id not in self.active_bots:
                print(f"{Utils.dateprint()} - ERROR: Bot '{bot_id}' no existe.")
                return False
            
            bot_info = self.active_bots[bot_id]
            
            if bot_info['status'] != 'paused':
                print(f"{Utils.dateprint()} - Bot '{bot_id}' no está pausado (status: {bot_info['status']}).")
                return False
            
            # Reanudar el bot
            bot_info['pause_event'].set()  # Reanudar
            bot_info['status'] = 'running'
            print(f"{Utils.dateprint()} - Bot '{bot_id}' reanudado.")
            
            # Emit event
            on_bot_status_change(bot_id, 'resumed')
        
        return True
    
    
    def stop_all_bots(self):
        """Detiene todos los bots activos completamente (solo al salir del programa)."""
        # Detener el servicio de sincronización
        self.trade_sync_service.stop()
        
        with self.lock:
            bot_ids = list(self.active_bots.keys())
        
        print(f"{Utils.dateprint()} - Deteniendo {len(bot_ids)} bots...")
        
        # Señalar a todos los bots que se detengan
        with self.lock:
            for bot_id in bot_ids:
                if bot_id in self.active_bots:
                    self.active_bots[bot_id]['stop_event'].set()
                    self.active_bots[bot_id]['pause_event'].set()  # Asegurar que no estén bloqueados en pausa
        
        # Esperar a que terminen
        for bot_id in bot_ids:
            if bot_id in self.active_bots:
                self.active_bots[bot_id]['thread'].join(timeout=5)
        
        print(f"{Utils.dateprint()} - Todos los bots detenidos.")
    
    def get_bot_status(self, bot_id: str) -> Optional[dict]:
        """
        Obtiene el estado de un bot específico.
        
        Args:
            bot_id: ID del bot
            
        Returns:
            Diccionario con información del bot o None si no existe
        """
        with self.lock:
            if bot_id not in self.active_bots:
                return None
            
            bot_info = self.active_bots[bot_id]
            config = bot_info['config']
            
            return {
                'bot_id': bot_id,
                'status': bot_info['status'],
                'symbol': config.symbol,
                'timeframe': config.timeframe,
                'interval_seconds': config.interval_seconds,
                'magic_number': config.magic_number,
                'is_alive': bot_info['thread'].is_alive()
            }
    
    def get_all_bots_status(self) -> list:
        """
        Obtiene el estado de todos los bots.
        
        Returns:
            Lista de diccionarios con información de cada bot
        """
        with self.lock:
            bot_ids = list(self.active_bots.keys())
        
        return [self.get_bot_status(bot_id) for bot_id in bot_ids]
    
    def list_bots(self) -> list:
        """
        Lista los IDs de todos los bots activos.
        
        Returns:
            Lista de IDs de bots
        """
        with self.lock:
            return list(self.active_bots.keys())
    
    def get_bot_trading_stats(self, bot_id: str) -> Optional[dict]:
        """
        Obtiene estadísticas de trading de un bot desde la base de datos.
        
        Args:
            bot_id: ID del bot
            
        Returns:
            Diccionario con estadísticas o None si no existe
        """
        return self.trade_logger.get_bot_stats(bot_id)
    
    def get_all_trading_stats(self) -> list:
        """
        Obtiene estadísticas de trading de todos los bots.
        
        Returns:
            Lista de diccionarios con estadísticas de cada bot
        """
        return self.trade_logger.get_all_stats()
    
    def sync_trades_now(self):
        """Ejecuta una sincronización manual inmediata con el historial de MT5."""
        self.trade_sync_service.sync_now()
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """Retorna el tiempo de la última sincronización con MT5."""
        return self.trade_sync_service.get_last_sync_time()
