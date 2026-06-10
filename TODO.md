# Checklist del Proyecto

- [x] Fase 1: Crear `docker-compose.yml` y `Dockerfile` para Postgres, Airflow y Metabase.
- [x] Fase 2: Crear scripts de Python (`scripts/`) usando Polars para descargar datos.
- [x] Fase 3: Crear DAGs de Airflow (`airflow_workspace/dags/`) para orquestar los scripts.
- [x] Fase 4: Configurar el proyecto dbt (`dbt_project/`) y el perfil de conexión.
- [x] Fase 5: Crear modelos dbt Staging (`stg_embalses.sql`, etc.).
- [x] Fase 6: Crear modelos dbt Marts (`dim_`, `fact_`).