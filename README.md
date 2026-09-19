# Andalucía Drought Monitor

Plataforma local de ingeniería de datos para monitorizar sequía y resiliencia agrícola en Andalucía.

Ingesta diaria de embalses (REDIAM) y climatología (RIA/IFAPA), transformación con **dbt** sobre **PostgreSQL/PostGIS**, orquestación con **Airflow**, y un panel de decisión **React + FastAPI**.

## Stack

| Capa | Tecnología |
|------|------------|
| Orquestación | Apache Airflow (`LocalExecutor`) |
| Almacén | PostgreSQL 16 + PostGIS |
| Transformación | dbt Core / dbt-postgres |
| API | FastAPI (`dashboard-api`) — lee solo el esquema `marts` |
| UI | React 19 + Vite + Tailwind + Leaflet + Recharts (`dashboard-frontend`) |

> El dashboard antiguo en Reflex (`docker/dashboard`) está deprecado en esta rama a favor de `dashboard-api` + `dashboard-frontend`.

## Arranque rápido

```bash
# Desde la raíz del repo
make up                 # stack completo (compose en docker/)
make dashboard-up       # solo API + frontend
```

- Frontend: http://localhost:5173  
- API: http://localhost:8000/api/dashboard · health en `/health`  
- Airflow: http://localhost:8080 (dev: `admin` / `admin`)

Los DAGs diarios/mensuales tienen `catchup=False`: para el primer poblado, lánzalos a mano y ejecuta `dbt run` / `dbt test`.

## Panel de decisión (UI)

La home prioriza:

1. Narrativa «qué cambió esta semana» + deltas  
2. Alertas accionables y recomendaciones  
3. Ranking de riesgo provincial  
4. KPIs con unidades correctas (precipitación en mm, volumen en hm³, déficit = ET0 − precip)  
5. Mapa / provincias / embalses / clima  

## Notas de métricas

- **Precipitación** = `avg_precipitation_mm` (mm), no el volumen de embalse.  
- **Déficit hídrico diario** = `daily_water_deficit_mm` (no es SPI-12).  
- **SPI-12** queda pendiente de climatología de referencia en marts.

## Desarrollo frontend

```bash
cd dashboard-frontend
npm install
npm run dev   # proxy /api → VITE_PROXY_TARGET o localhost:8000
```

## Secretos y despliegue (`.env`)

1. En la raíz del repo: `cp .env.example .env`
2. Pon la clave de Carto Basemaps en `VITE_CARTO_API_KEY=...` (pídela en https://carto.com/basemaps/apikey/ — es gratuita).
3. Arranca con `make up` o `make dashboard-up` (el Makefile pasa `--env-file .env`).
4. El mapa usa el parámetro de URL `?key=` (no `api_key`). Si ves la marca de agua, haz hard-refresh (Ctrl+Shift+R): el CDN y el navegador cachean las teselas.

Docker Compose también lee `docker/../.env` para el servicio `dashboard-frontend` y pasa la variable al contenedor (runtime) y como build arg. El `.env` está en `.gitignore` y en `.dockerignore`: no se copia dentro de la imagen.

## Marca / emblema

El logo del panel usa el [Emblema de la Junta de Andalucía 2020](https://commons.wikimedia.org/wiki/File:Emblema_de_la_Junta_de_Andaluc%C3%ADa_2020.svg)
(`dashboard-frontend/public/brand/emblema-junta-andalucia.svg`), licencia **CC BY-SA 4.0**.
