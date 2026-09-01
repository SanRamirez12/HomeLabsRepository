"""
config.py

Centraliza toda la configuración del proyecto (credenciales de BD, etc.)
leyéndola desde variables de entorno en vez de tenerla escrita ("hardcodeada")
en el código.

Soporta dos formas de configuración, según dónde corra el código:
1. Localmente / GitHub Actions: variables de entorno vía archivo .env
2. Streamlit Community Cloud: st.secrets (su propio sistema de secretos)

Esto permite que el mismo config.py sirva tanto para main.py (el pipeline)
como para app.py (el dashboard), sin importar dónde se ejecuten.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _get_setting(key: str, default: str = None) -> str:
    """
    Busca un valor de configuración, probando primero st.secrets
    (Streamlit Cloud) y luego variables de entorno normales (.env,
    GitHub Actions Secrets). Si ninguno tiene el valor, usa el default.

    Se hace el import de streamlit DENTRO de la función (no arriba del
    archivo) a propósito: así main.py y otros scripts que no necesitan
    Streamlit no fallan si streamlit no está instalado en ese entorno
    (por ejemplo, en GitHub Actions, donde no instalamos streamlit).
    """
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except (ImportError, FileNotFoundError):
        # ImportError: streamlit no está instalado en este entorno (ej. GitHub Actions)
        # FileNotFoundError: streamlit está instalado pero no hay secrets.toml (ej. local)
        pass

    return os.getenv(key, default)


class Config:
    """
    Agrupa toda la configuración en un solo lugar. Usamos una clase
    para que sea fácil de importar como un solo objeto:
    `from src.config import Config` y luego `Config.DB_HOST`.
    """

    DB_HOST = _get_setting("DB_HOST", "localhost")
    DB_PORT = _get_setting("DB_PORT", "5432")
    DB_NAME = _get_setting("DB_NAME", "finance_pipeline")
    DB_USER = _get_setting("DB_USER", "postgres")
    DB_PASSWORD = _get_setting("DB_PASSWORD")

    @classmethod
    def get_db_url(cls) -> str:
        """
        Construye la URL de conexión que SQLAlchemy necesita, con el
        formato: postgresql://usuario:password@host:puerto/nombre_db
        """
        if not cls.DB_PASSWORD:
            raise ValueError(
                "DB_PASSWORD no está definida. Si corres localmente, revisa "
                "tu archivo .env. Si corres en Streamlit Cloud, revisa la "
                "configuración de Secrets de la app."
            )

        return (
            f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )