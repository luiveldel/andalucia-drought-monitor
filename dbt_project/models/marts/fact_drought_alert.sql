{{
    config(
        materialized='view',
    )
}}
-- lógica: embalse en riesgo si fill_pct < 30% y déficit hídrico > 3mm/día durante más de 14 días consecutivos

with fact_drought_daily as (
    select * from {{ ref('fact_drought_daily') }}
)

select
    province_name,
    watershed_demarcation,
    count(*) as days_in_alert,
    min(avg_fill_pct) as min_fill_pct,
    max(daily_water_deficit_mm) as max_deficit_mm
from fact_drought_daily
where
    avg_fill_pct < 30
    and daily_water_deficit_mm > 3
    and observation_date >= current_date - interval '30 days'
group by 1, 2
having count(*) >= 14
