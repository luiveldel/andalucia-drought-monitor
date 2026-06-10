with source as (
    select * from {{ source('raw', 'raw_gis_agricultural_zones') }}
)

select
    cod_prov::varchar as province_id,
    trim(name)::varchar as province_name,
    cod_ccaa::varchar as region_id,
    cartodb_id::int as cartodb_id,
    geometry as geom, -- Mantenemos el tipo geometry puro de PostGIS
    _loaded_at as loaded_at
from source
