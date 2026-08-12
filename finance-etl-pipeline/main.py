"""
main.py

Punto de entrada del pipeline completo. Su único trabajo es ORQUESTAR:
llamar al extractor, y pasarle el resultado al loader. No sabe los
detalles internos de ninguno de los dos -- por diseño.

Esto es intencional: si mañana cambias yfinance por otra fuente, o
Postgres por otra base de datos, este archivo casi no cambia, porque
solo depende de que ambos cumplan su "contrato" (BaseExtractor.run()
y PostgresLoader.load()).

Correr con:
    python -m src.main
"""

from datetime import datetime, timezone

from src.extractors.stock_extractor import StockExtractor
from src.loaders.postgres_loader import PostgresLoader

# Lista de tickers que queremos trackear. Más adelante esto podría
# venir de un archivo de configuración o de una tabla en la BD en vez
# de estar hardcodeado aquí -- por ahora, simple es mejor.
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]


def run_pipeline() -> None:
    """
    Ejecuta el pipeline completo: extract -> load.

    Envuelto en try/except para que, si algo falla, el pipeline termine
    con un mensaje claro en vez de un traceback críptico -- esto
    importa mucho cuando lo automatices con GitHub Actions, porque ahí
    nadie va a estar viendo la consola en vivo.
    """
    start_time = datetime.now(timezone.utc)
    print(f"=== Iniciando pipeline: {start_time.isoformat()} ===")

    try:
        # --- EXTRACT ---
        extractor = StockExtractor(tickers=TICKERS, period="5d", interval="1d")
        df = extractor.run()

        if df.empty:
            print("El extractor no devolvió datos. Pipeline detenido.")
            return

        # --- LOAD ---
        loader = PostgresLoader(table_name="stock_prices", schema="raw")
        rows_loaded = loader.load(df)

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        print(f"=== Pipeline completado en {duration:.2f}s ===")
        print(f"Filas procesadas: {rows_loaded}")

    except Exception as error:
        # Capturamos cualquier error inesperado para que quede loggeado
        # de forma clara. En un proyecto más maduro, aquí mandarías
        # una notificación (email, Slack) en vez de solo un print.
        print(f"❌ El pipeline falló: {error}")
        raise  # re-lanzamos el error para que GitHub Actions marque el run como fallido


if __name__ == "__main__":
    run_pipeline()