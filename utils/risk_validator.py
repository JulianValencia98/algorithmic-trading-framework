from typing import Dict, Any, Optional, Tuple
import MetaTrader5 as mt5

class RiskValidator:
    """
    Validates trades against risk limits.
    """

    def __init__(
        self,
        max_drawdown: float = 0.1,
        max_position_size: float = 0.1,
        max_daily_loss: float = 0.05,
        sl_tp_mode: str = "fixed_pips",
        fixed_sl_pips: float = 20.0,
        fixed_tp_pips: float = 40.0,
        kelly_win_rate: float = 0.55,
        kelly_profit_factor: float = 1.5,
        kelly_rr: float = 2.0,
        min_sl_pips: float = 5.0,
        max_sl_pips: float = 200.0
    ):
        self.max_drawdown = max_drawdown
        self.max_position_size = max_position_size
        self.max_daily_loss = max_daily_loss
        self.daily_loss = 0.0
        self.current_drawdown = 0.0
        self.sl_tp_mode = sl_tp_mode
        self.fixed_sl_pips = fixed_sl_pips
        self.fixed_tp_pips = fixed_tp_pips
        self.kelly_win_rate = kelly_win_rate
        self.kelly_profit_factor = kelly_profit_factor
        self.kelly_rr = kelly_rr
        self.min_sl_pips = min_sl_pips
        self.max_sl_pips = max_sl_pips

    def validate_trade(self, symbol: str, action: str, price: float, quantity: float = 1.0) -> bool:
        """
        Validate if a trade can be executed based on risk limits.
        """
        # Placeholder validation
        # Check position size
        if self.max_position_size and quantity > self.max_position_size:
            return False
        
        # Check drawdown (simplified)
        if self.current_drawdown > self.max_drawdown:
            return False
        
        # Check daily loss (simplified)
        if self.daily_loss > self.max_daily_loss:
            return False
        
        return True

    def _kelly_pct(self, win_rate: float, profit_factor: float) -> float:
        k_c = (profit_factor * win_rate + win_rate - 1) / profit_factor
        return max(0.0, k_c)

    def _get_pip_size(self, symbol_info) -> float:
        if symbol_info is None:
            return 0.0
        if symbol_info.digits in (3, 5):
            return symbol_info.point * 10
        return symbol_info.point

    def _pips_to_prices(self, entry_price: float, pips: float, action: str, pip_size: float) -> Tuple[Optional[float], Optional[float]]:
        if pip_size <= 0:
            return None, None
        action = action.lower()
        if action == "buy":
            sl = entry_price - (pips * pip_size)
            tp = entry_price + (pips * pip_size)
        else:
            sl = entry_price + (pips * pip_size)
            tp = entry_price - (pips * pip_size)
        return float(sl), float(tp)

    def get_sl_tp(
        self,
        symbol: str,
        action: str,
        entry_price: float,
        volume: float,
        equity: float,
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculates SL/TP prices based on the configured mode.

        Strategy parameters supported:
          - sl_tp_mode: "fixed_pips" | "kelly_pips" | "none"
          - sl_pips, tp_pips, rr
          - kelly_win_rate, kelly_profit_factor, kelly_rr
          - min_sl_pips, max_sl_pips
        """
        params = params or {}
        mode = params.get("sl_tp_mode", self.sl_tp_mode)
        if mode == "none":
            return None, None

        symbol_info = mt5.symbol_info(symbol)
        pip_size = self._get_pip_size(symbol_info)
        if pip_size <= 0:
            return None, None

        if mode == "fixed_pips":
            sl_pips = params.get("sl_pips", self.fixed_sl_pips)
            tp_pips = params.get("tp_pips", self.fixed_tp_pips)
            rr = params.get("rr", self.kelly_rr)
            if tp_pips is None and sl_pips is not None:
                tp_pips = float(sl_pips) * float(rr)
            if sl_pips is None and tp_pips is not None:
                sl_pips = float(tp_pips) / float(rr)
            if sl_pips is None and tp_pips is None:
                sl_pips = self.fixed_sl_pips
                tp_pips = self.fixed_tp_pips
            return self._pips_to_prices(float(entry_price), float(sl_pips), action, pip_size)

        if mode == "kelly_pips":
            win_rate = params.get("kelly_win_rate", self.kelly_win_rate)
            profit_factor = params.get("kelly_profit_factor", self.kelly_profit_factor)
            rr = params.get("kelly_rr", self.kelly_rr)
            min_sl = params.get("min_sl_pips", self.min_sl_pips)
            max_sl = params.get("max_sl_pips", self.max_sl_pips)

            kelly_pct = self._kelly_pct(float(win_rate), float(profit_factor))
            risk_amount = float(equity) * kelly_pct

            if symbol_info is None or volume <= 0:
                return None, None

            pip_value_per_lot = float(symbol_info.trade_contract_size) * pip_size
            pip_value = pip_value_per_lot * float(volume)
            if pip_value <= 0:
                return None, None

            sl_pips = risk_amount / pip_value
            sl_pips = max(float(min_sl), min(float(max_sl), float(sl_pips)))
            tp_pips = float(sl_pips) * float(rr)
            return self._pips_to_prices(float(entry_price), float(sl_pips), action, pip_size)

        return None, None

    def update_risk_metrics(self, pnl: float):
        """
        Update risk metrics after a trade.
        """
        self.daily_loss += pnl if pnl < 0 else 0
        # Update drawdown logic here