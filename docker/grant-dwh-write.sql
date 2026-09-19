-- Grants for Airflow/dbt role after restore (run as postgres).
GRANT USAGE, CREATE ON SCHEMA raw, staging, intermediate, marts TO dwh_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw, staging, intermediate, marts TO dwh_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA raw, staging, intermediate, marts TO dwh_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT ALL ON TABLES TO dwh_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT ALL ON TABLES TO dwh_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA intermediate GRANT ALL ON TABLES TO dwh_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT ALL ON TABLES TO dwh_user;

ALTER SCHEMA raw OWNER TO dwh_user;
ALTER SCHEMA staging OWNER TO dwh_user;
ALTER SCHEMA intermediate OWNER TO dwh_user;
ALTER SCHEMA marts OWNER TO dwh_user;
