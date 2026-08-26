"""
test_connection.py

Script de prueba rápida y desechable -- NO es parte del pipeline final,
solo sirve para confirmar que config.py lee bien el .env y que
SQLAlchemy se puede conectar a tu base de datos (ahora en Supabase)
antes de meter yfinance en la ecuación.

Corre esto desde la raíz del proyecto con:
    python -m test_connection
"""

from sqlalchemy import create_engine, text

from src.config import Config


def test_connection():
    print("Probando conexión a la base de datos...")
    print(f"Host: {Config.DB_HOST}, DB: {Config.DB_NAME}, User: {Config.DB_USER}")

    engine = create_engine(Config.get_db_url())

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("✅ Conexión exitosa. Resultado de prueba:", result.scalar())

        # Bonus: confirmamos que los schemas raw/analytics existen,
        # y si ya corriste el SQL de creación de tablas, que aparezca ahí.
        result = connection.execute(text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema IN ('raw', 'analytics')
        """))
        tables = result.fetchall()
        print("Tablas encontradas en 'raw'/'analytics':", tables)


if __name__ == "__main__":
    test_connection()