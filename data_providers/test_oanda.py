"""
Test de conexión y funcionalidad de Oanda Provider
"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_providers.oanda_provider import OandaProvider
from data_providers.interfaces.data_provider_interface import TimeFrame
from dotenv import load_dotenv

def test_oanda_connection():
    """Prueba la conexión con Oanda API."""
    load_dotenv()
    
    print("=== TEST OANDA PROVIDER ===\n")
    
    # Crear instancia
    oanda = OandaProvider()
    
    # Test de conexión detallado
    print("1. Probando conexión...")
    connection_info = oanda.test_connection()
    
    for key, value in connection_info.items():
        print(f"   {key}: {value}")
    
    if not connection_info.get("success"):
        print("\n❌ Error de conexión - Verifica credenciales en .env")
        print("\nVariables requeridas en .env:")
        print("OANDA_ACCOUNT_ID=tu_account_id")
        print("OANDA_API_TOKEN=tu_api_token")
        print("OANDA_ENVIRONMENT=practice  # o 'trade'")
        return False
    
    print("\n✅ Conexión exitosa")
    
    # Conectar para pruebas siguientes
    if not oanda.connect():
        print("❌ No se pudo establecer conexión")
        return False
    
    # Test 2: Obtener instrumentos disponibles
    print("\n2. Obteniendo instrumentos disponibles...")
    symbols = oanda.get_available_symbols()
    print(f"   Total instrumentos: {len(symbols)}")
    if symbols:
        print(f"   Primeros 10: {symbols[:10]}")
    
    # Test 3: Información de instrumento
    print("\n3. Información de EURUSD...")
    info = oanda.get_symbol_info("EURUSD")
    if info:
        for key, value in info.items():
            print(f"   {key}: {value}")
    else:
        print("   ❌ No se pudo obtener información")
    
    # Test 4: Precio actual
    print("\n4. Precio actual de EURUSD...")
    price = oanda.get_current_price("EURUSD")
    if price:
        print(f"   Bid: {price['bid']:.5f}")
        print(f"   Ask: {price['ask']:.5f}")
        print(f"   Price: {price['price']:.5f}")
    else:
        print("   ❌ No se pudo obtener precio")
    
    # Test 5: Datos históricos
    print("\n5. Datos históricos EURUSD H1 (últimas 10 velas)...")
    market_data = oanda.get_historical_data("EURUSD", TimeFrame.H1, count=10)
    
    if market_data and market_data.data is not None:
        df = market_data.data
        print(f"   Velas obtenidas: {len(df)}")
        print(f"   Rango de fechas: {df.index[0]} a {df.index[-1]}")
        print(f"   Último Close: {df['Close'].iloc[-1]:.5f}")
        print("\n   Últimas 3 velas:")
        print(df.tail(3)[['Open', 'High', 'Low', 'Close', 'Volume']].to_string())
    else:
        print("   ❌ No se pudieron obtener datos históricos")
    
    # Test 6: Estado del mercado
    print("\n6. Estado del mercado EURUSD...")
    market_open = oanda.is_market_open("EURUSD")
    print(f"   Mercado abierto: {market_open}")
    
    # Desconectar
    oanda.disconnect()
    print("\n7. Desconectado de Oanda")
    
    print("\n=== FIN TEST ===")
    return True

if __name__ == "__main__":
    try:
        test_oanda_connection()
    except KeyboardInterrupt:
        print("\n\nTest interrumpido por usuario")
    except Exception as e:
        print(f"\n❌ Error en test: {e}")
        import traceback
        traceback.print_exc()