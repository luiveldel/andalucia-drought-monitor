with stg_reservoir_catalog as (
    select * from {{ ref('stg_reservoir_catalog') }}
),

cleaned as (
    select * from stg_reservoir_catalog
    where reservoir_id is not null and trim(reservoir_id) <> ''
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by reservoir_id
            order by loaded_at desc
        ) as row_num
    from cleaned
)

select
    fid,
    reservoir_id as reservoir_code,
    reservoir_type,
    reservoir_name,
    province as province_name,
    water_system as exploitation_system,
    hydrographic_district as watershed_demarcation,
    river_name,
    geometry_wkt,
    dam_name,
    loaded_at
from deduplicated
where row_num = 1
