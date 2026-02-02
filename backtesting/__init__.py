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

# Importaciones de estrategias específicas
from .simple_time_strategy_bt import (
    BacktestingEngine,
    run_backtest,
    run_backtest_with_oanda
)

try:
    from .simple_time_strategy_xau_bt import (
        run_backtest_from_mt5 as run_xau_backtest_from_mt5,
        run_backtest_with_oanda as run_xau_backtest_with_oanda
    )
except ImportError:
    run_xau_backtest_from_mt5 = None
    run_xau_backtest_with_oanda = None

try:
    from .simple_time_strategy_gbp_bt import (
        run_backtest_from_mt5 as run_gbp_backtest_from_mt5,
        run_backtest_with_oanda as run_gbp_backtest_with_oanda
    )
except ImportError:
    run_gbp_backtest_from_mt5 = None
    run_gbp_backtest_with_oanda = None

__all__ = [
    "UnifiedBacktestingEngine",
    "run_strategy_backtest", 
    "BacktestDataManager",
    "get_backtest_data",
    "BacktestingEngine",
    "run_backtest",
    "run_backtest_with_oanda",
    "run_xau_backtest_from_mt5",
    "run_xau_backtest_with_oanda",
    "run_gbp_backtest_from_mt5", 
    "run_gbp_backtest_with_oanda"
]