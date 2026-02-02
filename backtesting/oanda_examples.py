"""
Ejemplo de Backtesting con Datos de Oanda

Este script demuestra cómo ejecutar backtesting usando datos históricos
de Oanda como fuente principal, con MetaTrader5 como fallback.
"""
import os
from datetime import datetime, timedelta

# Importar sistema de backtesting unificado
from backtesting import (
    run_strategy_backtest,
    UnifiedBacktestingEngine,
    get_backtest_data
)

# Importar estrategias
from strategies.simple_time_strategy import SimpleTimeStrategy

from utils.utils import Utils


def run_single_backtest_example():
    """Ejemplo de backtesting individual usando datos de Oanda."""
    
    print("=== EJEMPLO: BACKTESTING CON DATOS DE OANDA ===\n")
    
    # Configuración del backtesting
    config = {
        "initial_capital": 10000.0,
        "risk_per_trade": 0.02,
        "commission": 0.0001,
        "count": 1000,
        "preferred_provider": "oanda"
    }
    
    print(f"Configuración:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print()
    
    # Test SimpleTimeStrategy con EURUSD
    print("1. Testing SimpleTimeStrategy con EURUSD H1...")
    results = run_strategy_backtest(
        strategy_class=SimpleTimeStrategy,
        symbol="EURUSD",
        timeframe="H1",
        count=config["count"],
        initial_capital=config["initial_capital"],
        risk_per_trade=config["risk_per_trade"],
        commission=config["commission"],
        preferred_provider=config["preferred_provider"],
        verbose=True
    )
    
    print_results(results, "SimpleTimeStrategy - EURUSD H1")
    
    print("\n=== FIN EJEMPLOS INDIVIDUALES ===")


def run_comparative_backtest():
    """Ejemplo comparando resultados entre Oanda y MT5."""
    
    print("\n=== EJEMPLO: COMPARACIÓN OANDA vs MT5 ===\n")
    
    symbol = "EURUSD"
    timeframe = "H1"
    count = 500
    
    # Test con Oanda
    print("1. Backtesting con datos de Oanda...")
    results_oanda = run_strategy_backtest(
        strategy_class=SimpleTimeStrategy,
        symbol=symbol,
        timeframe=timeframe,
        count=count,
        preferred_provider="oanda",
        verbose=False
    )
    
    # Test con MT5
    print("\n2. Backtesting con datos de MT5...")
    results_mt5 = run_strategy_backtest(
        strategy_class=SimpleTimeStrategy,
        symbol=symbol,
        timeframe=timeframe,
        count=count,
        preferred_provider="mt5",
        verbose=False
    )
    
    # Comparar resultados
    print(f"\n=== COMPARACIÓN DE RESULTADOS ===")
    print(f"Símbolo: {symbol} {timeframe}")
    print(f"{'Métrica':<20} {'Oanda':<15} {'MT5':<15} {'Diferencia':<15}")
    print("-" * 70)
    
    if 'error' not in results_oanda and 'error' not in results_mt5:
        compare_metric("Total PnL", results_oanda.get('total_pnl', 0), results_mt5.get('total_pnl', 0))
        compare_metric("Total Trades", results_oanda.get('total_trades', 0), results_mt5.get('total_trades', 0))
        compare_metric("Win Rate", results_oanda.get('win_rate', 0) * 100, results_mt5.get('win_rate', 0) * 100, is_percentage=True)
        compare_metric("Profit Factor", results_oanda.get('profit_factor', 0), results_mt5.get('profit_factor', 0))
        compare_metric("Max Drawdown", results_oanda.get('max_drawdown', 0) * 100, results_mt5.get('max_drawdown', 0) * 100, is_percentage=True)
    else:
        if 'error' in results_oanda:
            print(f"❌ Error Oanda: {results_oanda['error']}")
        if 'error' in results_mt5:
            print(f"❌ Error MT5: {results_mt5['error']}")


def compare_metric(name, oanda_val, mt5_val, is_percentage=False):
    """Helper para comparar métricas."""
    diff = oanda_val - mt5_val
    suffix = "%" if is_percentage else ""
    
    oanda_str = f"{oanda_val:.2f}{suffix}"
    mt5_str = f"{mt5_val:.2f}{suffix}"
    diff_str = f"{diff:+.2f}{suffix}"
    
    print(f"{name:<20} {oanda_str:<15} {mt5_str:<15} {diff_str:<15}")


def run_data_quality_test():
    """Ejemplo para verificar calidad de datos de diferentes proveedores."""
    
    print("\n=== EJEMPLO: TEST DE CALIDAD DE DATOS ===\n")
    
    symbol = "EURUSD"
    timeframe = "H1"
    count = 100
    
    # Obtener datos de Oanda
    print("1. Obteniendo datos de Oanda...")
    data_oanda = get_backtest_data(
        symbol=symbol,
        timeframe=timeframe,
        count=count,
        preferred_provider="oanda"
    )
    
    # Obtener datos de MT5
    print("2. Obteniendo datos de MT5...")
    data_mt5 = get_backtest_data(
        symbol=symbol,
        timeframe=timeframe,
        count=count,
        preferred_provider="mt5"
    )
    
    # Analizar calidad
    if data_oanda is not None:
        print(f"\n📊 Datos de Oanda:")
        analyze_data_quality(data_oanda, "Oanda")
    else:
        print("\n❌ No se pudieron obtener datos de Oanda")
    
    if data_mt5 is not None:
        print(f"\n📊 Datos de MT5:")
        analyze_data_quality(data_mt5, "MT5")
    else:
        print("\n❌ No se pudieron obtener datos de MT5")


def analyze_data_quality(data, source_name):
    """Analiza la calidad de los datos."""
    print(f"  Fuente: {source_name}")
    print(f"  Total velas: {len(data)}")
    print(f"  Rango fechas: {data.index[0]} a {data.index[-1]}")
    print(f"  Precio promedio: {data['Close'].mean():.5f}")
    print(f"  Volatilidad: {data['Close'].std():.5f}")
    print(f"  Volumen promedio: {data['Volume'].mean():.0f}")
    print(f"  Gaps detectados: {count_gaps(data)}")
    
    # Mostrar últimas 3 velas
    print(f"  Últimas 3 velas:")
    print(data.tail(3)[['Open', 'High', 'Low', 'Close', 'Volume']].to_string(float_format=lambda x: f'{x:.5f}' if x > 1 else f'{x:.5f}'))


def count_gaps(data):
    """Cuenta gaps en los datos (diferencias significativas entre velas)."""
    gaps = 0
    for i in range(1, len(data)):
        prev_close = data.iloc[i-1]['Close']
        curr_open = data.iloc[i]['Open']
        
        # Gap si hay más de 10 pips de diferencia
        if abs(curr_open - prev_close) > 0.001:
            gaps += 1
    
    return gaps


def print_results(results, title):
    """Imprime resultados de backtesting de forma formateada."""
    
    print(f"\n📈 {title}")
    print("=" * (len(title) + 4))
    
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
        return
    
    # Información básica
    if 'data_source' in results:
        print(f"Fuente de datos: {results['data_source'].upper()}")
    
    if 'data_period' in results:
        period = results['data_period']
        print(f"Período: {period['start']} a {period['end']} ({period['total_bars']} velas)")
    
    # Métricas principales
    print(f"\n💰 Resultados Financieros:")
    print(f"  Capital inicial: ${results.get('initial_capital', 'N/A'):,.2f}")
    print(f"  Capital final: ${results.get('final_capital', 0):,.2f}")
    print(f"  Total PnL: ${results.get('total_pnl', 0):,.2f}")
    print(f"  Retorno: {results.get('return_percentage', 0):.2f}%")
    
    print(f"\n📊 Estadísticas de Trading:")
    print(f"  Total trades: {results.get('total_trades', 0)}")
    print(f"  Trades ganadores: {results.get('winning_trades', 0)}")
    print(f"  Trades perdedores: {results.get('losing_trades', 0)}")
    print(f"  Win rate: {results.get('win_rate', 0):.2%}")
    
    print(f"\n🎯 Métricas de Performance:")
    print(f"  Ganancia promedio: ${results.get('avg_win', 0):,.2f}")
    print(f"  Pérdida promedio: ${results.get('avg_loss', 0):,.2f}")
    print(f"  Profit factor: {results.get('profit_factor', 0):.2f}")
    print(f"  Max drawdown: {results.get('max_drawdown', 0):.2%}")
    
    # Últimos trades
    trades = results.get('trades', [])
    if trades:
        print(f"\n🔍 Últimos 3 trades:")
        for i, trade in enumerate(trades[-3:], 1):
            exit_reason = trade.get('exit_reason', 'unknown')
            pnl = trade.get('pnl', 0)
            pnl_emoji = "✅" if pnl > 0 else "❌"
            print(f"  {i}. {trade.get('type', 'N/A')} - PnL: ${pnl:.2f} {pnl_emoji} ({exit_reason})")


if __name__ == "__main__":
    print(f"{Utils.dateprint()} - Iniciando ejemplos de backtesting con Oanda\n")
    
    try:
        # Ejecutar ejemplos
        run_single_backtest_example()
        
        # Solo ejecutar comparación si hay variable de entorno
        if os.getenv('BT_RUN_COMPARISON', 'false').lower() == 'true':
            run_comparative_backtest()
        
        # Test de calidad de datos
        if os.getenv('BT_RUN_DATA_QUALITY', 'false').lower() == 'true':
            run_data_quality_test()
        
        print(f"\n{Utils.dateprint()} - Ejemplos completados ✅")
        print("\nPara ejecutar comparaciones y tests adicionales:")
        print("  set BT_RUN_COMPARISON=true")
        print("  set BT_RUN_DATA_QUALITY=true")
        
    except KeyboardInterrupt:
        print(f"\n{Utils.dateprint()} - Ejemplos interrumpidos por usuario")
        
    except Exception as e:
        print(f"\n{Utils.dateprint()} - Error en ejemplos: {e}")
        import traceback
        traceback.print_exc()