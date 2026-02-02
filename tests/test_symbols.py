"""
Test rápido de conexión MT5 y símbolos

Ejecuta este script para diagnosticar el problema con EURUSD y otros símbolos.
"""
import os
import sys

# Agregar el directorio raíz al path para importaciones
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Easy_Trading import BasicTrading
from utils.utils import Utils

def test_connection():
    """Test básico de conexión y símbolos."""
    print(f"{Utils.dateprint()} - === TEST DE CONEXIÓN MT5 ===\n")
    
    try:
        # Crear instancia
        print("1. Inicializando BasicTrading...")
        bt = BasicTrading()
        print("   ✅ BasicTrading inicializado\n")
        
        # Probar solo el símbolo principal
        test_symbols = ["EURUSD"]
        
        for symbol in test_symbols:
            print(f"2. Probando símbolo: {symbol}")
            
            try:
                # Test is_market_open (que es donde falla)
                market_open = bt.is_market_open(symbol)
                print(f"   ✅ {symbol} - Mercado abierto: {market_open}")
                
            except Exception as e:
                print(f"   ❌ Error con {symbol}: {e}")
            
            print()  # Línea en blanco
        
        print("=== FIN TEST ===")
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
        print("\n🔧 Posibles soluciones:")
        print("1. Verifica que MetaTrader5 esté abierto y conectado")
        print("2. Revisa las credenciales en .env")
        print("3. Activa 'Allow algorithmic trading' en MT5")

if __name__ == "__main__":
    test_connection()