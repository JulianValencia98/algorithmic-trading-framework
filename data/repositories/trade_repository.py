import sqlite3
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from data.models.trade import Trade, TradeStatus
from data.models.signal import Signal


class TradeRepository:
    """
    Repositorio para persistir trades y señales en SQLite.
    Crea una base de datos separada para cada cuenta de MT5.
    Diseñado para ser fácilmente reemplazable por PostgreSQL en el futuro.
    """
    
    def __init__(self, account_id: int = None, db_path: str = None):
        """
        Inicializa el repositorio.
        
        Args:
            account_id: ID de la cuenta MT5 (crea DB específica por cuenta)
            db_path: Ruta personalizada al archivo SQLite (override)
        """
        if db_path:
            self.db_path = db_path
        elif account_id:
            self.db_path = f"data/trades_account_{account_id}.db"
        else:
            self.db_path = "data/trades_default.db"
        
        self.account_id = account_id
        self._ensure_directory()
        self._init_db()
    
    def _ensure_directory(self):
        """Asegura que el directorio de la base de datos exista."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Obtiene una conexión a la base de datos."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Inicializa las tablas de la base de datos."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Tabla de trades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket INTEGER,
                magic_number INTEGER,
                bot_id TEXT,
                strategy_name TEXT,
                symbol TEXT,
                action TEXT,
                volume REAL,
                entry_price REAL,
                exit_price REAL,
                sl_price REAL,
                tp_price REAL,
                profit REAL,
                profit_pips REAL,
                commission REAL,
                swap REAL,
                opened_at TEXT,
                closed_at TEXT,
                status TEXT,
                close_reason TEXT,
                signal_data TEXT,
                market_context TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de señales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT,
                strategy_name TEXT,
                symbol TEXT,
                timeframe TEXT,
                signal_type TEXT,
                generated_at TEXT,
                price_at_signal REAL,
                was_executed INTEGER,
                execution_ticket INTEGER,
                skip_reason TEXT,
                indicators_snapshot TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Índices para búsquedas comunes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_bot_id ON trades(bot_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_magic ON trades(magic_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_opened ON trades(opened_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_bot_id ON signals(bot_id)')
        
        conn.commit()
        conn.close()
    
    # ==================== TRADES ====================
    
    def save_trade(self, trade: Trade) -> int:
        """
        Guarda un trade en la base de datos.
        
        Args:
            trade: Trade a guardar
            
        Returns:
            ID del trade insertado
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades (
                ticket, magic_number, bot_id, strategy_name, symbol, action,
                volume, entry_price, exit_price, sl_price, tp_price,
                profit, profit_pips, commission, swap,
                opened_at, closed_at, status, close_reason,
                signal_data, market_context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.ticket, trade.magic_number, trade.bot_id, trade.strategy_name,
            trade.symbol, trade.action, trade.volume, trade.entry_price,
            trade.exit_price, trade.sl_price, trade.tp_price,
            trade.profit, trade.profit_pips, trade.commission, trade.swap,
            trade.opened_at.isoformat() if trade.opened_at else None,
            trade.closed_at.isoformat() if trade.closed_at else None,
            trade.status.value, trade.close_reason,
            trade.signal_data, trade.market_context
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    def update_trade(self, trade: Trade) -> bool:
        """
        Actualiza un trade existente.
        
        Args:
            trade: Trade con datos actualizados (debe tener id o ticket)
            
        Returns:
            True si se actualizó correctamente
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if trade.id:
            cursor.execute('''
                UPDATE trades SET
                    exit_price = ?, profit = ?, profit_pips = ?,
                    commission = ?, swap = ?, closed_at = ?,
                    status = ?, close_reason = ?
                WHERE id = ?
            ''', (
                trade.exit_price, trade.profit, trade.profit_pips,
                trade.commission, trade.swap,
                trade.closed_at.isoformat() if trade.closed_at else None,
                trade.status.value, trade.close_reason,
                trade.id
            ))
        elif trade.ticket:
            cursor.execute('''
                UPDATE trades SET
                    exit_price = ?, profit = ?, profit_pips = ?,
                    commission = ?, swap = ?, closed_at = ?,
                    status = ?, close_reason = ?
                WHERE ticket = ? AND status = 'opened'
            ''', (
                trade.exit_price, trade.profit, trade.profit_pips,
                trade.commission, trade.swap,
                trade.closed_at.isoformat() if trade.closed_at else None,
                trade.status.value, trade.close_reason,
                trade.ticket
            ))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return updated
    
    def get_trade_by_ticket(self, ticket: int) -> Optional[Trade]:
        """Obtiene un trade por su ticket de MT5."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trades WHERE ticket = ?', (ticket,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_trade(row)
        return None
    
    def get_open_trades(self, bot_id: Optional[str] = None) -> List[Trade]:
        """Obtiene todos los trades abiertos."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if bot_id:
            cursor.execute(
                "SELECT * FROM trades WHERE status = 'opened' AND bot_id = ? ORDER BY ticket DESC",
                (bot_id,)
            )
        else:
            cursor.execute("SELECT * FROM trades WHERE status = 'opened' ORDER BY ticket DESC")
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_trade(row) for row in rows]
    
    def get_trades_by_bot(self, bot_id: str, limit: int = 100) -> List[Trade]:
        """Obtiene trades de un bot específico."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM trades WHERE bot_id = ? ORDER BY ticket DESC LIMIT ?',
            (bot_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_trade(row) for row in rows]
    
    def get_trades_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        bot_id: Optional[str] = None
    ) -> List[Trade]:
        """Obtiene trades en un rango de fechas."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if bot_id:
            cursor.execute(
                '''SELECT * FROM trades 
                   WHERE opened_at >= ? AND opened_at <= ? AND bot_id = ?
                   ORDER BY ticket DESC''',
                (start_date.isoformat(), end_date.isoformat(), bot_id)
            )
        else:
            cursor.execute(
                '''SELECT * FROM trades 
                   WHERE opened_at >= ? AND opened_at <= ?
                   ORDER BY ticket DESC''',
                (start_date.isoformat(), end_date.isoformat())
            )
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_trade(row) for row in rows]
    
    def get_all_trades(self, limit: int = 1000) -> List[Trade]:
        """Obtiene todos los trades."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trades ORDER BY ticket DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_trade(row) for row in rows]
    
    def _row_to_trade(self, row: sqlite3.Row) -> Trade:
        """Convierte una fila de SQLite a objeto Trade."""
        return Trade(
            id=row['id'],
            ticket=row['ticket'],
            magic_number=row['magic_number'],
            bot_id=row['bot_id'],
            strategy_name=row['strategy_name'],
            symbol=row['symbol'],
            action=row['action'],
            volume=row['volume'],
            entry_price=row['entry_price'],
            exit_price=row['exit_price'],
            sl_price=row['sl_price'],
            tp_price=row['tp_price'],
            profit=row['profit'],
            profit_pips=row['profit_pips'],
            commission=row['commission'],
            swap=row['swap'],
            opened_at=datetime.fromisoformat(row['opened_at']) if row['opened_at'] else None,
            closed_at=datetime.fromisoformat(row['closed_at']) if row['closed_at'] else None,
            status=TradeStatus(row['status']),
            close_reason=row['close_reason'],
            signal_data=row['signal_data'],
            market_context=row['market_context'],
        )
    
    # ==================== SIGNALS ====================
    
    def save_signal(self, signal: Signal) -> int:
        """Guarda una señal en la base de datos."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO signals (
                bot_id, strategy_name, symbol, timeframe, signal_type,
                generated_at, price_at_signal, was_executed, execution_ticket,
                skip_reason, indicators_snapshot
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal.bot_id, signal.strategy_name, signal.symbol, signal.timeframe,
            signal.signal_type, signal.generated_at.isoformat() if signal.generated_at else None,
            signal.price_at_signal, 1 if signal.was_executed else 0,
            signal.execution_ticket, signal.skip_reason, signal.indicators_snapshot
        ))
        
        signal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return signal_id
    
    def get_signals_by_bot(self, bot_id: str, limit: int = 100) -> List[Signal]:
        """Obtiene señales de un bot específico."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM signals WHERE bot_id = ? ORDER BY generated_at DESC LIMIT ?',
            (bot_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_signal(row) for row in rows]
    
    def _row_to_signal(self, row: sqlite3.Row) -> Signal:
        """Convierte una fila de SQLite a objeto Signal."""
        return Signal(
            id=row['id'],
            bot_id=row['bot_id'],
            strategy_name=row['strategy_name'],
            symbol=row['symbol'],
            timeframe=row['timeframe'],
            signal_type=row['signal_type'],
            generated_at=datetime.fromisoformat(row['generated_at']) if row['generated_at'] else None,
            price_at_signal=row['price_at_signal'],
            was_executed=bool(row['was_executed']),
            execution_ticket=row['execution_ticket'],
            skip_reason=row['skip_reason'],
            indicators_snapshot=row['indicators_snapshot'],
        )
    
    # ==================== ANALYTICS ====================
    
    def get_bot_stats(self, bot_id: str) -> dict:
        """
        Obtiene estadísticas de un bot.
        
        Returns:
            Diccionario con estadísticas
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Total trades
        cursor.execute(
            "SELECT COUNT(*) as total FROM trades WHERE bot_id = ?",
            (bot_id,)
        )
        total = cursor.fetchone()['total']
        
        # Trades cerrados con profit
        cursor.execute(
            "SELECT COUNT(*) as wins FROM trades WHERE bot_id = ? AND status = 'closed' AND profit > 0",
            (bot_id,)
        )
        wins = cursor.fetchone()['wins']
        
        # Trades cerrados con pérdida
        cursor.execute(
            "SELECT COUNT(*) as losses FROM trades WHERE bot_id = ? AND status = 'closed' AND profit < 0",
            (bot_id,)
        )
        losses = cursor.fetchone()['losses']
        
        # Profit total
        cursor.execute(
            "SELECT COALESCE(SUM(profit), 0) as total_profit FROM trades WHERE bot_id = ? AND status = 'closed'",
            (bot_id,)
        )
        total_profit = cursor.fetchone()['total_profit']
        
        # Profit promedio
        cursor.execute(
            "SELECT COALESCE(AVG(profit), 0) as avg_profit FROM trades WHERE bot_id = ? AND status = 'closed'",
            (bot_id,)
        )
        avg_profit = cursor.fetchone()['avg_profit']
        
        conn.close()
        
        closed_trades = wins + losses
        win_rate = (wins / closed_trades * 100) if closed_trades > 0 else 0
        
        return {
            'bot_id': bot_id,
            'total_trades': total,
            'closed_trades': closed_trades,
            'open_trades': total - closed_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 2),
            'total_profit': round(total_profit, 2),
            'avg_profit': round(avg_profit, 2),
        }
    
    def get_all_bots_stats(self) -> List[dict]:
        """Obtiene estadísticas de todos los bots."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT bot_id FROM trades")
        bot_ids = [row['bot_id'] for row in cursor.fetchall()]
        conn.close()
        
        return [self.get_bot_stats(bot_id) for bot_id in bot_ids]
