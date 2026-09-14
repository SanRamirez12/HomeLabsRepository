# Home Labs — Repository

Monorepo de proyectos personales de **ingeniería y análisis de datos**, desarrollados
para mi portafolio y para aprender herramientas nuevas construyendo cosas completas, no
tutoriales sueltos.

Cada proyecto vive en su propia carpeta y **tiene su propio README detallado** con
arquitectura, decisiones de diseño e instrucciones para correrlo. Los enlaces de abajo
llevan directo a cada uno.

---

## Proyectos

### 📈 [finance-etl-pipeline](./finance-etl-pipeline) — *completo*

Pipeline ETL de datos financieros (AAPL, MSFT, GOOGL, AMZN, TSLA) usando `yfinance`.
Extrae, carga y transforma los datos con una arquitectura orientada a objetos, los
almacena en Supabase (PostgreSQL) y los modela con dbt Cloud (staging, marts, tests de
calidad, documentación auto-generada). Automatizado de punta a punta con GitHub Actions
(extracción diaria) y un Job de dbt Cloud (transformación diaria). Incluye un dashboard
interactivo construido con Streamlit y Plotly.

`Python` `yfinance` `PostgreSQL` `Supabase` `dbt Cloud` `GitHub Actions` `Streamlit` `Plotly`

**Documentación interna:** [código Python (E + L)](./finance-etl-pipeline/src) ·
[proyecto dbt (T)](./finance-etl-pipeline/dbt_project)

---

### 🛒 [retail-analytics-warehouse](./retail-analytics-warehouse) — *en construcción*

Plataforma de datos end-to-end sobre un dataset de e-commerce, enfocada en lo que el
proyecto anterior no cubre: **arquitectura medallón con capa de archivos en Parquet,
modelado dimensional en esquema estrella, historización de cambios (SCD tipo 2),
múltiples fuentes cruzadas, orquestación con DAGs y una capa de BI con modelo semántico
y DAX.**

El dato aterriza primero como Parquet inmutable en object storage, luego pasa a
PostgreSQL, y dbt lo convierte en un modelo dimensional que consume Power BI. Incluye una
fuente externa adicional (tipo de cambio del BCCR) para convertir las ventas a colones
usando la tasa vigente en la fecha de cada venta.

`Python` `Parquet` `Supabase Storage` `PostgreSQL` `dbt` `Apache Airflow` `Docker` `GitHub Actions` `pytest` `Power BI`

> **Nota sobre la orquestación:** Airflow corre localmente en Docker, con los DAGs
> versionados en el repo, como ejercicio de orquestación avanzada. El scheduler que
> efectivamente corre a diario en la nube es GitHub Actions. Ambos ejecutan los mismos
> scripts de Python, sin lógica duplicada.

---

## Cómo está organizado el repositorio

```
HomeLabsRepository/
├── .github/workflows/          # Todos los workflows de automatización
├── finance-etl-pipeline/       # Proyecto 1
└── retail-analytics-warehouse/ # Proyecto 2
```

## Automatización

Los workflows de GitHub Actions que automatizan los pipelines del repositorio viven en
[`.github/workflows`](./.github/workflows). Esto es un requisito de GitHub: solo se
detectan workflows ubicados en la raíz del repositorio, no dentro de las subcarpetas de
cada proyecto.

Por eso, y al tratarse de un monorepo, **cada archivo lleva el prefijo del proyecto
correspondiente** (`finance-etl-pipeline-*`, `retail-analytics-*`) para evitar colisiones
de nombres entre proyectos.

## Credenciales

Ningún proyecto de este repositorio contiene credenciales. Todas se gestionan como GitHub
Secrets, variables de entorno locales (`.env`, siempre ignorado por Git) o credenciales de
ambiente en los servicios en la nube. Cada proyecto incluye un `.env.example` como
plantilla.

---

## Autor

**Santiago Ramírez**
