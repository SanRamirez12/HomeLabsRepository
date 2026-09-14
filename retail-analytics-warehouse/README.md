# Retail Analytics Warehouse

Plataforma de datos end-to-end sobre un dataset de e-commerce: ingesta de archivos y
APIs, capa de archivos en Parquet, data warehouse dimensional en PostgreSQL, modelado
con dbt, orquestación con Airflow y GitHub Actions, y una capa de análisis en Power BI.

Segundo proyecto del portafolio. Mientras `finance-etl-pipeline` demuestra un pipeline
ETL simple de una sola fuente, este proyecto se enfoca en lo que ese no cubre:
**arquitectura medallón, modelado dimensional, historización de cambios, múltiples
fuentes cruzadas, orquestación con DAGs, testing automatizado y modelo semántico de BI**.

---

## Índice

1. [Arquitectura](#1-arquitectura)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Decisiones de diseño](#3-decisiones-de-diseño)
4. [Estructura del proyecto](#4-estructura-del-proyecto)
5. [Fuentes de datos](#5-fuentes-de-datos)
6. [Capas de datos](#6-capas-de-datos)
7. [Modelo dimensional](#7-modelo-dimensional)
8. [Orquestación](#8-orquestación)
9. [Testing](#9-testing)
10. [Capa de análisis (Power BI)](#10-capa-de-análisis-power-bi)
11. [Cómo correrlo localmente](#11-cómo-correrlo-localmente)
12. [Estado del proyecto](#12-estado-del-proyecto)
13. [Mejoras futuras](#13-mejoras-futuras)

---

## 1. Arquitectura

```
                        FUENTES
   ┌──────────────────┬──────────────────┬──────────────────┐
   │  Dataset Olist   │  Generador de    │   API del BCCR   │
   │   (CSV, carga    │  pedidos diarios │  (tipo de cambio │
   │    histórica)    │    (Python)      │      diario)     │
   └────────┬─────────┴────────┬─────────┴────────┬─────────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │  Extractors (OOP)   │   src/extractors/
                    └──────────┬──────────┘
                               ▼
            ╔══════════════════════════════════════╗
            ║  BRONZE — Parquet en object storage  ║   Supabase Storage (S3)
            ║  Dato crudo inmutable, particionado  ║
            ╚══════════════════┬═══════════════════╝
                               ▼
            ╔══════════════════════════════════════╗
            ║  SILVER — retail_raw (PostgreSQL)    ║   Supabase
            ║  Mismo dato, ya en tablas tipadas    ║
            ╚══════════════════┬═══════════════════╝
                               ▼
                    ┌─────────────────────┐
                    │   dbt Cloud         │
                    │   staging → marts   │
                    └──────────┬──────────┘
                               ▼
            ╔══════════════════════════════════════╗
            ║  GOLD — retail_analytics             ║   Supabase
            ║  Modelo estrella + snapshots SCD2    ║
            ╚══════════════════┬═══════════════════╝
                               ▼
                    ┌─────────────────────┐
                    │  Power BI Desktop   │   modo Import
                    │  Modelo semántico   │
                    └─────────────────────┘

 ORQUESTACIÓN
 ├── GitHub Actions  → scheduler de producción (corre diario en la nube)
 └── Apache Airflow  → mismos pasos como DAG, corriendo local en Docker
```

---

## 2. Stack tecnológico

| Capa | Herramienta | Dónde corre | Costo |
|---|---|---|---|
| Lenguaje | Python 3.11+ | — | — |
| Ingesta | pandas, requests, boto3 | GitHub Actions | Gratis |
| Almacenamiento de archivos | Parquet (pyarrow) sobre Supabase Storage | Cloud | Free tier |
| Base de datos | PostgreSQL (Supabase) | Cloud | Free tier |
| Transformación | dbt Cloud | Cloud | Free tier (1 usuario) |
| Orquestación (producción) | GitHub Actions | Cloud | Gratis en repos públicos |
| Orquestación (aprendizaje) | Apache Airflow + Docker | **Local** | Gratis |
| Testing | pytest, dbt tests | GitHub Actions | Gratis |
| BI | Power BI Desktop | **Local** | Gratis |
| Versionado | Git / GitHub | Cloud | Gratis |

---

## 3. Decisiones de diseño

Cada decisión no obvia de este proyecto, y el porqué. Esta sección existe porque las
decisiones importan más que el código.

### Por qué una capa Parquet antes de la base de datos

El proyecto anterior iba directo de la API a PostgreSQL. Funciona, pero tiene un
problema: **si la transformación hacia la tabla tenía un bug, el dato original ya se
perdió** y hay que volver a golpear la fuente.

Aquí el dato aterriza primero como Parquet inmutable y particionado por fecha
(`bronze/orders/year=2026/month=09/day=13/data.parquet`). Eso da:

- **Reprocesamiento.** Si el esquema de la tabla cambia, se relee el Parquet en vez de
  volver a descargar todo.
- **Auditoría.** Siempre existe la copia exacta de lo que entregó la fuente ese día.
- **Compresión y tipado.** Parquet es columnar, comprime mucho mejor que CSV y conserva
  los tipos de datos (una fecha sigue siendo fecha, no texto).
- **Es el patrón real de la industria.** Data lake primero, warehouse después.

### Por qué Airflow corre local y no en la nube

Airflow es open source y gratuito, pero requiere un scheduler encendido 24/7. Ningún
proveedor administrado ofrece eso gratis de forma permanente: los deployments de
Astronomer arrancan alrededor de 0.35 USD/hora, y MWAA (AWS) o Cloud Composer (GCP)
salen aún más caros.

La decisión: **Airflow corre local en Docker, con los DAGs versionados en este repo, y
GitHub Actions es el scheduler de producción que efectivamente corre todos los días.**

Los DAGs de Airflow y los workflows de Actions ejecutan **los mismos scripts de Python**,
así que no hay lógica duplicada, solo dos orquestadores distintos apuntando al mismo
código. Esto es honesto y explícito: Airflow está aquí como ejercicio de orquestación
avanzada (dependencias entre tareas, reintentos, backfills, sensores), no como
infraestructura productiva.

### Por qué Power BI local

Power BI Desktop es gratuito, pero publicar al Power BI Service requiere cuenta
corporativa o educativa. El proyecto asume trabajo local: el archivo `.pbix` se versiona
en el repo, y el README incluye capturas y un recorrido en video. El refresh es manual o
programado desde Desktop.

### Por qué Supabase Storage y no S3

Supabase Storage expone un endpoint compatible con S3, así que el código usa `boto3`
igual que contra AWS. Se gana la práctica con la API estándar de object storage sin abrir
otra cuenta ni arriesgar cobros por egress.

### Por qué se separan dos tablas de hechos

Un pedido contiene varias líneas de producto. Mezclar ambos niveles en una sola tabla es
el error clásico que duplica montos al sumar (el total del pedido se repite una vez por
cada ítem).

- `fct_pedidos` → **grano: un pedido.** Aquí viven el total, el flete, las fechas y el estado.
- `fct_items_pedido` → **grano: una línea de pedido.** Aquí viven producto, cantidad y precio unitario.

El grano de cada hecho está documentado explícitamente en su YAML de dbt.

### Por qué el tipo de cambio se aplica por fecha de venta

El mart en colones no usa el tipo de cambio de hoy: usa **el del día en que ocurrió la
venta**, uniendo contra `dim_fecha`. Convertir histórico con la tasa actual es un error
de modelado temporal que destruye cualquier comparación año contra año.

---

## 4. Estructura del proyecto

```
retail-analytics-warehouse/
├── src/
│   ├── config.py                    # Configuración centralizada (env vars)
│   ├── extractors/
│   │   ├── base_extractor.py        # Contrato abstracto (ABC)
│   │   ├── csv_extractor.py         # Carga histórica del dataset
│   │   ├── order_generator.py       # Simulación de pedidos diarios
│   │   └── exchange_rate_extractor.py  # API del BCCR
│   ├── storage/
│   │   └── parquet_writer.py        # Escritura particionada a Supabase Storage
│   └── loaders/
│       ├── base_loader.py           # Contrato abstracto de carga
│       └── postgres_loader.py       # Carga por lotes (COPY)
│
├── dbt_project/
│   ├── models/
│   │   ├── staging/                 # Limpieza 1:1, sin lógica de negocio
│   │   └── marts/                   # Dimensiones y hechos
│   ├── snapshots/                   # SCD tipo 2
│   ├── seeds/                       # Catálogos estáticos
│   └── dbt_project.yml
│
├── airflow/
│   ├── dags/
│   │   ├── retail_ingestion_dag.py
│   │   └── retail_transformation_dag.py
│   ├── docker-compose.yml
│   └── README.md                    # Cómo levantar Airflow local
│
├── powerbi/
│   ├── retail_analytics.pbix
│   ├── medidas_dax.md               # Las medidas documentadas en texto plano
│   └── screenshots/
│
├── tests/
│   ├── test_config.py
│   ├── test_extractors.py
│   ├── test_parquet_writer.py
│   └── test_loaders.py
│
├── scripts/
│   └── ddl/                         # DDL de los schemas y tablas crudas
│
├── main.py                          # Orquestador del pipeline de ingesta
├── requirements.txt
├── requirements-dev.txt             # pytest y herramientas de desarrollo
└── README.md
```

---

## 5. Fuentes de datos

| Fuente | Tipo | Frecuencia | Notas |
|---|---|---|---|
| Olist e-commerce (Kaggle) | CSV, 9 tablas relacionadas | Carga única | ~100k pedidos con datos sucios reales: fechas nulas, reviews vacías, geolocalización inconsistente |
| Generador de pedidos | Python | Diaria | Genera pedidos plausibles respetando las distribuciones del dataset original (categorías, ticket promedio, estacionalidad) |
| API del BCCR | REST | Diaria | Tipo de cambio compra/venta del día |

**Sobre el generador:** existe porque un dataset estático no ejercita un pipeline. Con
él, el warehouse recibe datos nuevos cada día y los modelos incrementales y snapshots
tienen algo real que procesar.

---

## 6. Capas de datos

| Capa | Ubicación | Formato | Regla |
|---|---|---|---|
| **Bronze** | Supabase Storage | Parquet particionado por fecha | Inmutable. Nunca se sobrescribe ni se corrige. |
| **Silver** | `retail_raw` (PostgreSQL) | Tablas | Mismo contenido que bronze, ya tipado. Upsert idempotente. |
| **Gold** | `retail_analytics` (PostgreSQL) | Vistas y tablas de dbt | Modelo dimensional listo para consumo. |

Regla estricta: **los marts nunca leen del source directamente, siempre pasan por
staging.** Si cambia el nombre de una columna cruda, solo se toca el modelo de staging.

---

## 7. Modelo dimensional

```
                    ┌──────────────┐
                    │  dim_fecha   │
                    └──────┬───────┘
                           │
   ┌──────────────┐        │        ┌──────────────┐
   │ dim_cliente  │───┐    │    ┌───│ dim_vendedor │
   └──────────────┘   │    │    │   └──────────────┘
                      ▼    ▼    ▼
                  ┌─────────────────┐
                  │   fct_pedidos   │  grano: un pedido
                  └────────┬────────┘
                           │
                  ┌────────▼────────────┐
                  │  fct_items_pedido   │  grano: una línea
                  └────────┬────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      ┌──────────────┐         ┌──────────────────┐
      │ dim_producto │         │  dim_geografia   │
      └──────────────┘         └──────────────────┘
```

### Dimensiones

| Modelo | Descripción | Tipo |
|---|---|---|
| `dim_fecha` | Calendario generado: año, trimestre, mes, semana ISO, día de semana, indicador de fin de semana | Estática |
| `dim_cliente` | Cliente con su ubicación y fecha de primera compra | SCD1 |
| `dim_producto` | Producto, categoría (traducida), dimensiones físicas | **SCD2** (historiza cambios de categoría y precio de lista) |
| `dim_vendedor` | Vendedor y su ubicación | SCD1 |
| `dim_geografia` | Estado, ciudad y código postal normalizados | Estática |

`dim_fecha` es la columna vertebral: es lo que después habilita toda la *time
intelligence* en DAX y lo que une las ventas con el tipo de cambio.

### Hechos

| Modelo | Grano | Materialización | Métricas |
|---|---|---|---|
| `fct_pedidos` | Un pedido | Incremental | Valor total, flete, días de entrega, días de retraso |
| `fct_items_pedido` | Una línea de pedido | Incremental | Cantidad, precio unitario, valor de línea |
| `fct_ventas_colones` | Una línea de pedido | Tabla | Valor convertido al tipo de cambio de la fecha de venta |

### Snapshots (SCD tipo 2)

`snapshots/snap_producto.sql` historiza los cambios de precio de lista y categoría con
`valid_from` / `valid_to`. Esto permite responder **"¿a qué precio estaba este producto
cuando se vendió?"**, que es distinto de "¿a qué precio está hoy?".

---

## 8. Orquestación

### Producción: GitHub Actions

| Workflow | Horario (UTC) | Qué hace |
|---|---|---|
| `retail-analytics-daily-ingest.yml` | 11:00 | Genera pedidos del día, consulta el BCCR, escribe Parquet a bronze y carga a `retail_raw` |
| `retail-analytics-tests.yml` | En cada push | Corre `pytest` sobre `src/` |
| dbt Cloud Job | 12:00 | `dbt build` sobre staging, snapshots y marts |

Los workflows viven en `HomeLabsRepository/.github/workflows/` (raíz del repositorio,
requisito de GitHub Actions) con el prefijo `retail-analytics-` para no colisionar con
los de otros proyectos del monorepo.

### Aprendizaje: Airflow local

Dos DAGs que ejecutan exactamente los mismos scripts de Python, pero modelando el
pipeline como grafo de dependencias:

- `retail_ingestion_dag` — extracción → escritura a bronze → carga a silver, con
  reintentos por tarea y un sensor que verifica que el Parquet del día exista antes de
  cargar.
- `retail_transformation_dag` — dispara dbt y valida los resultados.

Se levanta con Docker Compose. Instrucciones en `airflow/README.md`.

---

## 9. Testing

Tres niveles, cada uno atrapa cosas distintas:

| Nivel | Herramienta | Qué verifica |
|---|---|---|
| Unitario | `pytest` | Lógica de Python aislada, sin tocar red ni base de datos |
| Calidad de datos | `dbt test` | Que el dato cumpla las reglas: unicidad, no nulos, valores aceptados, integridad referencial |
| Frescura | `dbt source freshness` | Que el dato del día efectivamente llegó |

### Tests unitarios

Cubren, como mínimo:

- `Config.get_db_url()` — construcción de la cadena de conexión y error claro si falta la contraseña.
- Normalización de nombres de columnas en los extractores.
- Particionado de rutas del `ParquetWriter` (que una fecha produzca la ruta correcta).
- Armado del SQL de upsert del loader.
- Parseo de la respuesta del BCCR, incluyendo el caso de fin de semana (no hay tipo de
  cambio publicado y hay que arrastrar el del día hábil anterior).

Las dependencias externas se reemplazan con mocks: **un test unitario que necesita
internet o base de datos no es un test unitario.**

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing
```

### Tests de dbt

Sobre las llaves de cada modelo (`unique`, `not_null`), `accepted_values` en las
categóricas, y `relationships` entre cada hecho y sus dimensiones — este último es el
que detecta un hecho huérfano apuntando a una dimensión que no existe.

---

## 10. Capa de análisis (Power BI)

Conexión a `retail_analytics` en **modo Import** (no DirectQuery: el pooler de Supabase
no aguanta bien la latencia por visual).

### Modelo semántico

- Relaciones del esquema estrella, todas de un solo sentido, de dimensión hacia hecho.
- `dim_fecha` marcada como tabla de fecha oficial del modelo.
- Columnas técnicas (llaves subrogadas, timestamps de carga) ocultas de la vista de reporte.
- Medidas organizadas en carpetas, con formato consistente.

### Medidas DAX principales

Documentadas en `powerbi/medidas_dax.md`. Los grupos:

| Grupo | Ejemplos |
|---|---|
| Base | Ventas totales, unidades, pedidos, ticket promedio |
| Time intelligence | YTD, MoM, YoY, media móvil 7 días (con `CALCULATE` + `DATEADD`, no calculadas a mano) |
| Cliente | Clientes activos, clientes nuevos vs recurrentes, segmentación RFM |
| Operación | Tiempo promedio de entrega, % de entregas tardías |

### Páginas del reporte

1. **Ejecutiva** — KPIs, tendencia de ventas, comparación contra período anterior.
2. **Producto** — desempeño por categoría, top y bottom performers, márgenes.
3. **Cliente** — cohortes de retención, matriz RFM, distribución geográfica.

---

## 11. Cómo correrlo localmente

```bash
# 1. Entorno virtual
python -m venv venv
source venv/Scripts/activate        # Windows Git Bash

# 2. Dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Credenciales
cp .env.example .env                # completar con los datos de Supabase

# 4. Crear schemas y tablas
psql -f scripts/ddl/create_schemas.sql

# 5. Carga histórica (una sola vez)
python -m src.extractors.csv_extractor

# 6. Pipeline diario
python main.py

# 7. Transformaciones
cd dbt_project && dbt build

# 8. Tests
pytest tests/ -v

# 9. Airflow local (opcional)
cd airflow && docker compose up -d  # UI en http://localhost:8080
```

**Nota de conexión:** Supabase requiere el *Transaction pooler* (puerto 6543) en vez de
la conexión directa (5432), por incompatibilidad de IPv6 en algunas redes. Mismo
hallazgo que en `finance-etl-pipeline`.

---

## 12. Estado del proyecto

- [ ] Tanda 0 — Estructura, schemas y DDL
- [ ] Tanda 1 — Carga histórica con escritura a Parquet y carga por lotes
- [ ] Tanda 2 — Generador de pedidos diarios y workflow de ingesta
- [ ] Tanda 3 — Modelo estrella en dbt
- [ ] Tanda 4 — Snapshots SCD2 y materialización incremental
- [ ] Tanda 5 — Integración del tipo de cambio del BCCR
- [ ] Tanda 6 — Modelo semántico en Power BI
- [ ] Tanda 7 — Análisis avanzado (time intelligence, cohortes, RFM)
- [ ] Tanda 8 — Airflow local y alertas
- [ ] Tanda 9 — Documentación final, capturas y video

---

## 13. Mejoras futuras

- Capturar métricas de ejecución del pipeline (filas, duración, errores) en una tabla y
  graficarlas, para observabilidad propia.
- `dbt exposures` declarando el reporte de Power BI, de modo que el lineage llegue hasta
  el consumo final.
- Contenerizar el pipeline completo para que corra idéntico en cualquier máquina.
- Evaluar DuckDB sobre los Parquet de bronze para análisis exploratorio sin tocar Postgres.

---

## Autor

Santiago Ramírez
