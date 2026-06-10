{{
    config(
        materialized='table',
    )
}}

-- días de estrés térmico: cuando hace calor y hay poco agua
-- índice de estrés calórico agrícola: a 40°C con el embalse al 10%,
-- el riesgo es máximo; a 40°C con el embalse al 90%, el riesgo es bajo.

with fact_climate_daily as (
    select * from {{ ref('fact_climate_daily') }}
),

dim_stations as (
    select * from {{ ref('dim_stations') }}
),

dim_date as (
    select * from {{ ref('dim_date') }}
),

fact_drought_daily as (
    select * from {{ ref('fact_drought_daily') }}
),

heat_days as (
    select
        fc.date_key,
        ds.province_name,
        count(*) as stations_in_heat_stress,
        avg(fc.max_temperature_c) as avg_max_temp_c,
        avg(fc.min_humidity_pct) as avg_min_humidity_pct,
        avg(fc.solar_radiation) as avg_solar_radiation
    from fact_climate_daily as fc
        inner join dim_stations as ds
            on fc.station_key = ds.station_key
    where
        fc.max_temperature_c > 35
        and fc.min_humidity_pct < 30
    group by 1, 2
),

agg_by_date as (
    select
        dd.observation_date,
        dd.hydrological_year,
        h.province_name,
        h.stations_in_heat_stress,
        h.avg_max_temp_c,
        h.avg_min_humidity_pct,
        h.avg_solar_radiation,
        -- cruce con estado del embalse ese mismo día
        d.avg_fill_pct as reservoir_fill_pct,
        d.daily_water_deficit_mm,
        -- índice compuesto: cuanto más calor y menos agua, más crítico
        h.avg_max_temp_c * (1 - d.avg_fill_pct / 100.0) as agricultural_risk_index
    from heat_days as h
        inner join dim_date as dd
            on h.date_key = dd.date_key
        left join fact_drought_daily as d
            on h.date_key = d.date_key
        and h.province_name = d.province_name
)

select
    observation_date,
    hydrological_year,
    province_name,
    stations_in_heat_stress,
    avg_max_temp_c,
    avg_min_humidity_pct,
    avg_solar_radiation,
    reservoir_fill_pct,
    daily_water_deficit_mm,
    agricultural_risk_index
from agg_by_date