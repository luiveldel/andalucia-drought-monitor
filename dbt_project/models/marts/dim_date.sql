with int_clean_embalses as (
    select observation_date from {{ ref('int_clean_embalses') }}
),

int_clean_ria as (
    select observation_date from {{ ref('int_clean_ria') }}
),

observation_dates as (
    select observation_date
    from int_clean_embalses
    union
    select observation_date
    from int_clean_ria
),

enriched as (
    select
        cast(to_char(observation_date, 'YYYYMMDD') as integer) as date_key,
        observation_date,
        extract(year from observation_date)::integer as calendar_year,
        extract(month from observation_date)::integer as calendar_month,
        extract(day from observation_date)::integer as calendar_day,
        extract(dow from observation_date)::integer as day_of_week,
        to_char(observation_date, 'TMMonth') as month_name,
        to_char(observation_date, 'TMDay') as day_name,
        extract(quarter from observation_date)::integer as calendar_quarter,
        case
            when extract(month from observation_date) between 10 and 12
                then extract(year from observation_date) + 1
            else extract(year from observation_date)
        end::integer as hydrological_year
    from observation_dates
)

select * from enriched
