{{
    config(
        materialized='table',
    )
}}

-- ¿es este año hidrológico más seco o más húmedo que el anterior?

with fact_drought_daily as (
    select * from {{ ref('fact_drought_daily') }}
),

dim_date as (
    select * from {{ ref('dim_date') }}
),

by_hydro_year as (
    select
        dd.hydrological_year,
        f.province_name,
        f.watershed_demarcation,
        avg(f.avg_fill_pct) as avg_fill_pct,
        sum(f.avg_precipitation_mm) as total_precipitation_mm,
        sum(f.daily_water_deficit_mm) as total_water_deficit_mm,
        avg(f.avg_et0_mm) as avg_et0_mm,
        avg(f.avg_temp_c) as avg_temp_c,
        count(distinct f.date_key) as days_with_data
    from fact_drought_daily as f
        inner join dim_date as dd
            on f.date_key = dd.date_key
    group by 1, 2, 3
),

agg_by_year as (
    select
        *,
        avg_fill_pct - lag(avg_fill_pct) over (
            partition by province_name
            order by hydrological_year
        ) as fill_pct_yoy_delta,
        total_precipitation_mm - lag(total_precipitation_mm) over (
            partition by province_name
            order by hydrological_year
        ) as precipitation_yoy_delta_mm
    from by_hydro_year
)

select
    hydrological_year,
    province_name,
    watershed_demarcation,
    avg_fill_pct,
    total_precipitation_mm,
    total_water_deficit_mm,
    avg_et0_mm,
    avg_temp_c,
    days_with_data,
    fill_pct_yoy_delta,
    precipitation_yoy_delta_mm
from agg_by_year
