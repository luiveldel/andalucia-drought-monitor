{{
    config(
        materialized='table',
    )
}}

-- PostGIS Magic: Extraemos Latitud (Y) y Longitud (X) del centroide real del polígono
-- Calculamos el área en hectáreas (ST_Area en formato geography devuelve metros cuadrados / 10000)

with staging as (
    select * from {{ ref('stg_gis_agricultural_zones') }}
)

select
    province_id,
    province_name,
    ST_Y(ST_Centroid(geom))::float as latitude,
    ST_X(ST_Centroid(geom))::float as longitude,
    round((ST_Area(geom::geography) / 10000)::numeric, 1) as agricultural_area_ha
from staging
