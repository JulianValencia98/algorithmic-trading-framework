from typing import Optional, Tuple
from Easy_Trading import BasicTrading
from strategies.strategy_base import StrategyBase
from notifications.notifications import NotificationService
from data.trade_logger import TradeLogger
from events.event_bus import on_signal_generated, on_trade_opened, on_trade_closed
import pandas as pd
from datetime import datetime
import MetaTrader5 as mt5

class SimpleTradingDirector:
    """
    Orchestrates strategy execution and integration with BasicTrading.
    
    This director is strategy-agnostic: all trading decisions are made by the strategy.
    The director only handles:
    - Data extraction
    - Position management (close existing if needed)
    - Order execution
    - Notifications
    
    The STRATEGY decides:
    - Signal generation (buy/sell/hold)
    - Position sizing (lots)
    - SL/TP calculation
    - Whether to close before opening
    - Max simultaneous positions
    """

    def __init__(
        self, 
        basic_trading: BasicTrading, 
        strategy: StrategyBase, 
        notification_service: Optional[NotificationService] = None,
        magic_number: Optional[int] = None,
        trade_logger: Optional[TradeLogger] = None,
        bot_id: Optional[str] = None
    ):
        self.basic_trading = basic_trading
        self.strategy = strategy
        self.notification_service = notification_service
        self.magic_number = magic_number
        self.trade_logger = trade_logger
        self.bot_id = bot_id or "unknown_bot"
    
    def close_existing_positions(self, symbol: str, magic: int) -> int:
        """
        Cierra todas las posiciones abiertas para un símbolo y magic number específico.
        
        Args:
            symbol: Símbolo de trading
            magic: Magic number para filtrar posiciones
        
        Returns:
            Número de posiciones cerradas
        """
        try:
            count, df_positions = self.basic_trading.get_opened_positions(symbol=symbol, magic=magic)
            
            if count == 0:
                return 0
            
            closed_count = 0
            for _, position in df_positions.iterrows():
                ticket = position['ticket']
                volume = position['volume']
                pos_type = position['type']
                pos_symbol = position['symbol']
                profit = position.get('profit', 0.0)
                
                # Cerrar posición usando el método correcto
                result = self.basic_trading.close_position_by_ticket(
                    ticket=ticket,
                    symbol=pos_symbol,
                    volume=volume,
                    position_type=pos_type
                )
                
                if result is not None and hasattr(result, 'retcode') and result.retcode == mt5.TRADE_RETCODE_DONE:
                    closed_count += 1
                    
                    # Log trade closed
                    if self.trade_logger:
                        exit_price = result.price if hasattr(result, 'price') else 0.0
                        self.trade_logger.log_trade_closed(
                            ticket=ticket,
                            exit_price=exit_price,
                            profit=profit,
                            close_reason="signal"
                        )
                else:
                    print(f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S.%f')[:-3]} - Failed to close position {ticket}")
            
            return closed_count
        except Exception as e:
            print(f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S.%f')[:-3]} - ERROR in close_existing_positions: {e}")
            return 0
    
    def get_current_position_count(self, symbol: str, magic: int) -> int:
        """
        Obtiene el número actual de posiciones abiertas para un símbolo y magic number.
        
        Args:
            symbol: Símbolo de trading
            magic: Magic number para filtrar posiciones
        
        Returns:
            Número de posiciones abiertas
        """
        try:
            count, _ = self.basic_trading.get_opened_positions(symbol=symbol, magic=magic)
            return count
        except Exception as e:
            print(f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S.%f')[:-3]} - ERROR getting position count: {e}")
            return 0

    def run_strategy(self, symbol: str, timeframe, data_points: int = 100):
        """
        Run the strategy on live data.
        
        Flow:
        1. Extract market data
        2. Strategy generates signal
        3. Validate market is open
        4. Check position management (from strategy)
        5. Strategy calculates position size
        6. Strategy calculates SL/TP
        7. Execute trade
        """
        # Get recent data
        data = self.basic_trading.extract_data(symbol, timeframe, data_points)

        if data is None or data.empty:
            if self.notification_service:
                self.notification_service.send_notification("No Data", f"No data retrieved for {symbol}")
            return

        # Generate signal on latest bar
        last_index = len(data) - 1
        signal = self.strategy.generate_signal(data, last_index)

        if signal not in ['buy', 'sell']:
            return

        # Log signal generated (even if not executed)
        current_price = data.iloc[-1]['close'] if 'close' in data.columns else data.iloc[-1]['Close']
        
        # Emit signal event
        on_signal_generated(
            bot_id=self.bot_id,
            strategy_name=self.strategy.__class__.__name__,
            symbol=symbol,
            signal_type=signal,
            price=float(current_price)
        )

        # Check market open
        if not self.basic_trading.is_market_open(symbol):
            if self.notification_service:
                self.notification_service.send_notification("Market Closed", f"Skipping {signal} for {symbol}: market closed")
            return

        # Get magic number (from director first, then strategy)
        magic = self.magic_number if self.magic_number is not None else self.strategy.get_magic_number()
        
        # ===== POSITION MANAGEMENT (from strategy) =====
        close_before_open = self.strategy.should_close_before_open()
        max_open_positions = self.strategy.get_max_open_positions()
        
        current_positions = self.get_current_position_count(symbol, magic)
        
        if close_before_open:
            # Strategy wants to close existing positions before opening new
            if current_positions > 0:
                closed_count = self.close_existing_positions(symbol, magic)
                if closed_count > 0:
                    print(f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S.%f')[:-3]} - Closed {closed_count} existing position(s) before opening new trade")
        else:
            # Strategy allows multiple positions - check limit
            if current_positions >= max_open_positions:
                print(f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S.%f')[:-3]} - Max positions reached ({current_positions}/{max_open_positions}). Skipping signal.")
                return

        # Get entry price and equity
        _, _, equity, _ = self.basic_trading.info_account()
        entry_price = data.iloc[-1]['close'] if 'close' in data.columns else data.iloc[-1]['Close']

        # ===== POSITION SIZE (from strategy) =====
        volume = self.strategy.calculate_position_size(symbol, float(equity), float(entry_price))

        # ===== SL/TP (from strategy) =====
        sl, tp = self.strategy.calculate_sl_tp(symbol, signal, float(entry_price))

        # Execute order
        try:
            if signal == 'buy':
                result = self.basic_trading.buy(symbol, float(volume), strategy_name='FWK Market Order', sl=sl, tp=tp, magic=magic)
            else:
                result = self.basic_trading.sell(symbol, float(volume), strategy_name='FWK Market Order', sl=sl, tp=tp, magic=magic)

            # Check if trade was successful
            trade_success = result is not None and hasattr(result, 'retcode') and result.retcode == mt5.TRADE_RETCODE_DONE
            
            if trade_success:
                ticket = result.order if hasattr(result, 'order') else 0
                
                # Log trade to database
                if self.trade_logger:
                    self.trade_logger.log_trade_opened(
                        ticket=ticket,
                        magic_number=magic,
                        bot_id=self.bot_id,
                        strategy_name=self.strategy.__class__.__name__,
                        symbol=symbol,
                        action=signal,
                        volume=float(volume),
                        entry_price=float(entry_price),
                        sl_price=sl,
                        tp_price=tp
                    )
                
                # Emit trade opened event
                on_trade_opened(
                    bot_id=self.bot_id,
                    ticket=ticket,
                    symbol=symbol,
                    action=signal,
                    volume=float(volume),
                    price=float(entry_price),
                    sl=sl,
                    tp=tp,
                    magic_number=magic
                )

            if self.notification_service:
                self.notification_service.send_notification(
                    "Trade Executed", 
                    f"{signal.capitalize()} {symbol}\nVol: {volume}\nSL: {sl}\nTP: {tp}\nRetcode: {getattr(result, 'retcode', 'n/a')}"
                )
        except Exception as e:
            if self.notification_service:
                self.notification_service.send_notification("Trade Error", f"Failed to execute {signal} on {symbol}: {e}")
            raise

