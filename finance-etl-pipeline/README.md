# Finance ETL Pipeline

Pipeline de datos financieros que extrae precios de acciones desde Yahoo Finance
(vía `yfinance`), los carga en PostgreSQL (alojado en Supabase), y los transforma
con `dbt` para dejarlos listos para análisis o visualización. Corre de forma
completamente automatizada todos los días mediante GitHub Actions y dbt Cloud.

Proyecto de portfolio construido para practicar conceptos de Data Engineering:
extracción de APIs, diseño orientado a objetos, carga a bases de datos,
transformación con dbt, testing de calidad de datos, y automatización.

## Arquitectura

```
GitHub Actions (cron diario, 12:00 UTC)
        ↓
yfinance API → Extractor (Python/OOP) → Supabase (PostgreSQL, schema raw)
        ↓
dbt Cloud Job (cron diario, 13:00 UTC)
        ↓
raw.stock_prices → stg_stock_prices (staging) → daily_returns, rolling_avg_price (schema analytics)
        ↓
Dashboard (Streamlit, local)
```

**Nota sobre la base de datos:** el proyecto empezó con PostgreSQL local
(pgAdmin4), pero se migró a [Supabase](https://supabase.com) para que tanto
el pipeline de Python como dbt Cloud pudieran conectarse a la misma fuente de
datos en la nube. La conexión usa el modo *Transaction pooler* de Supabase
(puerto 6543) en vez de la conexión directa, por compatibilidad de red
(IPv4 vs IPv6).

## Estructura del proyecto

```
finance-etl-pipeline/
├── src/
│   ├── extractors/           # Se conectan a fuentes de datos externas (APIs)
│   ├── loaders/              # Cargan datos a la base de datos
│   └── config.py             # Configuración centralizada (soporta .env y Streamlit secrets)
├── dbt_project/
│   ├── models/
│   │   ├── staging/           # Limpieza básica (sources.yml, stg_stock_prices)
│   │   └── marts/              # Modelos de negocio (daily_returns, rolling_avg_price)
│   └── dbt_project.yml
├── app.py                     # Dashboard de Streamlit
├── main.py                    # Orquestador del pipeline de extracción y carga
├── tests/                     # Pruebas unitarias
└── requirements.txt
```

**Nota sobre el workflow de automatización:** el archivo vive en la raíz del
repo (`HomeLabsRepository/.github/workflows/finance-etl-daily-extract.yml`),
no dentro de esta subcarpeta, porque GitHub Actions solo detecta workflows
ubicados en la raíz del repositorio. Al ser un monorepo, el archivo lleva el
prefijo `finance-etl-` para evitar colisiones con workflows de otros proyectos.

## Stack tecnológico

| Componente | Herramienta |
|---|---|
| Lenguaje | Python 3.11+ |
| Fuente de datos | [yfinance](https://pypi.org/project/yfinance/) (Yahoo Finance, gratis, sin API key) |
| Base de datos | PostgreSQL, alojado en [Supabase](https://supabase.com) (free tier) |
| Transformación | dbt Cloud |
| Automatización (extract/load) | GitHub Actions (cron diario) |
| Automatización (transform) | dbt Cloud Job (cron diario) |
| Visualización | Streamlit + Plotly |

## Modelos de dbt

| Modelo | Capa | Materialización | Descripción |
|---|---|---|---|
| `stg_stock_prices` | staging | view | Limpieza y renombrado de columnas del source crudo |
| `daily_returns` | marts | table | Retorno diario (%) por ticker, usando `LAG()` |
| `rolling_avg_price` | marts | table | Media móvil de 7 días del precio de cierre, usando `AVG() OVER()` |

Todos los modelos cuentan con tests de calidad de datos (`unique`, `not_null`,
`accepted_values`), y documentación generada automáticamente con
`dbt docs generate`, incluyendo el grafo de lineage.

## Automatización

Dos jobs independientes, encadenados por horario:

- **Extract + Load** (`main.py`): GitHub Actions, diario a las 12:00 UTC.
  Incluye reintentos automáticos con espera (retry + backoff) para manejar
  el rate limiting que Yahoo Finance aplica a IPs compartidas como las de
  los runners de GitHub Actions.
- **Transform** (`dbt build`): dbt Cloud Job, diario a las 13:00 UTC (una
  hora después, para asegurar que los datos crudos ya estén cargados).
  Corre modelos y tests en el orden correcto de dependencias, y regenera
  la documentación en cada ejecución.

Las credenciales de la base de datos se gestionan como GitHub Secrets
(para el workflow de Python) y como credenciales de ambiente en dbt Cloud
(para el job de transformación) — nunca se exponen en el código.

## Dashboard

El dashboard (`app.py`) visualiza los datos ya transformados: precio +
media móvil de 7 días, y retorno diario por ticker, con selector interactivo.

**Estado actual:** funcional en local. El deploy a Streamlit Community Cloud
quedó pendiente por limitaciones de tiempo de build en el tier gratuito
(el `requirements.txt` completo, compartido con el resto del pipeline,
incluye `dbt-core`, que es pesado de instalar). La solución sería separar
un `requirements.txt` más liviano solo para el dashboard — queda documentado
como mejora futura.

Cómo correrlo:
```bash
streamlit run app.py
```

## Cómo correrlo localmente

1. Clona el repo y entra a esta carpeta
2. Crea un entorno virtual:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows Git Bash
   ```
3. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Copia `.env.example` a `.env` y completa tus credenciales de Supabase
5. Corre el pipeline de extracción y carga:
   ```bash
   python main.py
   ```
6. Corre las transformaciones de dbt (desde `dbt_project/`, o vía dbt Cloud):
   ```bash
   dbt run
   dbt test
   ```
7. Corre el dashboard:
   ```bash
   streamlit run app.py
   ```

## Estado del proyecto

✅ Proyecto completo — pipeline end-to-end funcionando de forma automatizada.

- [x] Extractor de datos (yfinance), con manejo de rate limiting
- [x] Loader a PostgreSQL con upsert
- [x] Migración a Supabase (base de datos en la nube)
- [x] Modelos de dbt (staging + marts, con tests y documentación)
- [x] Automatización completa (GitHub Actions + dbt Cloud Job)
- [x] Dashboard de visualización (funcional en local)
- [ ] Deploy del dashboard a la nube *(mejora futura)*

## Posibles próximos pasos

- Separar un `requirements.txt` liviano para agilizar el deploy del dashboard
- Agregar una segunda fuente de datos (ej. indicadores macroeconómicos) para
  practicar modelos con múltiples sources relacionados entre sí
- Explorar Airflow como alternativa de orquestación más robusta que cron

## Autor

Santiago Ramírez
