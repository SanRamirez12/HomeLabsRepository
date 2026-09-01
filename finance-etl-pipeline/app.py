"""
app.py

Dashboard de Streamlit que visualiza los datos ya transformados por dbt:
retornos diarios y media móvil de 7 días, por ticker.

Corre con:
    streamlit run app.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine

from src.config import Config

# --- Configuración general de la página (debe ir primero, antes de
# cualquier otro comando de Streamlit) ---
st.set_page_config(
    page_title="Finance ETL Dashboard",
    page_icon="📈",
    layout="wide",
)


# --- Conexión a la base de datos ---
# @st.cache_resource evita reabrir una conexión nueva cada vez que el
# usuario interactúa con la app (Streamlit re-ejecuta todo el script
# en cada interacción, así que cachear el engine es importante para
# no saturar el pool de conexiones de Supabase).
@st.cache_resource
def get_engine():
    return create_engine(Config.get_db_url())


# --- Carga de datos ---
# @st.cache_data cachea el RESULTADO de la query, no solo la conexión.
# ttl=300 significa "recachea cada 5 minutos" -- así el dashboard no
# golpea la base de datos en cada click, pero tampoco muestra datos
# eternamente viejos si el pipeline diario ya corrió.
@st.cache_data(ttl=300)
def load_daily_returns() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT ticker, price_date, close_price, daily_return_pct
        FROM analytics.daily_returns
        ORDER BY ticker, price_date
    """
    return pd.read_sql(query, engine)


@st.cache_data(ttl=300)
def load_rolling_avg() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT ticker, price_date, close_price, moving_avg_7d
        FROM analytics.rolling_avg_price
        ORDER BY ticker, price_date
    """
    return pd.read_sql(query, engine)


# --- Header ---
st.title("📈 Finance ETL Pipeline — Dashboard")
st.caption(
    "Datos extraídos diariamente de Yahoo Finance, transformados con dbt. "
    "Pipeline automatizado con GitHub Actions."
)

# --- Cargar datos ---
returns_df = load_daily_returns()
rolling_df = load_rolling_avg()

# --- Sidebar: selector de ticker ---
# sorted() + unique() para tener la lista de tickers ordenada
# alfabéticamente en el dropdown, sin duplicados.
available_tickers = sorted(returns_df["ticker"].unique())
selected_ticker = st.sidebar.selectbox("Selecciona un ticker", available_tickers)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Sobre este dashboard**\n\n"
    "Construido con Streamlit, conectado en vivo a una base de datos "
    "PostgreSQL (Supabase) transformada con dbt.\n\n"
    "[Ver código en GitHub](https://github.com/SanRamirez12/HomeLabsRepository)"
)

# --- Filtrar datos por el ticker seleccionado ---
ticker_returns = returns_df[returns_df["ticker"] == selected_ticker]
ticker_rolling = rolling_df[rolling_df["ticker"] == selected_ticker]

# --- Métricas rápidas (KPIs) ---
col1, col2, col3 = st.columns(3)

latest_price = ticker_rolling["close_price"].iloc[-1] if not ticker_rolling.empty else 0
latest_return = ticker_returns["daily_return_pct"].iloc[-1] if not ticker_returns.empty else 0
avg_return = ticker_returns["daily_return_pct"].mean() if not ticker_returns.empty else 0

col1.metric("Precio más reciente", f"${latest_price:,.2f}")
col2.metric("Retorno diario más reciente", f"{latest_return:.2f}%")
col3.metric("Retorno diario promedio", f"{avg_return:.2f}%")

st.markdown("---")

# --- Gráfico 1: Precio de cierre + media móvil de 7 días ---
st.subheader(f"Precio de cierre y media móvil (7 días) — {selected_ticker}")

fig_price = go.Figure()
fig_price.add_trace(go.Scatter(
    x=ticker_rolling["price_date"],
    y=ticker_rolling["close_price"],
    mode="lines",
    name="Precio de cierre",
    line=dict(color="#636EFA"),
))
fig_price.add_trace(go.Scatter(
    x=ticker_rolling["price_date"],
    y=ticker_rolling["moving_avg_7d"],
    mode="lines",
    name="Media móvil 7 días",
    line=dict(color="#EF553B", dash="dash"),
))
fig_price.update_layout(
    xaxis_title="Fecha",
    yaxis_title="Precio (USD)",
    hovermode="x unified",
)
st.plotly_chart(fig_price, use_container_width=True)

# --- Gráfico 2: Retorno diario en porcentaje ---
st.subheader(f"Retorno diario (%) — {selected_ticker}")

# Colorea las barras: verde si el retorno fue positivo, rojo si negativo.
# Esto es una convención visual estándar en finanzas.
bar_colors = [
    "#2ECC71" if val >= 0 else "#E74C3C"
    for val in ticker_returns["daily_return_pct"]
]

fig_returns = go.Figure(go.Bar(
    x=ticker_returns["price_date"],
    y=ticker_returns["daily_return_pct"],
    marker_color=bar_colors,
))
fig_returns.update_layout(
    xaxis_title="Fecha",
    yaxis_title="Retorno diario (%)",
)
st.plotly_chart(fig_returns, use_container_width=True)

# --- Tabla de datos crudos (opcional, expandible) ---
with st.expander("Ver datos en tabla"):
    st.dataframe(
        ticker_returns.merge(
            ticker_rolling[["price_date", "moving_avg_7d"]],
            on="price_date",
        ),
        use_container_width=True,
    )