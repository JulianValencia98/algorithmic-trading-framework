import os
import pandas as pd
import MetaTrader5 as mt5
import streamlit as st

from Easy_Trading import BasicTrading
from data.repositories.trade_repository import TradeRepository
from trading_director.app_director import AppDirector, BotConfig
from utils.strategy_discovery import StrategyDiscovery
from utils.utils import Utils


@st.cache_resource(show_spinner=False)
def get_bt_client() -> BasicTrading:
    """Crea una única instancia de BasicTrading (MT5)."""
    return BasicTrading()


def get_app_director() -> AppDirector:
    """Crea una instancia de AppDirector para controlar los bots.

    No se cachea para garantizar que siempre tenga los métodos más recientes
    cuando cambia el código durante el desarrollo.
    """
    bt_client = get_bt_client()
    return AppDirector(bt_client, notification_service=None)


@st.cache_resource(show_spinner=False)
def get_trade_repository() -> TradeRepository:
    """Crea un repositorio de trades para la cuenta MT5 actual."""
    account_id = None
    try:
        account_info = mt5.account_info()
        if account_info:
            account_id = account_info.login
    except Exception:
        account_id = None
    return TradeRepository(account_id=account_id)


def create_default_bots() -> list:
    """Replica la lógica de simple_trading_app para detectar y crear bots por defecto."""
    bots = []
    strategies = StrategyDiscovery.get_all_strategies()
    strategy_symbols = StrategyDiscovery.get_strategy_symbols()

    for strategy_name, strategy_class in strategies.items():
        symbols = strategy_symbols.get(strategy_name, ['EURUSD'])
        for symbol in symbols:
            try:
                strategy_instance = strategy_class()
                bot = BotConfig(
                    strategy=strategy_instance,
                    symbol=symbol,
                    timeframe=mt5.TIMEFRAME_M1,
                    interval_seconds=60,
                    data_points=100,
                )
                bots.append(bot)
            except Exception as e:
                print(f"{Utils.dateprint()} - [Streamlit] Error creando bot para {strategy_name}-{symbol}: {e}")

    return bots


def main():
    st.set_page_config(page_title="Framework Trading - Dashboard", layout="wide")
    st.title("Framework Trading - Dashboard")
    st.markdown("Información básica de cuenta, posiciones abiertas y control de bots.")

    bt_client = get_bt_client()
    app_director = get_app_director()

    # Sección cuenta
    st.subheader("Información de Cuenta")
    col0, col1, col2, col3, col4 = st.columns([1.5, 2, 2, 2, 2])

    # Indicador de conexión MT5
    try:
        if bt_client.check_connection():
            col0.success("MT5 conectado")
        else:
            col0.error("MT5 desconectado")
    except Exception:
        col0.warning("Estado MT5 desconocido")

    try:
        balance, profit, equity, free_margin = bt_client.info_account()
        col1.metric("Balance", f"{balance:,.2f}")
        col2.metric("Profit", f"{profit:,.2f}")
        col3.metric("Equity", f"{equity:,.2f}")
        col4.metric("Free Margin", f"{free_margin:,.2f}")
    except Exception as e:
        st.error(f"No se pudo obtener info de cuenta: {e}")

    st.divider()

    # ==================== CONTROL DE BOTS ====================
    st.subheader("Control de Bots")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        if st.button("🔄 Iniciar bots por defecto", help="Crea y arranca bots detectando estrategias disponibles"):
            default_bots = create_default_bots()
            if not default_bots:
                st.warning("No se encontraron estrategias válidas para crear bots.")
            else:
                created = 0
                for bot in default_bots:
                    if app_director.add_bot(bot):
                        created += 1
                st.success(f"Se intentaron crear {len(default_bots)} bots. Bots agregados: {created}.")

        if st.button("⏹️ Detener todos los bots"):
            app_director.stop_all_bots()
            st.success("Todos los bots detenidos.")

    with col_right:
        if app_director.is_globally_paused():
            st.info("Sistema en pausa global (todos los bots pausados).")

    bot_status_list = app_director.get_all_bots_status()
    if not bot_status_list:
        st.info("No hay bots activos actualmente.")
    else:
        st.write("### Estado de bots activos")
        for status in bot_status_list:
            if not status:
                continue
            bot_id = status["bot_id"]
            cols = st.columns([3, 2, 2, 2, 3])
            cols[0].markdown(f"**{bot_id}**")
            cols[1].write(f"Status: {status['status']}")
            cols[2].write(f"Símbolo: {status['symbol']}")
            cols[3].write(f"TF: {status['timeframe']}")

            with cols[4]:
                c1, c2 = st.columns(2)
                if status['status'] in ['running', 'waiting_market']:
                    if c1.button("⏸️ Pausar", key=f"pause_{bot_id}"):
                        app_director.pause_bot(bot_id)
                        st.experimental_rerun()
                elif status['status'] == 'paused':
                    if c1.button("▶️ Reanudar", key=f"resume_{bot_id}"):
                        app_director.resume_bot(bot_id)
                        st.experimental_rerun()
                # Botón de reinicio disponible siempre
                if c2.button("🔁 Reiniciar", key=f"restart_{bot_id}"):
                    app_director.restart_bot(bot_id)
                    st.experimental_rerun()

    # Estadísticas agregadas por bot (desde la base de datos)
    st.write("### Estadísticas por Bot")
    try:
        bot_stats = app_director.get_all_trading_stats()
        if not bot_stats:
            st.info("No hay estadísticas de trading por bot todavía.")
        else:
            df_bot_stats = pd.DataFrame(bot_stats)
            st.dataframe(df_bot_stats, width="stretch")
    except Exception as e:
        st.error(f"No se pudieron cargar las estadísticas por bot: {e}")

    st.divider()

    # Sección posiciones
    st.subheader("Posiciones Abiertas")
    if st.button("Refrescar Posiciones"):
        try:
            count, df_pos = bt_client.get_opened_positions()
            if count == 0:
                st.info("Sin posiciones abiertas.")
            else:
                st.success(f"{count} posiciones abiertas.")
                st.dataframe(df_pos, width="stretch")
        except Exception as e:
            st.error(f"No se pudieron obtener posiciones: {e}")

    st.divider()

    # Sección estadísticas históricas desde la base de datos
    st.subheader("Histórico de Cuenta (P&L acumulado)")
    try:
        repo = get_trade_repository()
        trades = repo.get_all_trades(limit=100000)

        if not trades:
            st.info("No hay trades registrados en la base de datos aún.")
        else:
            df_trades = pd.DataFrame([t.to_dict() for t in trades])

            # Filtrar solo trades cerrados con profit válido
            df_closed = df_trades[
                (df_trades["status"] == "closed")
                & df_trades["profit"].notna()
                & df_trades["closed_at"].notna()
            ].copy()

            if df_closed.empty:
                st.info("No hay trades cerrados para calcular el P&L acumulado.")
            else:
                # Parsear timestamps ISO8601 (incluyendo microsegundos) de forma robusta
                df_closed["closed_at"] = pd.to_datetime(
                    df_closed["closed_at"], format="ISO8601", errors="coerce"
                )
                df_closed["date"] = df_closed["closed_at"].dt.date

                daily = (
                    df_closed
                    .groupby("date")["profit"]
                    .sum()
                    .reset_index()
                    .rename(columns={"profit": "daily_profit"})
                )
                daily["date"] = pd.to_datetime(daily["date"])
                daily["equity_curve"] = daily["daily_profit"].cumsum()

                st.line_chart(daily.set_index("date")["equity_curve"], height=300)
                st.caption("Curva de P&L acumulado basada en los trades registrados por el framework.")

            # Estadísticas por estrategia: ganadores y perdedores
            st.subheader("Resultados por Estrategia")
            if "strategy_name" in df_trades.columns and not df_closed.empty:
                df_closed["is_win"] = df_closed["profit"] > 0
                df_closed["is_loss"] = df_closed["profit"] < 0

                stats = (
                    df_closed
                    .groupby("strategy_name")
                    .agg(
                        total_trades=("profit", "size"),
                        wins=("is_win", "sum"),
                        losses=("is_loss", "sum"),
                        total_profit=("profit", "sum"),
                    )
                    .reset_index()
                )

                # Calcular win rate
                stats["win_rate"] = stats.apply(
                    lambda row: (row["wins"] / row["total_trades"] * 100) if row["total_trades"] > 0 else 0,
                    axis=1,
                )

                # Ordenar por total_profit desc
                stats = stats.sort_values("total_profit", ascending=False)

                st.dataframe(stats, width="stretch")
            else:
                st.info("No hay información suficiente para calcular estadísticas por estrategia.")

    except Exception as e:
        st.error(f"Error al cargar estadísticas históricas: {e}")


if __name__ == "__main__":
    main()
