-- Run after pg_restore so dashboard-api (dwh_user) can read marts.
GRANT USAGE ON SCHEMA marts, staging, raw, intermediate TO dwh_user;
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO dwh_user;
GRANT SELECT ON ALL TABLES IN SCHEMA staging TO dwh_user;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO dwh_user;
GRANT SELECT ON ALL TABLES IN SCHEMA intermediate TO dwh_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA marts TO dwh_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO dwh_user;
