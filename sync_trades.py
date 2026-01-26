"""
Script para sincronizar trades con MT5 sin ejecutar la app completa.
Uso: python sync_trades.py
"""
import MetaTrader5 as mt5
from data.repositories.trade_repository import TradeRepository
from data.trade_sync_service import TradeSyncService
from utils.utils import Utils


def main():
    # Inicializar MT5
    if not mt5.initialize():
        print("Error: No se pudo inicializar MT5")
        return
    
    print(f"{Utils.dateprint()} - MT5 inicializado")
    
    # Obtener account ID
    account_info = mt5.account_info()
    if not account_info:
        print("Error: No se pudo obtener info de cuenta")
        mt5.shutdown()
        return
    
    account_id = account_info.login
    print(f"{Utils.dateprint()} - Cuenta: {account_id}")
    
    # Crear repositorio y sync service
    repository = TradeRepository(account_id=account_id)
    sync_service = TradeSyncService(
        repository=repository,
        sync_interval_minutes=10,
        history_days=7
    )
    
    # Ejecutar sincronización
    print(f"{Utils.dateprint()} - Iniciando sincronización...")
    sync_service.sync_now()
    
    # Cerrar MT5
    mt5.shutdown()
    print(f"{Utils.dateprint()} - Completado")


if __name__ == "__main__":
    main()
