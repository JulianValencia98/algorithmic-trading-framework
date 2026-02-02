import pandas as pd
import numpy as np
from typing import Dict, List, Any

from strategies.simple_time_strategy import SimpleTimeStrategy
from .unified_backtest_engine import run_strategy_backtest
from .data_manager import get_backtest_data


class BacktestingEngine:
    """
    Backtesting engine for SimpleTimeStrategy.
    """

    def __init__(self, initial_capital: float = 10000.0, risk_per_trade: float = 0.01, commission: float = 0.0001):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.commission = commission

    def backtest(self, data: pd.DataFrame) -> Dict[str, Any]:
        if not isinstance(data, pd.DataFrame) or data.empty:
            raise ValueError("Data must be a non-empty pandas DataFrame")

        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"Data must contain columns: {required_columns}")

        strategy = SimpleTimeStrategy()
        params = strategy.get_parameters()
        sl_tp_mode = params.get("sl_tp_mode", "fixed_pips")
        sl_pips = params.get("sl_pips", 100.0)
        tp_pips = params.get("tp_pips", 300.0)
        hold_seconds = params.get("hold_seconds", 120)
        pip_size = params.get("pip_size", 0.0001)

        capital = self.initial_capital
        position = 0  # 0: no position, 1: long, -1: short
        entry_price = 0.0
        position_size = 0.0
        entry_time = None
        sl_price = None
        tp_price = None
        trades = []
        equity_curve = [capital]

        for i in range(len(data)):
            current_bar = data.iloc[i]
            signal = strategy.generate_signal(data, i)

            if position != 0:
                # SL/TP check (intrabar)
                if sl_tp_mode == "fixed_pips" and sl_price is not None and tp_price is not None:
                    if position == 1:
                        if current_bar['Low'] <= sl_price:
                            exit_price = sl_price
                            pnl = (exit_price - entry_price) * position_size
                            capital += pnl - (position_size * exit_price * self.commission)
                            trades.append({
                                'entry_time': entry_time,
                                'exit_time': data.index[i],
                                'entry_price': entry_price,
                                'exit_price': exit_price,
                                'pnl': pnl,
                                'type': 'long',
                                'exit_reason': 'sl'
                            })
                            position = 0
                            position_size = 0.0
                            entry_time = None
                            sl_price = None
                            tp_price = None
                        elif current_bar['High'] >= tp_price:
                            exit_price = tp_price
                            pnl = (exit_price - entry_price) * position_size
                            capital += pnl - (position_size * exit_price * self.commission)
                            trades.append({
                                'entry_time': entry_time,
                                'exit_time': data.index[i],
                                'entry_price': entry_price,
                                'exit_price': exit_price,
                                'pnl': pnl,
                                'type': 'long',
                                'exit_reason': 'tp'
                            })
                            position = 0
                            position_size = 0.0
                            entry_time = None
                            sl_price = None
                            tp_price = None
                    elif position == -1:
                        if current_bar['High'] >= sl_price:
                            exit_price = sl_price
                            pnl = (entry_price - exit_price) * position_size
                            capital += pnl - (position_size * exit_price * self.commission)
                            trades.append({
                                'entry_time': entry_time,
                                'exit_time': data.index[i],
                                'entry_price': entry_price,
                                'exit_price': exit_price,
                                'pnl': pnl,
                                'type': 'short',
                                'exit_reason': 'sl'
                            })
                            position = 0
                            position_size = 0.0
                            entry_time = None
                            sl_price = None
                            tp_price = None
                        elif current_bar['Low'] <= tp_price:
                            exit_price = tp_price
                            pnl = (entry_price - exit_price) * position_size
                            capital += pnl - (position_size * exit_price * self.commission)
                            trades.append({
                                'entry_time': entry_time,
                                'exit_time': data.index[i],
                                'entry_price': entry_price,
                                'exit_price': exit_price,
                                'pnl': pnl,
                                'type': 'short',
                                'exit_reason': 'tp'
                            })
                            position = 0
                            position_size = 0.0
                            entry_time = None
                            sl_price = None
                            tp_price = None

                # Time-based close
                if position != 0 and entry_time is not None:
                    time_diff_seconds = (data.index[i] - entry_time).total_seconds() if hasattr(data.index[i], 'to_pydatetime') else 0
                    if time_diff_seconds >= hold_seconds:
                        exit_price = current_bar['Close']
                        pnl = (exit_price - entry_price) * position_size if position == 1 else (entry_price - exit_price) * position_size
                        capital += pnl - (position_size * exit_price * self.commission)
                        trades.append({
                            'entry_time': entry_time,
                            'exit_time': data.index[i],
                            'entry_price': entry_price,
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'type': 'long' if position == 1 else 'short',
                            'exit_reason': 'time'
                        })
                        position = 0
                        position_size = 0.0
                        entry_time = None
                        sl_price = None
                        tp_price = None

            if signal == 'buy' and position == 0:
                entry_price = current_bar['Close']
                position_size = (capital * self.risk_per_trade) / entry_price
                position = 1
                entry_time = data.index[i]
                if sl_tp_mode == "fixed_pips":
                    sl_price = entry_price - (sl_pips * pip_size)
                    tp_price = entry_price + (tp_pips * pip_size)
                capital -= position_size * entry_price * self.commission

            elif signal == 'sell' and position == 1:
                exit_price = current_bar['Close']
                pnl = (exit_price - entry_price) * position_size
                capital += pnl - (position_size * exit_price * self.commission)
                trades.append({
                    'entry_time': data.index[i-1] if i > 0 else data.index[i],
                    'exit_time': data.index[i],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'type': 'long'
                })
                position = 0
                position_size = 0.0

            elif signal == 'sell' and position == 0:
                entry_price = current_bar['Close']
                position_size = (capital * self.risk_per_trade) / entry_price
                position = -1
                entry_time = data.index[i]
                if sl_tp_mode == "fixed_pips":
                    sl_price = entry_price + (sl_pips * pip_size)
                    tp_price = entry_price - (tp_pips * pip_size)
                capital -= position_size * entry_price * self.commission

            elif signal == 'buy' and position == -1:
                exit_price = current_bar['Close']
                pnl = (entry_price - exit_price) * position_size
                capital += pnl - (position_size * exit_price * self.commission)
                trades.append({
                    'entry_time': data.index[i-1] if i > 0 else data.index[i],
                    'exit_time': data.index[i],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'type': 'short',
                    'exit_reason': 'signal'
                })
                position = 0
                position_size = 0.0
                entry_time = None
                sl_price = None
                tp_price = None

            equity_curve.append(capital)

        total_pnl = capital - self.initial_capital
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        profit_factor = sum(t['pnl'] for t in winning_trades) / abs(sum(t['pnl'] for t in losing_trades)) if losing_trades else float('inf')
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
            'final_capital': capital,
            'trades': trades,
            'equity_curve': equity_curve,
            'strategy_parameters': strategy.get_parameters()
        }

    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        peak = equity_curve[0]
        max_dd = 0.0
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        return max_dd


def run_backtest(data: pd.DataFrame, initial_capital: float = 10000.0, risk_per_trade: float = 0.01, commission: float = 0.0001) -> Dict[str, Any]:
    engine = BacktestingEngine(initial_capital=initial_capital, risk_per_trade=risk_per_trade, commission=commission)
    return engine.backtest(data)


def run_backtest_with_oanda(symbol: str = "EURUSD", timeframe: str = "H1", count: int = 1000, 
                            initial_capital: float = 10000.0, risk_per_trade: float = 0.01, 
                            commission: float = 0.0001, verbose: bool = True) -> Dict[str, Any]:
    """
    Ejecuta backtesting usando datos de Oanda como fuente principal.
    
    Args:
        symbol: Símbolo del instrumento
        timeframe: Timeframe (M1, M5, H1, H4, D1)
        count: Número de velas
        initial_capital: Capital inicial
        risk_per_trade: Riesgo por trade
        commission: Comisión por trade
        verbose: Mostrar logs detallados
        
    Returns:
        Dict con resultados del backtesting
    """
    return run_strategy_backtest(
        strategy_class=SimpleTimeStrategy,
        symbol=symbol,
        timeframe=timeframe,
        count=count,
        initial_capital=initial_capital,
        risk_per_trade=risk_per_trade,
        commission=commission,
        preferred_provider="oanda",
        verbose=verbose
    )
