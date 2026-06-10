# Cursor AI Rules & Project Context
# Project: Agricultural Resilience and Drought Monitor (Andalusia)

## 1. Role and Purpose
Act as a Senior Data Engineer. Your goal is to help build a local data platform that ingests, cleans, models, and visualizes public data from the Junta de Andalucía (Hydrology, Meteorology, and Agriculture) to monitor the impact of drought.

The main focus is to create clean, memory-efficient code ready for a Docker container environment.

## 2. Tech Stack and Code Preferences
You MUST strictly use these tools and conventions when generating code:

* **Orchestration:** Apache Airflow. DAGs must be idempotent, use `kwargs['ds']` for incremental loads, and be well documented.
* **Python Processing:** ALWAYS use `polars` for in-memory data manipulation (NEVER `pandas`). Use `requests` for API calls and `SQLAlchemy`/`psycopg2` for database connections.
* **Database:** PostgreSQL 16. Always use `snake_case` for table, schema, and column names. Enforce strict data types (e.g., dates as `DATE`, metrics as `NUMERIC`).
* **SQL Transformation:** dbt Core. Generate models structured in CTEs (Common Table Expressions).

## 3. Data Architecture (Medallion Schema)
The PostgreSQL Data Warehouse is logically divided into three layers managed by dbt. All SQL/Python code must respect this flow:

1. **`raw` (Bronze Layer):** Landing zone for raw data extracted by Airflow. No transformations applied; original format is kept.
2. **`staging` (Silver Layer):** dbt models for technical cleaning (data typing, null removal, string/UTF-8 normalization).
3. **`marts` (Gold Layer):** Analytical dbt models (Star Schema) ready for BI (Metabase).

## 4. Project Structure
When reading or creating new files, assume this directory structure:

```text
agro-sequia-andalucia/
├── .cursor/
│   └── project_context.md
├── docker/
│   ├── docker-compose.yml
│   └── airflow/Dockerfile
├── airflow_workspace/
│   ├── dags/
│   ├── plugins/
│   └── logs/
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/
│       └── marts/
└── scripts/

## 5. Critical Instructions for Code Generation
Python Scripts: When writing ingestion scripts in the /scripts folder, wrap the core logic in modular functions (e.g., def fetch_data(), def process_with_polars(), def load_to_postgres()) so Airflow can easily invoke them using a PythonOperator.

dbt Models: .sql files in /models/staging must have the stg_ prefix. Files in /models/marts must have the dim_ (dimensions) or fact_ (facts) prefixes. Always add configuration blocks at the top of dbt models ({{ config(materialized='table'/'view') }}).

Docker: Ensure that Docker network dependencies assume all services (Postgres, Airflow, Metabase) run on the same docker-compose network.

## 6. Data Sources (Context)
Reservoirs (Embalses): Volume, capacity, % filled (Daily update).

RIA (Agroclimatic Information Network): Precipitation, temperatures (Daily update).

IECA: Agricultural production and surface areas (Monthly/Annual).

## 7. MCP Tools Utilization (Token & Context Optimization)
* ALWAYS use the `graphify` tool to map relationships between dbt models, tables, or Python functions before writing complex transformations.
* ALWAYS use the `caveman` tool to summarize long system outputs, logs, or external API documentations. Keep your internal reasoning and outputs extremely concise to save tokens.