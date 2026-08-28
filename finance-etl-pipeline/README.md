# Finance ETL Pipeline

Pipeline de datos financieros que extrae precios de acciones desde Yahoo Finance
(vía `yfinance`), los carga en PostgreSQL (alojado en Supabase), y los transforma
con `dbt` para dejarlos listos para análisis o visualización. Corre de forma
completamente automatizada todos los días mediante GitHub Actions.

Proyecto de portfolio construido para practicar conceptos de Data Engineering:
extracción de APIs, diseño orientado a objetos, carga a bases de datos,
transformación con dbt, testing de calidad de datos, y automatización con
GitHub Actions.

## Arquitectura

Pipeline por capas (extract → load → transform), orquestado diariamente por
GitHub Actions:

```
GitHub Actions (cron diario)
        ↓
yfinance API  →  Extractor (Python/OOP)  →  Supabase (PostgreSQL)  →  dbt (transform)  →  Analytics-ready tables
```

**Nota sobre la base de datos:** el proyecto empezó con PostgreSQL local
(pgAdmin4), pero se migró a [Supabase](https://supabase.com) para tener la
base de datos accesible desde la nube — esto permite que tanto el pipeline de
Python como dbt Cloud se conecten a la misma fuente de datos sin depender de
que una máquina local esté encendida. La conexión usa el modo *Transaction
pooler* de Supabase (puerto 6543) en vez de la conexión directa, por
compatibilidad de red (IPv4 vs IPv6).

## Estructura del proyecto

```
finance-etl-pipeline/
├── src/
│   ├── extractors/           # Se conectan a fuentes de datos externas (APIs)
│   ├── loaders/              # Cargan datos a la base de datos
│   └── config.py             # Configuración centralizada (lee variables de entorno)
├── dbt_project/
│   ├── models/
│   │   ├── staging/           # Limpieza básica (sources.yml, stg_stock_prices)
│   │   └── marts/              # Modelos de negocio (daily_returns, rolling_avg_price)
│   └── dbt_project.yml
├── .github/workflows/         # Automatización (corre el pipeline diariamente)
├── notebooks/                 # Exploración de datos (opcional, no productivo)
├── tests/                     # Pruebas unitarias
└── requirements.txt
```

**Nota sobre el archivo de workflow:** vive en la raíz del repo
(`HomeLabsRepository/.github/workflows/finance-etl-daily-extract.yml`), no
dentro de esta subcarpeta — GitHub Actions solo detecta workflows ubicados en
la raíz del repositorio. Al ser un monorepo con varios proyectos, el archivo
lleva el prefijo `finance-etl-` para evitar colisiones de nombres con
workflows de otros proyectos futuros.

## Stack tecnológico

| Componente | Herramienta |
|---|---|
| Lenguaje | Python 3.11+ |
| Fuente de datos | [yfinance](https://pypi.org/project/yfinance/) (Yahoo Finance, gratis, sin API key) |
| Base de datos | PostgreSQL, alojado en [Supabase](https://supabase.com) (free tier) |
| Transformación | dbt Cloud / dbt-core |
| Automatización | GitHub Actions (cron diario) |
| Visualización | *(pendiente — Metabase o Streamlit)* |

## Modelos de dbt

| Modelo | Capa | Materialización | Descripción |
|---|---|---|---|
| `stg_stock_prices` | staging | view | Limpieza y renombrado de columnas del source crudo |
| `daily_returns` | marts | table | Retorno diario (%) por ticker, usando `LAG()` |
| `rolling_avg_price` | marts | table | Media móvil de 7 días del precio de cierre, usando `AVG() OVER()` |

Todos los modelos cuentan con tests de calidad de datos (`unique`, `not_null`,
`accepted_values`) definidos en sus archivos `.yml` correspondientes, y
documentación generada automáticamente con `dbt docs generate`.

## Automatización

El pipeline de extracción y carga (`main.py`) corre automáticamente todos los
días mediante un workflow de GitHub Actions, sin depender de que una máquina
local esté encendida:

- **Trigger**: cron diario (configurable) + disparo manual (`workflow_dispatch`)
- **Credenciales**: gestionadas como GitHub Secrets, nunca expuestas en el código
- **Resiliencia ante rate limiting**: la API de Yahoo Finance aplica límites de
  solicitudes más agresivos a IPs compartidas como las de los runners de
  GitHub Actions. El extractor implementa reintentos automáticos con espera
  (retry + backoff) por ticker, además de una pausa preventiva entre
  descargas, para manejar esto sin que falle todo el pipeline

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

## Estado del proyecto

🚧 En construcción — proyecto de aprendizaje activo.

- [x] Estructura base del repo
- [x] Extractor de datos (yfinance)
- [x] Loader a PostgreSQL
- [x] Migración a Supabase (base de datos en la nube)
- [x] Modelos de dbt (staging + marts, con tests y documentación)
- [x] Automatización con GitHub Actions
- [ ] Dashboard de visualización

## Autor

Santiago Ramírez
