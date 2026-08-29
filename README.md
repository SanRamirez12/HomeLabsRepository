# Home Labs - Repository
Este repositorio aloja proyectos personales desarrollados para mi portafolio/CV, así como proyectos creados para aprender y experimentar con nuevas tecnologías.

## Proyectos

### 📈 [finance-etl-pipeline](./finance-etl-pipeline)
Pipeline ETL de datos financieros (AAPL, MSFT, GOOGL, AMZN, TSLA) usando `yfinance`. Extrae, carga y transforma los datos con una arquitectura orientada a objetos, los almacena en Supabase (PostgreSQL) y los modela con dbt Cloud (staging, marts, tests de calidad). Automatizado con GitHub Actions.

### ⚙️ [.github/workflows](./.github/workflows)
Workflows de GitHub Actions que automatizan la ejecución diaria de los pipelines del repositorio (por ejemplo, la extracción diaria del proyecto de finance-etl-pipeline).
