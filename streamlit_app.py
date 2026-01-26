import os
import pandas as pd
import MetaTrader5 as mt5
import streamlit as st

from Easy_Trading import BasicTrading


@st.cache_resource(show_spinner=False)
def get_bt_client() -> BasicTrading:
    """Crea una única instancia de BasicTrading (MT5)."""
    return BasicTrading()


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
                st.dataframe(df_pos, use_container_width=True)
        except Exception as e:
            st.error(f"No se pudieron obtener posiciones: {e}")


if __name__ == "__main__":
    main()
