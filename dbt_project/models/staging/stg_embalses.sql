with source as (
    select * from {{ source('raw', 'raw_embalses_diarios') }}
)

select
    cast(fecha as date) as observation_date,
    trim(cod_est) as reservoir_code,
    cast(reserva_hm3 as numeric(12, 2)) as stored_volume_hm3,
    cast(capacidad_hm3 as numeric(12, 2)) as reservoir_capacity_hm3,
    cast(porcentaje_llenado as numeric(5, 2)) as fill_percentage,
    _loaded_at as loaded_at
from source
