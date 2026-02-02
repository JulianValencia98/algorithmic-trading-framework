"""
Backtesting Engine Unificado con Datos de Oanda

Este motor de backtesting usa datos históricos de Oanda como fuente principal,
con MetaTrader5 como fallback. Soporta múltiples estrategias.
"""
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Type
from datetime import datetime, timedelta

# Importar strategies disponibles
from strategies.simple_time_strategy import SimpleTimeStrategy
from strategies.strategy_base import StrategyBase

# Importar data manager
from .data_manager import BacktestDataManager, get_backtest_data
from utils.utils import Utils


class UnifiedBacktestingEngine:
    """
    Motor de backtesting unificado que soporta múltiples estrategias
    y usa datos de Oanda como fuente principal.
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        risk_per_trade: float = 0.01,
        commission: float = 0.0001,
        preferred_provider: str = "oanda"
    ):
        """
        Inicializa el motor de backtesting.
        
        Args:
            initial_capital: Capital inicial
            risk_per_trade: Riesgo por trade (no usado si strategy maneja sizing)
            commission: Comisión por trade
            preferred_provider: "oanda" o "mt5"
        """
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.commission = commission
        self.preferred_provider = preferred_provider
    
    def backtest_strategy(
        self,
        strategy_class: Type[StrategyBase],
        symbol: str,
        timeframe: str,
        count: int = 1000,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta backtesting para una estrategia específica.
        
        Args:
            strategy_class: Clase de la estrategia a testear
            symbol: Símbolo del instrumento
            timeframe: Timeframe (M1, M5, H1, etc.)
            count: Número de velas a obtener
            start_date: Fecha inicial (opcional)
            end_date: Fecha final (opcional)
            verbose: Mostrar logs detallados
            
        Returns:
            Dict con resultados del backtesting
        """
        if verbose:
            print(f"{Utils.dateprint()} - [Backtesting] Iniciando test de {strategy_class.__name__}")
            print(f"   Símbolo: {symbol}")
            print(f"   Timeframe: {timeframe}")
            print(f"   Velas: {count}")
            print(f"   Proveedor preferido: {self.preferred_provider}")
        
        # Obtener datos históricos
        data = get_backtest_data(
            symbol=symbol,
            timeframe=timeframe,
            count=count,
            preferred_provider=self.preferred_provider,
            start_date=start_date,
            end_date=end_date
        )
        
        if data is None or data.empty:
            return {
                "error": "No se pudieron obtener datos históricos",
                "symbol": symbol,
                "timeframe": timeframe,
                "strategy": strategy_class.__name__
            }
        
        if verbose:
            print(f"{Utils.dateprint()} - [Backtesting] ✅ Datos obtenidos: {len(data)} velas")
            print(f"   Rango: {data.index[0]} a {data.index[-1]}")
        
        # Ejecutar backtesting
        try:
            results = self.backtest(data, strategy_class, verbose=verbose)
            results.update({
                "symbol": symbol,
                "timeframe": timeframe,
                "strategy": strategy_class.__name__,
                "data_source": self._determine_data_source(),
                "data_period": {
                    "start": str(data.index[0]),
                    "end": str(data.index[-1]),
                    "total_bars": len(data)
                }
            })
            return results
            
        except Exception as e:
            return {
                "error": f"Error en backtesting: {str(e)}",
                "symbol": symbol,
                "timeframe": timeframe,
                "strategy": strategy_class.__name__
            }
    
    def backtest(
        self,
        data: pd.DataFrame,
        strategy_class: Type[StrategyBase],
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Ejecuta el backtesting en los datos proporcionados.
        
        Args:
            data: DataFrame con datos OHLCV
            strategy_class: Clase de estrategia a usar
            verbose: Mostrar logs detallados
            
        Returns:
            Dict con resultados del backtesting
        """
        # Validar datos
        if not isinstance(data, pd.DataFrame) or data.empty:
            raise ValueError("Data debe ser un DataFrame no vacío")
        
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"Data debe contener columnas: {required_columns}")
        
        # Crear instancia de estrategia
        strategy = strategy_class()
        params = strategy.get_parameters()
        
        # Configuración de SL/TP
        sl_tp_mode = params.get("sl_tp_mode", "fixed_pips")
        sl_pips = params.get("sl_pips", 100.0)
        tp_pips = params.get("tp_pips", 300.0)
        pip_size = params.get("pip_size", 0.0001)
        
        # Variables de estado
        capital = self.initial_capital
        position = 0  # 0: sin posición, 1: long, -1: short
        entry_price = 0.0
        position_size = 0.0
        entry_time = None
        sl_price = None
        tp_price = None
        trades = []
        equity_curve = [capital]
        
        if verbose:
            print(f"{Utils.dateprint()} - [Backtesting] Ejecutando con {strategy_class.__name__}")
            print(f"   Capital inicial: ${capital:,.2f}")
            print(f"   SL/TP Mode: {sl_tp_mode}")
        
        # Loop principal de backtesting
        for i in range(len(data)):
            current_bar = data.iloc[i]
            current_time = data.index[i]
            
            # Generar señal
            signal = strategy.generate_signal(data, i)
            
            # Gestión de posiciones abiertas
            if position != 0:
                # Verificar SL/TP
                if sl_tp_mode == "fixed_pips" and sl_price is not None and tp_price is not None:
                    exit_occurred = False
                    
                    if position == 1:  # Long
                        if current_bar['Low'] <= sl_price:
                            # Stop Loss hit
                            exit_price = sl_price
                            exit_reason = 'sl'
                            exit_occurred = True
                        elif current_bar['High'] >= tp_price:
                            # Take Profit hit
                            exit_price = tp_price
                            exit_reason = 'tp'
                            exit_occurred = True
                            
                    elif position == -1:  # Short
                        if current_bar['High'] >= sl_price:
                            # Stop Loss hit
                            exit_price = sl_price
                            exit_reason = 'sl'
                            exit_occurred = True
                        elif current_bar['Low'] <= tp_price:
                            # Take Profit hit
                            exit_price = tp_price
                            exit_reason = 'tp'
                            exit_occurred = True
                    
                    # Procesar salida
                    if exit_occurred:
                        pnl = self._calculate_pnl(position, entry_price, exit_price, position_size)
                        capital += pnl - (position_size * exit_price * self.commission)
                        
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': current_time,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'long' if position == 1 else 'short',
                            'exit_reason': exit_reason,
                            'position_size': position_size
                        })
                        
                        # Reset posición
                        position = 0
                        position_size = 0.0
                        entry_time = None
                        sl_price = None
                        tp_price = None
                        
                        if verbose and len(trades) % 10 == 0:
                            print(f"{Utils.dateprint()} - [Backtesting] Trade #{len(trades)} - PnL: ${pnl:.2f}")
                
                # Verificar si estrategia quiere cerrar antes de abrir nueva posición
                if position != 0 and signal in ['buy', 'sell']:
                    should_close = params.get('close_before_open', True)
                    max_positions = params.get('max_open_positions', 1)
                    
                    if should_close or len([t for t in trades if 'exit_time' not in t or t['exit_time'] is None]) >= max_positions:
                        # Cerrar posición actual
                        exit_price = current_bar['Close']
                        pnl = self._calculate_pnl(position, entry_price, exit_price, position_size)
                        capital += pnl - (position_size * exit_price * self.commission)
                        
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': current_time,
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'long' if position == 1 else 'short',
                            'exit_reason': 'strategy_close',
                            'position_size': position_size
                        })
                        
                        position = 0
                        position_size = 0.0
                        entry_time = None
                        sl_price = None
                        tp_price = None
            
            # Procesar nuevas señales
            if position == 0 and signal in ['buy', 'sell']:
                entry_price = current_bar['Close']
                
                # Calcular tamaño de posición usando la estrategia
                try:
                    position_size = strategy.calculate_position_size(
                        symbol="BACKTESTING",  # Símbolo dummy para BT
                        equity=capital,
                        entry_price=entry_price
                    )
                except Exception as e:
                    # Fallback a cálculo simple
                    position_size = (capital * self.risk_per_trade) / (sl_pips * pip_size)
                
                # Calcular SL/TP usando la estrategia
                try:
                    sl_price, tp_price = strategy.calculate_sl_tp(
                        symbol="BACKTESTING",
                        action=signal,
                        entry_price=entry_price
                    )
                except Exception as e:
                    # Fallback a cálculo simple
                    if signal == 'buy':
                        sl_price = entry_price - (sl_pips * pip_size)
                        tp_price = entry_price + (tp_pips * pip_size)
                    else:  # sell
                        sl_price = entry_price + (sl_pips * pip_size)
                        tp_price = entry_price - (tp_pips * pip_size)
                
                # Abrir posición
                position = 1 if signal == 'buy' else -1
                entry_time = current_time
                
                # Deducir comisión de entrada
                capital -= position_size * entry_price * self.commission
            
            # Actualizar equity curve
            if position != 0:
                # Calcular PnL no realizado
                unrealized_pnl = self._calculate_pnl(position, entry_price, current_bar['Close'], position_size)
                current_equity = capital + unrealized_pnl
            else:
                current_equity = capital
            
            equity_curve.append(current_equity)
        
        # Cerrar posición final si está abierta
        if position != 0:
            exit_price = data.iloc[-1]['Close']
            pnl = self._calculate_pnl(position, entry_price, exit_price, position_size)
            capital += pnl - (position_size * exit_price * self.commission)
            
            trades.append({
                'entry_time': entry_time,
                'exit_time': data.index[-1],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl': pnl,
                'type': 'long' if position == 1 else 'short',
                'exit_reason': 'end_of_data',
                'position_size': position_size
            })
        
        # Calcular métricas
        results = self._calculate_metrics(capital, trades, equity_curve, strategy.get_parameters())
        
        if verbose:
            print(f"{Utils.dateprint()} - [Backtesting] ✅ Completado")
            print(f"   Total trades: {results['total_trades']}")
            print(f"   Win rate: {results['win_rate']:.2%}")
            print(f"   Total PnL: ${results['total_pnl']:.2f}")
            print(f"   Max drawdown: {results['max_drawdown']:.2%}")
        
        return results
    
    def _calculate_pnl(self, position: int, entry_price: float, exit_price: float, position_size: float) -> float:
        """Calcula PnL de una posición."""
        if position == 1:  # Long
            return (exit_price - entry_price) * position_size
        else:  # Short
            return (entry_price - exit_price) * position_size
    
    def _calculate_metrics(self, final_capital: float, trades: List[Dict], equity_curve: List[float], strategy_params: Dict) -> Dict[str, Any]:
        """Calcula métricas de performance."""
        
        total_pnl = final_capital - self.initial_capital
        
        if not trades:
            return {
                'total_pnl': total_pnl,
                'win_rate': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0,
                'final_capital': final_capital,
                'trades': [],
                'equity_curve': equity_curve,
                'strategy_parameters': strategy_params
            }
        
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        win_rate = len(winning_trades) / len(trades)
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        
        return {
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'final_capital': final_capital,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'trades': trades,
            'equity_curve': equity_curve,
            'strategy_parameters': strategy_params,
            'return_percentage': (total_pnl / self.initial_capital) * 100
        }
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calcula drawdown máximo."""
        if len(equity_curve) < 2:
            return 0.0
            
        peak = equity_curve[0]
        max_dd = 0.0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
                
        return max_dd
    
    def _determine_data_source(self) -> str:
        """Determina qué fuente de datos se usó."""
        # Sería ideal que el data manager devolviera esta info
        return self.preferred_provider


def run_strategy_backtest(
    strategy_class: Type[StrategyBase],
    symbol: str = None,
    timeframe: str = None,
    count: int = 1000,
    initial_capital: float = 10000.0,
    risk_per_trade: float = 0.01,
    commission: float = 0.0001,
    preferred_provider: str = "oanda",
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Función helper para ejecutar backtesting de una estrategia.
    
    Args:
        strategy_class: Clase de estrategia a testear
        symbol: Símbolo (si None, usa el de la estrategia)
        timeframe: Timeframe (si None, usa el de la estrategia)
        count: Número de velas
        initial_capital: Capital inicial
        risk_per_trade: Riesgo por trade
        commission: Comisión
        preferred_provider: "oanda" o "mt5"
        verbose: Logs detallados
        
    Returns:
        Dict con resultados del backtesting
    """
    
    # Crear instancia de estrategia para obtener parámetros por defecto
    strategy_instance = strategy_class()
    params = strategy_instance.get_parameters()
    
    # Usar parámetros de la estrategia si no se proporcionan
    final_symbol = symbol or params.get('symbol', 'EURUSD')
    final_timeframe = timeframe or params.get('timeframe', 'H1')
    
    # Crear engine y ejecutar
    engine = UnifiedBacktestingEngine(
        initial_capital=initial_capital,
        risk_per_trade=risk_per_trade,
        commission=commission,
        preferred_provider=preferred_provider
    )
    
    return engine.backtest_strategy(
        strategy_class=strategy_class,
        symbol=final_symbol,
        timeframe=final_timeframe,
        count=count,
        verbose=verbose
    )


if __name__ == "__main__":
    # Test del backtesting con datos de Oanda
    print("=== TEST UNIFIED BACKTESTING ENGINE ===")
    
    # Test SimpleTimeStrategy con datos de Oanda
    results = run_strategy_backtest(
        strategy_class=SimpleTimeStrategy,
        symbol="EURUSD",
        timeframe="H1",
        count=500,
        preferred_provider="oanda",
        verbose=True
    )
    
    # Mostrar resultados
    print(f"\n=== RESULTADOS BACKTESTING ===")
    print(f"Estrategia: {results.get('strategy', 'N/A')}")
    print(f"Símbolo: {results.get('symbol', 'N/A')}")
    print(f"Timeframe: {results.get('timeframe', 'N/A')}")
    print(f"Fuente de datos: {results.get('data_source', 'N/A')}")
    
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
    else:
        print(f"Total PnL: ${results['total_pnl']:.2f} ({results['return_percentage']:.2f}%)")
        print(f"Total trades: {results['total_trades']}")
        print(f"Win rate: {results['win_rate']:.2%}")
        print(f"Profit factor: {results['profit_factor']:.2f}")
        print(f"Max drawdown: {results['max_drawdown']:.2%}")
        print(f"Capital final: ${results['final_capital']:.2f}")
    
    print("\n=== FIN TEST ===")