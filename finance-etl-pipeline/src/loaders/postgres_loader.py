"""
postgres_loader.py

Recibe un pandas DataFrame (sin importar de qué extractor vino) y lo
carga a PostgreSQL. Usa "upsert" (INSERT ... ON CONFLICT DO UPDATE) para
que correr el pipeline varias veces el mismo día no duplique filas --
en vez de eso, actualiza el precio si ya existía esa combinación de
ticker + fecha.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import Config


class PostgresLoader:
    """
    Encargada únicamente de la carga (la "L" de ETL). No sabe nada de
    yfinance, ni de cómo se extrajeron los datos -- solo sabe recibir
    un DataFrame con ciertas columnas y guardarlo en Postgres.
    """

    def __init__(self, table_name: str = "stock_prices", schema: str = "raw"):
        """
        Args:
            table_name: nombre de la tabla destino (sin el schema)
            schema: schema de Postgres donde vive la tabla (ej. "raw")
        """
        self.table_name = table_name
        self.schema = schema

        # El "engine" de SQLAlchemy es el objeto que administra la
        # conexión a la base de datos. Se crea una sola vez y se
        # reutiliza -- no abrimos una conexión nueva por cada query.
        self.engine: Engine = create_engine(Config.get_db_url())

    def load(self, df: pd.DataFrame) -> int:
        """
        Carga el DataFrame a Postgres usando upsert.

        Args:
            df: DataFrame con columnas [ticker, date, open, high, low,
                close, volume, dividends, stock_splits, extracted_at]

        Returns:
            int: cantidad de filas procesadas (insertadas o actualizadas)
        """
        if df.empty:
            print(f"[loader] DataFrame vacío, no hay nada que cargar.")
            return 0

        # Nos aseguramos de trabajar solo con las columnas que la tabla
        # espera, en el orden correcto -- por si el DataFrame trae
        # columnas extra que no nos interesa guardar.
        expected_cols = [
            "ticker", "date", "open", "high", "low", "close",
            "volume", "dividends", "stock_splits", "extracted_at",
        ]
        # Filtramos solo las columnas que sí existen en el df, por si
        # yfinance no siempre devuelve dividends/stock_splits.
        cols_to_use = [c for c in expected_cols if c in df.columns]
        df_clean = df[cols_to_use]

        rows_processed = 0

        # Usamos una conexión con transacción (begin) para que, si algo
        # falla a la mitad, no se quede la base de datos en un estado
        # inconsistente (o se cargan todas las filas, o ninguna).
        with self.engine.begin() as connection:
            for _, row in df_clean.iterrows():
                self._upsert_row(connection, row, cols_to_use)
                rows_processed += 1

        print(f"[loader] {rows_processed} filas procesadas en {self.schema}.{self.table_name}")
        return rows_processed

    def _upsert_row(self, connection, row: pd.Series, columns: list[str]) -> None:
        """
        Inserta una fila individual, o la actualiza si ya existe una
        con el mismo (ticker, date) -- gracias al UNIQUE constraint
        que definimos en la tabla.

        Método "privado" (empieza con _) -- es un detalle interno del
        loader, no algo que otras clases deban llamar directamente.
        """
        # Construimos la parte de columnas e "placeholders" (:nombre)
        # dinámicamente, según las columnas que realmente tengamos.
        col_names = ", ".join(columns)
        placeholders = ", ".join(f":{col}" for col in columns)

        # En el UPDATE, actualizamos todas las columnas excepto las
        # que forman parte de la clave única (ticker, date) -- esas
        # no tiene sentido "actualizarlas" porque son las que usamos
        # para decidir si es la misma fila.
        update_cols = [c for c in columns if c not in ("ticker", "date")]
        update_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in update_cols)

        query = text(f"""
            INSERT INTO {self.schema}.{self.table_name} ({col_names})
            VALUES ({placeholders})
            ON CONFLICT (ticker, date)
            DO UPDATE SET {update_clause}
        """)

        # row.to_dict() convierte la fila de pandas en un diccionario
        # {nombre_columna: valor}, que es lo que SQLAlchemy espera
        # para rellenar los placeholders (:ticker, :date, etc.)
        connection.execute(query, row.to_dict())


# Prueba rápida y manual de este archivo solo, sin correr todo el pipeline.
if __name__ == "__main__":
    from src.extractors.stock_extractor import StockExtractor

    extractor = StockExtractor(tickers=["AAPL"], period="5d")
    df = extractor.run()

    loader = PostgresLoader()
    loader.load(df)