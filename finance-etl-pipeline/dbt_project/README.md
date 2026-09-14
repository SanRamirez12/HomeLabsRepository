# dbt_project — Capa de transformación (la "T" del ETL)

Esta carpeta es el proyecto de **dbt** del pipeline. Aquí es donde los datos
crudos que el pipeline de Python dejó en Postgres (`raw.stock_prices`) se
limpian, se renombran y se convierten en tablas listas para analizar
(`daily_returns`, `rolling_avg_price`), que son las que consume el dashboard
de Streamlit.

> **Recordatorio para el yo del futuro:** Python hace *extract* + *load*
> (ver `../src/README.md`). dbt hace *transform*. Nada de Python toca las
> tablas finales; nada de dbt habla con Yahoo Finance. Esa separación es
> intencional.

---

## 1. Qué es dbt y por qué se usó aquí

**dbt (data build tool)** es una herramienta que permite transformar datos
*dentro* de la base de datos escribiendo únicamente `SELECT`s. Uno no escribe
`CREATE TABLE` ni `INSERT`: escribe una consulta, y dbt se encarga de
envolverla en el DDL necesario y materializarla como vista o tabla.

Lo que aporta y por lo que se eligió para este proyecto:

| Aporte | Cómo se ve en este proyecto |
|---|---|
| **Modularidad** | Cada transformación es un archivo `.sql` (un "modelo"), no un script gigante |
| **Dependencias automáticas** | `ref()` y `source()` le dicen a dbt en qué orden ejecutar todo (DAG) |
| **Tests de calidad de datos** | `unique`, `not_null`, `accepted_values` declarados en YAML |
| **Documentación viva** | `dbt docs generate` produce un sitio con descripciones y grafo de lineage |
| **Versionado en Git** | La lógica analítica vive en el repo, no en vistas sueltas dentro de la BD |
| **Un mismo código, varios entornos** | El *profile* decide a qué base de datos apuntar; el SQL no cambia |

Idea clave: **dbt no mueve datos entre sistemas**. Los datos ya están en
Postgres; dbt solo los reordena ahí mismo (`ELT`, no `ETL` clásico).

---

## 2. Estructura de la carpeta

```
dbt_project/
├── dbt_project.yml            # Configuración del proyecto (nombre, profile, materializaciones)
├── profiles.yml.example       # Plantilla de conexión para correr dbt en local
└── models/
    ├── staging/
    │   ├── sources.yml            # Declara la tabla cruda raw.stock_prices como "source"
    │   ├── stg_stock_prices.sql   # Limpieza y renombrado (materializado como VIEW)
    │   └── stg_stock_prices.yml   # Descripciones + tests del modelo staging
    └── marts/
        ├── daily_returns.sql      # Retorno diario % por ticker (TABLE)
        ├── daily_returns.yml
        ├── rolling_avg_price.sql  # Media móvil de 7 días (TABLE)
        └── rolling_avg_price.yml
```

Carpetas que **no** están versionadas (están en el `.gitignore` del proyecto):
`target/` (SQL compilado y artefactos), `dbt_packages/`, `logs/` y el
`profiles.yml` real (contiene credenciales).

---

## 3. Arquitectura de capas: staging → marts

Es la convención estándar de dbt, y se respetó a propósito:

```
raw.stock_prices          ← source: lo que carga el pipeline de Python (NO se toca)
        ↓
stg_stock_prices          ← staging: limpieza 1:1, sin lógica de negocio (view)
        ↓
   ┌────┴────┐
daily_returns   rolling_avg_price   ← marts: métricas de negocio (tables)
        ↓
   Dashboard de Streamlit
```

**Regla que se siguió:** los modelos de marts **nunca** leen del source
directamente, siempre pasan por staging. Así, si mañana cambia el nombre de una
columna en la tabla cruda, solo hay que tocar `stg_stock_prices.sql` y todo lo
demás sigue funcionando.

### Por qué staging es *view* y marts son *table*

Definido en `dbt_project.yml`:

```yaml
models:
  finance_etl_pipeline:
    staging:
      +materialized: view     # no ocupa espacio, siempre refleja el dato crudo actual
    marts:
      +materialized: table    # se materializa físicamente → consultas rápidas para el dashboard
```

- **View** en staging: la transformación es barata (solo renombrar columnas), no
  vale la pena duplicar datos en disco.
- **Table** en marts: llevan funciones de ventana (`LAG`, `AVG OVER`) que son más
  caras; materializarlas hace que el dashboard responda rápido y que la carga se
  pague una sola vez al día, cuando corre el job.

---

## 4. Los archivos, uno por uno

### `dbt_project.yml`

El archivo raíz que le dice a dbt "esto es un proyecto dbt". Define:

- `name: finance_etl_pipeline` → el nombre del proyecto. **Importante:** este
  mismo nombre es el que se usa como clave dentro del bloque `models:` para
  aplicar configuraciones por carpeta.
- `profile: default` → qué conexión usar (ver sección 6).
- Las rutas estándar (`model-paths`, `test-paths`, `macro-paths`, etc.).
- `clean-targets` → qué borra `dbt clean`.
- El bloque `models:` con las materializaciones por capa explicadas arriba.

### `models/staging/sources.yml`

Declara **de dónde vienen los datos crudos**. Registrar la tabla como *source*
(en vez de escribir `select * from raw.stock_prices` a pelo) da tres cosas:

1. Se puede referenciar con `{{ source('raw', 'stock_prices') }}`, y dbt sabe
   que ese es el punto de entrada del DAG.
2. Aparece en el grafo de lineage de la documentación.
3. Se le pueden poner **tests directamente al dato crudo**, antes de transformarlo:
   `id` es `unique` y `not_null`; `ticker`, `date` y `close` son `not_null`.

Si esos tests fallan, el problema está en el pipeline de Python, no en dbt — es
un detector temprano muy útil.

### `models/staging/stg_stock_prices.sql`

Modelo de staging. Es deliberadamente aburrido: un CTE que lee el source y otro
que **renombra columnas** a nombres explícitos y sin conflicto con palabras
reservadas de SQL:

| Columna cruda | Columna en staging | Por qué |
|---|---|---|
| `id` | `price_id` | Más descriptivo que un `id` genérico |
| `date` | `price_date` | `date` es tipo/palabra reservada en SQL |
| `open` | `open_price` | `open` es palabra reservada |
| `high` / `low` / `close` | `high_price` / `low_price` / `close_price` | Consistencia y claridad |

Aquí **no hay lógica de negocio a propósito**: staging solo estandariza. Toda la
matemática vive en marts.

### `models/staging/stg_stock_prices.yml`

Documentación y tests del modelo:
- `price_id`: `unique` + `not_null` → garantiza que no se duplicaron filas al cargar.
- `ticker`: `not_null` + `accepted_values` con la lista `['AAPL','MSFT','GOOGL','AMZN','TSLA']`
  → si algún día se agrega un ticker nuevo en `main.py` (`TICKERS`) y se olvida
  actualizar esta lista, **el test falla**. Es intencional: obliga a mantener
  ambos lados sincronizados.
- `price_date`: `not_null`.

### `models/marts/daily_returns.sql`

Calcula el **retorno diario porcentual** por acción.

```sql
lag(close_price) over (partition by ticker order by price_date) as previous_close_price
```

- `LAG()` trae el valor de la fila anterior.
- `partition by ticker` es lo crítico: sin eso, el "día anterior" de la primera
  fila de MSFT sería la última fila de AAPL, y el cálculo sería basura.
- Fórmula: `(close_price - previous_close_price) / previous_close_price * 100`,
  redondeada a 2 decimales.
- El `where previous_close_price is not null` elimina el primer día de cada
  ticker, que por definición no tiene día anterior (y evitaría una división
  contra `NULL`).

### `models/marts/rolling_avg_price.sql`

Calcula la **media móvil de 7 días** del precio de cierre:

```sql
avg(close_price) over (
    partition by ticker
    order by price_date
    rows between 6 preceding and current row
) as moving_avg_7d
```

- `rows between 6 preceding and current row` = ventana de 7 filas (las 6
  anteriores + la actual).
- Otra vez `partition by ticker` para no mezclar acciones.
- En los primeros días de cada ticker la ventana tiene menos de 7 filas, así que
  el promedio es sobre lo que haya disponible — está documentado así en el YAML.

### `models/marts/*.yml`

Descripciones y tests `not_null` sobre las llaves (`ticker`, `price_date`) de
cada mart.

### `profiles.yml.example`

Plantilla de conexión. **Actualmente está vacío** — es un pendiente conocido.
Contenido sugerido para rellenarlo (usando Supabase, *Transaction pooler*,
puerto 6543):

```yaml
default:
  target: dev
  outputs:
    dev:
      type: postgres
      host: "{{ env_var('DB_HOST') }}"
      port: 6543
      user: "{{ env_var('DB_USER') }}"
      password: "{{ env_var('DB_PASSWORD') }}"
      dbname: "{{ env_var('DB_NAME') }}"
      schema: analytics
      threads: 4
```

El `profiles.yml` real va en `~/.dbt/profiles.yml` (o en esta carpeta, pero
está ignorado por Git) y **nunca se sube al repo**.

---

## 5. Dónde terminan las tablas: el schema `analytics`

`schema:` en el profile (o la credencial de dbt Cloud) es `analytics`, y como
ningún modelo define un `+schema` propio, **todos los modelos se materializan
en `analytics`**:

- `analytics.stg_stock_prices` (view)
- `analytics.daily_returns` (table)
- `analytics.rolling_avg_price` (table)

Por eso el dashboard (`../app.py`) consulta `analytics.daily_returns` y
`analytics.rolling_avg_price`. El schema `raw` queda exclusivamente para el dato
crudo que escribe Python.

---

## 6. Conexión: profile local vs dbt Cloud

dbt separa **el código** (esta carpeta, versionada) de **las credenciales**
(el profile, fuera del repo). El mismo SQL corre contra cualquier base de datos
según qué profile se use.

- **En local:** `dbt_project.yml` pide el profile `default`, y dbt lo busca en
  `~/.dbt/profiles.yml` (o en esta carpeta). Ahí van host, usuario, contraseña y
  el schema destino.
- **En dbt Cloud:** no existe `profiles.yml`. La conexión y las credenciales se
  configuran en la interfaz del entorno de dbt Cloud, y dbt Cloud genera el
  profile al vuelo. Por eso el proyecto funciona igual en ambos lados sin
  cambiar una línea de SQL.

**Detalle importante de Supabase:** se usa el *Transaction pooler* (puerto
**6543**) en vez de la conexión directa (5432), por compatibilidad de red
(IPv4 vs IPv6). Es el mismo motivo por el que el pipeline de Python se conecta
por ahí.

---

## 7. Automatización

La transformación corre sola en **dbt Cloud**, con un job programado
**diariamente a las 13:00 UTC** — una hora después del workflow de GitHub
Actions que hace extract + load (12:00 UTC), para asegurar que el dato crudo ya
esté en la base cuando dbt lo lea.

El job corre `dbt build`, que en un solo comando:
1. Ejecuta los modelos en orden de dependencias (staging antes que marts).
2. Corre los tests de cada modelo **inmediatamente después** de construirlo, así
   que un modelo con datos malos no propaga el problema aguas abajo.
3. Regenera la documentación.

---

## 8. Comandos útiles

Todos se corren **desde dentro de esta carpeta** (`dbt_project/`):

```bash
dbt debug            # verifica que la conexión y el profile estén bien configurados
dbt run              # construye todos los modelos
dbt test             # corre solo los tests
dbt build            # run + test en orden de dependencias (lo que corre dbt Cloud)

dbt run  -s stg_stock_prices     # construir un modelo puntual
dbt build -s daily_returns+      # ese modelo y todo lo que depende de él
dbt run  -s staging              # solo la carpeta staging

dbt compile          # ver el SQL final (con ref/source resueltos) en target/
dbt docs generate    # genera la documentación
dbt docs serve       # la abre en el navegador, con el grafo de lineage
dbt clean            # borra target/ y dbt_packages/
```

---

## 9. Cómo agregar un modelo nuevo (receta rápida)

1. Crear `models/marts/mi_modelo.sql` con un `SELECT` que lea de
   `{{ ref('stg_stock_prices') }}` (nunca del source directo).
2. Crear `models/marts/mi_modelo.yml` con la descripción y al menos los tests
   `not_null` de las llaves.
3. `dbt build -s mi_modelo` para construirlo y testearlo.
4. Si es para el dashboard, consultarlo como `analytics.mi_modelo` en `app.py`.

**Si se agrega un ticker nuevo:** hay que tocar dos lugares — la lista `TICKERS`
en `../main.py` y el test `accepted_values` en
`models/staging/stg_stock_prices.yml`. Si no, `dbt test` falla (por diseño).

---

## 10. Pendientes / mejoras futuras

- Rellenar `profiles.yml.example` (hoy está vacío) con la plantilla de la sección 4.
- Agregar tests de relaciones (`relationships`) entre marts y staging.
- Sacar la lista de tickers a un `seed` de dbt, para que fuente de verdad y test
  de `accepted_values` sean el mismo archivo.
- Considerar materialización `incremental` en marts si el histórico crece mucho
  (hoy se reconstruyen completas cada día, lo cual está perfecto a esta escala).
