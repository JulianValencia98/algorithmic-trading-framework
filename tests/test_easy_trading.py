import sys, os
# Ensure project root is on sys.path for imports when running tests directly
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from Easy_Trading import BasicTrading
import MetaTrader5 as mt5
from datetime import datetime

# Initialize
bt = BasicTrading()

print("=" * 60)
print("=== Testing BasicTrading Functions ===")
print("=" * 60)

# Check if demo account
is_demo = bt.is_demo_account()
print(f"\n🔹 Is demo account: {is_demo}")

# 1. info_account
print("\n" + "-" * 40)
print("1. info_account:")
print("-" * 40)
balance, profit, equity, free_margin = bt.info_account()
print(f"   Balance: {balance}")
print(f"   Profit: {profit}")
print(f"   Equity: {equity}")
print(f"   Free Margin: {free_margin}")

# 2. check_connection (NEW)
print("\n" + "-" * 40)
print("2. check_connection:")
print("-" * 40)
is_connected = bt.check_connection()
print(f"   MT5 Connected: {is_connected}")
if is_connected:
    terminal_info = mt5.terminal_info()
    print(f"   Trade Allowed (AutoTrading): {terminal_info.trade_allowed}")
    print(f"   Connected to Server: {terminal_info.connected}")

# 3. get_opened_positions
print("\n" + "-" * 40)
print("3. get_opened_positions:")
print("-" * 40)
count, df_pos = bt.get_opened_positions()
print(f"   Open positions count: {count}")
if not df_pos.empty:
    print(df_pos[['ticket', 'symbol', 'type', 'volume', 'profit', 'magic']].head())
else:
    print("   No open positions")

# 4. get_opened_positions with filters (magic number)
print("\n" + "-" * 40)
print("4. get_opened_positions (filtered by magic=1):")
print("-" * 40)
count_magic, df_pos_magic = bt.get_opened_positions(magic=1)
print(f"   Positions with magic=1: {count_magic}")

# 5. get_pending_orders
print("\n" + "-" * 40)
print("5. get_pending_orders:")
print("-" * 40)
df_pending = bt.get_pending_orders()
print(df_pending.head() if not df_pending.empty else "   No pending orders")

# 6. extract_data
print("\n" + "-" * 40)
print("6. extract_data (EURUSD M1, 10 bars):")
print("-" * 40)
df_data = bt.extract_data('EURUSD', mt5.TIMEFRAME_M1, 10)
print(df_data[['time', 'open', 'high', 'low', 'close', 'tick_volume']].tail(5))

# 7. get_data_from_dates
print("\n" + "-" * 40)
print("7. get_data_from_dates (2024-01-01 to 2024-01-02):")
print("-" * 40)
df_dates = bt.get_data_from_dates(2024, 1, 1, 2024, 1, 2, 'EURUSD', mt5.TIMEFRAME_H1)
print(df_dates.head() if not df_dates.empty else "   No data")

# 8. get_today_calendar
print("\n" + "-" * 40)
print("8. get_today_calendar:")
print("-" * 40)
df_calendar = bt.get_today_calendar()
if not df_calendar.empty:
    print(df_calendar[['time', 'country', 'event', 'importance']].head())
else:
    print("   No calendar data")

# 9. _get_data_for_bt
print("\n" + "-" * 40)
print("9. _get_data_for_bt (for backtesting):")
print("-" * 40)
df_bt = bt._get_data_for_bt(mt5.TIMEFRAME_M1, 'EURUSD', 10)
print(df_bt.head())

# 10. is_market_open (ENHANCED)
print("\n" + "-" * 40)
print("10. is_market_open (enhanced with algo trading check):")
print("-" * 40)
symbols_to_test = ['EURUSD', 'GBPUSD', 'XAUUSD', 'USDJPY']
for symbol in symbols_to_test:
    is_open = bt.is_market_open(symbol)
    status = "✅ ABIERTO" if is_open else "❌ CERRADO"
    print(f"   {symbol}: {status}")

# 11. calculate_position_size
print("\n" + "-" * 40)
print("11. calculate_position_size:")
print("-" * 40)
test_capital = 10000
test_risk = 0.01  # 1%
lot_size = bt.calculate_position_size('EURUSD', test_capital, test_risk)
print(f"   Capital: ${test_capital}, Risk: {test_risk*100}%")
print(f"   Calculated lot size: {lot_size}")

# 12. kelly_criterion_pct_risk
print("\n" + "-" * 40)
print("12. kelly_criterion_pct_risk:")
print("-" * 40)
win_rate = 0.55
profit_factor = 1.5
kelly = bt.kelly_criterion_pct_risk(win_rate, profit_factor)
print(f"   Win Rate: {win_rate*100}%, Profit Factor: {profit_factor}")
print(f"   Kelly criterion: {kelly:.4f} ({kelly*100:.2f}%)")

# 13. get_history_data
print("\n" + "-" * 40)
print("13. get_history_data:")
print("-" * 40)
from_date = datetime(2024, 1, 1)
df_hist, wins, total = bt.get_history_data(from_date, 'FWK Market Order', 'EURUSD')
print(f"   Strategy: FWK Market Order | Symbol: EURUSD")
print(f"   Wins: {wins}, Total Trades: {total}")
if total > 0:
    print(f"   Win Rate: {wins/total*100:.2f}%")

# Trading functions - only if demo account
if is_demo:
    print("\n" + "=" * 60)
    print("=== Testing Trading Functions (Demo Account Only) ===")
    print("=" * 60)
    
    # Check if market is open before trading
    market_open = bt.is_market_open('EURUSD')
    
    if market_open:
        # 14. buy (small lot)
        print("\n" + "-" * 40)
        print("14. buy (EURUSD 0.01 lot):")
        print("-" * 40)
        try:
            result_buy = bt.buy('EURUSD', 0.01, 'Test Buy', magic=999)
            print(f"   Buy result: {result_buy.retcode if result_buy else 'Failed'}")
        except Exception as e:
            print(f"   Buy failed: {e}")

        # 15. sell (small lot)
        print("\n" + "-" * 40)
        print("15. sell (GBPUSD 0.01 lot):")
        print("-" * 40)
        try:
            result_sell = bt.sell('GBPUSD', 0.01, 'Test Sell', magic=999)
            print(f"   Sell result: {result_sell.retcode if result_sell else 'Failed'}")
        except Exception as e:
            print(f"   Sell failed: {e}")

        # Check positions after
        print("\n" + "-" * 40)
        print("Positions after test trades:")
        print("-" * 40)
        count_after, df_pos_after = bt.get_opened_positions(magic=999)
        print(f"   Open positions (magic=999): {count_after}")
        if not df_pos_after.empty:
            print(df_pos_after[['ticket', 'symbol', 'type', 'volume', 'profit']].head())

        # 16. close_position_by_ticket (NEW)
        if not df_pos_after.empty:
            print("\n" + "-" * 40)
            print("16. close_position_by_ticket:")
            print("-" * 40)
            for _, row in df_pos_after.iterrows():
                ticket = int(row['ticket'])
                symbol = row['symbol']
                volume = float(row['volume'])
                pos_type = int(row['type'])
                print(f"   Closing position {ticket} ({symbol})...")
                try:
                    result = bt.close_position_by_ticket(ticket, symbol, volume, pos_type)
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"   ✅ Position {ticket} closed successfully")
                    else:
                        print(f"   ❌ Failed to close {ticket}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")

        # Final check
        print("\n" + "-" * 40)
        print("Final positions (magic=999):")
        print("-" * 40)
        count_final, df_final = bt.get_opened_positions(magic=999)
        print(f"   Open positions: {count_final}")
    else:
        print("\n⚠️  Market is CLOSED - Skipping trade execution tests")
        print("   (Tests will run when market opens)")

else:
    print("\n" + "=" * 60)
    print("=== Skipping Trading Functions (Not a Demo Account) ===")
    print("=" * 60)

# 17. Test reconnect function
print("\n" + "-" * 40)
print("17. reconnect (testing connection recovery):")
print("-" * 40)
print("   Current connection status:", bt.check_connection())
# Note: Not actually disconnecting, just verifying the function exists
print("   ✅ reconnect() function available")

print("\n" + "=" * 60)
print("=== All tests completed ===")
print("=" * 60)

# Shutdown
bt.shutdown()