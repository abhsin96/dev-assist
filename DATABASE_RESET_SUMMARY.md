# Database Reset Summary

## Issue
The DevHub API was failing with the following error:
```
ProgrammingError: relation "hitl_approvals" does not exist
```

This occurred because the database was created before the HITL interrupts feature was implemented, so the `hitl_approvals` and `audit_log` tables were missing.

## Solution
Recreated the PostgreSQL database with the updated schema by:

1. **Stopped and removed existing containers and volumes:**
   ```bash
   docker compose -f infra/docker/docker-compose.yml down -v
   ```

2. **Started fresh containers:**
   ```bash
   docker compose -f infra/docker/docker-compose.yml up -d
   ```

3. **Verified table creation:**
   The `init.sql` script automatically created all required tables:
   - `users`
   - `threads`
   - `runs`
   - `hitl_approvals` ✅
   - `audit_log` ✅

## Database Schema Verification

### Tables Created
```
 Schema |      Name      | Type  |  Owner   
--------+----------------+-------+----------
 public | audit_log      | table | postgres
 public | hitl_approvals | table | postgres
 public | runs           | table | postgres
 public | threads        | table | postgres
 public | users          | table | postgres
```

### HITL Approvals Table Schema
```
    Column    |           Type           | Nullable |      Default      
--------------+--------------------------+----------+-------------------
 id           | uuid                     | not null | gen_random_uuid()
 run_id       | uuid                     | not null | 
 tool_call    | jsonb                    | not null | 
 summary      | text                     | not null | 
 risk         | text                     | not null | 'medium'::text
 status       | text                     | not null | 'pending'::text
 expires_at   | timestamp with time zone | not null | 
 created_at   | timestamp with time zone | not null | now()
 resolved_at  | timestamp with time zone |          | 
 decision     | text                     |          | 
 patched_args | jsonb                    |          | 
```

### Indexes
- Primary key on `id`
- Index on `run_id` for foreign key lookups
- Index on `status` for filtering pending approvals

### Foreign Keys
- `run_id` references `runs(id)` with CASCADE delete
- Referenced by `audit_log.approval_id`

## Next Steps
The database is now ready. You can start the DevHub API server:

```bash
cd apps/api
uv run fastapi dev src/devhub/main.py
```

The HITL interrupts feature should now work correctly with:
- Approval creation and storage
- Background task for expiring pending approvals
- Audit logging for approval decisions
