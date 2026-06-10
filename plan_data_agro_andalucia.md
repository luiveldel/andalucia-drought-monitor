# Proyecto de Ingeniería de Datos: Monitor de Resiliencia Agrícola y Sequía en Andalucía

Este documento sirve como especificación técnica completa, registro de decisiones de arquitectura y guía de desarrollo para la plataforma de datos. El objetivo es analizar el impacto de la sequía en el sector agrícola andaluz cruzando datos meteorológicos, hidrográficos y de delimitación geográfica de la Junta de Andalucía.

---

## 1. Visión General del Proyecto

### El Problema Técnico y Social
Andalucía se enfrenta de forma recurrente a crisis hídricas severas que afectan directamente a su principal motor económico: la agricultura. Este proyecto automatiza la ingesta, limpieza, modelado y visualización de datos públicos para monitorizar la resiliencia del sector frente a la escasez de agua, eliminando silos informativos mediante un pipeline centralizado.

### Fuentes de Datos de la Junta de Andalucía

#### Métricas de Telemetría (Carga Diaria):
1. **Datos Hidrológicos:** Estado de los embalses y pantanos (Volumen actual, capacidad máxima, porcentaje de llenado). Actualización diaria.
2. **Datos Meteorológicos:** Red de Información Agroclimática (RIA) de Andalucía (Precipitaciones, temperaturas, evapotranspiración). Actualización diaria.

#### Datos Maestros e Infraestructura (Carga Mensual / Semicruda):
1. **Datos Agrícolas:** Estadísticas de producción agrícola del Instituto de Estadística y Cartografía de Andalucía (IECA) y registros de superficies cultivadas. Actualización anual/mensual.
2. **Datos Geográficos:** Delimitación de cuencas hidrográficas y términos municipales (GeoJSON/Shapefiles estáticos).

---

## 2. Arquitectura de Datos (Medallion Architecture)

Para garantizar un flujo ordenado, histórico y tolerante a fallos, el Data Warehouse local (PostgreSQL + PostGIS) se estructura en esquemas lógicos gestionados de forma secuencial por dbt, aplicando una estricta convención de nomenclatura industrial en inglés:

```text
[Airflow Ingest] ──> RAW (Bronze) ──> STAGING (Silver) ──> INTERMEDIATE (Silver Guard) ──> MARTS (Gold) ──> [Reflex UI]
```

1. **Capa Bronze (Esquema: `raw`):**
   * Aterrizaje directo de las extracciones hechas por Apache Airflow desde las APIs, Web Scraping o ficheros de la Junta de Andalucía mediante scripts optimizados en Polars.
   * Operación por truncado masivo (TRUNCATE) para catálogos estáticos y anexado particionado por fecha para series temporales. No se aplican transformaciones.
2. **Capa Silver (Esquema: `staging`):**
   * Modelos de Staging (stg_*): Enfocados en la limpieza técnica inicial. Tipado estricto (fechas a DATE, volúmenes a NUMERIC), renombrado de columnas a inglés estándar (snake_case) y normalización UTF-8.
   * Modelos Intermedios (int_*): Capa de seguridad defensiva. Implementa estrategias de desduplicación analítica avanzada mediante funciones de ventana analíticas:
3. **Capa Gold (Esquema: `marts`):**
   * Modelos analíticos estructurados bajo un modelo dimensional optimizado (Esquema en Estrella) para su consumo inmediato.
   * Tablas de Hechos: fact_drought_daily, fact_reservoir_daily, fact_drought_alert.
   * Tablas de Dimensiones Geoespaciales: dim_reservoirs, dim_provinces_geo. Esta última explota la extensión PostGIS ejecutando funciones nativas en el DWH (ST_Centroid, ST_Area) para extraer dinámicamente las coordenadas físicas y las hectáreas agrícolas reales del polígono geometry crudo.

---

## 3. Stack Tecnológico (100% Local y Open Source)

* **Orquestador:** Apache Airflow corriendo en contenedores Docker.
* **Ingesta:** Scripts nativos en Python (Polars para manejo de memoria ultrarrápido + SQLAlchemy).
* **Data Warehouse:** PostgreSQL 16 (con soporte opcional para PostGIS para análisis espacial).
* **Transformación y Modelado:** dbt Core (v1.7 o superior) ejecutado localmente o mediante la CLI de dbt.
* **Capa de Visualización (BI)** Reflex Dashboard App (Framework Full-Stack en Python embebido con Next.js, Tailwind CSS, Recharts y Plotly Express), sustituyendo herramientas rígidas externas por código modular.
*
---

## 4. Estructura de Directorios del Proyecto
Para optimizar el rendimiento hídrico del servidor local, las cargas de trabajo de Airflow se dividen de manera estricta según la volatilidad del dato:

📆 DAG de Telemetría Diaria: Extrae, limpia y cruza los niveles de agua de los embalses y la climatología RIA cada 24 horas. Mantiene los KPIs actualizados al día en el frontend.

🗄️ DAG de Infraestructura Mensual: Se ejecuta el primer día de cada mes. Refresca el catálogo maestro de la REDIAM y procesa la geometría pesada de las zonas agrícolas SIGPAC. Aísla el coste de cálculo computacional de PostGIS fuera de la rutina diaria.

---

## 5. Estructura de Directorios del Proyecto

Code output
Archivo plan_proyecto_datos_andalucia.md generado con éxito.

```text
agro-sequia-andalucia/
├── docker/
│   ├── docker-compose.yml
│   └── airflow/
│       └── Dockerfile
├── airflow_workspace/
│   ├── dags/
│   │   ├── dag_daily_telemetry.py          # Flujo síncrono diario (Lluvias/Embalses)
│   │   └── dag_monthly_infrastructure.py   # Flujo estático mensual (Catálogos/PostGIS)
│   ├── plugins/
│   └── logs/
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/
│       │   ├── src_andalucia.yml
│       │   ├── stg_embalses_daily.sql
│       │   ├── stg_ria_climate_daily.sql
│       │   └── stg_reservoir_catalog.sql
│       ├── intermediate/
│       │   └── int_reservoir_catalog.sql   # Filtro defensivo de desduplicación
│       └── marts/
│           ├── dim_reservoirs.sql
│           ├── dim_provinces_geo.sql       # Extracción de centroides con PostGIS
│           ├── fact_drought_daily.sql
│           └── fact_drought_alert.sql
├── dashboard/
│   ├── rxconfig.py                        # Configuración del servidor Reflex
│   ├── requirements.txt                   # Pandas, Plotly, SQLAlchemy, Reflex
│   └── app/
│       ├── app.py                         # Layout principal, Estado y Mapa interactivo
│       ├── components.py                  # KPI Cards, Donut semántico y Tablas en Dark Mode
│       └── db.py                          # Pasarela de lectura optimizada a marts en SQLAlchemy
└── plan.md