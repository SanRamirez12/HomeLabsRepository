# Finance ETL Pipeline

Pipeline de datos financieros que extrae precios de acciones desde Yahoo Finance
(vía `yfinance`), los carga en PostgreSQL, y los transforma con `dbt` para dejarlos
listos para análisis o visualización.

Proyecto de portfolio construido para practicar conceptos de Data Engineering:
extracción de APIs, diseño orientado a objetos, carga a bases de datos,
transformación con dbt, y automatización con GitHub Actions.

## Arquitectura

Pipeline por capas (extract → load → transform):

```
yfinance API  →  Extractor (Python/OOP)  →  PostgreSQL  →  dbt (transform)  →  Analytics-ready tables
```

## Estructura del proyecto

```
finance-etl-pipeline/
├── src/
│   ├── extractors/       # Se conectan a fuentes de datos externas (APIs)
│   ├── loaders/          # Cargan datos a la base de datos
│   └── config.py         # Configuración centralizada (lee variables de entorno)
├── dbt_project/          # Modelos de transformación SQL
├── .github/workflows/    # Automatización (corre el pipeline diariamente)
├── notebooks/            # Exploración de datos (opcional, no productivo)
├── tests/                # Pruebas unitarias
└── requirements.txt
```

## Stack tecnológico

| Componente | Herramienta |
|---|---|
| Lenguaje | Python 3.11+ |
| Fuente de datos | [yfinance](https://pypi.org/project/yfinance/) (Yahoo Finance, gratis, sin API key) |
| Base de datos | PostgreSQL |
| Transformación | dbt-core |
| Automatización | GitHub Actions |
| Visualización | *(pendiente — Metabase o Streamlit)* |

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
4. Copia `.env.example` a `.env` y completa tus credenciales locales de Postgres
5. Corre el pipeline:
   ```bash
   python -m src.main
   ```

## Estado del proyecto

🚧 En construcción — proyecto de aprendizaje activo.

- [x] Estructura base del repo
- [ ] Extractor de datos (yfinance)
- [ ] Loader a PostgreSQL
- [ ] Modelos de dbt
- [ ] Automatización con GitHub Actions
- [ ] Dashboard de visualización

## Autor

Santiago Ramírez — parte de [HomeLabsRepository](../)
