{{
    config(
        materialized='incremental',
        unique_key=['date_key', 'reservoir_key'],
        on_schema_change='append_new_columns',
    )
}}

with int_clean_embalses as (
    select * from {{ ref('int_clean_embalses') }}
),

dim_date as (
    select * from {{ ref('dim_date') }}
),

dim_reservoirs as (
    select * from {{ ref('dim_reservoirs') }}
),

joined as (
    select
        d.date_key,
        r.reservoir_key,
        s.observation_date,
        s.stored_volume_hm3,
        s.reservoir_capacity_hm3,
        s.fill_percentage,
        s.loaded_at
    from int_clean_embalses as s
        inner join dim_date as d
            on s.observation_date = d.observation_date
        inner join dim_reservoirs as r
            on s.reservoir_code = r.reservoir_code
    {% if is_incremental() %}
        where d.date_key > (
            select coalesce(max(prev.date_key), 0)
            from {{ this }} as prev
        )
    {% endif %}
)

select
    date_key,
    reservoir_key,
    observation_date,
    stored_volume_hm3,
    reservoir_capacity_hm3,
    fill_percentage,
    loaded_at
from joined
