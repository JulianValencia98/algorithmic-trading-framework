# AI Coding Agent Instructions for Simplified Trading Framework

## Architecture Overview
This is a simplified event-driven trading framework focused on ease of use with MetaTrader5 for live execution. The core is `Easy_Trading.py` (BasicTrading class), which handles all MT5 interactions. The framework supports multiple concurrent trading bots through `AppDirector`, with individual control and monitoring capabilities.

**Key Principle: Strategy Autonomy**
The framework only orchestrates execution - each strategy decides EVERYTHING about its trading:
- Signal generation (buy/sell/hold)
- Position sizing (lots)
- Stop Loss and Take Profit calculation
- Position management (close before open or allow multiple)

**Key Components:**
- `BasicTrading` (Easy_Trading.py): Central class for MT5 operations (open/close trades, data extraction, orders). Includes reconnection logic.
- `AppDirector`: Multi-bot orchestrator with pause/resume functionality (semaphore system). Each bot runs in independent thread.
- `BotConfig`: Auto-generates bot IDs based on strategy, symbol, and timeframe. Uses strategy's magic number.
- `SimpleTradingDirector`: Single-bot orchestrator that delegates all decisions to the strategy.
- `StrategyBase`: Abstract base for implementing trading strategies. Each strategy is fully autonomous.
- `TelegramNotificationService`: Sends alerts via Telegram.
- `TradeLogger`: Service that persists all trades to SQLite database. Enables analytics and AI training.
- `EventBus`: Pub/sub system for decoupling components. Emits events on trades, signals, and bot status changes.
- `TradeRepository`: SQLite-based persistence for trades and signals.

## Component Structure
- **Easy_Trading.py**: Standalone class with methods for trading, data, and account management. Includes health checks and reconnection.
- **trading_director/**: 
  - `app_director.py`: Multi-bot orchestrator with pause/resume system. Thread-safe operations with locks.
  - `simple_trading_director.py`: Single-bot director that calls strategy methods for all decisions. Integrates TradeLogger.
- **data/**: Persistence layer for trades and signals.
  - `models/trade.py`: Trade dataclass with full schema including AI context fields.
  - `models/signal.py`: Signal dataclass for tracking generated signals.
  - `repositories/trade_repository.py`: SQLite implementation for trade persistence.
  - `trade_logger.py`: Service for logging trades and signals with query methods.
- **events/**: Event system for decoupling.
  - `event_bus.py`: Pub/sub singleton with EventType enum (TRADE_OPENED, TRADE_CLOSED, SIGNAL_GENERATED, etc.).
- **notifications/**: Telegram channel for alerts.
- **utils/**: 
  - `utils.py`: Date formatting and helper functions.
- **strategies/**: Inherit from StrategyBase. Each strategy is autonomous and defines its own sizing and SL/TP logic.
- **streamlit_app.py**: Web dashboard for viewing account info and positions.
- **simple_trading_app.py**: Main application with CLI for pause/resume control and stats.

## Event Flow
**Single Bot (SimpleTradingDirector):**
1. Extract market data via BasicTrading.
2. Strategy generates signal via `generate_signal()`.
3. Emit signal event via EventBus.
4. Check position management rules from strategy (`should_close_before_open()`, `get_max_open_positions()`).
5. Strategy calculates position size via `calculate_position_size()`.
6. Strategy calculates SL/TP via `calculate_sl_tp()`.
7. Execute trade via BasicTrading.
8. Log trade to database via TradeLogger.
9. Emit trade_opened event via EventBus.
10. Notifications sent via TelegramNotificationService (if configured).

**Multiple Bots (AppDirector):**
1. Each bot runs in its own thread with independent execution loop.
2. AppDirector manages bot lifecycle with pause/resume functionality (semaphore system).
3. Each bot has its own SimpleTradingDirector instance with unique magic number.
4. Bots can be paused/resumed individually via CLI without stopping.
5. **Market open verification**: When adding bot shows warning if market closed; during execution bot waits automatically if market is closed (status: `waiting_market`).
6. Health checks and MT5 reconnection in each bot loop.

## Key Patterns
- **Strategy Autonomy**: Each strategy controls its own sizing, SL/TP, and position management.
- **Dependency Injection**: Components receive BasicTrading instance.
- **Strategy Plugins**: Strategies inherit from StrategyBase and implement 4 required methods.
- **Magic Numbers by Strategy**: Each strategy has fixed magic number defined in __init__.
- **Automatic Bot Naming**: Format: `StrategyName_Symbol_Timeframe` (e.g., SimpleTime_EURUSD_M1).
- **Pause/Resume System**: Semaphore-based control without stopping threads completely.
- **Multi-Threading**: Each bot runs in independent thread with pause_event and stop_event.
- **Thread-Safe Operations**: Lock mechanisms for safe bot management.
- **Health Checks**: MT5 connection monitoring with automatic reconnection.
- **Market Verification**: Checks if market is open before executing trades.
- **Configuration**: Use .env for MT5 credentials and Telegram token.

## Workflows
- **Live Trading (Multiple Bots)**: Run `python simple_trading_app.py` (requires MT5 terminal).
  - Interactive commands: `status`, `stats`, `pause`, `resume`, `help`, `exit`
  - Each bot runs with independent symbol, timeframe, and interval
  - Bots can be paused/resumed without stopping completely
- **Dashboard**: Run `streamlit run streamlit_app.py` for web-based monitoring.
- **Add Strategy**: 
  1. Create class inheriting StrategyBase in strategies/
  2. Assign unique magic number in __init__: `self.magic_number = X`
  3. Implement 4 required methods: `generate_signal()`, `get_parameters()`, `calculate_position_size()`, `calculate_sl_tp()`
  4. Add BotConfig in simple_trading_app.py
- **Control Bots**: Use CLI commands for pause/resume control.
- **Notifications**: Configure Telegram in .env.

## Conventions
- **Naming**: English comments and variables.
- **Bot IDs**: Auto-generated format: `StrategyName_Symbol_Timeframe` (e.g., "SimpleTime_EURUSD_M1").
- **Magic Numbers**: Each strategy defines its unique magic number in __init__.
  - Example: SimpleTimeStrategy always uses magic_number=1
  - Multiple bots using same strategy will share the same magic number
  - Validate duplicates when adding strategies to prevent conflicts
- **Bot States**: `running` (▶️), `waiting_market` (🕐), `paused` (⏸️), `stopped` (⏹️).
- **Imports**: Relative imports within modules.
- **Error Handling**: Raise exceptions with descriptive messages.
- **Logging**: Use `print(f"{Utils.dateprint()} - [bot_id] message")` for bot-specific logs.
- **Data Access**: Via BasicTrading methods.
- **Thread Safety**: Use locks when modifying shared state in AppDirector.

## Strategy Implementation
Each strategy must implement 4 methods:
```python
class MyStrategy(StrategyBase):
    def __init__(self):
        super().__init__()
        self.magic_number = 99  # Unique identifier
    
    def generate_signal(self, data, current_index) -> str:
        """Returns 'buy', 'sell', or 'hold'"""
        pass
    
    def get_parameters(self) -> dict:
        """Returns position management config"""
        return {
            'close_before_open': True,
            'max_open_positions': 1,
        }
    
    def calculate_position_size(self, symbol, equity, entry_price) -> float:
        """Returns lot size"""
        pass
    
    def calculate_sl_tp(self, symbol, action, entry_price) -> Tuple[float, float]:
        """Returns (sl_price, tp_price)"""
        pass
```

## Dependencies
- MetaTrader5 for platform integration.
- python-telegram-bot for notifications.
- pandas/numpy for data processing.
- python-dotenv for config.
- streamlit for web dashboard.
- threading (built-in) for concurrent bot execution.

## Key Files Reference
- `Easy_Trading.py`: Core MT5 operations and data access.
- `trading_director/app_director.py`: Multi-bot orchestration with threading.
- `trading_director/simple_trading_director.py`: Single-bot execution logic.
- `simple_trading_app.py`: Main application with interactive CLI.
- `streamlit_app.py`: Web dashboard for monitoring.
- `strategies/strategy_base.py`: Base class for all strategies (4 required methods).</content>
<parameter name="filePath">c:/Users/cryty/Desktop/Documentos Generales Julian/Inversiones/Framework_Traiding_Alg/Framework_Trading_Alg/.github/copilot-instructions.md