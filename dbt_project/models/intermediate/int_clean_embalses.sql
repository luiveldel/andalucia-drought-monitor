with stg_embalses as (
    select * from {{ ref('stg_embalses') }}
),

cleaned as (
    select * from stg_embalses
    where observation_date is not null
        and reservoir_code is not null
        and trim(reservoir_code) <> ''
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by observation_date, reservoir_code
            order by loaded_at desc
        ) as row_num
    from cleaned
)

select
    observation_date,
    reservoir_code,
    stored_volume_hm3,
    reservoir_capacity_hm3,
    fill_percentage,
    loaded_at
from deduplicated
where row_num = 1
