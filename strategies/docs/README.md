# Estrategias del Framework

## Arquitectura: Estrategia Autónoma

Cada estrategia es **completamente autónoma**. El framework solo orquesta la ejecución.

### 🆕 Sistema de Pausa Global

El framework incluye un sistema inteligente que pausa automáticamente el envío/pedido de información (eventos, notificaciones, logging) cuando todos los bots están pausados. Esto significa que las estrategias no necesitan preocuparse por el manejo del estado global - el sistema lo maneja automáticamente.

### Métodos que DEBE implementar cada estrategia:

```python
class MiEstrategia(StrategyBase):
    
    def generate_signal(self, data, current_index) -> str:
        """Retorna: 'buy', 'sell', o 'hold'"""
        pass
    
    def get_parameters(self) -> dict:
        """Retorna configuración de position management"""
        return {
            'close_before_open': True,   # Cerrar existentes antes de abrir
            'max_open_positions': 1,      # Máximo de posiciones simultáneas
        }
    
    def calculate_position_size(self, symbol, equity, entry_price) -> float:
        """Retorna el tamaño de la posición en lotes"""
        return 0.05
    
    def calculate_sl_tp(self, symbol, action, entry_price) -> Tuple[float, float]:
        """Retorna (sl_price, tp_price) o (None, None)"""
        pass
```

### Métodos Helper disponibles (heredados de StrategyBase):

```python
# Obtener pip size del símbolo
pip_size = self.get_pip_size(symbol)

# Obtener info completa del símbolo
symbol_info = self.get_symbol_info(symbol)

# Convertir pips a precio
price = self.pips_to_price(entry_price, pips, action, pip_size)
```

---

## Estrategias Actuales

### SimpleTimeStrategy (Magic: 1)
- **Símbolo:** EURUSD
- **Lógica:** Abre buy, espera 2 min, cierra y reabre
- **Position Management:** `close_before_open=False`, `max_open_positions=1`
- **Sizing:** Fixed 0.05 lots
- **SL/TP:** 100/300 pips

---

## Ejemplo: Estrategia con Kelly Criterion

```python
class KellyStrategy(StrategyBase):
    def __init__(self):
        super().__init__()
        self.magic_number = 99
        self.win_rate = 0.55
        self.profit_factor = 1.5
        self.sl_pips = 50
        self.rr = 2.0  # Risk/Reward
    
    def calculate_position_size(self, symbol, equity, entry_price):
        # Kelly: f = (p*b - q) / b donde p=win_rate, q=1-p, b=profit_factor
        kelly_pct = (self.profit_factor * self.win_rate + self.win_rate - 1) / self.profit_factor
        kelly_pct = max(0, min(kelly_pct, 0.25))  # Cap at 25%
        
        risk_amount = equity * kelly_pct
        pip_size = self.get_pip_size(symbol)
        symbol_info = self.get_symbol_info(symbol)
        
        # Calcular lotes basado en riesgo
        pip_value = symbol_info.trade_contract_size * pip_size
        volume = risk_amount / (self.sl_pips * pip_value)
        
        return round(volume, 2)
    
    def calculate_sl_tp(self, symbol, action, entry_price):
        pip_size = self.get_pip_size(symbol)
        tp_pips = self.sl_pips * self.rr
        
        if action == 'buy':
            sl = entry_price - (self.sl_pips * pip_size)
            tp = entry_price + (tp_pips * pip_size)
        else:
            sl = entry_price + (self.sl_pips * pip_size)
            tp = entry_price - (tp_pips * pip_size)
        
        return sl, tp
```
