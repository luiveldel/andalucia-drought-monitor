with stg_ria_clima as (
    select * from {{ ref('stg_ria_clima') }}
),

cleaned as (
    select * from stg_ria_clima
    where observation_date is not null
        and province_id is not null
        and station_code is not null
        and trim(station_code) <> ''
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by observation_date, province_id, station_code
            order by loaded_at desc
        ) as row_num
    from cleaned
)

select
    observation_date,
    province_id,
    province_name,
    station_code,
    station_name,
    mean_temperature_c,
    max_temperature_c,
    min_temperature_c,
    mean_humidity_pct,
    max_humidity_pct,
    min_humidity_pct,
    precipitation_mm,
    solar_radiation,
    mean_wind_speed,
    max_wind_speed,
    mean_wind_direction_deg,
    max_wind_direction_deg,
    reference_evapotranspiration_mm,
    battery_level,
    source_updated_at,
    loaded_at
from deduplicated
where row_num = 1