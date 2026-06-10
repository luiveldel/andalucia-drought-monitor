with int_clean_embalses as (
    select * from {{ ref('int_clean_embalses') }}
),

reservoir_catalog as (
    select * from {{ ref('int_clean_embalses_catalog') }}
),

reservoir_observations as (
    select
        reservoir_code,
        max(reservoir_capacity_hm3) as observed_capacity_hm3,
        min(observation_date) as first_observation_date,
        max(observation_date) as last_observation_date
    from int_clean_embalses
    group by 1

),

reservoir_codes as (
    select reservoir_code from reservoir_observations
    union
    select reservoir_code from reservoir_catalog
),

joined as (
    select
        codes.reservoir_code,
        cat.reservoir_name,
        cat.reservoir_type,
        cat.province_name,
        cat.exploitation_system,
        cat.watershed_demarcation,
        cat.river_name,
        cat.dam_name,
        cat.geometry_wkt,
        ro.observed_capacity_hm3 as reservoir_capacity_hm3,
        ro.first_observation_date,
        ro.last_observation_date
    from reservoir_codes as codes
        left join reservoir_catalog as cat
            on codes.reservoir_code = cat.reservoir_code
        left join reservoir_observations as ro
            on codes.reservoir_code = ro.reservoir_code
),

final as (
    select
        row_number() over (order by reservoir_code) as reservoir_key,
        reservoir_code,
        reservoir_name,
        reservoir_type,
        province_name,
        exploitation_system,
        watershed_demarcation,
        river_name,
        dam_name,
        geometry_wkt,
        reservoir_capacity_hm3,
        first_observation_date,
        last_observation_date
    from joined
)

select * from final
