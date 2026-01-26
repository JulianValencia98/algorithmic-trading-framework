from typing import Dict, Any, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from Easy_Trading import BasicTrading
from utils.risk_validator import RiskValidator


class PositionSizer:
    """
    Handles position sizing logic (fixed or variable).
    """

    def __init__(
        self,
        mode: str = "fixed",
        fixed_lot: float = 0.01,
        risk_pct: float = 0.01,
        min_risk_pct: float = 0.002,
        max_risk_pct: float = 0.02,
        use_kelly: bool = False,
        kelly_win_rate: float = 0.55,
        kelly_profit_factor: float = 1.5
    ):
        self.mode = mode
        self.fixed_lot = fixed_lot
        self.risk_pct = risk_pct
        self.min_risk_pct = min_risk_pct
        self.max_risk_pct = max_risk_pct
        self.use_kelly = use_kelly
        self.kelly_win_rate = kelly_win_rate
        self.kelly_profit_factor = kelly_profit_factor

    def _kelly_pct(self, win_rate: float, profit_factor: float) -> float:
        k_c = (profit_factor * win_rate + win_rate - 1) / profit_factor
        return max(0.0, k_c)

    def get_position_size(
        self,
        basic_trading: "BasicTrading",
        symbol: str,
        equity: float,
        params: Optional[Dict[str, Any]] = None,
        risk_validator: Optional[RiskValidator] = None
    ) -> float:
        """
        Returns the position size (lots) based on the configured mode.

        Strategy parameters supported:
          - position_size_mode: "fixed" | "variable"
          - fixed_lot: float
          - risk_pct: float
          - use_kelly: bool
          - kelly_win_rate: float
          - kelly_profit_factor: float
          - min_risk_pct: float
          - max_risk_pct: float
        """
        params = params or {}
        mode = params.get("position_size_mode", self.mode)

        if mode == "fixed":
            lot = params.get("fixed_lot", self.fixed_lot)
            return float(lot)

        if mode != "variable":
            # Fallback to fixed if mode is unknown
            lot = params.get("fixed_lot", self.fixed_lot)
            return float(lot)

        use_kelly = params.get("use_kelly", self.use_kelly)
        min_risk_pct = params.get("min_risk_pct", self.min_risk_pct)
        max_risk_pct = params.get("max_risk_pct", self.max_risk_pct)

        risk_pct = params.get("risk_pct", self.risk_pct)
        if use_kelly:
            win_rate = params.get("kelly_win_rate", self.kelly_win_rate)
            profit_factor = params.get("kelly_profit_factor", self.kelly_profit_factor)
            risk_pct = self._kelly_pct(float(win_rate), float(profit_factor))

        # Clamp risk percent
        risk_pct = max(float(min_risk_pct), min(float(max_risk_pct), float(risk_pct)))

        # Calculate position size using core MT5-aware function
        volume = basic_trading.calculate_position_size(symbol, equity, risk_pct)

        # Optional cap via risk validator (interpreted as max lot size)
        if risk_validator and risk_validator.max_position_size is not None:
            max_lot = float(risk_validator.max_position_size)
            if max_lot > 0:
                volume = min(float(volume), max_lot)

        return float(volume)
