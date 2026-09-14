# Home Labs - Repository

Este repositorio aloja proyectos personales desarrollados para mi portafolio/CV, así como proyectos creados para aprender y experimentar con nuevas tecnologías.

## Proyectos

### 📈 [finance-etl-pipeline](./finance-etl-pipeline)
Pipeline ETL de datos financieros (AAPL, MSFT, GOOGL, AMZN, TSLA) usando `yfinance`. Extrae, carga y transforma los datos con una arquitectura orientada a objetos, los almacena en Supabase (PostgreSQL) y los modela con dbt Cloud (staging, marts, tests de calidad, documentación auto-generada). Automatizado de punta a punta con GitHub Actions (extracción diaria) y un Job de dbt Cloud (transformación diaria). Incluye un dashboard interactivo construido con Streamlit y Plotly.

## Automatización

Los workflows de GitHub Actions que automatizan los pipelines del repositorio viven en [`.github/workflows`](./.github/workflows) (requisito de GitHub: solo se detectan workflows ubicados en la raíz del repositorio, no dentro de las subcarpetas de cada proyecto). Cada archivo lleva el prefijo del proyecto correspondiente para evitar colisiones de nombres entre distintos proyectos del monorepo.
