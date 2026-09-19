{{
    config(
        materialized='incremental',
        unique_key=['date_key', 'province_name'],
        on_schema_change='sync_all_columns',
    )
}}

{#
  Grain: one row per province per day.
  Reservoirs in the same province can span several watershed_demarcation values;
  we roll them up here (capacity-weighted fill, summed volumes).
#}

with fact_reservoir_daily as (
    select * from {{ ref('fact_reservoir_daily') }}
    {% if is_incremental() %}
        where date_key >= (select coalesce(max(date_key), 0) from {{ this }})
    {% endif %}
),

fact_climate_daily as (
    select * from {{ ref('fact_climate_daily') }}
    {% if is_incremental() %}
        where date_key >= (select coalesce(max(date_key), 0) from {{ this }})
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
    where dr.province_name is not null
      and trim(dr.province_name) <> ''
    group by 1, 2
),

reservoir_agg as (
    select
        fr.date_key,
        dr.province_name,
        -- capacity-weighted mean fill across all basins in the province
        case
            when sum(dr.reservoir_capacity_hm3) > 0
                then 100.0 * sum(fr.stored_volume_hm3) / sum(dr.reservoir_capacity_hm3)
            else avg(fr.fill_percentage)
        end as avg_fill_pct,
        sum(fr.stored_volume_hm3) as total_stored_hm3,
        sum(dr.reservoir_capacity_hm3) as total_capacity_hm3,
        -- primary basin by capacity (for display / debugging, not part of grain)
        (
            array_agg(dr.watershed_demarcation order by dr.reservoir_capacity_hm3 desc nulls last)
        )[1] as primary_watershed_demarcation
    from fact_reservoir_daily as fr
        inner join dim_reservoirs as dr
            on fr.reservoir_key = dr.reservoir_key
    where dr.province_name is not null
      and trim(dr.province_name) <> ''
    group by 1, 2
),

climate_agg as (
    select
        fc.date_key,
        ds.province_name,
        avg(fc.precipitation_mm) as avg_precipitation_mm,
        avg(fc.reference_evapotranspiration_mm) as avg_et0_mm,
        avg(fc.mean_temperature_c) as avg_temp_c,
        avg(fc.reference_evapotranspiration_mm - fc.precipitation_mm) as daily_water_deficit_mm,
        max(dp.avg_volume_delta_hm3) as avg_volume_delta_hm3
    from fact_climate_daily as fc
        left join dim_stations as ds
            on fc.station_key = ds.station_key
        left join delta_province_agg as dp
            on fc.date_key = dp.date_key
            and ds.province_name = dp.province_name
    where ds.province_name is not null
      and trim(ds.province_name) <> ''
    group by 1, 2
),

joined as (
    select
        r.date_key,
        dd.observation_date,
        dd.hydrological_year,
        r.province_name,
        r.primary_watershed_demarcation as watershed_demarcation,
        round(r.avg_fill_pct::numeric, 2) as avg_fill_pct,
        round(r.total_stored_hm3::numeric, 2) as total_stored_hm3,
        round(r.total_capacity_hm3::numeric, 2) as total_capacity_hm3,
        round(c.avg_precipitation_mm::numeric, 3) as avg_precipitation_mm,
        round(c.avg_et0_mm::numeric, 3) as avg_et0_mm,
        round(c.avg_temp_c::numeric, 2) as avg_temp_c,
        round(c.daily_water_deficit_mm::numeric, 3) as daily_water_deficit_mm,
        round(coalesce(c.avg_volume_delta_hm3, dlt.avg_volume_delta_hm3)::numeric, 4) as avg_volume_delta_hm3,
        round(
            (
                coalesce(c.avg_volume_delta_hm3, dlt.avg_volume_delta_hm3)
                / nullif(c.avg_precipitation_mm, 0)
            )::numeric,
            6
        ) as implicit_runoff_coeff,
        round(
            (r.avg_fill_pct / nullif(c.avg_et0_mm, 0))::numeric,
            4
        ) as hydric_stress_index
    from reservoir_agg as r
        left join climate_agg as c
            on r.date_key = c.date_key
            and r.province_name = c.province_name
        left join delta_province_agg as dlt
            on r.date_key = dlt.date_key
            and r.province_name = dlt.province_name
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
