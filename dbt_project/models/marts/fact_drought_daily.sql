{{
    config(
        materialized='incremental',
        unique_key=['date_key', 'province_name'],
        on_schema_change='append_new_columns',
    )
}}

with fact_reservoir_daily as (
    select * from {{ ref('fact_reservoir_daily') }}
    {% if is_incremental() %}
        where date_key > (select max(date_key) from {{ this }})
    {% endif %}
),

fact_climate_daily as (
    select * from {{ ref('fact_climate_daily') }}
    {% if is_incremental() %}
        where date_key > (select max(date_key) from {{ this }})
    {% endif %}
),

dim_reservoirs as (
    select * from {{ ref('dim_reservoirs') }}
),

dim_stations as (
    select * from {{ ref('dim_stations') }}
),

dim_date as (
    select * from {{ ref('dim_date') }}
),

int_reservoir_daily_delta as (
    select * from {{ ref('int_reservoir_daily_delta') }}
),

delta_province_agg as (
    select
        d.date_key,
        dr.province_name,
        avg(delta.daily_volume_delta_hm3) as avg_volume_delta_hm3
    from int_reservoir_daily_delta as delta
        inner join dim_date as d
            on delta.observation_date = d.observation_date
        inner join dim_reservoirs as dr
            on delta.reservoir_code = dr.reservoir_code
    group by 1, 2
),

reservoir_agg as (
    select
        fr.date_key,
        dr.province_name,
        dr.watershed_demarcation,
        avg(fr.fill_percentage)        as avg_fill_pct,
        sum(fr.stored_volume_hm3)      as total_stored_hm3,
        sum(dr.reservoir_capacity_hm3) as total_capacity_hm3
    from fact_reservoir_daily as fr
        left join dim_reservoirs as dr
            on fr.reservoir_key = dr.reservoir_key
    group by 1, 2, 3
),

climate_agg as (
    select
        fc.date_key,
        ds.province_name,
        avg(fc.precipitation_mm)                                          as avg_precipitation_mm,
        avg(fc.reference_evapotranspiration_mm)                           as avg_et0_mm,
        avg(fc.mean_temperature_c)                                        as avg_temp_c,
        -- déficit hídrico diario: lo que se evapora menos lo que llueve
        avg(fc.reference_evapotranspiration_mm - fc.precipitation_mm)     as daily_water_deficit_mm,
        dp.avg_volume_delta_hm3                                           as avg_volume_delta_hm3,
        dp.avg_volume_delta_hm3 / nullif(avg(fc.precipitation_mm), 0)     as implicit_runoff_coeff
    from fact_climate_daily as fc
        left join dim_stations as ds
            on fc.station_key = ds.station_key
        left join delta_province_agg as dp
            on fc.date_key = dp.date_key
            and ds.province_name = dp.province_name
    group by 1, 2, dp.avg_volume_delta_hm3
),

joined as (
    select
        r.date_key,
        dd.observation_date,
        dd.hydrological_year,
        r.province_name,
        r.watershed_demarcation,
        r.avg_fill_pct,
        r.total_stored_hm3,
        r.total_capacity_hm3,
        c.avg_precipitation_mm,
        c.avg_et0_mm,
        c.avg_temp_c,
        c.daily_water_deficit_mm,
        c.avg_volume_delta_hm3,
        c.implicit_runoff_coeff,
        -- índice clave: correlación lluvia → llenado con lag
        r.avg_fill_pct / nullif(c.avg_et0_mm, 0) as hydric_stress_index
    from reservoir_agg as r
        left join climate_agg as c
            on r.date_key = c.date_key
            and r.province_name = c.province_name
        left join dim_date as dd
            on r.date_key = dd.date_key
)

select
    date_key,
    observation_date,
    hydrological_year,
    province_name,
    watershed_demarcation,
    avg_fill_pct,
    total_stored_hm3,
    total_capacity_hm3,
    avg_precipitation_mm,
    avg_et0_mm,
    avg_temp_c,
    daily_water_deficit_mm,
    avg_volume_delta_hm3,
    implicit_runoff_coeff,
    hydric_stress_index
from joined
