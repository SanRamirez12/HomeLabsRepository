"""
config.py

Centraliza toda la configuración del proyecto (credenciales de BD, etc.)
leyéndola desde variables de entorno en vez de tenerla escrita ("hardcodeada")
en el código. Así el archivo .env (que SÍ tiene tus contraseñas reales)
nunca se sube a GitHub -- está en el .gitignore -- pero config.py sí se
sube, porque no contiene ningún secreto, solo lógica para leerlos.
"""

import os

from dotenv import load_dotenv

# Busca un archivo .env en la raíz del proyecto y carga sus variables
# al entorno del sistema operativo (como si hicieras "export VAR=valor").
load_dotenv()


class Config:
    """
    Agrupa toda la configuración en un solo lugar. Usamos una clase
    (en vez de variables sueltas) para que sea fácil de importar como
    un solo objeto: `from src.config import Config` y luego `Config.DB_HOST`.
    """

    # os.getenv(nombre, valor_por_defecto) -- si la variable de entorno
    # no existe, usa el segundo argumento como fallback. Esto evita que
    # el programa truene si alguien olvida configurar algo opcional.
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "finance_pipeline")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD")  # sin default -- esto SÍ debe venir del .env

    @classmethod
    def get_db_url(cls) -> str:
        """
        Construye la URL de conexión que SQLAlchemy necesita, con el
        formato: postgresql://usuario:password@host:puerto/nombre_db

        Usamos @classmethod porque no necesitamos crear una instancia
        de Config para llamar este método -- se llama directo como
        Config.get_db_url().
        """
        if not cls.DB_PASSWORD:
            raise ValueError(
                "DB_PASSWORD no está definida. ¿Creaste tu archivo .env "
                "a partir de .env.example?"
            )

        return (
            f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )