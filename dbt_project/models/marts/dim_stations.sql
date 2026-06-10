{{
    config(
        materialized='table',
    )
}}

with int_clean_ria as (
    select * from {{ ref('int_clean_ria') }}
),

station_attributes as (
    select
        province_id,
        station_code,
        max(province_name) as province_name,
        max(station_name) as station_name,
        min(observation_date) as first_observation_date,
        max(observation_date) as last_observation_date
    from int_clean_ria
    group by 1, 2
),

final as (
    select
        row_number() over (order by province_id, station_code) as station_key,
        province_id,
        station_code,
        province_name,
        station_name,
        first_observation_date,
        last_observation_date
    from station_attributes
)

select * from final
