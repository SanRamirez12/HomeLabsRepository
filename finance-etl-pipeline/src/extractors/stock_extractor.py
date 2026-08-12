"""
stock_extractor.py

Extractor concreto que hereda de BaseExtractor. Se conecta a Yahoo Finance
(a través de la librería yfinance) y trae precios históricos de una o
varias acciones.

Este archivo es la implementación REAL del contrato que definimos en
base_extractor.py -- por eso implementa extract(), que ahí era abstracto.
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

from src.extractors.base_extractor import BaseExtractor


class StockExtractor(BaseExtractor):
    """
    Extractor de precios históricos de acciones vía yfinance.

    Hereda de BaseExtractor, así que automáticamente tiene los métodos
    validate() y run() sin tener que reescribirlos.
    """

    def __init__(self, tickers: list[str], period: str = "1mo", interval: str = "1d"):
        """
        Args:
            tickers: lista de símbolos bursátiles, ej. ["AAPL", "MSFT", "GOOGL"]
            period: rango de tiempo a traer. Ej: "1d", "5d", "1mo", "1y", "max"
            interval: granularidad de los datos. Ej: "1d" (diario), "1h" (horario)
        """
        # super().__init__() llama al constructor de la clase padre
        # (BaseExtractor), que es quien define self.source_name
        super().__init__(source_name="yahoo_finance")

        self.tickers = tickers
        self.period = period
        self.interval = interval

    def extract(self) -> pd.DataFrame:
        """
        Implementación real de la extracción. Este método es el que
        BaseExtractor exigía que existiera (era @abstractmethod ahí).

        Recorre cada ticker, descarga sus datos históricos con yfinance,
        y los junta todos en un solo DataFrame "largo" (long format),
        que es la forma más fácil de cargar a una tabla SQL después.

        Returns:
            pd.DataFrame con columnas:
            [ticker, date, open, high, low, close, volume, extracted_at]
        """
        all_data = []

        for ticker in self.tickers:
            print(f"[{self.source_name}] Descargando {ticker}...")

            stock = yf.Ticker(ticker)
            hist = stock.history(period=self.period, interval=self.interval)

            if hist.empty:
                print(f"[{self.source_name}] Sin datos para {ticker}, se omite.")
                continue

            # yfinance devuelve la fecha como índice del DataFrame;
            # la convertimos en una columna normal para que sea más
            # fácil de cargar a SQL más adelante.
            hist = hist.reset_index()

            # Normalizamos nombres de columnas a minúsculas y sin espacios,
            # buena práctica para que luego dbt/SQL no se pelee con
            # mayúsculas o espacios en los nombres.
            hist.columns = [col.lower().replace(" ", "_") for col in hist.columns]

            # Agregamos metadata útil: de qué ticker es cada fila,
            # y cuándo se extrajo (importante para auditar el pipeline).
            hist["ticker"] = ticker
            hist["extracted_at"] = datetime.now(timezone.utc)

            all_data.append(hist)

        if not all_data:
            # Si ningún ticker trajo datos, devolvemos un DataFrame vacío
            # en vez de None -- así el resto del pipeline no se rompe
            # esperando un tipo de dato distinto.
            return pd.DataFrame()

        # pd.concat junta todos los DataFrames individuales (uno por
        # ticker) en uno solo.
        combined_df = pd.concat(all_data, ignore_index=True)

        return combined_df


# Esto permite correr este archivo solo, directamente, para probarlo
# rápido sin tener que montar todo el pipeline completo todavía.
# Se ejecuta SOLO si corres "python stock_extractor.py" directamente,
# no cuando lo importas desde otro archivo.
if __name__ == "__main__":
    extractor = StockExtractor(tickers=["AAPL", "MSFT"], period="5d")
    df = extractor.run()
    print(df.head())