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

-- Users table (DEVHUB-005: auth scaffold)
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    name        TEXT,
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Threads table (DEVHUB-006: hexagonal skeleton)
CREATE TABLE IF NOT EXISTS threads (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL DEFAULT 'New thread',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS threads_user_id_idx ON threads(user_id);

-- Runs table (DEVHUB-008: supervisor graph)
CREATE TABLE IF NOT EXISTS runs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id   UUID NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'running',
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    error_data  JSONB
);
CREATE INDEX IF NOT EXISTS runs_thread_id_idx ON runs(thread_id);

-- HITL approvals table (DEVHUB-015: HITL interrupts)
CREATE TABLE IF NOT EXISTS hitl_approvals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    tool_call   JSONB NOT NULL,
    summary     TEXT NOT NULL,
    risk        TEXT NOT NULL DEFAULT 'medium',
    status      TEXT NOT NULL DEFAULT 'pending',
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    decision    TEXT,
    patched_args JSONB
);
CREATE INDEX IF NOT EXISTS hitl_approvals_run_id_idx ON hitl_approvals(run_id);
CREATE INDEX IF NOT EXISTS hitl_approvals_status_idx ON hitl_approvals(status);

-- Audit log table (DEVHUB-015: HITL interrupts)
CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    approval_id UUID NOT NULL REFERENCES hitl_approvals(id) ON DELETE CASCADE,
    decision    TEXT NOT NULL,
    patched_args JSONB,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS audit_log_user_id_idx ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS audit_log_approval_id_idx ON audit_log(approval_id);

-- MCP servers table (DEVHUB-024: MCP connections UI)
CREATE TABLE IF NOT EXISTS mcp_servers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_id   TEXT UNIQUE NOT NULL,
    url         TEXT NOT NULL,
    transport   TEXT NOT NULL DEFAULT 'streamable-http',
    enabled     BOOLEAN NOT NULL DEFAULT true,
    config      JSONB,
    error_code  TEXT,
    error_message TEXT,
    last_connected_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS mcp_servers_enabled_idx ON mcp_servers(enabled);
CREATE INDEX IF NOT EXISTS mcp_servers_server_id_idx ON mcp_servers(server_id);