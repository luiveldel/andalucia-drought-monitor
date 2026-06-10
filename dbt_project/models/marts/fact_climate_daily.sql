{{
    config(
        materialized='table',
    )
}}

with int_clean_ria as (
    select * from {{ ref('int_clean_ria') }}
),

dim_date as (
    select * from {{ ref('dim_date') }}
),

dim_stations as (
    select * from {{ ref('dim_stations') }}
),

joined as (
    select
        d.date_key,
        st.station_key,
        s.mean_temperature_c,
        s.max_temperature_c,
        s.min_temperature_c,
        s.mean_humidity_pct,
        s.max_humidity_pct,
        s.min_humidity_pct,
        s.precipitation_mm,
        s.solar_radiation,
        s.mean_wind_speed,
        s.max_wind_speed,
        s.mean_wind_direction_deg,
        s.max_wind_direction_deg,
        s.reference_evapotranspiration_mm,
        s.battery_level,
        s.loaded_at
    from int_clean_ria as s
        inner join dim_date as d
            on s.observation_date = d.observation_date
        inner join dim_stations as st
            on s.province_id = st.province_id
            and s.station_code = st.station_code
)

select * from joined
