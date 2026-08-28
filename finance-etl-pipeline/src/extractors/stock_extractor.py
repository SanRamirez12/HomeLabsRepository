"""
stock_extractor.py

Extractor concreto que hereda de BaseExtractor. Se conecta a Yahoo Finance
(a través de la librería yfinance) y trae precios históricos de una o
varias acciones.

Incluye reintentos con espera (retry + backoff) porque Yahoo Finance aplica
rate limiting agresivo a IPs compartidas, como las de GitHub Actions --
sin esto, el pipeline automatizado falla intermitentemente en la nube
aunque funcione perfecto en una máquina local.
"""

import time
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from src.extractors.base_extractor import BaseExtractor


class StockExtractor(BaseExtractor):
    """
    Extractor de precios históricos de acciones vía yfinance.

    Hereda de BaseExtractor, así que automáticamente tiene los métodos
    validate() y run() sin tener que reescribirlos.
    """

    def __init__(
        self,
        tickers: list[str],
        period: str = "1mo",
        interval: str = "1d",
        max_retries: int = 3,
        retry_wait_seconds: int = 15,
    ):
        """
        Args:
            tickers: lista de símbolos bursátiles, ej. ["AAPL", "MSFT", "GOOGL"]
            period: rango de tiempo a traer. Ej: "1d", "5d", "1mo", "1y", "max"
            interval: granularidad de los datos. Ej: "1d" (diario), "1h" (horario)
            max_retries: cuántas veces reintentar un ticker si Yahoo devuelve
                         rate limit, antes de darlo por perdido y continuar
            retry_wait_seconds: cuántos segundos esperar entre reintentos
        """
        super().__init__(source_name="yahoo_finance")

        self.tickers = tickers
        self.period = period
        self.interval = interval
        self.max_retries = max_retries
        self.retry_wait_seconds = retry_wait_seconds

    def _download_with_retry(self, ticker: str) -> pd.DataFrame:
        """
        Descarga el historial de un ticker, reintentando con espera si
        Yahoo Finance responde con rate limit (YFRateLimitError).

        Este método es "privado" -- es un detalle interno de cómo
        StockExtractor maneja la comunicación con la API, no algo que
        el resto del pipeline necesite saber.
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                stock = yf.Ticker(ticker)
                return stock.history(period=self.period, interval=self.interval)

            except YFRateLimitError as error:
                last_error = error
                print(
                    f"[{self.source_name}] Rate limit en {ticker} "
                    f"(intento {attempt}/{self.max_retries}). "
                    f"Esperando {self.retry_wait_seconds}s..."
                )
                # No esperamos después del último intento -- si ya
                # falló la última vez, no tiene caso esperar de más.
                if attempt < self.max_retries:
                    time.sleep(self.retry_wait_seconds)

        # Si llegamos aquí, se agotaron los reintentos -- devolvemos un
        # DataFrame vacío en vez de lanzar el error, así un solo ticker
        # problemático no tumba todo el pipeline (los demás tickers
        # que sí funcionaron igual se cargan).
        print(f"[{self.source_name}] Se agotaron los reintentos para {ticker}: {last_error}")
        return pd.DataFrame()

    def extract(self) -> pd.DataFrame:
        """
        Implementación real de la extracción. Recorre cada ticker,
        descarga sus datos históricos con reintentos automáticos, y los
        junta todos en un solo DataFrame "largo" (long format).

        Returns:
            pd.DataFrame con columnas:
            [ticker, date, open, high, low, close, volume, extracted_at]
        """
        all_data = []

        for ticker in self.tickers:
            print(f"[{self.source_name}] Descargando {ticker}...")

            hist = self._download_with_retry(ticker)

            if hist.empty:
                print(f"[{self.source_name}] Sin datos para {ticker}, se omite.")
                continue

            hist = hist.reset_index()
            hist.columns = [col.lower().replace(" ", "_") for col in hist.columns]
            hist["ticker"] = ticker
            hist["extracted_at"] = datetime.now(timezone.utc)

            all_data.append(hist)

            # Pausa breve entre tickers exitosos también -- ayuda a
            # prevenir que dispares el rate limit desde el principio,
            # en vez de solo reaccionar después de que ya ocurrió.
            time.sleep(2)

        if not all_data:
            return pd.DataFrame()

        combined_df = pd.concat(all_data, ignore_index=True)

        return combined_df


if __name__ == "__main__":
    extractor = StockExtractor(tickers=["AAPL", "MSFT"], period="5d")
    df = extractor.run()
    print(df.head())