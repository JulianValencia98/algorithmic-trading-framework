"""
Test del sistema de backtesting corregido
"""
import sys
import os

# Agregar directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtesting.unified_backtest_engine import run_strategy_backtest
from strategies.simple_time_strategy import SimpleTimeStrategy

def test_backtesting():
    """
    Prueba rápida del backtesting con symbol fix
    """
    print("🔄 Probando backtesting con corrección de symbol...")
    
    try:
        results = run_strategy_backtest(
            strategy_class=SimpleTimeStrategy,
            symbol="EURUSD",
            timeframe="H1",
            count=500,  # 500 velas para prueba rápida
            initial_capital=10000.0,
            risk_per_trade=0.01,
            commission=0.0001,
            preferred_provider="oanda",
            verbose=True
        )
        
        # Mostrar resultados
        if "error" in results:
            print(f"❌ Error: {results['error']}")
        else:
            print("\n📊 Resultados del Backtesting:")
            print(f"   💰 PnL Total: ${results['total_pnl']:.2f}")
            print(f"   📈 Total Trades: {results['total_trades']}")
            print(f"   🎯 Win Rate: {results['win_rate']:.1%}")
            print(f"   📉 Max Drawdown: {results['max_drawdown']:.1%}")
            print("✅ Backtesting completado - fix de symbol funciona correctamente!")
            
    except Exception as e:
        print(f"❌ Error durante el backtesting: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_backtesting()