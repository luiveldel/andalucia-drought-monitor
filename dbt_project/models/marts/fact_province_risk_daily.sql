{{
  config(
    materialized='view',
    schema='marts',
  )
}}
-- Vista ligera de riesgo provincial diario (heurística operativa, no SPI-12).
-- El dashboard puede calcular lo mismo en Python; esta vista facilita BI/SQL ad-hoc.

with base as (
  select
    observation_date,
    province_name,
    watershed_demarcation,
    avg_fill_pct,
    total_stored_hm3,
    avg_precipitation_mm,
    daily_water_deficit_mm,
    hydric_stress_index,
    -- 0–100: mayor = peor
    round((
      0.50 * greatest(0, least(100, 100 - coalesce(avg_fill_pct, 0)))
      + 0.35 * greatest(0, least(100, coalesce(daily_water_deficit_mm, 0) * 12))
      + 0.15 * greatest(0, least(100, abs(coalesce(hydric_stress_index, 0)) * 25))
    )::numeric, 1) as risk_score
  from {{ ref('fact_drought_daily') }}
)

select
  observation_date,
  province_name,
  watershed_demarcation,
  avg_fill_pct,
  total_stored_hm3,
  avg_precipitation_mm,
  daily_water_deficit_mm,
  hydric_stress_index,
  risk_score,
  case
    when avg_fill_pct < 30 or daily_water_deficit_mm > 4.5 then 'crítica'
    when avg_fill_pct < 50 or daily_water_deficit_mm > 3 then 'alta'
    when avg_fill_pct < 70 or daily_water_deficit_mm > 1 then 'media'
    else 'baja'
  end as severity
from base
