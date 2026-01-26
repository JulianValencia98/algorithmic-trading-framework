from dotenv import load_dotenv, find_dotenv
import MetaTrader5 as mt5
import sys, os
# Ensure project root is on sys.path for imports when running tests directly
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from Easy_Trading import BasicTrading


def main():
    load_dotenv(find_dotenv())
    try:
        bt = BasicTrading()
        # Test basic connection by getting account info
        balance, profit, equity, free_margin = bt.info_account()
        print(f"MT5 Connection OK - Balance: {balance}, Equity: {equity}")
    except Exception as e:
        print("Error al conectar:", e)
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
