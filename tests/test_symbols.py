"""
Test dinámico de conexión MT5 y símbolos utilizados por las estrategias

Este test detecta automáticamente todas las estrategias disponibles
y verifica los símbolos que cada una utiliza.
"""
import os
import sys

# Agregar el directorio raíz al path para importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Easy_Trading import BasicTrading
from utils.utils import Utils
from utils.strategy_discovery import StrategyDiscovery

def test_connection():
    """Test dinámico de conexión y símbolos basado en estrategias existentes."""
    print(f"{Utils.dateprint()} - === TEST DINÁMICO DE CONEXIÓN MT5 ===\n")
    
    try:
        # Crear instancia
        print("1. Inicializando BasicTrading...")
        bt = BasicTrading()
        print("   ✅ BasicTrading inicializado\n")
        
        # Descubrir estrategias y símbolos automáticamente
        print("2. Descubriendo estrategias disponibles...")
        strategies = StrategyDiscovery.get_all_strategies()
        strategy_symbols = StrategyDiscovery.get_strategy_symbols()
        unique_symbols = StrategyDiscovery.get_all_unique_symbols()
        
        print(f"   📊 Estrategias encontradas: {len(strategies)}")
        print(f"   🎯 Símbolos únicos a probar: {len(unique_symbols)}")
        print(f"   📋 Lista de símbolos: {', '.join(unique_symbols)}\n")
        
        # Test de cada símbolo
        print("3. Probando símbolos de las estrategias:")
        symbol_results = {}
        
        for symbol in unique_symbols:
            print(f"   🔍 Probando símbolo: {symbol}")
            
            try:
                # Test is_market_open (que es donde falla)
                market_open = bt.is_market_open(symbol)
                symbol_results[symbol] = {'status': 'OK', 'market_open': market_open}
                print(f"      ✅ {symbol} - Mercado abierto: {market_open}")
                
            except Exception as e:
                symbol_results[symbol] = {'status': 'ERROR', 'error': str(e)}
                print(f"      ❌ Error con {symbol}: {e}")
        
        print("\n4. Detalles por estrategia:")
        for strategy_name, symbols in strategy_symbols.items():
            print(f"   📈 {strategy_name}:")
            for symbol in symbols:
                result = symbol_results.get(symbol, {})
                status = "✅" if result.get('status') == 'OK' else "❌"
                print(f"      {status} {symbol} - {result.get('status', 'UNKNOWN')}")
        
        # Resumen final
        successful_symbols = [s for s, r in symbol_results.items() if r.get('status') == 'OK']
        failed_symbols = [s for s, r in symbol_results.items() if r.get('status') == 'ERROR']
        
        print(f"\n=== RESUMEN ===")
        print(f"✅ Símbolos OK: {len(successful_symbols)}/{len(unique_symbols)}")
        print(f"❌ Símbolos con error: {len(failed_symbols)}")
        
        if failed_symbols:
            print(f"\n🔧 Símbolos que necesitan revisión: {', '.join(failed_symbols)}")
        
        print("=== FIN TEST ===")
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        print("\n🔧 Posibles soluciones:")
        print("1. Verifica que MetaTrader5 esté abierto y conectado")
        print("2. Revisa las credenciales en .env")
        print("3. Activa 'Allow algorithmic trading' en MT5")
        print("4. Verifica que las estrategias tengan símbolos válidos configurados")

def test_strategy_discovery():
    """Test específico del sistema de descubrimiento de estrategias."""
    print(f"\n{Utils.dateprint()} - === TEST DE DESCUBRIMIENTO DE ESTRATEGIAS ===\n")
    
    try:
        StrategyDiscovery.print_strategy_info()
        print("✅ Descubrimiento de estrategias funcionando correctamente")
        
    except Exception as e:
        print(f"❌ Error en descubrimiento de estrategias: {e}")

if __name__ == "__main__":
    # Ejecutar ambos tests
    test_strategy_discovery()
    test_connection()
    test_connection()