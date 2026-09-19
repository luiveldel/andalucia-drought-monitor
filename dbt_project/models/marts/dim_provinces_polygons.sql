{{
    config(
        materialized='table',
        tags=['gis', 'map'],
    )
}}

{#
  Province polygons for Andalusia (cod_ccaa / region_id = '01').
  dim_provinces_geo keeps centroids + area only; this mart preserves
  simplified boundaries for the decision UI map (GeoJSON via API).
#}

with staging as (
    select * from {{ ref('stg_gis_agricultural_zones') }}
),

andalucia as (
    select
        province_id,
        province_name,
        region_id,
        cartodb_id,
        geom,
        -- ~0.005° ≈ 500 m; keeps payloads small for Leaflet
        ST_SimplifyPreserveTopology(geom, 0.005) as geom_simplified
    from staging
    where region_id = '01'
       or province_id in ('04', '11', '14', '18', '21', '23', '29', '41')
       or lower(trim(province_name)) in (
            'almería', 'almeria',
            'cádiz', 'cadiz',
            'córdoba', 'cordoba',
            'granada',
            'huelva',
            'jaén', 'jaen',
            'málaga', 'malaga',
            'sevilla'
       )
)

select
    province_id,
    province_name,
    region_id,
    cartodb_id,
    ST_Y(ST_Centroid(geom))::float as latitude,
    ST_X(ST_Centroid(geom))::float as longitude,
    round((ST_Area(geom::geography) / 10000)::numeric, 1) as agricultural_area_ha,
    ST_AsGeoJSON(geom_simplified)::text as geojson,
    ST_NPoints(geom_simplified)::int as n_points,
    current_timestamp as computed_at
from andalucia
where geom is not null
