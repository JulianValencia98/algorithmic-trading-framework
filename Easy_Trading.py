import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from bs4 import BeautifulSoup
from datetime import datetime
from utils.utils import Utils
import os
import time
from dotenv import load_dotenv, find_dotenv

class BasicTrading:

    def __init__(self):
        """
        Initializes the BasicTrading object with MT5 credentials from .env file.
        """
        # Load environment variables from .env file
        load_dotenv(find_dotenv())

        # Get MT5 credentials from environment
        self.mt5_path = os.getenv("MT5_PATH")
        self.mt5_password = os.getenv("MT5_PASSWORD")
        self.mt5_server = os.getenv("MT5_SERVER")
        self.mt5_timeout = int(os.getenv("MT5_TIMEOUT", 60000))  # Default timeout
        # Optional broker-specific symbol prefix/suffix (for brokers like RoboForex)
        # Example: MT5_SYMBOL_SUFFIX=".ecn" or MT5_SYMBOL_SUFFIX=".pro"
        self.symbol_prefix = os.getenv("MT5_SYMBOL_PREFIX", "") or ""
        self.symbol_suffix = os.getenv("MT5_SYMBOL_SUFFIX", "") or ""
        # Parse login safely
        login_raw = os.getenv("MT5_LOGIN")
        try:
            self.mt5_login = int(login_raw) if login_raw is not None else None
        except Exception:
            self.mt5_login = None

        # Validate required env vars
        self._validate_env()

        # Initialize MT5 platform once
        self._initialize_mt5()

    def _initialize_mt5(self, max_retries: int = 3, retry_delay: int = 5) -> None:
        """
        Initializes the MT5 platform with retry logic.

        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Seconds to wait between retries

        Raises:
            Exception: If initialization fails after all retries.
        """
        for attempt in range(1, max_retries + 1):
            try:
                if not mt5.initialize(
                    path=self.mt5_path,
                    login=self.mt5_login,
                    password=self.mt5_password,
                    server=self.mt5_server,
                    timeout=self.mt5_timeout
                ):
                    last_error = mt5.last_error()
                    raise Exception(f"MT5 initialization failed. Error: {last_error}")
                print(f"{Utils.dateprint()} - MT5 initialized successfully.")
                return
            except Exception as e:
                if attempt < max_retries:
                    print(f"{Utils.dateprint()} - ERROR: Failed to initialize MT5 (attempt {attempt}/{max_retries}). Retrying in {retry_delay}s... Exception: {e}")
                    time.sleep(retry_delay)
                else:
                    print(f"{Utils.dateprint()} - ERROR: Failed to initialize MT5 after {max_retries} attempts. Exception: {e}")
                    raise
    
    def check_connection(self) -> bool:
        """
        Verifica si la conexión a MT5 está activa.
        
        Returns:
            True si está conectado, False si no
        """
        try:
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                return False
            return terminal_info.connected
        except Exception:
            return False
    
    def reconnect(self, max_retries: int = 3, retry_delay: int = 5) -> bool:
        """
        Intenta reconectar a MT5 si la conexión se perdió.
        
        Args:
            max_retries: Máximo número de intentos
            retry_delay: Segundos entre intentos
        
        Returns:
            True si se reconectó exitosamente, False si no
        """
        print(f"{Utils.dateprint()} - Attempting to reconnect to MT5...")
        
        # Primero intentar shutdown limpio
        try:
            mt5.shutdown()
        except:
            pass
        
        # Intentar reinicializar
        try:
            self._initialize_mt5(max_retries=max_retries, retry_delay=retry_delay)
            return True
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to reconnect to MT5. Exception: {e}")
            return False

    def _validate_env(self) -> None:
        """
        Validates required environment variables for MT5 connection.

        Raises:
            Exception: If any required env var is missing or invalid.
        """
        missing = []
        if not self.mt5_path:
            missing.append("MT5_PATH")
        if self.mt5_login is None:
            missing.append("MT5_LOGIN")
        if not self.mt5_password:
            missing.append("MT5_PASSWORD")
        if not self.mt5_server:
            missing.append("MT5_SERVER")
        if missing:
            raise Exception(f"Missing or invalid MT5 env vars: {', '.join(missing)}")

    def ensure_symbol_selected(self, symbol: str) -> None:
        """
        Ensures the trading symbol is selected/visible in MT5 Market Watch.
        Uses _find_symbol_info to handle symbol suffixes correctly.

        Raises:
            Exception: If the symbol cannot be selected.
        """
        try:
            # Find the actual symbol with correct suffix
            info = self._find_symbol_info(symbol)
            if info is None:
                raise Exception(f"Symbol {symbol} not found in any format")
            
            actual_symbol = info.name
            print(f"{Utils.dateprint()} - Ensuring symbol {actual_symbol} (requested: {symbol}) is selected")
            
            if not mt5.symbol_select(actual_symbol, True):
                raise Exception(f"Unable to select symbol {actual_symbol}. MT5 error: {mt5.last_error()}")
                
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to select symbol {symbol}. Exception: {e}")
            raise

    def get_actual_symbol(self, symbol: str) -> str:
        """
        Helper method to get the actual symbol name with correct suffix.
        
        Args:
            symbol (str): Requested symbol name
            
        Returns:
            str: Actual symbol name with suffix (e.g., EURUSD.sml)
        """
        info = self._find_symbol_info(symbol)
        if info is None:
            raise Exception(f"Symbol {symbol} not found in any format")
        return info.name

    def modify_orders(self, symbol: str, ticket: int, stop_loss: float = None, take_profit: float = None, type_order=mt5.ORDER_TYPE_BUY, type_fill=mt5.ORDER_FILLING_FOK) -> None:
        """
        Modifies stop loss and take profit for an existing order.

        Args:
            symbol (str): Trading symbol.
            ticket (int): Order ticket.
            stop_loss (float, optional): Stop loss price.
            take_profit (float, optional): Take profit price.
            type_order: Order type.
            type_fill: Filling policy.
        """
        try:
            # Ensure symbol is selected
            self.ensure_symbol_selected(symbol)

            # Validate position exists and get its type if needed
            pos = mt5.positions_get(ticket=ticket)
            if pos is None or len(pos) == 0:
                raise Exception(f"Position {ticket} not found for {symbol}. MT5 error: {mt5.last_error()}")
            pos_type = pos[0].type
            inferred_type_order = mt5.ORDER_TYPE_BUY if pos_type == mt5.POSITION_TYPE_SELL else mt5.ORDER_TYPE_SELL
            # If caller didn't pass a type_order explicitly, infer from position type (opposite to close)
            type_order = type_order if type_order is not None else inferred_type_order

            request_common = {
                'action': mt5.TRADE_ACTION_SLTP,
                'symbol': symbol,
                'position': ticket,
                'type': type_order,
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': type_fill
            }

            if (stop_loss is not None) and (take_profit is None):
                modify_order_request = {**request_common, 'sl': stop_loss}
            elif (stop_loss is None) and (take_profit is not None):
                modify_order_request = {**request_common, 'tp': take_profit}
            else:
                modify_order_request = {**request_common, 'sl': stop_loss, 'tp': take_profit}

            result = mt5.order_send(modify_order_request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                raise Exception(f"Failed to modify order. Error: {result if result is not None else mt5.last_error()}")
            print(f"{Utils.dateprint()} - Order modified successfully for ticket {ticket}.")
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to modify order for ticket {ticket}. Exception: {e}")
            raise

    def extract_data(self, symbol: str, timeframe, count: int) -> pd.DataFrame:
        """
        Extracts historical data from MT5 and converts it to a DataFrame.

        Args:
            symbol (str): Trading symbol.
            timeframe: MT5 timeframe (e.g., mt5.TIMEFRAME_M1).
            count (int): Number of records to extract.

        Returns:
            pd.DataFrame: Historical data.
        """
        try:
            self.ensure_symbol_selected(symbol)
            actual_symbol = self.get_actual_symbol(symbol)
            rates = None
            for _ in range(3):
                rates = mt5.copy_rates_from_pos(actual_symbol, timeframe, 0, count)
                if rates is not None:
                    break
                time.sleep(0.5)
            if rates is None:
                raise Exception(f"Failed to get rates for {actual_symbol} (requested: {symbol}). Error: {mt5.last_error()}")
            table = pd.DataFrame(rates)
            table['time'] = pd.to_datetime(table['time'], unit='s')
            print(f"{Utils.dateprint()} - Data extracted successfully for {symbol}.")
            return table
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to extract data for {symbol}. Exception: {e}")
            raise

    def get_pending_orders(self) -> pd.DataFrame:
        """
        Retrieves pending orders.

        Returns:
            pd.DataFrame: Pending orders.
        """
        try:
            orders = mt5.orders_get()
            if orders is None or len(orders) == 0:
                print(f"{Utils.dateprint()} - No pending orders found.")
                return pd.DataFrame()
            df = pd.DataFrame(list(orders), columns=orders[0]._asdict().keys())
            print(f"{Utils.dateprint()} - Pending orders retrieved successfully.")
            return df
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to get pending orders. Exception: {e}")
            return pd.DataFrame()

    def remove_pending_operation(self, strategy_name: str, type_fill) -> None:
        """
        Removes pending orders for a specific strategy.
        """
        try:
            df = self.get_pending_orders()
            df_strategy = df[df['comment'] == strategy_name]
            ticket_list = df_strategy['ticket'].unique().tolist()
            for ticket in ticket_list:
                close_pend_request = {
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": ticket,
                    "type_filling": type_fill
                }
                result = mt5.order_send(close_pend_request)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    raise Exception(f"Failed to remove pending order {ticket}. Error: {result}")
            print(f"{Utils.dateprint()} - Pending orders removed for strategy {strategy_name}.")
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to remove pending orders for {strategy_name}. Exception: {e}")
            raise

    def _open_operations(self, symbol: str, volume: float, operation_type, strategy_name: str, sl: float = None, tp: float = None, type_fill=mt5.ORDER_FILLING_FOK, magic: int = 202204):
        """
        Opens a trade operation.
        
        Args:
            magic (int): Magic number to identify the strategy.
        """
        try:
            # Ensure symbol is selected
            self.ensure_symbol_selected(symbol)
            actual_symbol = self.get_actual_symbol(symbol)
            
            if (sl is None) and (tp is None):
                order = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": actual_symbol,
                    "volume": volume,
                    "type": operation_type,
                    "magic": magic,
                    "comment": strategy_name,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": type_fill
                }
                result = mt5.order_send(order)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    raise Exception(f"Failed to open {operation_type} order. Error: {result}")
                print(f"{Utils.dateprint()} - Opened {operation_type} with volume {volume} for {actual_symbol}.")

            elif (sl is None) and (tp is not None):
                order = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": actual_symbol,
                    "tp": tp,
                    "volume": volume,
                    "type": operation_type,
                    "magic": magic,
                    "comment": strategy_name,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": type_fill
                }
                result = mt5.order_send(order)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    raise Exception(f"Failed to open {operation_type} order. Error: {result}")

            elif (sl is not None) and (tp is None):
                order = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": actual_symbol,
                    "sl": sl,
                    "volume": volume,
                    "type": operation_type,
                    "magic": magic,
                    "comment": strategy_name,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": type_fill
                }
                result = mt5.order_send(order)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    raise Exception(f"Failed to open {operation_type} order. Error: {result}")

            elif (sl is not None) and (tp is not None):
                order = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": actual_symbol,
                    "sl": sl,
                    "tp": tp,
                    "volume": volume,
                    "type": operation_type,
                    "magic": magic,
                    "comment": strategy_name,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": type_fill
                }
                result = mt5.order_send(order)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    raise Exception(f"Failed to open {operation_type} order. Error: {result}")

            return result
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to open operation. Exception: {e}")
            raise

    def close_partial(self, type_op, id_position: int, symbol: str, volume_to_close: float):
        """
        Closes a partial position.
        """
        try:
            self.ensure_symbol_selected(symbol)
            actual_symbol = self.get_actual_symbol(symbol)
            pos = mt5.positions_get(ticket=id_position)
            if pos is None or len(pos) == 0:
                raise Exception(f"Position {id_position} not found. MT5 error: {mt5.last_error()}")
            current_volume = pos[0].volume
            step = mt5.symbol_info(actual_symbol).volume_step
            min_lot = mt5.symbol_info(actual_symbol).volume_min
            volume = min(current_volume, volume_to_close)
            # Round volume to step
            if step and step > 0:
                steps = np.floor(volume / step)
                volume = steps * step
            volume = max(min_lot, volume)
            order = {
                'action': mt5.TRADE_ACTION_DEAL,
                'type': type_op,
                'position': id_position,
                'symbol': symbol,
                'volume': volume
            }
            result = mt5.order_send(order)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                raise Exception(f"Failed to close partial position {id_position}. Error: {result if result is not None else mt5.last_error()}")
            print(f"{Utils.dateprint()} - Partial close executed for position {id_position} with volume {volume}.")
            return result
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to close partial position {id_position}. Exception: {e}")
            raise

    def buy(self, symbol, volume, strategy_name: str = 'Py', sl: float = None, tp: float = None, type_fill=mt5.ORDER_FILLING_FOK, magic: int = 202204):
        """
        Opens a long trade.
        
        Args:
            magic (int): Magic number to identify the strategy (default 202204 for backwards compatibility).
        """
        return self._open_operations(symbol, volume, mt5.ORDER_TYPE_BUY, strategy_name, sl, tp, type_fill, magic)

    def sell(self, symbol, volume, strategy_name: str = 'Py', sl: float = None, tp: float = None, type_fill=mt5.ORDER_FILLING_FOK, magic: int = 202204):
        """
        Opens a short trade.
        
        Args:
            magic (int): Magic number to identify the strategy (default 202204 for backwards compatibility).
        """
        return self._open_operations(symbol, volume, mt5.ORDER_TYPE_SELL, strategy_name, sl, tp, type_fill, magic)

    def close_position_by_ticket(self, ticket: int, symbol: str, volume: float, position_type: int, filling_mode=mt5.ORDER_FILLING_FOK):
        """
        Closes a specific position by ticket number.
        
        Args:
            ticket: Position ticket number
            symbol: Trading symbol
            volume: Position volume
            position_type: Position type (0=Buy, 1=Sell)
            filling_mode: Order filling mode
            
        Returns:
            Order result or None if failed
        """
        try:
            # Para cerrar Buy (tipo 0) usamos Sell, para cerrar Sell (tipo 1) usamos Buy
            close_type = mt5.ORDER_TYPE_BUY if position_type == 1 else mt5.ORDER_TYPE_SELL
            
            close_request = {
                'action': mt5.TRADE_ACTION_DEAL,
                'symbol': symbol,
                'volume': volume,
                'type': close_type,
                'position': ticket,
                'comment': 'Close position',
                'type_filling': filling_mode
            }
            
            result = mt5.order_send(close_request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"{Utils.dateprint()} - ERROR: Failed to close position {ticket}. Retcode: {result.retcode}")
                return None
            
            print(f"{Utils.dateprint()} - Position {ticket} closed successfully.")
            return result
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to close position {ticket}. Exception: {e}")
            return None
    
    def close_all_open_operations(self, data: pd.DataFrame, filling_mode=mt5.ORDER_FILLING_FOK) -> None:
        """
        Closes all operations in the provided DataFrame.
        """
        try:
            df_open_positions = data.copy()
            lista_ops = df_open_positions['ticket'].unique().tolist()

            for operacion in lista_ops:
                df_operacion = df_open_positions[df_open_positions['ticket'] == operacion]
                price_close = df_operacion['price_current']
                tipo_operacion = df_operacion['type'].item()
                simbolo_operacion = df_operacion['symbol'].item()
                volumen_operacion = df_operacion['volume'].item()
                # 1 Sell / 0 Buy
                if tipo_operacion == 1:
                    tip_op = mt5.ORDER_TYPE_BUY
                    close_request = {
                        'action': mt5.TRADE_ACTION_DEAL,
                        'symbol': simbolo_operacion,
                        'volume': volumen_operacion,
                        'type': tip_op,
                        'position': operacion,
                        'comment': 'Close positions',
                        'type_filling': filling_mode
                    }
                    result = mt5.order_send(close_request)
                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        raise Exception(f"Failed to close short position {operacion}. Error: {result}")

                if tipo_operacion == 0:
                    tip_op = mt5.ORDER_TYPE_SELL
                    close_request = {
                        'action': mt5.TRADE_ACTION_DEAL,
                        'symbol': simbolo_operacion,
                        'volume': volumen_operacion,
                        'type': tip_op,
                        'position': operacion,
                        'comment': 'Close positions',
                        'type_filling': filling_mode
                    }
                    result = mt5.order_send(close_request)
                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        raise Exception(f"Failed to close long position {operacion}. Error: {result}")
            print(f"{Utils.dateprint()} - All open operations closed.")
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to close all operations. Exception: {e}")
            raise

    def get_opened_positions(self, symbol: str = None, magic: int = None) -> tuple:
        """
        Retrieves open positions, optionally filtered by symbol and/or magic number.
        
        Args:
            symbol: Filter by symbol (optional)
            magic: Filter by magic number (optional)
        
        Returns:
            Tuple of (count, DataFrame of positions)
        """
        try:
            o_pos = mt5.positions_get()
            if o_pos is None:
                raise Exception(f"Failed to get positions. Error: {mt5.last_error()}")
            if len(o_pos) == 0:
                print(f"{Utils.dateprint()} - Open positions retrieved successfully.")
                return 0, pd.DataFrame()
            df_pos = pd.DataFrame(list(o_pos), columns=o_pos[0]._asdict().keys())
            
            # Aplicar filtros
            if symbol is not None:
                df_pos = df_pos[df_pos['symbol'] == symbol]
            if magic is not None:
                df_pos = df_pos[df_pos['magic'] == magic]

            len_d_pos = len(df_pos)
            print(f"{Utils.dateprint()} - Open positions retrieved successfully.")
            return len_d_pos, df_pos
        except Exception as e:
            len_d_pos = 0
            df_pos_temp = pd.DataFrame()
            print(f"{Utils.dateprint()} - ERROR: Failed to get open positions. Exception: {e}")
            return len_d_pos, df_pos_temp

    def get_all_positions(self) -> pd.DataFrame:
        """
        Retrieves all open positions.
        """
        try:
            o_pos = mt5.positions_get()
            if o_pos is None:
                raise Exception(f"Failed to get positions. Error: {mt5.last_error()}")
            if len(o_pos) == 0:
                print(f"{Utils.dateprint()} - All positions retrieved successfully.")
                return pd.DataFrame()
            df_pos = pd.DataFrame(list(o_pos), columns=o_pos[0]._asdict().keys())
            print(f"{Utils.dateprint()} - All positions retrieved successfully.")
            return df_pos
        except Exception as e:
            df_pos = pd.DataFrame()
            print(f"{Utils.dateprint()} - ERROR: Failed to get all positions. Exception: {e}")
            return df_pos

    def send_to_breakeven(self, df_pos: pd.DataFrame, perc_rec: float) -> None:
        """
        Moves positions to breakeven based on a recovery percentage.
        """
        if df_pos.empty:
            print(f"{Utils.dateprint()} - No open positions to move to breakeven.")
            return
        try:
            lista_operaciones = df_pos['ticket'].tolist()
            for op in lista_operaciones:
                df_temp = df_pos[df_pos['ticket'] == op]
                symb = df_temp['symbol'].iloc[0]
                ticket = op
                stop_loss = df_temp['price_open'].iloc[0]
                take_profit = df_temp['tp'].iloc[0]
                precio_actual = df_temp['price_current'].iloc[0]
                tipo_operacion = df_temp['type'].iloc[0]

                if (tipo_operacion == 1) and (precio_actual < stop_loss):
                    type_order = mt5.ORDER_TYPE_BUY
                    self.modify_orders(symb, ticket, stop_loss, take_profit, type_order)
                if (tipo_operacion == 0) and (precio_actual > stop_loss):
                    type_order = mt5.ORDER_TYPE_SELL
                    self.modify_orders(symb, ticket, stop_loss, take_profit, type_order)
            print(f"{Utils.dateprint()} - Positions moved to breakeven.")
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to move positions to breakeven. Exception: {e}")
            raise

    def kelly_criterion_pct_risk(self, win_rate: float, profit_factor: float) -> float:
        """
        Calculates the percentage of capital to risk using Kelly criterion.
        """
        k_c = (profit_factor * win_rate + win_rate - 1) / profit_factor
        if k_c < 0:
            k_c = 0.01
        return k_c

    def calculate_position_size(self, symbol: str, capital: float, per_to_risk: float) -> float:
        """
        Calculates optimal lot size based on risk.
        """
        try:
            print(f"Total Account Capital: {capital}")
            leverage = mt5.account_info().leverage
            print(f"Leverage: {leverage}")
            invested_capital = capital * leverage * per_to_risk
            print(f"Leveraged Account Capital: {invested_capital}")
            actual_symbol = self.get_actual_symbol(symbol)
            trade_size = mt5.symbol_info(actual_symbol).trade_contract_size
            print(f"Trade Size: {trade_size}")
            price = (mt5.symbol_info(actual_symbol).ask + mt5.symbol_info(actual_symbol).bid) / 2
            print(f"Price: {price}")
            lot_size = invested_capital / trade_size / price
            print(f"Lot size weighted by risk: {lot_size}")
            min_lot = mt5.symbol_info(actual_symbol).volume_min
            print(f"Min Lot: {min_lot}")
            max_lot = mt5.symbol_info(actual_symbol).volume_max
            print(f"Max Lot: {max_lot}")

            step_lot = mt5.symbol_info(actual_symbol).volume_step
            print(f"Lot Step: {step_lot}")

            if lot_size <= min_lot:
                print(f"Lot size too small, using min lot: {min_lot}")
                return min_lot

            # Round down to nearest step within bounds
            try:
                if step_lot and step_lot > 0:
                    steps = np.floor((lot_size - min_lot) / step_lot)
                    lot_size_rounded = min_lot + steps * step_lot
                else:
                    # Fallback to decimal rounding based on min_lot
                    number_decimal = str(min_lot)[::-1].find(".")
                    lot_size_rounded = np.round(lot_size, number_decimal if number_decimal > 0 else 0)
                    if lot_size < lot_size_rounded:
                        lot_size_rounded = lot_size_rounded - (10 ** -number_decimal if number_decimal > 0 else 1)
                if lot_size_rounded > max_lot:
                    lot_size_rounded = max_lot
                print(f"Good Size Lot: {lot_size_rounded}")
                return float(lot_size_rounded)
            except Exception:
                # Last resort
                lot_size_rounded = min(max(min_lot, lot_size), max_lot)
                print(f"Fallback Size Lot: {lot_size_rounded}")
                return float(lot_size_rounded)
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to calculate position size for {symbol}. Exception: {e}")
            raise


    def _get_data_for_bt(self, timeframe, symbol, count):
        """
        Gets data formatted for backtesting.
        """
        try:
            self.ensure_symbol_selected(symbol)
            actual_symbol = self.get_actual_symbol(symbol)
            rates = None
            for _ in range(3):
                rates = mt5.copy_rates_from_pos(actual_symbol, timeframe, 0, count)
                if rates is not None:
                    break
                time.sleep(0.5)
            if rates is None:
                raise Exception(f"Failed to get rates for {actual_symbol} (requested: {symbol}). Error: {mt5.last_error()}")
            rates_frame = pd.DataFrame(rates)
            rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
            data = rates_frame.copy()
            data = data.iloc[:, [0, 1, 2, 3, 4, 5, 7]]
            data.columns = ['time', 'Open', 'High', 'Low', 'Close', 'Volume', 'OpenInterest']
            data = data.set_index('time')
            print(f"{Utils.dateprint()} - Backtesting data retrieved for {symbol}.")
            return data
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to get backtesting data for {symbol}. Exception: {e}")
            raise

    def info_account(self) -> tuple:
        """
        Returns account info: balance, profit, equity, free margin.
        """
        try:
            cuentaDict = mt5.account_info()._asdict()
            balance = cuentaDict["balance"]
            profit_account = cuentaDict["profit"]
            equity = cuentaDict["equity"]
            free_margin = cuentaDict["margin_free"]
            print(f"{Utils.dateprint()} - Account info retrieved successfully.")
            return balance, profit_account, equity, free_margin
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to get account info. Exception: {e}")
            raise

    def is_demo_account(self) -> bool:
        """
        Checks if the account is a demo account.
        """
        try:
            account_info = mt5.account_info()
            if account_info is None:
                raise Exception(f"Failed to get account info. Error: {mt5.last_error()}")
            return account_info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to check account type. Exception: {e}")
            return False

    def get_data_from_dates(self, year_ini: int, month_ini: int, day_ini: int, year_fin: int, month_fin: int, day_fin: int, symbol: str, timeframe, for_bt: bool = False) -> pd.DataFrame:
        """
        Gets data between dates.
        """
        try:
            self.ensure_symbol_selected(symbol)
            actual_symbol = self.get_actual_symbol(symbol)
            from_date = datetime(year_ini, month_ini, day_ini)
            to_date = datetime(year_fin, month_fin, day_fin)
            rates = None
            for _ in range(3):
                rates = mt5.copy_rates_range(actual_symbol, timeframe, from_date, to_date)
                if rates is not None:
                    break
                time.sleep(0.5)
            if rates is None:
                raise Exception(f"Failed to get rates for {actual_symbol} (requested: {symbol}). Error: {mt5.last_error()}")
            rates_frame = pd.DataFrame(rates)
            rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')

            if for_bt:
                rates_frame = rates_frame.iloc[:, [0, 1, 2, 3, 4, 5, 7]]
                rates_frame.columns = ['time', 'Open', 'High', 'Low', 'Close', 'Volume', 'OpenInterest']
                rates_frame = rates_frame.set_index('time')
            print(f"{Utils.dateprint()} - Data from dates retrieved for {symbol}.")
            return rates_frame
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to get data from dates for {symbol}. Exception: {e}")
            raise

    def shutdown(self) -> None:
        """
        Gracefully shuts down the MT5 terminal connection.
        """
        try:
            mt5.shutdown()
            print(f"{Utils.dateprint()} - MT5 shutdown completed.")
        except Exception as e:
            print(f"{Utils.dateprint()} - WARNING: MT5 shutdown encountered an issue. Exception: {e}")

    def send_pending_order(self, symbol: str, volume: float, price: float, type_op, expirationdate, type_fill, sl: float = None, tp: float = None, strategy_name: str = 'Py'):
        """
        Sends a pending order.
        """
        try:
            # Ensure symbol is selected
            self.ensure_symbol_selected(symbol)
            if (sl is not None) and (tp is not None):
                pending_order = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": symbol,
                    "volume": volume,
                    "price": price,
                    "type": type_op,
                    "sl": sl,
                    "tp": tp,
                    "type_time": mt5.ORDER_TIME_SPECIFIED,
                    "expiration": expirationdate,
                    "comment": strategy_name,
                    "type_filling": type_fill
                }
                if expirationdate is None:
                    del pending_order["expiration"]
                result = mt5.order_send(pending_order)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    raise Exception(f"Failed to send pending order. Error: {result}")

            elif (sl is not None) and (tp is None):
                pending_order = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": symbol,
                    "volume": volume,
                    "price": price,
                    "type": type_op,
                    "sl": sl,
                    "type_time": mt5.ORDER_TIME_SPECIFIED,
                    "expiration": expirationdate,
                    "comment": strategy_name,
                    "type_filling": type_fill
                }
                if expirationdate is None:
                    del pending_order["expiration"]
                result = mt5.order_send(pending_order)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    raise Exception(f"Failed to send pending order. Error: {result}")

            elif (sl is None) and (tp is not None):
                pending_order = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": symbol,
                    "volume": volume,
                    "price": price,
                    "type": type_op,
                    "tp": tp,
                    "type_time": mt5.ORDER_TIME_SPECIFIED,
                    "expiration": expirationdate,
                    "comment": strategy_name,
                    "type_filling": type_fill
                }
                if expirationdate is None:
                    del pending_order["expiration"]
                result = mt5.order_send(pending_order)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    raise Exception(f"Failed to send pending order. Error: {result}")

            elif (sl is None) and (tp is None):
                pending_order = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": symbol,
                    "volume": volume,
                    "price": price,
                    "type": type_op,
                    "type_time": mt5.ORDER_TIME_SPECIFIED,
                    "expiration": expirationdate,
                    "comment": strategy_name,
                    "type_filling": type_fill
                }
                if expirationdate is None:
                    del pending_order["expiration"]
                result = mt5.order_send(pending_order)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    raise Exception(f"Failed to send pending order. Error: {result}")
            print(f"{Utils.dateprint()} - Pending order sent successfully.")
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to send pending order. Exception: {e}")
            raise

    def buy_limit(self, symbol: str, volume: float, price: float, expirationdate, type_fill, sl: float = None, tp: float = None, strategy_name: str = 'Py'):
        self.send_pending_order(symbol, volume, price, mt5.ORDER_TYPE_BUY_LIMIT, expirationdate, type_fill, sl, tp, strategy_name)

    def sell_limit(self, symbol: str, volume: float, price: float, expirationdate, type_fill, sl: float = None, tp: float = None, strategy_name: str = 'Py'):
        self.send_pending_order(symbol, volume, price, mt5.ORDER_TYPE_SELL_LIMIT, expirationdate, type_fill, sl, tp, strategy_name)

    def buy_stop(self, symbol: str, volume: float, price: float, expirationdate, type_fill, sl: float = None, tp: float = None, strategy_name: str = 'Py'):
        self.send_pending_order(symbol, volume, price, mt5.ORDER_TYPE_BUY_STOP, expirationdate, type_fill, sl, tp, strategy_name)

    def sell_stop(self, symbol: str, volume: float, price: float, expirationdate, type_fill, sl: float = None, tp: float = None, strategy_name: str = 'Py'):
        self.send_pending_order(symbol, volume, price, mt5.ORDER_TYPE_SELL_STOP, expirationdate, type_fill, sl, tp, strategy_name)

    def get_today_calendar(self) -> pd.DataFrame:
        """
        Retrieves today's economic calendar from investing.com.
        """
        try:
            url = 'https://www.investing.com/economic-calendar/'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            r = Request(url, headers=headers)
            try:
                response = urlopen(r).read()
            except HTTPError as he:
                if he.code in (301, 302, 303, 307, 308) and he.headers.get('Location'):
                    redirect_url = he.headers.get('Location')
                    r = Request(redirect_url, headers=headers)
                    response = urlopen(r).read()
                else:
                    raise
            soup = BeautifulSoup(response, "html.parser")
            table = soup.find_all(class_="js-event-item")

            result = []
            base = {}

            for bl in table:
                time = bl.find(class_="first left time js-time").text
                currency = bl.find(class_="left flagCur noWrap").text.split(' ')
                intensity = bl.find_all(class_="left textNum sentiment noWrap")
                id_hour = currency[1] + '_' + time

                if not id_hour in base:
                    base.update({id_hour: {'currency': currency[1], 'time': time, 'intensity': 0}})

                intencity = 0
                for intence in intensity:
                    _true = intence.find_all(class_="grayFullBullishIcon")
                    if len(_true) == 1:
                        intencity = 1
                    elif len(_true) == 2:
                        intencity = 2
                    elif len(_true) == 3:
                        intencity = 3
                base[id_hour].update({'intensity': intencity})

            for b in base:
                result.append(base[b])

            news = pd.DataFrame.from_records(result)
            print(f"{Utils.dateprint()} - Economic calendar retrieved successfully.")
            return news
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to get economic calendar. Exception: {e}")
            return pd.DataFrame()

    def get_history_data(self, from_date: datetime, strategy_name: str, symbol: str) -> tuple:
        """
        Gets historical trades for a strategy and symbol.
        """
        try:
            history_orders = mt5.history_deals_get(from_date, datetime.now())
            if history_orders is None:
                raise Exception(f"Failed to get history deals. Error: {mt5.last_error()}")
            df = pd.DataFrame(list(history_orders), columns=history_orders[0]._asdict().keys())
            df['time'] = pd.to_datetime(df['time'], unit='s')

            df_names = df.copy()
            df_names = df_names[df_names['entry'] == 0]
            df_names = df_names[['position_id', 'comment']]
            df_names.columns = ['position_id', 'strategy_name']

            df_new = df.merge(df_names, how='left', on='position_id')
            df_new = df_new[df_new['entry'] == 1]

            df_est = df_new.copy()
            df_est = df_est[df_est['strategy_name'] == strategy_name]

            df_est['win'] = np.where(df_est['profit'] > 0, 1, 0)

            df_est_symbol = df_est.copy()
            df_est_symbol = df_est_symbol[df_est_symbol['symbol'] == symbol]

            win_trades = df_est_symbol['win'].sum()
            total_trades = len(df_est_symbol)

            print(f"{Utils.dateprint()} - History data retrieved for {strategy_name} on {symbol}.")
            return df_est_symbol, win_trades, total_trades
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to get history data for {strategy_name} on {symbol}. Exception: {e}")
            raise

    def is_market_open(self, symbol: str) -> bool:
        """
        Validates if the market is open for the given symbol based on trading sessions.

        Args:
            symbol (str): The symbol to check.

        Returns:
            bool: True if the market is open, False otherwise.
        """
        try:
            # Check if algo trading is enabled in terminal
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                print(f"{Utils.dateprint()} - WARNING: MT5 terminal not connected")
                return False
            if not terminal_info.trade_allowed:
                print(f"{Utils.dateprint()} - WARNING: Algorithmic trading not allowed in terminal")
                return False
            
            # Try to find symbol with various suffixes/formats
            info = self._find_symbol_info(symbol)
            if info is None:
                print(f"{Utils.dateprint()} - ERROR: Symbol {symbol} not found in any format. Available symbols: {self._get_sample_symbols()}")
                return False
            
            actual_symbol = info.name
            print(f"{Utils.dateprint()} - Using symbol: {actual_symbol} (requested: {symbol})")
            
            # Ensure symbol visible
            if not info.visible:
                if not mt5.symbol_select(actual_symbol, True):
                    print(f"{Utils.dateprint()} - ERROR: Unable to select {actual_symbol}. MT5 error: {mt5.last_error()}")
                    return False
                print(f"{Utils.dateprint()} - Symbol {actual_symbol} made visible")
            
            # Check if trading is disabled for this symbol
            if info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
                print(f"{Utils.dateprint()} - WARNING: Trading disabled for {actual_symbol}")
                return False
            
            # Check tick data
            tick = mt5.symbol_info_tick(actual_symbol)
            if tick is None:
                print(f"{Utils.dateprint()} - WARNING: No tick data for {actual_symbol}")
                return False
            if tick.time == 0:
                print(f"{Utils.dateprint()} - WARNING: Invalid tick time for {actual_symbol}")
                return False
            
            # Check if spread is available (usually 0 or very high when market closed)
            # Also check if bid/ask are valid
            if tick.bid == 0 or tick.ask == 0:
                return False
            
            # Check session trade - if no active trading session
            # session_deals = 0 means no trading session is active
            if hasattr(info, 'session_deals') and info.session_deals == 0:
                # Double check with session_trades
                if hasattr(info, 'session_buy_orders') and hasattr(info, 'session_sell_orders'):
                    if info.session_buy_orders == 0 and info.session_sell_orders == 0:
                        # Check time since last tick - if more than 5 minutes, market likely closed
                        import time as time_module
                        current_time = int(time_module.time())
                        if current_time - tick.time > 300:  # 5 minutes
                            return False
            
            # Final check: try to get current time from server and compare with session times
            # Use trade_mode to determine if trading is allowed
            if info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                # Check if we're in a trading session by examining last tick age
                import time as time_module
                current_time = int(time_module.time())
                tick_age = current_time - tick.time
                
                # If last tick is older than 2 minutes and spread is suspiciously wide, market might be closed
                if tick_age > 120:
                    # Market might be in weekend or holiday
                    spread_points = (tick.ask - tick.bid) / info.point
                    if spread_points > info.spread * 10:  # Spread way higher than normal
                        return False
            
            return True
        except Exception as e:
            print(f"{Utils.dateprint()} - ERROR: Failed to check market open for {symbol}. Exception: {e}")
            return False

    def _find_symbol_info(self, symbol: str):
        """
        Tries to find symbol info with various suffix/format variations.
        
        Args:
            symbol (str): Base symbol name (e.g., 'EURUSD')
            
        Returns:
            Symbol info object or None if not found
        """
        variations = []

        # 1) Broker-specific prefix/suffix from env (e.g. RoboForex: ".ecn", ".pro", etc.)
        #    Allows you to keep strategies using clean symbols like "EURUSD" while
        #    automatically mapping to the broker's actual market-watch name.
        custom_candidates = set()
        try:
            prefix = getattr(self, "symbol_prefix", "") or ""
            suffix = getattr(self, "symbol_suffix", "") or ""
        except AttributeError:
            prefix, suffix = "", ""

        if prefix or suffix:
            base = symbol
            custom_candidates.add(f"{prefix}{base}{suffix}")
            custom_candidates.add(f"{base}{suffix}")
            custom_candidates.add(f"{prefix}{base}")

        # 2) Common symbol variations used by different brokers
        common_variations = [
            symbol,                     # Original (EURUSD)
            symbol + "m",              # Micro lots (EURUSDm)
            symbol + ".c",             # CFD (EURUSD.c)
            symbol + ".",              # With dot (EURUSD.)
            symbol + "#",              # Hash suffix (EURUSD#)
            "#" + symbol,              # Hash prefix (#EURUSD)
            symbol + "_",              # Underscore (EURUSD_)
            symbol + "pro",            # Pro account (EURUSDpro)
            symbol + "pro-cent",       # Cent accounts with suffix (EURUSDpro-cent)
            symbol + "cent",           # Cent accounts (EURUSDcent)
            symbol + "fix",            # Fixed spread (EURUSDfix)
            symbol + "ex",             # Some ECN/EX accounts (EURUSDex)
            symbol.lower(),             # Lowercase (eurusd)
            symbol.upper(),             # Uppercase
            symbol + "c",              # Alternative CFD (EURUSDc)
            symbol + "ecn",            # ECN (EURUSDecn)
            "." + symbol,              # Dot prefix (.EURUSD)
        ]

        # Combine, keeping order: custom → common, removing duplicates while
        # preserving insertion order.
        seen = set()
        for candidate in list(custom_candidates) + common_variations:
            if candidate and candidate not in seen:
                variations.append(candidate)
                seen.add(candidate)
        
        for variant in variations:
            try:
                info = mt5.symbol_info(variant)
                if info is not None:
                    return info
            except:
                continue
        
        # If no exact variations found, try partial match in all symbols
        return self._search_symbol_by_pattern(symbol)
    
    def _search_symbol_by_pattern(self, symbol: str):
        """
        Searches for symbols containing the pattern in available symbols list.
        
        Args:
            symbol (str): Symbol pattern to search
            
        Returns:
            First matching symbol info or None
        """
        try:
            all_symbols = mt5.symbols_get()
            if not all_symbols:
                return None
            
            symbol_upper = symbol.upper()
            
            # First try exact matches
            for sym in all_symbols:
                if sym.name.upper() == symbol_upper:
                    return sym
            
            # Then try contains matches
            for sym in all_symbols:
                if symbol_upper in sym.name.upper():
                    # Prefer forex pairs (6-8 characters typically)
                    if len(sym.name) <= 10:
                        return sym
            
            return None
        except:
            return None
    
    def _get_sample_symbols(self, limit: int = 5) -> str:
        """
        Gets a sample of available symbols for debugging.
        
        Args:
            limit (int): Number of symbols to return
            
        Returns:
            Comma-separated string of sample symbols
        """
        try:
            symbols = mt5.symbols_get()
            if not symbols:
                return "No symbols available"
            
            # Get first few forex pairs for reference
            forex_symbols = []
            for sym in symbols:
                name = sym.name
                # Typical forex pair patterns
                if len(name) in [6, 7, 8] and any(curr in name.upper() for curr in ['EUR', 'USD', 'GBP', 'JPY']):
                    forex_symbols.append(name)
                    if len(forex_symbols) >= limit:
                        break
            
            if forex_symbols:
                return ", ".join(forex_symbols[:limit])
            else:
                # Return any symbols if no forex found
                return ", ".join([sym.name for sym in symbols[:limit]])
        except:
            return "Error getting symbols"
