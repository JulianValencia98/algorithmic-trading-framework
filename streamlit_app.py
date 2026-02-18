import os
import pandas as pd
import MetaTrader5 as mt5
import streamlit as st

from Easy_Trading import BasicTrading
from data.repositories.trade_repository import TradeRepository


@st.cache_resource(show_spinner=False)
def get_bt_client() -> BasicTrading:
    """Crea una única instancia de BasicTrading (MT5)."""
    return BasicTrading()


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


def main():
    st.set_page_config(page_title="Framework Trading - Dashboard", layout="wide")
    st.title("Framework Trading - Dashboard")
    st.markdown("Información básica de cuenta y posiciones abiertas.")

    bt_client = get_bt_client()

    # Sección cuenta
    st.subheader("Información de Cuenta")
    col1, col2, col3, col4 = st.columns(4)
    try:
        balance, profit, equity, free_margin = bt_client.info_account()
        col1.metric("Balance", f"{balance:,.2f}")
        col2.metric("Profit", f"{profit:,.2f}")
        col3.metric("Equity", f"{equity:,.2f}")
        col4.metric("Free Margin", f"{free_margin:,.2f}")
    except Exception as e:
        st.error(f"No se pudo obtener info de cuenta: {e}")

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
                df_closed["closed_at"] = pd.to_datetime(df_closed["closed_at"])
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
