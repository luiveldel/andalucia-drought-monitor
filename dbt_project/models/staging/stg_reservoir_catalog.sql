{{ config(materialized='table') }}

with source as (
    select * from {{ source('raw', 'raw_embalses_catalog') }}
)

select
    fid,
    cod_est as reservoir_id,
    trim(tipo)::varchar as reservoir_type,
    trim(nombre)::varchar as reservoir_name,
    trim(provincia)::varchar as province,
    trim(sistema)::varchar as water_system,
    trim(dist_dem)::varchar as hydrographic_district,
    trim(nombre_rio)::varchar as river_name,
    trim(geom)::varchar as geometry_wkt,
    trim(nom_pres)::varchar as dam_name,
    _loaded_at as loaded_at
from source
