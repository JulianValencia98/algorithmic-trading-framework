import json
import os
import pandas as pd
import MetaTrader5 as mt5
import streamlit as st

from Easy_Trading import BasicTrading
from data.repositories.trade_repository import TradeRepository
from data.trade_logger import TradeLogger


def read_bots_state() -> dict:
    """Lee el estado de los bots desde el archivo JSON compartido.
    
    Returns:
        Diccionario con el estado: {'global_paused': bool, 'bots': [...]}
        Retorna estado vacío si el archivo no existe.
    """
    state_file = os.path.join(os.path.dirname(__file__), 'bots_state.json')
    try:
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error leyendo estado de bots: {e}")
    return {'global_paused': False, 'bots': []}


def send_bot_command(action: str, bot_id: str = None):
    """Envía un comando al framework escribiendo en el archivo de comandos.
    
    Args:
        action: Acción a ejecutar (pause, resume, stop, restart, pause_all, resume_all)
        bot_id: ID del bot (opcional para acciones globales)
    """
    commands_file = os.path.join(os.path.dirname(__file__), 'bots_commands.json')
    
    # Leer comandos existentes (si hay)
    existing_commands = []
    try:
        if os.path.exists(commands_file):
            with open(commands_file, 'r') as f:
                existing_commands = json.load(f)
    except:
        existing_commands = []
    
    # Añadir nuevo comando
    new_command = {'action': action}
    if bot_id:
        new_command['bot_id'] = bot_id
    existing_commands.append(new_command)
    
    # Escribir archivo
    try:
        with open(commands_file, 'w') as f:
            json.dump(existing_commands, f, indent=2)
    except Exception as e:
        st.error(f"Error enviando comando: {e}")


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
    st.markdown("Información básica de cuenta, posiciones abiertas y control de bots.")

    bt_client = get_bt_client()

    # Sección cuenta
    st.subheader("Información de Cuenta")
    # Botón para refrescar manualmente los datos básicos de la cuenta
    if st.button("🔄 Refrescar datos de cuenta"):
        try:
            # Si la conexión se ha caído, intentar reconectar antes de leer datos
            if not bt_client.check_connection():
                bt_client.reconnect()
        except Exception as e:
            st.warning(f"No se pudo refrescar la conexión MT5: {e}")

    col0, col1, col2, col3, col4 = st.columns([1.5, 2, 2, 2, 2])

    # Indicador de conexión MT5
    try:
        if bt_client.check_connection():
            col0.success("MT5 conectado")
        else:
            col0.error("MT5 desconectado")
    except Exception:
        col0.warning("Estado MT5 desconocido")

    # Tipo de cuenta (DEMO / REAL)
    try:
        if bt_client.is_demo_account():
            col0.caption("Cuenta DEMO")
        else:
            col0.caption("Cuenta REAL")
    except Exception:
        col0.caption("Tipo de cuenta desconocido")

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
    bots_state = read_bots_state()
    bot_status_list = bots_state.get('bots', [])
    
    # Contador de bots activos
    running_count = sum(1 for b in bot_status_list if b.get('status') in ['running', 'waiting_market'])
    paused_count = sum(1 for b in bot_status_list if b.get('status') == 'paused')
    total_count = len(bot_status_list)
    
    # Expander para ver y controlar bots
    with st.expander(f"🤖 Bots ({running_count} activos / {total_count} total)", expanded=False):
        if not bot_status_list:
            st.info("No hay bots. Inicia el framework con `python simple_trading_app.py`")
        else:
            # Botón refrescar arriba
            if st.button("🔄 Actualizar estado"):
                st.rerun()
            
            st.write("")
            
            for status in bot_status_list:
                if not status:
                    continue
                bot_id = status["bot_id"]
                bot_status_str = status['status']
                
                # Icono según estado
                status_colors = {
                    'running': '🟢',
                    'paused': '🟡',
                    'waiting_market': '🔵',
                    'stopped': '🔴',
                    'starting': '⚪'
                }
                color = status_colors.get(bot_status_str, '⚪')
                
                # Una fila por bot: Indicador + Nombre + Controles tipo video
                col_indicator, col_name, col_play, col_pause, col_stop = st.columns([0.5, 4, 0.8, 0.8, 0.8])
                
                col_indicator.write(color)
                col_name.write(f"**{bot_id}** ({status['symbol']})")
                
                # Play (reanudar)
                play_disabled = bot_status_str not in ['paused', 'stopped']
                if col_play.button("▶️", key=f"play_{bot_id}", disabled=play_disabled):
                    if bot_status_str == 'stopped':
                        send_bot_command('restart', bot_id)
                    else:
                        send_bot_command('resume', bot_id)
                    st.rerun()
                
                # Pause
                pause_disabled = bot_status_str not in ['running', 'waiting_market']
                if col_pause.button("⏸️", key=f"pause_{bot_id}", disabled=pause_disabled):
                    send_bot_command('pause', bot_id)
                    st.rerun()
                
                # Stop
                stop_disabled = bot_status_str == 'stopped'
                if col_stop.button("⏹️", key=f"stop_{bot_id}", disabled=stop_disabled):
                    send_bot_command('stop', bot_id)
                    st.rerun()

    # Estadísticas agregadas por bot (desde la base de datos)
    st.write("### Estadísticas por Bot")
    try:
        repo = get_trade_repository()
        trade_logger = TradeLogger(repository=repo)
        bot_stats = trade_logger.get_all_stats()
        if not bot_stats:
            st.info("No hay estadísticas de trading por bot todavía.")
        else:
            df_bot_stats = pd.DataFrame(bot_stats)
            st.dataframe(df_bot_stats, use_container_width=True)
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
