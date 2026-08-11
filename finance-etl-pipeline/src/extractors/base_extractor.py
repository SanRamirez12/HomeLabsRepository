"""
base_extractor.py

Define el "contrato" que debe cumplir cualquier extractor de datos en este
proyecto. No extrae datos por sí mismo — es una clase abstracta que obliga
a las clases hijas (ej. StockExtractor) a implementar los mismos métodos.

¿Por qué hacer esto? Porque main.py va a poder usar CUALQUIER extractor
que herede de aquí sin necesitar saber los detalles internos de cada uno.
Esto se llama "polimorfismo": distintos objetos responden al mismo método
(.extract()) cada uno a su manera.
"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseExtractor(ABC):
    """
    Clase base abstracta para todos los extractores de datos.

    'ABC' (Abstract Base Class) le dice a Python que esta clase no se
    puede instanciar directamente (no puedes hacer BaseExtractor()) --
    solo sirve como plantilla para que otras clases hereden de ella.
    """

    def __init__(self, source_name: str):
        """
        Constructor de la clase base.

        Args:
            source_name: nombre identificador de la fuente de datos,
                         ej. "yahoo_finance". Útil para logs y para
                         saber de dónde vino cada dato una vez cargado.
        """
        self.source_name = source_name

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """
        Método que TODA clase hija debe implementar obligatoriamente.

        El decorador @abstractmethod hace que Python lance un error si
        alguien intenta crear una clase hija sin definir este método.

        Debe devolver siempre un pandas DataFrame, sin importar la fuente
        de datos -- así el resto del pipeline (loaders, etc.) siempre
        recibe el mismo tipo de objeto y no le importa de dónde vino.

        Returns:
            pd.DataFrame: los datos extraídos, ya limpios/estructurados.
        """
        pass

    def validate(self, df: pd.DataFrame) -> bool:
        """
        Validación básica y genérica, compartida por TODOS los extractores.

        Al no ser abstracto (no tiene @abstractmethod), las clases hijas
        heredan este comportamiento automáticamente sin tener que
        reescribirlo -- a menos que quieran sobreescribirlo (override).

        Args:
            df: el DataFrame que se quiere validar.

        Returns:
            bool: True si pasa las validaciones mínimas, False si no.
        """
        if df is None or df.empty:
            print(f"[{self.source_name}] Advertencia: DataFrame vacío.")
            return False

        if df.isnull().all().any():
            print(f"[{self.source_name}] Advertencia: hay columnas completamente vacías.")
            return False

        return True

    def run(self) -> pd.DataFrame:
        """
        Método "orquestador" que junta extract() + validate().

        Este es el único método que main.py va a llamar en la práctica.
        Así, main.py no necesita saber que existe un paso de validación --
        simplemente confía en que run() le entrega datos ya verificados.
        """
        print(f"[{self.source_name}] Iniciando extracción...")
        df = self.extract()

        if self.validate(df):
            print(f"[{self.source_name}] Extracción exitosa: {len(df)} filas.")
        else:
            print(f"[{self.source_name}] La extracción no pasó la validación.")

        return df
