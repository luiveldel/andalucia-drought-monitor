{{
    config(
        materialized='table',
        tags=['spi', 'climate', 'provisional'],
    )
}}

{#
  Provisional SPI (target window 12 months).

  Classic SPI-12 needs ~30 years of monthly precip for a Pearson-III fit.
  Local RIA series in agro_sequia are typically short (weeks–months), so we:

  1. Aggregate daily precip to monthly totals per province.
  2. Build a rolling sum over LEAST(12, available_months) — "SPI-k" with k<=12.
  3. Standardize each rolling sum as a z-score against that province's own
     distribution of rolling sums (sample mean / stddev).
  4. Flag is_provisional=true and expose calibration_months / window_months.

  When calibration_months < 24 the index is exploratory only — UI must show the caveat.
#}

with climate as (
    select
        fc.date_key,
        dd.observation_date,
        dd.calendar_year,
        dd.calendar_month,
        ds.province_name,
        fc.precipitation_mm
    from {{ ref('fact_climate_daily') }} as fc
    inner join {{ ref('dim_date') }} as dd
        on fc.date_key = dd.date_key
    inner join {{ ref('dim_stations') }} as ds
        on fc.station_key = ds.station_key
    where ds.province_name is not null
      and trim(ds.province_name) <> ''
),

monthly as (
    select
        province_name,
        calendar_year,
        calendar_month,
        make_date(calendar_year, calendar_month, 1) as month_start,
        sum(precipitation_mm)::float as precip_mm,
        count(*)::int as days_with_obs
    from climate
    group by 1, 2, 3, 4
),

province_span as (
    select
        province_name,
        count(*)::int as calibration_months,
        min(month_start) as first_month,
        max(month_start) as last_month
    from monthly
    group by 1
),

ordered as (
    select
        m.*,
        p.calibration_months,
        p.first_month,
        p.last_month,
        least(12, p.calibration_months)::int as window_months,
        row_number() over (
            partition by m.province_name
            order by m.month_start
        ) as month_seq
    from monthly as m
    inner join province_span as p
        on m.province_name = p.province_name
),

rolling as (
    select
        o.province_name,
        o.calendar_year,
        o.calendar_month,
        o.month_start,
        o.precip_mm,
        o.days_with_obs,
        o.calibration_months,
        o.window_months,
        o.first_month,
        o.last_month,
        sum(o.precip_mm) over (
            partition by o.province_name
            order by o.month_start
            rows between 11 preceding and current row
        ) as precip_roll_12_raw,
        count(*) over (
            partition by o.province_name
            order by o.month_start
            rows between 11 preceding and current row
        )::int as months_in_roll
    from ordered as o
),

eligible as (
    select
        r.*,
        case
            when r.months_in_roll >= r.window_months then r.precip_roll_12_raw
            else null
        end as precip_window_mm
    from rolling as r
    where r.months_in_roll >= greatest(1, least(r.window_months, 3))
),

stats as (
    select
        province_name,
        avg(precip_window_mm)::float as mu,
        stddev_samp(precip_window_mm)::float as sigma,
        count(*)::int as n_windows
    from eligible
    where precip_window_mm is not null
    group by 1
),

-- With only one rolling window per province, within-province sigma is 0 and SPI
-- collapses to 0. Fall back to cross-province z-score for the same month.
cross_month as (
    select
        month_start,
        avg(precip_window_mm)::float as mu_x,
        stddev_samp(precip_window_mm)::float as sigma_x,
        count(*)::int as n_x
    from eligible
    where precip_window_mm is not null
    group by 1
),

scored as (
    select
        e.province_name,
        e.calendar_year,
        e.calendar_month,
        e.month_start,
        e.precip_mm as precip_month_mm,
        e.precip_window_mm,
        e.window_months,
        e.calibration_months,
        e.months_in_roll,
        e.days_with_obs,
        e.first_month,
        e.last_month,
        s.mu as calib_mean_mm,
        s.sigma as calib_stddev_mm,
        s.n_windows as calib_n_windows,
        case
            when e.precip_window_mm is null then null
            when s.sigma is not null and s.sigma > 0
                then ((e.precip_window_mm - s.mu) / s.sigma)::float
            when x.sigma_x is not null and x.sigma_x > 0
                then ((e.precip_window_mm - x.mu_x) / x.sigma_x)::float
            else null
        end as spi_value,
        true as is_provisional,
        case
            when e.calibration_months >= 24 and e.window_months = 12 then 'spi12_short_calib'
            when e.window_months = 12 then 'spi12_provisional'
            when s.sigma is not null and s.sigma > 0 then 'spi_best_window'
            when x.sigma_x is not null and x.sigma_x > 0 then 'spi_cross_province'
            else 'spi_insufficient'
        end as method_tag
    from eligible as e
    left join stats as s
        on e.province_name = s.province_name
    left join cross_month as x
        on e.month_start = x.month_start
),

classified as (
    select
        *,
        case
            when spi_value is null then 'sin_dato'
            when spi_value <= -2.0 then 'sequia_extrema'
            when spi_value <= -1.5 then 'sequia_severa'
            when spi_value <= -1.0 then 'sequia_moderada'
            when spi_value < 1.0 then 'cerca_normal'
            when spi_value < 1.5 then 'humedo_moderado'
            when spi_value < 2.0 then 'humedo_severo'
            else 'humedo_extremo'
        end as spi_class_es
    from scored
)

select
    province_name,
    calendar_year,
    calendar_month,
    month_start,
    precip_month_mm,
    precip_window_mm,
    window_months,
    calibration_months,
    months_in_roll,
    days_with_obs,
    first_month,
    last_month,
    calib_mean_mm,
    calib_stddev_mm,
    calib_n_windows,
    round(spi_value::numeric, 3)::float as spi_value,
    is_provisional,
    method_tag,
    spi_class_es,
    current_timestamp as computed_at
from classified
