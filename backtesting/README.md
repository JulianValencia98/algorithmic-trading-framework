# Sistema de Backtesting con Datos de Oanda

El framework ahora soporta **datos históricos de Oanda** como fuente principal para backtesting, con MetaTrader5 como fallback automático. Esto proporciona datos de mayor calidad y confiabilidad para el análisis de estrategias.

## 🚀 Características Principales

### ✅ **Múltiples Fuentes de Datos**
- **Oanda API v20** (principal) - Datos históricos de alta calidad
- **MetaTrader5** (fallback) - Respaldo si Oanda no está disponible
- **Failover automático** entre proveedores

### ✅ **Motor Unificado**
- **Un solo engine** para todas las estrategias
- **Compatibilidad total** con estrategias existentes
- **Métricas detalladas** de performance

### ✅ **Configuración Flexible**
- Variables de entorno para control
- Soporte para diferentes timeframes
- Configuración por estrategia

## 📁 Estructura del Sistema

```
backtesting/
├── unified_backtest_engine.py    # Motor principal unificado
├── data_manager.py               # Gestor de múltiples fuentes de datos
├── oanda_examples.py            # Ejemplos de uso
├── simple_time_strategy_bt.py   # ✅ Actualizado para Oanda
├── simple_time_strategy_xau_bt.py # ✅ Actualizado para Oanda
├── simple_time_strategy_gbp_bt.py # ✅ Actualizado para Oanda
└── __init__.py                  # Exportaciones unificadas
```

## 🔧 Configuración Requerida

### 1. **Variables de Entorno (.env)**

```env
# Credenciales Oanda (para backtesting)
OANDA_ACCOUNT_ID=your_account_id
OANDA_API_TOKEN=your_api_token
OANDA_ENVIRONMENT=practice

# Configuración de Backtesting (opcional)
BT_USE_OANDA=true                # true=Oanda, false=MT5
BT_SYMBOL=EURUSD                # Símbolo por defecto
BT_TIMEFRAME=H1                 # Timeframe por defecto
BT_COUNT=1000                   # Número de velas
BT_INITIAL_CAPITAL=10000        # Capital inicial
BT_RISK_PER_TRADE=0.01          # Riesgo por trade
BT_COMMISSION=0.0001            # Comisión
```

### 2. **Dependencias**

```bash
pip install requests==2.32.3
```

## 📊 Uso del Sistema

### **Método 1: Motor Unificado (Recomendado)**

```python
from backtesting import run_strategy_backtest
from strategies.simple_time_strategy import SimpleTimeStrategy

# Backtesting con datos de Oanda
results = run_strategy_backtest(
    strategy_class=SimpleTimeStrategy,
    symbol="EURUSD",
    timeframe="H1", 
    count=1000,
    preferred_provider="oanda",  # o "mt5"
    verbose=True
)

print(f"Total PnL: ${results['total_pnl']:.2f}")
print(f"Win Rate: {results['win_rate']:.2%}")
```

### **Método 2: Funciones Específicas**

```python
from backtesting import run_backtest_with_oanda

# Específico para SimpleTimeStrategy
results = run_backtest_with_oanda(
    symbol="EURUSD",
    timeframe="H1",
    count=1000,
    verbose=True
)
```

### **Método 3: Archivos Individuales**

```bash
# EURUSD con datos de Oanda
python backtesting/simple_time_strategy_bt.py

# XAUUSD con datos de Oanda
python backtesting/simple_time_strategy_xau_bt.py

# GBPUSD con datos de Oanda  
python backtesting/simple_time_strategy_gbp_bt.py
```

## 🎯 Ejemplos Prácticos

### **Ejemplo 1: Backtesting Simple**

```python
from backtesting.oanda_examples import run_single_backtest_example

# Ejecuta ejemplos con múltiples estrategias
run_single_backtest_example()
```

### **Ejemplo 2: Comparación de Fuentes**

```python
import os
os.environ['BT_RUN_COMPARISON'] = 'true'

from backtesting.oanda_examples import run_comparative_backtest

# Compara resultados entre Oanda y MT5
run_comparative_backtest()
```

### **Ejemplo 3: Análisis de Calidad**

```python
from backtesting import get_backtest_data

# Obtener datos de Oanda
data = get_backtest_data(
    symbol="EURUSD",
    timeframe="H1", 
    count=500,
    preferred_provider="oanda"
)

print(f"Datos obtenidos: {len(data)} velas")
print(f"Rango: {data.index[0]} a {data.index[-1]}")
```

## ⚙️ Configuración Avanzada

### **Variables de Control**

```bash
# Usar solo Oanda (por defecto)
set BT_USE_OANDA=true

# Usar solo MT5 (fallback)
set BT_USE_OANDA=false

# Ejecutar comparaciones
set BT_RUN_COMPARISON=true

# Test de calidad de datos
set BT_RUN_DATA_QUALITY=true
```

### **Configuración por Estrategia**

```python
# La estrategia define sus propios parámetros
class MyStrategy(StrategyBase):
    def get_parameters(self):
        return {
            'symbol': 'GBPUSD',       # Símbolo preferido
            'timeframe': 'M15',       # Timeframe preferido
            'sl_pips': 50,           # Stop Loss en pips
            'tp_pips': 150,          # Take Profit en pips
            # ... otros parámetros
        }
```

## 📈 Métricas Disponibles

El sistema proporciona métricas detalladas:

```python
results = {
    'total_pnl': 1250.50,           # PnL total
    'win_rate': 0.65,               # Tasa de acierto (65%)
    'total_trades': 45,             # Total de trades
    'winning_trades': 29,           # Trades ganadores
    'losing_trades': 16,            # Trades perdedores
    'avg_win': 85.30,               # Ganancia promedio
    'avg_loss': -42.15,             # Pérdida promedio
    'profit_factor': 2.15,          # Factor de beneficio
    'max_drawdown': 0.08,           # Drawdown máximo (8%)
    'final_capital': 11250.50,      # Capital final
    'return_percentage': 12.50,     # Retorno porcentual
    'data_source': 'oanda',         # Fuente de datos usada
    'trades': [...],                # Lista completa de trades
    'equity_curve': [...]           # Curva de equity
}
```

## 🔍 Diagnóstico y Troubleshooting

### **Verificar Conexión a Oanda**

```python
from data_providers.test_oanda import test_oanda_connection

# Test completo de conexión
test_oanda_connection()
```

### **Verificar Estado de Proveedores**

```python
from backtesting import BacktestDataManager

manager = BacktestDataManager()
status = manager.get_provider_status()
print(status)  # {"oanda": True, "mt5": True, "preferred": "oanda"}
```

### **Logs Detallados**

```python
# Activar verbose para ver logs detallados
results = run_strategy_backtest(
    strategy_class=MyStrategy,
    verbose=True  # ← Muestra logs paso a paso
)
```

## 🚨 Errores Comunes

### **1. Credenciales Oanda**
```
❌ Error: API token o account ID no configurados
✅ Solución: Configurar OANDA_ACCOUNT_ID y OANDA_API_TOKEN en .env
```

### **2. Sin Datos Históricos**
```
❌ Error: No se pudieron obtener datos históricos  
✅ Solución: Verificar símbolo y timeframe, revisar conexión a internet
```

### **3. MT5 No Disponible**
```
❌ Error: MetaTrader5 no está disponible
✅ Solución: Instalar MT5 o usar solo Oanda (BT_USE_OANDA=true)
```

## 🔄 Migración desde Sistema Anterior

### **Antes (solo MT5):**
```python
from backtesting.simple_time_strategy_bt import run_backtest_from_mt5

results = run_backtest_from_mt5("EURUSD", "H1", 1000)
```

### **Ahora (Oanda + MT5 fallback):**
```python
from backtesting import run_strategy_backtest

results = run_strategy_backtest(
    strategy_class=SimpleTimeStrategy,
    symbol="EURUSD",
    timeframe="H1",
    count=1000,
    preferred_provider="oanda"  # ← Nuevo parámetro
)
```

## 📝 Notas de Desarrollo

### **Límites de Oanda**
- **Máximo 5000 velas** por request
- **Rate limiting**: 100ms entre requests
- **Entornos**: `practice` y `trade`

### **Compatibilidad**
- ✅ **Todas las estrategias existentes** funcionan sin cambios
- ✅ **Resultados idénticos** con mismo motor de backtesting
- ✅ **Failover automático** si Oanda no está disponible

### **Extensibilidad**
- Fácil agregar **nuevos proveedores** (IEX, Alpha Vantage, etc.)
- **Interface común** para todos los proveedores
- **Configuración centralizada** por priority

## 🎉 Beneficios vs Sistema Anterior

| Característica | Anterior | Nuevo |
|---|---|---|
| **Fuentes de datos** | Solo MT5 | Oanda + MT5 fallback |
| **Calidad de datos** | Dependiente del broker | Datos de Oanda de alta calidad |
| **Disponibilidad** | Requiere MT5 corriendo | Funciona sin MT5 |
| **Configuración** | Manual por archivo | Unificada y flexible |
| **Failover** | No | Automático entre proveedores |
| **APIs** | Una interface | Múltiples interfaces |

El nuevo sistema mantiene **100% compatibilidad** con el anterior mientras agrega capacidades avanzadas para backtesting más confiable y profesional.