"""
Backtesting para MeanReversionBBStrategy

Este script ejecuta un backtest completo de la estrategia MeanReversionBB
con datos del último año, generando gráficas detalladas de los trades.

Compatible con RoboForex a través de MetaTrader5.
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Agregar el directorio raíz al path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Importar estrategia y utilidades
from strategies.mean_reversion_bb_strategy import MeanReversionBBStrategy
from strategies.strategy_base import StrategyBase
from utils.utils import Utils

# Importar MT5 para datos de RoboForex
try:
    import MetaTrader5 as mt5
    from Easy_Trading import BasicTrading
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("⚠️ MetaTrader5 no disponible. Instalar con: pip install MetaTrader5")


class MeanReversionBBBacktester:
    """
    Motor de backtesting especializado para MeanReversionBBStrategy.
    
    Features:
    - Datos desde RoboForex via MT5
    - Gráficas de precio con entradas/salidas
    - Equity curve
    - Drawdown chart
    - Estadísticas detalladas
    """
    
    # Mapeo de timeframes
    TIMEFRAME_MAP = {
        'M1': mt5.TIMEFRAME_M1 if MT5_AVAILABLE else None,
        'M5': mt5.TIMEFRAME_M5 if MT5_AVAILABLE else None,
        'M15': mt5.TIMEFRAME_M15 if MT5_AVAILABLE else None,
        'M30': mt5.TIMEFRAME_M30 if MT5_AVAILABLE else None,
        'H1': mt5.TIMEFRAME_H1 if MT5_AVAILABLE else None,
        'H4': mt5.TIMEFRAME_H4 if MT5_AVAILABLE else None,
        'D1': mt5.TIMEFRAME_D1 if MT5_AVAILABLE else None,
        'W1': mt5.TIMEFRAME_W1 if MT5_AVAILABLE else None,
    }
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.00007,  # 0.7 pips spread/comisión típica RoboForex
    ):
        """
        Inicializa el backtester.
        
        Args:
            initial_capital: Capital inicial en USD
            commission: Comisión por operación (como decimal)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.basic_trading: Optional[BasicTrading] = None
        
    def _connect_mt5(self) -> bool:
        """Conecta a MetaTrader5 (RoboForex)."""
        if not MT5_AVAILABLE:
            print("❌ MT5 no disponible")
            return False
        
        try:
            self.basic_trading = BasicTrading()
            print(f"✅ Conectado a MT5 (RoboForex)")
            return True
        except Exception as e:
            print(f"❌ Error conectando MT5: {e}")
            return False
    
    def _get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        Obtiene datos históricos de MT5.
        
        Args:
            symbol: Símbolo (ej: EURUSD)
            timeframe: Timeframe (M1, M5, H1, etc.)
            start_date: Fecha inicio
            end_date: Fecha fin
            
        Returns:
            DataFrame con OHLCV
        """
        if not MT5_AVAILABLE or not self.basic_trading:
            return None
        
        tf = self.TIMEFRAME_MAP.get(timeframe)
        if tf is None:
            print(f"❌ Timeframe {timeframe} no soportado")
            return None
        
        # Obtener datos desde MT5
        rates = mt5.copy_rates_range(symbol, tf, start_date, end_date)
        
        if rates is None or len(rates) == 0:
            print(f"❌ No se obtuvieron datos para {symbol}")
            return None
        
        # Convertir a DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # Renombrar columnas para compatibilidad
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'tick_volume': 'Volume'
        }, inplace=True)
        
        # Añadir columnas en minúsculas para la estrategia
        df['open'] = df['Open']
        df['high'] = df['High']
        df['low'] = df['Low']
        df['close'] = df['Close']
        df['tick_volume'] = df['Volume']
        
        return df
    
    def run_backtest(
        self,
        symbol: str = "EURUSD",
        timeframe: str = "H1",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        strategy_params: Optional[Dict] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta el backtesting completo.
        
        Args:
            symbol: Símbolo a testear
            timeframe: Timeframe
            start_date: Fecha inicio (default: hace 1 año)
            end_date: Fecha fin (default: hoy)
            strategy_params: Parámetros personalizados de la estrategia
            verbose: Mostrar logs
            
        Returns:
            Dict con resultados completos
        """
        # Configurar fechas (último año por defecto)
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"  BACKTEST: MeanReversionBBStrategy")
            print(f"{'='*60}")
            print(f"  Símbolo: {symbol}")
            print(f"  Timeframe: {timeframe}")
            print(f"  Período: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
            print(f"  Capital inicial: ${self.initial_capital:,.2f}")
            print(f"{'='*60}\n")
        
        # Conectar a MT5
        if not self._connect_mt5():
            return {"error": "No se pudo conectar a MT5 (RoboForex)"}
        
        # Obtener datos
        if verbose:
            print("📊 Obteniendo datos históricos...")
        
        data = self._get_historical_data(symbol, timeframe, start_date, end_date)
        
        if data is None or data.empty:
            return {"error": f"No se obtuvieron datos para {symbol}"}
        
        if verbose:
            print(f"   ✅ {len(data)} velas obtenidas")
            print(f"   Rango: {data.index[0]} → {data.index[-1]}")
        
        # Crear estrategia con parámetros personalizados
        if strategy_params:
            strategy = MeanReversionBBStrategy(**strategy_params)
        else:
            strategy = MeanReversionBBStrategy()
        
        # Ejecutar simulación
        if verbose:
            print("\n🔄 Ejecutando simulación...")
        
        results = self._simulate(data, strategy, symbol, verbose)
        
        # Agregar metadata
        results['symbol'] = symbol
        results['timeframe'] = timeframe
        results['start_date'] = str(start_date)
        results['end_date'] = str(end_date)
        results['data_points'] = len(data)
        results['data'] = data  # Para gráficas
        
        return results
    
    def _precalculate_indicators(
        self,
        data: pd.DataFrame,
        strategy: MeanReversionBBStrategy
    ) -> pd.DataFrame:
        """
        Pre-calcula todos los indicadores para optimizar el backtest.
        """
        df = data.copy()
        close = df['close']
        high = df['high']
        low = df['low']
        
        # === BOLLINGER BANDS ===
        df['bb_sma'] = close.rolling(window=strategy.bb_period).mean()
        df['bb_std'] = close.rolling(window=strategy.bb_period).std()
        df['bb_upper'] = df['bb_sma'] + (strategy.bb_std * df['bb_std'])
        df['bb_lower'] = df['bb_sma'] - (strategy.bb_std * df['bb_std'])
        
        # === RSI ===
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=strategy.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=strategy.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # === EMA TREND ===
        df['ema_trend'] = close.ewm(span=strategy.trend_ema_period, adjust=False).mean()
        
        # === ATR ===
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        df['atr'] = tr.rolling(window=strategy.atr_period).mean()
        
        # === VOLUME (si hay) ===
        if 'tick_volume' in df.columns:
            df['avg_volume'] = df['tick_volume'].rolling(window=strategy.volume_period).mean()
        
        # === BB WIDTH (for squeeze) ===
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_sma']
        df['avg_bb_width'] = df['bb_width'].rolling(window=strategy.squeeze_lookback).mean()
        
        return df
    
    def _generate_signal_fast(
        self,
        row: pd.Series,
        strategy: MeanReversionBBStrategy
    ) -> str:
        """
        Genera señal usando indicadores pre-calculados (mucho más rápido).
        """
        # Verificar si hay suficientes datos
        if pd.isna(row.get('bb_upper')) or pd.isna(row.get('rsi')):
            return 'hold'
        
        current_price = row['close']
        bb_upper = row['bb_upper']
        bb_lower = row['bb_lower']
        rsi = row['rsi']
        ema_trend = row['ema_trend']
        
        # === SQUEEZE FILTER ===
        if strategy.use_squeeze_filter:
            bb_width = row.get('bb_width', 1)
            avg_bb_width = row.get('avg_bb_width', 1)
            if not pd.isna(avg_bb_width) and bb_width < avg_bb_width * strategy.squeeze_threshold:
                return 'hold'
        
        # === VOLUME FILTER ===
        if strategy.use_volume_filter and 'tick_volume' in row.index:
            current_vol = row['tick_volume']
            avg_vol = row.get('avg_volume', 0)
            if not pd.isna(avg_vol) and current_vol < avg_vol * strategy.volume_factor:
                return 'hold'
        
        # === RSI CONFIRMATION ===
        rsi_ok_buy = True
        rsi_ok_sell = True
        if strategy.use_rsi:
            rsi_ok_buy = rsi < strategy.rsi_oversold
            rsi_ok_sell = rsi > strategy.rsi_overbought
        
        # === TREND CONFIRMATION ===
        trend_ok_buy = True
        trend_ok_sell = True
        if strategy.use_trend_filter and not pd.isna(ema_trend):
            trend_ok_buy = current_price > ema_trend * (1 - strategy.trend_tolerance)
            trend_ok_sell = current_price < ema_trend * (1 + strategy.trend_tolerance)
        
        # === GENERATE SIGNALS ===
        if current_price <= bb_lower and rsi_ok_buy and trend_ok_buy:
            return 'buy'
        
        if current_price >= bb_upper and rsi_ok_sell and trend_ok_sell:
            return 'sell'
        
        return 'hold'
    
    def _simulate(
        self,
        data: pd.DataFrame,
        strategy: MeanReversionBBStrategy,
        symbol: str,
        verbose: bool
    ) -> Dict[str, Any]:
        """
        Ejecuta la simulación de trading (versión optimizada).
        """
        params = strategy.get_parameters()
        
        # Pre-calcular todos los indicadores
        if verbose:
            print("   Precalculando indicadores...")
        df = self._precalculate_indicators(data, strategy)
        
        # Estado inicial
        capital = self.initial_capital
        position = 0  # 0: sin posición, 1: long, -1: short
        entry_price = 0.0
        position_size = 0.0
        entry_time = None
        sl_price = None
        tp_price = None
        
        # Registros
        trades = []
        equity_curve = []
        drawdown_curve = []
        peak_equity = capital
        
        # Indicadores para gráficas (ya pre-calculados)
        bb_upper = df['bb_upper'].tolist()
        bb_lower = df['bb_lower'].tolist()
        bb_middle = df['bb_sma'].tolist()
        rsi_values = df['rsi'].tolist()
        atr_values = df['atr'].tolist()
        
        if verbose:
            print("   Ejecutando simulación...")
        
        # Loop principal
        for i in range(len(df)):
            row = df.iloc[i]
            current_time = df.index[i]
            current_price = row['close']
            current_atr = row['atr'] if not pd.isna(row['atr']) else 0.001
            
            # Generar señal usando indicadores pre-calculados
            signal = self._generate_signal_fast(row, strategy)
            
            # Gestión de posiciones abiertas
            if position != 0:
                exit_occurred = False
                exit_reason = None
                exit_price = None
                
                # Verificar SL/TP
                if position == 1:  # Long
                    if sl_price and row['Low'] <= sl_price:
                        exit_price = sl_price
                        exit_reason = 'SL'
                        exit_occurred = True
                    elif tp_price and row['High'] >= tp_price:
                        exit_price = tp_price
                        exit_reason = 'TP'
                        exit_occurred = True
                elif position == -1:  # Short
                    if sl_price and row['High'] >= sl_price:
                        exit_price = sl_price
                        exit_reason = 'SL'
                        exit_occurred = True
                    elif tp_price and row['Low'] <= tp_price:
                        exit_price = tp_price
                        exit_reason = 'TP'
                        exit_occurred = True
                
                # Procesar salida
                if exit_occurred:
                    pnl = self._calculate_pnl(position, entry_price, exit_price, position_size)
                    commission_cost = position_size * exit_price * self.commission
                    net_pnl = pnl - commission_cost
                    capital += net_pnl
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'type': 'LONG' if position == 1 else 'SHORT',
                        'pnl': net_pnl,
                        'exit_reason': exit_reason,
                        'volume': position_size
                    })
                    
                    if verbose and len(trades) % 20 == 0:
                        print(f"   Trade #{len(trades)}: {exit_reason} | PnL: ${net_pnl:.2f}")
                    
                    # Reset
                    position = 0
                    position_size = 0.0
                    entry_time = None
                    sl_price = None
                    tp_price = None
            
            # Nueva señal y close_before_open
            if position != 0 and signal in ['buy', 'sell']:
                if params.get('close_before_open', True):
                    # Cerrar posición actual
                    exit_price = current_price
                    pnl = self._calculate_pnl(position, entry_price, exit_price, position_size)
                    commission_cost = position_size * exit_price * self.commission
                    net_pnl = pnl - commission_cost
                    capital += net_pnl
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'type': 'LONG' if position == 1 else 'SHORT',
                        'pnl': net_pnl,
                        'exit_reason': 'SIGNAL',
                        'volume': position_size
                    })
                    
                    position = 0
                    position_size = 0.0
                    entry_time = None
                    sl_price = None
                    tp_price = None
            
            # Abrir nueva posición
            if position == 0 and signal in ['buy', 'sell']:
                entry_price = current_price
                entry_time = current_time
                
                # Calcular tamaño de posición (simplificado para backtest)
                # Usando riesgo fijo del 1% con SL basado en ATR
                pip_size = 0.0001 if 'JPY' not in symbol else 0.01
                sl_distance = current_atr * strategy.sl_atr_mult if strategy.use_atr_sl_tp else strategy.sl_pips * pip_size
                tp_distance = current_atr * strategy.tp_atr_mult if strategy.use_atr_sl_tp else strategy.tp_pips * pip_size
                
                # Position size basado en riesgo
                risk_amount = capital * (strategy.risk_percent / 100)
                sl_pips = sl_distance / pip_size
                pip_value = 10.0  # $10 por pip por lote estándar para pares USD
                position_size = risk_amount / (sl_pips * pip_value) if sl_pips > 0 else 0.01
                position_size = max(0.01, min(position_size, 10.0))  # Limitar entre 0.01 y 10 lotes
                
                # Calcular SL/TP
                if signal == 'buy':
                    sl_price = entry_price - sl_distance
                    tp_price = entry_price + tp_distance
                else:
                    sl_price = entry_price + sl_distance
                    tp_price = entry_price - tp_distance
                
                position = 1 if signal == 'buy' else -1
                
                # Comisión de entrada
                capital -= position_size * entry_price * self.commission
            
            # Actualizar equity
            if position != 0:
                unrealized_pnl = self._calculate_pnl(position, entry_price, current_price, position_size)
                current_equity = capital + unrealized_pnl
            else:
                current_equity = capital
            
            equity_curve.append(current_equity)
            
            # Drawdown
            if current_equity > peak_equity:
                peak_equity = current_equity
            dd = (peak_equity - current_equity) / peak_equity if peak_equity > 0 else 0
            drawdown_curve.append(dd)
        
        # Cerrar posición final
        if position != 0:
            exit_price = data.iloc[-1]['close']
            pnl = self._calculate_pnl(position, entry_price, exit_price, position_size)
            capital += pnl - (position_size * exit_price * self.commission)
            
            trades.append({
                'entry_time': entry_time,
                'exit_time': data.index[-1],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'type': 'LONG' if position == 1 else 'SHORT',
                'pnl': pnl,
                'exit_reason': 'END',
                'volume': position_size
            })
        
        # Calcular métricas
        metrics = self._calculate_metrics(capital, trades, equity_curve)
        
        # Agregar datos para gráficas
        metrics['trades'] = trades
        metrics['equity_curve'] = equity_curve
        metrics['drawdown_curve'] = drawdown_curve
        metrics['bb_upper'] = bb_upper
        metrics['bb_lower'] = bb_lower
        metrics['bb_middle'] = bb_middle
        metrics['rsi_values'] = rsi_values
        metrics['strategy_params'] = strategy.get_parameters()
        
        return metrics
    
    def _calculate_pnl(self, position: int, entry_price: float, exit_price: float, volume: float) -> float:
        """Calcula PnL."""
        if position == 1:
            return (exit_price - entry_price) * volume * 100000  # Lotes estándar
        else:
            return (entry_price - exit_price) * volume * 100000
    
    def _calculate_metrics(self, final_capital: float, trades: List[Dict], equity_curve: List[float]) -> Dict[str, Any]:
        """Calcula métricas de performance."""
        
        total_pnl = final_capital - self.initial_capital
        
        if not trades:
            return {
                'total_pnl': total_pnl,
                'return_pct': 0,
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'final_capital': final_capital
            }
        
        winning = [t for t in trades if t['pnl'] > 0]
        losing = [t for t in trades if t['pnl'] < 0]
        
        win_rate = len(winning) / len(trades) if trades else 0
        
        gross_profit = sum(t['pnl'] for t in winning)
        gross_loss = abs(sum(t['pnl'] for t in losing))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        avg_win = np.mean([t['pnl'] for t in winning]) if winning else 0
        avg_loss = np.mean([t['pnl'] for t in losing]) if losing else 0
        
        # Max drawdown
        peak = equity_curve[0] if equity_curve else self.initial_capital
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        
        # Por tipo de salida
        sl_exits = len([t for t in trades if t['exit_reason'] == 'SL'])
        tp_exits = len([t for t in trades if t['exit_reason'] == 'TP'])
        signal_exits = len([t for t in trades if t['exit_reason'] == 'SIGNAL'])
        
        return {
            'total_pnl': total_pnl,
            'return_pct': (total_pnl / self.initial_capital) * 100,
            'final_capital': final_capital,
            'total_trades': len(trades),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'max_drawdown': max_dd,
            'sl_exits': sl_exits,
            'tp_exits': tp_exits,
            'signal_exits': signal_exits,
            'long_trades': len([t for t in trades if t['type'] == 'LONG']),
            'short_trades': len([t for t in trades if t['type'] == 'SHORT'])
        }
    
    def plot_results(self, results: Dict[str, Any], save_path: Optional[str] = None):
        """
        Genera gráficas completas del backtest.
        
        Args:
            results: Resultados del backtest
            save_path: Ruta para guardar la imagen (opcional)
        """
        if 'error' in results:
            print(f"❌ No se pueden generar gráficas: {results['error']}")
            return
        
        data = results['data']
        trades = results['trades']
        equity_curve = results['equity_curve']
        drawdown_curve = results['drawdown_curve']
        bb_upper = results.get('bb_upper', [])
        bb_lower = results.get('bb_lower', [])
        bb_middle = results.get('bb_middle', [])
        
        # Crear figura con subplots
        fig = plt.figure(figsize=(16, 14), constrained_layout=True)
        fig.suptitle(
            f"Backtest: MeanReversionBBStrategy - {results['symbol']} {results['timeframe']}\n"
            f"Período: {results['start_date'][:10]} → {results['end_date'][:10]}",
            fontsize=14, fontweight='bold'
        )
        
        # Definir grid
        gs = fig.add_gridspec(4, 2, height_ratios=[2, 1, 1, 1])
        
        # ========== 1. PRECIO CON TRADES ==========
        ax1 = fig.add_subplot(gs[0, :])
        
        # Precio
        ax1.plot(data.index, data['close'], label='Precio', color='blue', alpha=0.7, linewidth=0.8)
        
        # Bollinger Bands
        if bb_upper and len(bb_upper) == len(data):
            ax1.plot(data.index, bb_upper, 'g--', alpha=0.5, linewidth=0.7, label='BB Superior')
            ax1.plot(data.index, bb_lower, 'r--', alpha=0.5, linewidth=0.7, label='BB Inferior')
            ax1.fill_between(data.index, bb_lower, bb_upper, alpha=0.1, color='gray')
        
        # Marcar trades
        for trade in trades:
            entry_time = trade['entry_time']
            exit_time = trade['exit_time']
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            trade_type = trade['type']
            pnl = trade['pnl']
            
            # Color según resultado
            color = 'green' if pnl > 0 else 'red'
            marker_entry = '^' if trade_type == 'LONG' else 'v'
            marker_exit = 's'
            
            # Entrada
            ax1.scatter(entry_time, entry_price, marker=marker_entry, color=color, s=80, zorder=5, edgecolors='black')
            # Salida
            ax1.scatter(exit_time, exit_price, marker=marker_exit, color=color, s=60, zorder=5, edgecolors='black')
            # Línea conectando
            ax1.plot([entry_time, exit_time], [entry_price, exit_price], color=color, alpha=0.3, linewidth=1)
        
        ax1.set_title('Precio y Trades (▲ Long Entry, ▼ Short Entry, ■ Exit)', fontsize=11)
        ax1.set_ylabel('Precio')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        
        # ========== 2. EQUITY CURVE ==========
        ax2 = fig.add_subplot(gs[1, :])
        
        eq_index = data.index[:len(equity_curve)]
        ax2.plot(eq_index, equity_curve, label='Equity', color='blue', linewidth=1.2)
        ax2.axhline(y=self.initial_capital, color='gray', linestyle='--', alpha=0.5, label='Capital Inicial')
        ax2.fill_between(eq_index, self.initial_capital, equity_curve, 
                         where=[e >= self.initial_capital for e in equity_curve], 
                         color='green', alpha=0.3)
        ax2.fill_between(eq_index, self.initial_capital, equity_curve, 
                         where=[e < self.initial_capital for e in equity_curve], 
                         color='red', alpha=0.3)
        
        ax2.set_title(f"Equity Curve | Final: ${results['final_capital']:,.2f} ({results['return_pct']:+.2f}%)", fontsize=11)
        ax2.set_ylabel('Equity ($)')
        ax2.legend(loc='upper left', fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        
        # ========== 3. DRAWDOWN ==========
        ax3 = fig.add_subplot(gs[2, :])
        
        dd_index = data.index[:len(drawdown_curve)]
        ax3.fill_between(dd_index, 0, [-d * 100 for d in drawdown_curve], color='red', alpha=0.5)
        ax3.plot(dd_index, [-d * 100 for d in drawdown_curve], color='darkred', linewidth=0.8)
        
        ax3.set_title(f"Drawdown | Max: {results['max_drawdown']*100:.2f}%", fontsize=11)
        ax3.set_ylabel('Drawdown (%)')
        ax3.set_ylim(bottom=-max(drawdown_curve) * 120 if drawdown_curve else -10)
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        
        # ========== 4. ESTADÍSTICAS (izquierda) ==========
        ax4 = fig.add_subplot(gs[3, 0])
        ax4.axis('off')
        
        stats_text = (
            f"═══════════════ ESTADÍSTICAS ═══════════════\n\n"
            f"Total Trades:        {results['total_trades']}\n"
            f"Win Rate:            {results['win_rate']*100:.1f}%\n"
            f"Profit Factor:       {results['profit_factor']:.2f}\n\n"
            f"Trades Ganadores:    {results['winning_trades']}\n"
            f"Trades Perdedores:   {results['losing_trades']}\n\n"
            f"Ganancia Promedio:   ${results['avg_win']:.2f}\n"
            f"Pérdida Promedio:    ${results['avg_loss']:.2f}\n\n"
            f"Ganancia Bruta:      ${results['gross_profit']:.2f}\n"
            f"Pérdida Bruta:       ${results['gross_loss']:.2f}\n\n"
            f"Max Drawdown:        {results['max_drawdown']*100:.2f}%"
        )
        ax4.text(0.05, 0.95, stats_text, transform=ax4.transAxes, fontsize=10,
                 verticalalignment='top', fontfamily='monospace',
                 bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        # ========== 5. DISTRIBUCIÓN DE TRADES (derecha) ==========
        ax5 = fig.add_subplot(gs[3, 1])
        
        # Pie chart de tipo de salida
        exit_types = [results['tp_exits'], results['sl_exits'], results['signal_exits']]
        exit_labels = ['Take Profit', 'Stop Loss', 'Signal/Other']
        exit_colors = ['green', 'red', 'orange']
        
        # Filtrar los que tienen valor
        filtered = [(l, v, c) for l, v, c in zip(exit_labels, exit_types, exit_colors) if v > 0]
        if filtered:
            labels, values, colors = zip(*filtered)
            ax5.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax5.set_title(f"Distribución de Salidas\n(Long: {results['long_trades']} | Short: {results['short_trades']})", fontsize=10)
        else:
            ax5.text(0.5, 0.5, 'Sin trades', ha='center', va='center')
        
        # No usar tight_layout - ya usamos constrained_layout=True
        
        # Guardar o mostrar
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"\n📊 Gráfica guardada en: {save_path}")
        
        plt.show()
    
    def print_summary(self, results: Dict[str, Any]):
        """Imprime resumen del backtest."""
        
        if 'error' in results:
            print(f"\n❌ Error: {results['error']}")
            return
        
        print(f"\n{'='*60}")
        print(f"  RESULTADOS DEL BACKTEST")
        print(f"{'='*60}")
        print(f"  Símbolo:           {results['symbol']}")
        print(f"  Timeframe:         {results['timeframe']}")
        print(f"  Período:           {results['start_date'][:10]} → {results['end_date'][:10]}")
        print(f"  Velas analizadas:  {results['data_points']}")
        print(f"{'='*60}")
        print(f"  RENDIMIENTO")
        print(f"  ─────────────────────────────────────────")
        print(f"  Capital inicial:   ${self.initial_capital:,.2f}")
        print(f"  Capital final:     ${results['final_capital']:,.2f}")
        print(f"  PnL Total:         ${results['total_pnl']:,.2f} ({results['return_pct']:+.2f}%)")
        print(f"  Max Drawdown:      {results['max_drawdown']*100:.2f}%")
        print(f"{'='*60}")
        print(f"  TRADES")
        print(f"  ─────────────────────────────────────────")
        print(f"  Total trades:      {results['total_trades']}")
        print(f"  Win Rate:          {results['win_rate']*100:.1f}%")
        print(f"  Profit Factor:     {results['profit_factor']:.2f}")
        print(f"  Ganadores:         {results['winning_trades']}")
        print(f"  Perdedores:        {results['losing_trades']}")
        print(f"  Long/Short:        {results['long_trades']} / {results['short_trades']}")
        print(f"{'='*60}")
        print(f"  SALIDAS")
        print(f"  ─────────────────────────────────────────")
        print(f"  Take Profit:       {results['tp_exits']}")
        print(f"  Stop Loss:         {results['sl_exits']}")
        print(f"  Por señal:         {results['signal_exits']}")
        print(f"{'='*60}\n")


def run_mean_reversion_backtest(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    days: int = 365,
    initial_capital: float = 10000.0,
    strategy_params: Optional[Dict] = None,
    show_plot: bool = True,
    save_plot: bool = True
):
    """
    Función helper para ejecutar backtest de MeanReversionBB.
    
    Args:
        symbol: Símbolo a testear
        timeframe: Timeframe (M5, M15, H1, H4, D1)
        days: Días de histórico (default: 365 = 1 año)
        initial_capital: Capital inicial
        strategy_params: Parámetros personalizados de la estrategia
        show_plot: Mostrar gráficas
        save_plot: Guardar gráficas en archivo
    """
    
    # Crear backtester
    bt = MeanReversionBBBacktester(initial_capital=initial_capital)
    
    # Calcular fechas
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Ejecutar backtest
    results = bt.run_backtest(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        strategy_params=strategy_params,
        verbose=True
    )
    
    # Mostrar resumen
    bt.print_summary(results)
    
    # Generar gráficas
    if show_plot or save_plot:
        save_path = None
        if save_plot:
            save_path = os.path.join(
                current_dir, 
                f"backtest_results_{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
        
        bt.plot_results(results, save_path=save_path)
    
    return results


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  BACKTEST: MeanReversionBBStrategy")
    print("  Broker: RoboForex (via MetaTrader5)")
    print("  Período: Último año")
    print("="*60 + "\n")
    
    # Ejecutar backtest - GBPUSD
    results = run_mean_reversion_backtest(
        symbol="GBPUSD",
        timeframe="H1",
        days=365,
        initial_capital=10000.0,
        show_plot=True,
        save_plot=True
    )
    
    # También puedes probar con parámetros personalizados:
    # results = run_mean_reversion_backtest(
    #     symbol="GBPUSD",
    #     timeframe="M15",
    #     days=365,
    #     strategy_params={
    #         'bb_period': 15,
    #         'bb_std': 2.5,
    #         'use_rsi': True,
    #         'rsi_oversold': 25,
    #         'rsi_overbought': 75,
    #         'risk_percent': 0.5,
    #     },
    #     show_plot=True
    # )
