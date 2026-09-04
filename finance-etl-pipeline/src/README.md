# src — Código Python del pipeline (la "E" y la "L" del ETL)

Esta carpeta contiene todo el código Python que **extrae** los precios de
acciones desde Yahoo Finance y los **carga** en PostgreSQL (Supabase). No hay
lógica analítica aquí: todo lo que sea transformar, calcular métricas o generar
tablas de negocio vive en `../dbt_project/` (ver su propio README).

> **División de responsabilidades del proyecto:**
> `src/` → Extract + Load (dato crudo a `raw.stock_prices`)
> `dbt_project/` → Transform (de `raw` a `analytics`)
> `app.py` → Visualización (lee `analytics`)

---

## 1. Estructura

```
src/
├── __init__.py                    # convierte src/ en paquete Python importable
├── config.py                      # configuración y credenciales centralizadas
├── extractors/
│   ├── __init__.py
│   ├── base_extractor.py          # clase abstracta: el "contrato" de todo extractor
│   └── stock_extractor.py         # extractor concreto de Yahoo Finance (yfinance)
└── loaders/
    ├── __init__.py
    └── postgres_loader.py         # carga a PostgreSQL con upsert
```

Archivos relacionados que viven **fuera** de esta carpeta pero dependen de ella:

- `../main.py` → orquestador: `StockExtractor().run()` → `PostgresLoader().load()`
- `../app.py` → dashboard de Streamlit (usa `src.config`)
- `../test_connection.py` → script desechable para probar la conexión a la BD

Los `__init__.py` están vacíos a propósito: solo existen para que Python trate
estas carpetas como paquetes y funcionen los imports del estilo
`from src.extractors.stock_extractor import StockExtractor`.

---

## 2. Flujo completo, de arriba a abajo

```
main.py
  │  TICKERS = ["AAPL","MSFT","GOOGL","AMZN","TSLA"]
  │
  ├─► StockExtractor(tickers, period="5d", interval="1d", max_retries=5, retry_wait_seconds=30)
  │       .run()                          ← método heredado de BaseExtractor
  │         ├─ extract()                  ← implementación propia de StockExtractor
  │         │    └─ por cada ticker: _download_with_retry() → yfinance
  │         └─ validate()                 ← método heredado de BaseExtractor
  │       ⇒ devuelve un pandas DataFrame en formato largo
  │
  └─► PostgresLoader(table_name="stock_prices", schema="raw")
          .load(df)
            └─ por cada fila: INSERT ... ON CONFLICT (ticker, date) DO UPDATE
          ⇒ devuelve cuántas filas se procesaron

               (a partir de aquí toma el relevo dbt)
```

El punto de este diseño: **`main.py` no sabe nada de yfinance ni de SQL**. Solo
sabe que existe algo con `.run()` que devuelve un DataFrame, y algo con
`.load(df)` que lo guarda. Cambiar la fuente de datos o la base de datos no
obliga a reescribir el orquestador.

---

## 3. `config.py` — configuración y credenciales

Centraliza toda la configuración en un solo lugar, leyéndola de **variables de
entorno** en vez de tenerla escrita en el código. Esto es lo que permite que las
contraseñas nunca lleguen a GitHub.

### `_get_setting(key, default)`

Función auxiliar que busca un valor de configuración en dos lugares, en orden:

1. **`st.secrets`** de Streamlit (para cuando la app corre en Streamlit Cloud).
2. **Variables de entorno** (`.env` en local vía `python-dotenv`, o GitHub
   Secrets cuando corre en GitHub Actions).

Detalle importante: **el `import streamlit` está dentro de la función, no arriba
del archivo**. Es a propósito — en GitHub Actions no se instala Streamlit, y si
el import estuviera al inicio, `main.py` reventaría antes de empezar. Por eso el
`try/except` captura dos casos distintos:

- `ImportError` → Streamlit no está instalado en este entorno.
- `FileNotFoundError` → Streamlit sí está instalado, pero no hay `secrets.toml`
  (el caso típico corriendo en local).

### `class Config`

Agrupa los valores como atributos de clase, para poder hacer
`from src.config import Config` y luego `Config.DB_HOST`:

| Atributo | Default | Nota |
|---|---|---|
| `DB_HOST` | `localhost` | En producción, el host de Supabase |
| `DB_PORT` | `5432` | **En Supabase se usa 6543** (Transaction pooler) |
| `DB_NAME` | `finance_pipeline` | En Supabase suele ser `postgres` |
| `DB_USER` | `postgres` | |
| `DB_PASSWORD` | *(sin default)* | Obligatorio; si falta, `get_db_url()` lanza error |

`get_db_url()` arma la cadena de conexión que SQLAlchemy espera
(`postgresql://user:password@host:port/dbname`) y **falla temprano con un
mensaje claro** si no hay contraseña, en vez de dejar que el error aparezca
después como un fallo de conexión confuso.

Para configurarlo en local: copiar `../.env.example` a `.env` y rellenarlo. El
`.env` real está en `.gitignore`.

---

## 4. `extractors/` — de dónde salen los datos

### `base_extractor.py` — la clase abstracta

Define el **contrato** que debe cumplir cualquier extractor del proyecto. No
extrae nada por sí misma; es una `ABC` (Abstract Base Class), o sea que no se
puede instanciar directamente.

Métodos:

- **`__init__(source_name)`** — guarda un nombre identificador de la fuente
  (`"yahoo_finance"`), usado en todos los logs para saber quién habla.
- **`extract()`** — marcado con `@abstractmethod`: **toda** clase hija está
  obligada a implementarlo, si no Python lanza error al instanciarla. Debe
  devolver siempre un `pd.DataFrame`, sin importar la fuente.
- **`validate(df)`** — validación genérica y compartida (no abstracta, así que
  se hereda gratis): rechaza DataFrames vacíos o con columnas completamente
  nulas.
- **`run()`** — orquesta `extract()` + `validate()` e imprime los logs. **Es el
  único método que `main.py` llama en la práctica**, lo que le permite ignorar
  que existe un paso de validación.

Esto es **polimorfismo** en la práctica: el día que se agregue, por ejemplo, un
`CryptoExtractor` o un `MacroIndicatorsExtractor`, bastará con heredar de
`BaseExtractor` e implementar `extract()`. `main.py` los usará exactamente
igual.

> Ojo con un detalle del diseño actual: si `validate()` falla, `run()` **igual
> devuelve el DataFrame** (solo imprime la advertencia). La decisión de parar la
> corre `main.py`, que revisa `if df.empty`. Es un comportamiento consciente,
> pero es el primer lugar donde mirar si algún día se cuela un dato raro.

### `stock_extractor.py` — el extractor concreto

Hereda de `BaseExtractor` e implementa la extracción real contra Yahoo Finance
usando la librería `yfinance` (gratuita, sin API key).

**Parámetros del constructor:**

| Parámetro | Qué hace | Valor usado en `main.py` |
|---|---|---|
| `tickers` | Lista de símbolos a descargar | `["AAPL","MSFT","GOOGL","AMZN","TSLA"]` |
| `period` | Rango histórico (`"1d"`, `"5d"`, `"1mo"`, `"1y"`, `"max"`) | `"5d"` |
| `interval` | Granularidad (`"1d"`, `"1h"`, …) | `"1d"` |
| `max_retries` | Reintentos por ticker ante rate limit | `5` |
| `retry_wait_seconds` | Espera entre reintentos | `30` |

Se usa `period="5d"` (y no un histórico largo) porque el pipeline corre a
diario: solo hace falta traer los últimos días y dejar que el **upsert** del
loader resuelva los solapamientos.

**`_download_with_retry(ticker)`** — método privado que maneja el problema más
molesto del proyecto: **Yahoo Finance aplica rate limiting agresivo a IPs
compartidas**, como las de los runners de GitHub Actions. En local funcionaba
siempre; en la nube fallaba de forma intermitente. La solución:

- Reintentar hasta `max_retries` veces al capturar `YFRateLimitError`,
  esperando `retry_wait_seconds` entre intentos.
- No dormir después del último intento (sería tiempo perdido).
- Si se agotan los reintentos, **devolver un DataFrame vacío en lugar de lanzar
  la excepción**: así un ticker problemático no tumba todo el pipeline y los
  demás tickers igual se cargan.

**`extract()`** — recorre los tickers, y por cada uno:

1. Descarga el historial con reintentos.
2. Si vino vacío, lo salta con un log y continúa.
3. `reset_index()` para que la fecha (que yfinance entrega como índice) pase a
   ser una columna normal.
4. Normaliza los nombres de columnas a `snake_case` minúscula
   (`"Stock Splits"` → `stock_splits`).
5. Agrega la columna `ticker` (yfinance no la incluye al descargar de a uno).
6. Agrega `extracted_at` con el timestamp UTC de la extracción — trazabilidad:
   siempre se sabe cuándo se trajo cada fila.
7. `time.sleep(2)` entre tickers exitosos, para **prevenir** el rate limit en
   lugar de solo reaccionar cuando ya ocurrió.

Al final concatena todo en un solo DataFrame en **formato largo** (una fila por
ticker + fecha), con columnas:
`ticker, date, open, high, low, close, volume, dividends, stock_splits, extracted_at`.

El bloque `if __name__ == "__main__"` al final permite probar solo este archivo
sin correr el pipeline completo.

---

## 5. `loaders/postgres_loader.py` — cómo se guardan los datos

Clase responsable **únicamente** de la carga (la "L"). No sabe nada de yfinance
ni de cómo se obtuvieron los datos: solo recibe un DataFrame y lo guarda.

**`__init__(table_name="stock_prices", schema="raw")`** — crea el *engine* de
SQLAlchemy una sola vez con `Config.get_db_url()`. El engine administra el pool
de conexiones; abrir una conexión nueva por cada query sería mucho más lento y
saturaría el pooler de Supabase.

**`load(df)`** — el método público:

1. Si el DataFrame está vacío, sale devolviendo `0`.
2. Filtra y ordena las columnas contra una lista esperada
   (`expected_cols`), quedándose solo con las que realmente existen — porque
   yfinance no siempre devuelve `dividends` / `stock_splits`.
3. Abre **una transacción** con `engine.begin()`: si algo falla a la mitad, se
   revierte todo. La base nunca queda en un estado a medias.
4. Itera fila por fila llamando a `_upsert_row()`.
5. Devuelve el número de filas procesadas.

**`_upsert_row(connection, row, columns)`** — el corazón de la idempotencia.
Construye dinámicamente y ejecuta:

```sql
INSERT INTO raw.stock_prices (columnas...)
VALUES (:placeholders...)
ON CONFLICT (ticker, date)
DO UPDATE SET columna = EXCLUDED.columna, ...
```

- El **upsert** es lo que hace que correr el pipeline varias veces el mismo día
  **no duplique filas**: si ya existe esa combinación `(ticker, date)`, la
  actualiza en vez de insertarla de nuevo. Esto depende de un `UNIQUE
  constraint` sobre `(ticker, date)` creado en la tabla — sin él, el
  `ON CONFLICT` falla.
- En el `DO UPDATE` se excluyen `ticker` y `date`: son las columnas que definen
  la identidad de la fila, no tiene sentido "actualizarlas".
- Se usan **placeholders con nombre** (`:ticker`, `:date`, …) y
  `row.to_dict()`, en vez de interpolar valores en el string SQL — es lo
  correcto para evitar inyección SQL y problemas de tipos.

> Nota de rendimiento consciente: la carga es fila por fila, lo cual es lento si
> el volumen crece. A esta escala (5 tickers × 5 días ≈ 25 filas diarias) es
> irrelevante, y a cambio se gana claridad. Si algún día molesta, el camino es
> agrupar en lotes (`executemany` / `execute` con lista de dicts).

También trae su propio `if __name__ == "__main__"` para probarlo aislado.

---

## 6. Configuración y secretos

Las credenciales se resuelven distinto según dónde corra el código, pero
**siempre** a través de `Config`:

| Entorno | De dónde salen las credenciales |
|---|---|
| Local | Archivo `.env` (a partir de `.env.example`), leído por `python-dotenv` |
| GitHub Actions | GitHub Secrets, expuestos como variables de entorno al workflow |
| Streamlit Cloud | `st.secrets` de la app |
| dbt Cloud | No usa este código; sus credenciales se configuran en dbt Cloud |

Nada de esto está en el repositorio: `.env` está en `.gitignore`, y solo se
versiona `.env.example` como plantilla.

---

## 7. Cómo correr y probar

Desde la raíz de `finance-etl-pipeline/`:

```bash
# entorno virtual + dependencias
python -m venv venv
source venv/Scripts/activate      # Windows Git Bash
pip install -r requirements.txt

# 1) verificar que la conexión a la base de datos funciona
python -m test_connection

# 2) pipeline completo (extract + load)
python main.py

# 3) probar módulos por separado
python -m src.extractors.stock_extractor
python -m src.loaders.postgres_loader
```

Importante: correr siempre **desde la raíz del proyecto** (con `python -m ...`),
no desde dentro de `src/`. Si no, los imports `from src.…` no resuelven.

En producción, `main.py` lo dispara el workflow
`.github/workflows/finance-etl-pipeline-daily-extract.yml` (en la raíz del
repositorio, no en esta subcarpeta, porque GitHub Actions solo detecta workflows
ahí), todos los días a las **12:00 UTC**. `main.py` re-lanza cualquier excepción
después de loguearla, precisamente para que GitHub Actions marque el run como
fallido en vez de "pasar" en silencio.

---

## 8. Cómo extenderlo

**Agregar un ticker nuevo:** editar `TICKERS` en `../main.py` **y** la lista del
test `accepted_values` en
`../dbt_project/models/staging/stg_stock_prices.yml`. Si se olvida el segundo,
`dbt test` falla — por diseño.

**Agregar una fuente de datos nueva** (ej. indicadores macro):

1. Crear `src/extractors/mi_extractor.py` con una clase que herede de
   `BaseExtractor`.
2. Llamar a `super().__init__(source_name="mi_fuente")` e implementar
   `extract()` devolviendo un `pd.DataFrame`.
3. Instanciarla en `main.py` y pasar el resultado a un loader.

**Agregar un destino nuevo** (ej. S3, BigQuery): crear una clase en
`src/loaders/` con un método `load(df) -> int`. Vale la pena, llegado el caso,
crear un `BaseLoader` abstracto equivalente a `BaseExtractor` — hoy no existe
porque solo hay un loader.

---

## 9. Pendientes conocidos

- No hay carpeta `tests/` con pruebas unitarias todavía (`pytest` ya está en
  `requirements.txt`). Los candidatos naturales: `Config.get_db_url()`,
  la normalización de columnas de `extract()` y el armado del SQL de
  `_upsert_row()`.
- Los logs son `print()`. Migrar al módulo `logging` daría niveles y timestamps
  reales, que es lo que se agradece al depurar un run fallido en la nube.
- La lista de tickers está hardcodeada en `main.py`; podría venir de config o de
  una tabla en la base de datos.
- `test_connection.py` es un script manual desechable, no un test de `pytest`
  pese al nombre.
