# Backtesting Package
"""
Sistema de backtesting unificado que soporta múltiples fuentes de datos.

Fuentes de datos disponibles:
- Oanda API v20 (principal)
- MetaTrader5 (fallback)

Características:
- Motor unificado para todas las estrategias
- Failover automático entre proveedores
- Métricas detalladas de performance
- Soporte para configuración por variables de entorno
"""

from .unified_backtest_engine import (
    UnifiedBacktestingEngine,
    run_strategy_backtest
)

from .data_manager import (
    BacktestDataManager,
    get_backtest_data
)

# Importaciones de estrategias específicas - temporalmente comentadas para evitar importaciones circulares
# from .simple_time_strategy_bt import (
#     BacktestingEngine,
#     run_backtest,
#     run_backtest_with_oanda
# )

__all__ = [
    "UnifiedBacktestingEngine",
    "run_strategy_backtest", 
    "BacktestDataManager",
    "get_backtest_data",
    # "BacktestingEngine",
    # "run_backtest", 
    # "run_backtest_with_oanda"
]