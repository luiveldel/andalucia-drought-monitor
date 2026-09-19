with source as (
    select * from {{ source('raw', 'raw_siar_clima_diario') }}
)

select
    cast(fecha as date) as observation_date,
    trim(ccaa_codigo) as ccaa_code,
    trim(codigo_estacion) as station_code,
    trim(nombre_estacion) as station_name,
    trim(provincia_nombre) as province_name,
    trim(termino) as municipality,
    cast(altitud as numeric(8, 2)) as altitude_m,
    latitud_raw,
    longitud_raw,
    cast(temp_media as numeric(6, 2)) as mean_temperature_c,
    cast(temp_max as numeric(6, 2)) as max_temperature_c,
    cast(temp_min as numeric(6, 2)) as min_temperature_c,
    cast(humedad_media as numeric(6, 2)) as mean_humidity_pct,
    cast(humedad_max as numeric(6, 2)) as max_humidity_pct,
    cast(humedad_min as numeric(6, 2)) as min_humidity_pct,
    cast(precipitacion as numeric(8, 2)) as precipitation_mm,
    cast(precip_efectiva as numeric(8, 2)) as effective_precipitation_mm,
    cast(radiacion as numeric(10, 2)) as solar_radiation,
    cast(vel_viento as numeric(8, 3)) as mean_wind_speed,
    cast(vel_viento_max as numeric(8, 3)) as max_wind_speed,
    cast(dir_viento as numeric(6, 2)) as mean_wind_direction_deg,
    cast(dir_viento_vel_max as numeric(6, 2)) as max_wind_direction_deg,
    cast(et0 as numeric(8, 4)) as reference_evapotranspiration_mm,
    cast(temp_suelo_1 as numeric(6, 2)) as soil_temperature_1_c,
    cast(temp_suelo_2 as numeric(6, 2)) as soil_temperature_2_c,
    _loaded_at as loaded_at
from source
