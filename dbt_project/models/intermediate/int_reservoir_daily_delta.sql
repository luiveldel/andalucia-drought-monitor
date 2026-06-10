{{
    config(
        materialized='view',
    )
}}

-- delta diario de volumen por embalse
with int_clean_embalses as (
    select * from {{ ref('int_clean_embalses') }}
),

base as (
    select
        observation_date,
        reservoir_id,
        stored_volume_hm3,
        lag(stored_volume_hm3) over (
            partition by reservoir_id
            order by observation_date
        ) as prev_stored_volume_hm3
    from int_clean_embalses
),

final as (
    select
    observation_date,
    reservoir_id,
    stored_volume_hm3,
    prev_stored_volume_hm3,
    -- positivo = llenando, negativo = vaciando
    stored_volume_hm3 - prev_stored_volume_hm3 as daily_volume_delta_hm3,
    -- tasa de cambio porcentual respecto a la capacidad observada
    (stored_volume_hm3 - prev_stored_volume_hm3)
        / nullif(prev_stored_volume_hm3, 0) * 100 as daily_fill_rate_pct
    from base
)

select
    observation_date,
    reservoir_id,
    stored_volume_hm3,
    prev_stored_volume_hm3,
    daily_volume_delta_hm3,
    daily_fill_rate_pct
from final