-- Grain: one row per province per day
select
    date_key,
    province_name,
    count(*) as n
from {{ ref('fact_drought_daily') }}
group by 1, 2
having count(*) > 1
