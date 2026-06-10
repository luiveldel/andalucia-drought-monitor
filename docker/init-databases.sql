-- Inicialización de usuarios y bases de datos para la plataforma de datos

CREATE USER dwh_user WITH PASSWORD 'dwh_password';
CREATE DATABASE agro_sequia OWNER dwh_user;

CREATE USER airflow WITH PASSWORD 'airflow';
CREATE DATABASE airflow OWNER airflow;

CREATE USER metabase WITH PASSWORD 'metabase';
CREATE DATABASE metabase OWNER metabase;

-- Esquemas Medallion en el Data Warehouse
\c agro_sequia
-- PostGIS ships with postgis/postgis image; must be enabled per database
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS raw AUTHORIZATION dwh_user;
CREATE SCHEMA IF NOT EXISTS staging AUTHORIZATION dwh_user;
CREATE SCHEMA IF NOT EXISTS intermediate AUTHORIZATION dwh_user;
CREATE SCHEMA IF NOT EXISTS marts AUTHORIZATION dwh_user;

GRANT ALL PRIVILEGES ON SCHEMA raw TO dwh_user;
GRANT ALL PRIVILEGES ON SCHEMA staging TO dwh_user;
GRANT ALL PRIVILEGES ON SCHEMA intermediate TO dwh_user;
GRANT ALL PRIVILEGES ON SCHEMA marts TO dwh_user;
