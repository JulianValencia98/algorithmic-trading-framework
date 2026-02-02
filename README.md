# Framework Trading Alg (Simplificado)

Framework de trading algorítmico simplificado, orientado a ejecución en vivo con MetaTrader 5. El núcleo es `BasicTrading` en Easy_Trading.py y se complementa con un sistema multi-bot (`AppDirector`) y estrategias autónomas.

## Arquitectura: Estrategia Autónoma

**El framework solo orquesta, la estrategia decide TODO:**
- ✅ Señales de trading (buy/sell/hold)
- ✅ Tamaño de posición (lots)
- ✅ Stop Loss y Take Profit
- ✅ Gestión de posiciones (cerrar antes de abrir o permitir múltiples)

## Características
- Conexión y gestión de cuenta MT5 (`BasicTrading`) con reconexión automática.
- **Ejecución multi-bot concurrente** con `AppDirector` (múltiples estrategias simultáneas).
- **Control pausa/reanudación estilo semáforo** mediante CLI (pause, resume, status).
- **🆕 Sistema de pausa global inteligente**: Cuando todos los bots están pausados, el sistema automáticamente pausa el envío/pedido de toda la información (eventos, notificaciones, logging).
- **Threading independiente** para cada bot con eventos de control.
- **Magic numbers por estrategia**: Cada estrategia tiene su propio magic number único.
- **Nombres de bots automáticos** (formato: StrategyName_Symbol_Timeframe).
- **Gestión de posiciones configurable por estrategia**.
- **Health checks y reconexión MT5** con límite de errores por bot.
- **Verificación automática de mercado abierto**.
- Órdenes de mercado (buy/sell con SL/TP).
- **Dashboard web con Streamlit** para monitoreo de cuenta y posiciones.
- Notificaciones integrables (Telegram).

## Requisitos
- Windows con MetaTrader 5 instalado y accesible.
- Python 3.10+ recomendado.
- Dependencias del proyecto: ver [requirements.txt](requirements.txt).

## Instalación
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuración (.env)
Coloca un archivo `.env` en la raíz del proyecto con tus credenciales MT5.

```ini
MT5_PATH=C:\\Program Files\\MetaTrader 5\\terminal64.exe
MT5_LOGIN=12345678
MT5_PASSWORD=tu_password
MT5_SERVER=TuBroker-Server
MT5_TIMEOUT=60000
```

Notas:
- Asegúrate de que el `MT5_PATH` apunte al ejecutable correcto.
- Usa una cuenta demo para pruebas; el framework detecta el modo demo.

## Estructura principal
- Núcleo MT5: [Easy_Trading.py](Easy_Trading.py) - Conexión, operaciones, reconexión automática
- App principal multi-bot: [simple_trading_app.py](simple_trading_app.py) - Aplicación con CLI interactivo
- Directores:
  - [trading_director/app_director.py](trading_director/app_director.py) - Orquestador multi-bot con threading
  - [trading_director/simple_trading_director.py](trading_director/simple_trading_director.py) - Director para bot individual
- Dashboard web: [streamlit_app.py](streamlit_app.py) - Monitoreo de cuenta y posiciones
- Estrategias: [strategies/](strategies) - Estrategias autónomas con magic numbers únicos
- Backtesting: scripts en [backtesting/](backtesting)
- Notificaciones: [notifications/](notifications) - Sistema de alertas Telegram
- **🆕 Estado Global**: [utils/global_state.py](utils/global_state.py) - Gestión de pausa global del sistema
- Utilidades: [utils/](utils) - Helpers varios

### Conexión y prueba de cuenta
```powershell
python tests/test_connect.py
```

### Ejecución multi-bot en vivo (recomendado)
```powershell
python simple_trading_app.py
```

La aplicación iniciará con 3 bots por defecto (SimpleTime_EURUSD_M1, SimpleTimeGBP_GBPUSD_M1 y SimpleTimeXAU_XAUUSD_M1) y mostrará una interfaz interactiva con comandos:

**Comandos disponibles:**
- `status` - Muestra el estado de todos los bots con iconos
- `pause` - Pausa un bot específico (muestra menú numerado)
- `resume` - Reanuda un bot pausado (muestra menú numerado)
- `help` - Muestra la ayuda
- `exit` - Detiene todos los bots y sale

**Estados de bot:**
- ▶️ `running` - Bot ejecutando estrategia activamente
- 🕐 `waiting_market` - Bot esperando apertura del mercado
- ⏸️ `paused` - Bot pausado manualmente por el usuario
- ⏹️ `stopped` - Bot detenido completamente

**Ejemplo de sesión:**
```
23/01/2026 08:33:08.574 > status
Bot: SimpleTime_EURUSD_M1 - Estado: running ▶️ - Magic: 1
Bot: SimpleTimeGBP_GBPUSD_M1 - Estado: running ▶️ - Magic: 2
Bot: SimpleTimeXAU_XAUUSD_M1 - Estado: running ▶️ - Magic: 3

23/01/2026 08:34:10.123 > pause
Bots disponibles para pausar:
1. SimpleTime_EURUSD_M1
2. SimpleTimeGBP_GBPUSD_M1
3. SimpleTimeXAU_XAUUSD_M1
Selecciona el número del bot (0 para cancelar): 1
Bot 'SimpleTime_EURUSD_M1' pausado.

23/01/2026 08:35:20.456 > status
Bot: SimpleTime_EURUSD_M1 - Estado: paused ⏸️ - Magic: 1
Bot: SimpleTimeGBP_GBPUSD_M1 - Estado: running ▶️ - Magic: 2
Bot: SimpleTimeXAU_XAUUSD_M1 - Estado: running ▶️ - Magic: 3

23/01/2026 08:36:30.789 > resume
Bots pausados:
1. SimpleTime_EURUSD_M1
Selecciona el número del bot (0 para cancelar): 1
Bot 'SimpleTime_EURUSD_M1' reanudado.
```
## Arquitectura Multi-Bot

El framework utiliza `AppDirector` para gestionar múltiples bots de trading simultáneamente con sistema de pausa/reanudación estilo semáforo:

- **Threading independiente**: Cada bot corre en su propio thread sin afectar a los demás
- **Control pausa/reanudación**: Pausa/reanuda bots sin detenerlos completamente (pause_event.wait())
- **Thread-safe**: Operaciones protegidas con locks para concurrencia segura
- **BotConfig**: Auto-genera bot_id basado en estrategia, símbolo y timeframe
- **Magic numbers por estrategia**: Cada estrategia tiene su magic number único y fijo
- **Gestión automática de posiciones**: Cierra posiciones existentes antes de abrir nuevas (por magic number)
- **Health checks**: Verifica conexión MT5 y reconecta automáticamente si falla
- **Verificación de mercado**: Al agregar bot muestra si mercado está abierto/cerrado; en ejecución espera automáticamente si está cerrado
- **Estados de bot**: running (▶️), waiting_market (🕐), paused (⏸️), stopped (⏹️)

**Ejemplo programático:**
```python
from Easy_Trading import BasicTrading
from trading_director.app_director import AppDirector, BotConfig
from strategies.simple_time_strategy import SimpleTimeStrategy
from strategies.simple_time_strategy_gbp import SimpleTimeStrategyGBP
from strategies.simple_time_strategy_xau import SimpleTimeStrategyXAU
import MetaTrader5 as mt5

bt = BasicTrading()
app_director = AppDirector(bt)

# Agregar múltiples bots (auto-genera bot_id, usa magic_number de estrategia)
bot1 = BotConfig(SimpleTimeStrategy(), "EURUSD", mt5.TIMEFRAME_M1, 60)
bot2 = BotConfig(SimpleTimeStrategyGBP(), "GBPUSD", mt5.TIMEFRAME_M1, 60)
bot3 = BotConfig(SimpleTimeStrategyXAU(), "XAUUSD", mt5.TIMEFRAME_M1, 60)

app_director.add_bot(bot1)  # bot_id: SimpleTime_EURUSD_M1, magic: 1
app_director.add_bot(bot2)  # bot_id: SimpleTimeGBP_GBPUSD_M1, magic: 2
app_director.add_bot(bot3)  # bot_id: SimpleTimeXAU_XAUUSD_M1, magic: 3

# Control programático
app_director.pause_bot("SimpleTime_EURUSD_M1")  # Pausa el bot
app_director.resume_bot("SimpleTime_EURUSD_M1")  # Reanuda el bot
status = app_director.get_all_bots_status()
app_director.stop_all_bots()
bt.shutdown()
```

## 🆕 Sistema de Pausa Global

El framework incluye un **sistema inteligente de pausa global** que automáticamente gestiona el flujo de información cuando todos los bots están pausados:

### Funcionamiento Automático
- **Cuando TODOS los bots están pausados**: El sistema automáticamente pausa:
  - ❌ Eventos (señales, apertura/cierre de trades)
  - ❌ Notificaciones (Telegram, etc.)
  - ❌ Logging de trades y señales
  - ❌ Cualquier envío/pedido de información

- **Cuando AL MENOS UN bot está activo**: El sistema automáticamente reanuda:
  - ✅ Todos los eventos
  - ✅ Todas las notificaciones  
  - ✅ Todo el logging
  - ✅ Flujo normal de información

### Beneficios
- **Ahorro de recursos**: No se envían eventos innecesarios cuando no hay actividad
- **Control de ruido**: Las notificaciones se pausan automáticamente
- **Gestión inteligente**: El sistema detecta automáticamente el estado global
- **Thread-safe**: Implementación segura para entornos concurrentes

### Ejemplo de uso
```python
# Pausar todos los bots → Sistema se pausa globalmente
app_director.pause_bot("SimpleTime_EURUSD_M1")
app_director.pause_bot("SimpleTimeGBP_GBPUSD_M1")  
app_director.pause_bot("SimpleTimeXAU_XAUUSD_M1")
# → Automáticamente: Sin eventos, notificaciones ni logging

# Reanudar un bot → Sistema se reanuda globalmente
app_director.resume_bot("SimpleTime_EURUSD_M1")
# → Automáticamente: Vuelven todos los eventos, notificaciones y logging
```

### Verificación programática
```python
# Verificar si el sistema está pausado globalmente
if app_director.is_globally_paused():
    print("Sistema en pausa global - Sin actividad de información")
else:
    print("Sistema activo - Flujo normal de información")
```

## Flujo de Ejecución

```
┌─────────────────────────────────────────────────────┐
│  1. extract_data() - Obtener datos del mercado      │
│  2. strategy.generate_signal() → 'buy'/'sell'       │
│  3. Verificar mercado abierto                       │
│  4. strategy.should_close_before_open()?            │
│     └── Sí: cerrar posiciones existentes            │
│     └── No: verificar max_open_positions            │
│  5. strategy.calculate_position_size() → lotes     │
│  6. strategy.calculate_sl_tp() → (sl, tp)          │
│  7. basic_trading.buy/sell() - Ejecutar orden       │
└─────────────────────────────────────────────────────┘
```

## Crear Nueva Estrategia

Cada estrategia es **completamente autónoma**. Debe implementar 4 métodos:

```python
from strategies.strategy_base import StrategyBase
from typing import Tuple, Optional

class MiEstrategia(StrategyBase):
    def __init__(self):
        super().__init__()
        self.magic_number = 99  # Número único para esta estrategia
        
        # Tus parámetros de riesgo
        self.fixed_lot = 0.05
        self.sl_pips = 50.0
        self.tp_pips = 100.0
    
    def generate_signal(self, data, current_index: int) -> str:
        """Genera señal de trading."""
        # Tu lógica aquí
        return 'buy'  # o 'sell' o 'hold'
    
    def get_parameters(self) -> dict:
        """Configuración de gestión de posiciones."""
        return {
            'close_before_open': True,   # Cerrar existentes antes de abrir
            'max_open_positions': 1,      # Máximo de posiciones simultáneas
        }
    
    def calculate_position_size(self, symbol: str, equity: float, entry_price: float) -> float:
        """Calcula el tamaño de la posición."""
        return self.fixed_lot  # O tu lógica (Kelly, % riesgo, etc.)
    
    def calculate_sl_tp(self, symbol: str, action: str, entry_price: float) -> Tuple[Optional[float], Optional[float]]:
        """Calcula Stop Loss y Take Profit."""
        pip_size = self.get_pip_size(symbol)
        
        if action == 'buy':
            sl = entry_price - (self.sl_pips * pip_size)
            tp = entry_price + (self.tp_pips * pip_size)
        else:
            sl = entry_price + (self.sl_pips * pip_size)
            tp = entry_price - (self.tp_pips * pip_size)
        
        return sl, tp
```

### Métodos Helper disponibles en StrategyBase:

```python
self.get_pip_size(symbol)        # Tamaño de pip del símbolo
self.get_symbol_info(symbol)     # Info completa MT5
self.pips_to_price(...)          # Convertir pips a precio
```

### Agregar bot en simple_trading_app.py:

```python
from strategies.mi_estrategia import MiEstrategia

bot = BotConfig(
    strategy=MiEstrategia(),
    symbol="USDJPY",
    timeframe=mt5.TIMEFRAME_M15,
    interval_seconds=900
)
app_director.add_bot(bot)
# Auto-genera bot_id: MiEstrategia_USDJPY_M15
```

## Buenas prácticas
- **Magic numbers únicos**: Cada estrategia define su magic number en __init__
- **Estrategia autónoma**: La estrategia controla sizing, SL/TP y gestión de posiciones
- **Nombres automáticos**: Se generan como StrategyName_Symbol_Timeframe
- **Control de bots**: Usa `pause` y `resume` para control en tiempo real
- **🆕 Pausa inteligente**: Pausar todos los bots automáticamente silencia todo el sistema
- **Validación de duplicados**: El sistema valida que no haya magic numbers duplicados
- **Monitoreo**: Usa el comando `status` para verificar el estado de tus bots
- **Cierre seguro**: Usa `exit` en el CLI o `app_director.stop_all_bots()` + `bt.shutdown()`

## Notificaciones (Telegram)
- Crea un bot y obtén `token` + `chat_id`.
- Inicializa `NotificationService` con `TelegramNotificationProperties(token, chat_id)`.
- Pásalo al AppDirector para recibir alertas.

## Dashboard web
```powershell
streamlit run streamlit_app.py
```
Muestra información de cuenta y posiciones abiertas.

## Limitaciones conocidas
- Backtesting no modela SL/TP, slippage ni sesiones de mercado.
- `is_market_open` depende de la información de sesiones del broker.
- Los bots deben configurarse antes de ejecutar (no hay comando `add` en runtime).

## Consejos de seguridad
- Operar en vivo conlleva riesgo. Usa cuenta demo para validar.
- Cada estrategia controla su propio sizing - verifica `volume_min/max/step` del broker.

## Licencia y responsabilidad
Este framework no constituye asesoramiento financiero. Úsalo bajo tu propio riesgo.
