-- Create the application role (non-superuser)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'devhub_app') THEN
    CREATE ROLE devhub_app WITH LOGIN PASSWORD 'devhub_app_password';
  END IF;
END
$$;

-- Create the devhub database owned by the app role
SELECT 'CREATE DATABASE devhub OWNER devhub_app'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'devhub') \gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE devhub TO devhub_app;

-- Connect to the devhub database and set up schema permissions
\c devhub
GRANT ALL ON SCHEMA public TO devhub_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO devhub_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO devhub_app;
