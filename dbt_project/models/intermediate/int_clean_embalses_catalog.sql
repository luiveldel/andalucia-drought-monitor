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
    reservoir_id,
    reservoir_type,
    reservoir_name,
    province,
    water_system,
    hydrographic_district,
    river_name,
    geometry,
    dam_name,
    loaded_at
from deduplicated
where row_num = 1
