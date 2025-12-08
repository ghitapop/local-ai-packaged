# Migration Guide: Supabase to PostgreSQL

This guide helps you migrate from the Supabase-based setup to the simplified PostgreSQL-only architecture.

## What Changed

**Removed**:
- Supabase stack (Kong, GoTrue, PostgREST, Supabase Studio, etc.)
- Automatic Supabase repository cloning
- Complex authentication and API layer

**Added**:
- Single PostgreSQL instance with pgvector
- Support for multiple databases within one PostgreSQL instance
- Simplified backup/restore scripts
- Direct database access for all services

## Migration Steps

### 1. Backup Your Existing Data

**CRITICAL**: Before proceeding, backup your existing Supabase database!

```bash
# If Supabase is still running, backup from the 'db' container
docker exec db pg_dumpall -U postgres > supabase_backup_$(date +%Y%m%d).sql

# Or backup specific databases
docker exec db pg_dump -U postgres -d postgres > postgres_db_backup.sql
```

### 2. Stop All Services

```bash
# Stop with your current profile
docker compose -p localai -f docker-compose.yml --profile <your-profile> down
```

### 3. Update Configuration Files

**Update .env file**:

```bash
# Copy the new example
cp .env.example .env.new

# Edit .env.new and set:
# - POSTGRES_USER (keep same as before)
# - POSTGRES_PASSWORD (keep same as before)
# - POSTGRES_DB=postgres (or your preferred main database name)

# Optional: Create separate databases
# POSTGRES_ADDITIONAL_DBS=n8n_db,flowise_db,langfuse_db,archon_db
# N8N_DB=n8n_db
# FLOWISE_DB=flowise_db
# LANGFUSE_DB=langfuse_db

# Copy other required secrets from old .env:
# - N8N_ENCRYPTION_KEY
# - N8N_USER_MANAGEMENT_JWT_SECRET
# - NEO4J_AUTH
# - CLICKHOUSE_PASSWORD
# - MINIO_ROOT_PASSWORD
# - LANGFUSE_SALT
# - NEXTAUTH_SECRET
# - ENCRYPTION_KEY

# Replace old .env
mv .env .env.old
mv .env.new .env
```

### 4. Remove Supabase Data (Optional)

If you're sure you have backups and don't need Supabase anymore:

```bash
# Remove the cloned Supabase repository
rm -rf supabase/

# Remove Supabase Docker volumes
docker volume rm localai_db-data 2>/dev/null || true
docker volume rm localai_analytics-data 2>/dev/null || true
```

### 5. Start New Stack

```bash
# Start services with your GPU profile
python start_services.py --profile <your-profile>
```

Wait for PostgreSQL to initialize (watch the logs):
```bash
docker logs -f postgres
```

### 6. Restore Your Data

**Option A: Restore all databases**:
```bash
# Restore from your backup
cat supabase_backup_YYYYMMDD.sql | docker exec -i postgres psql -U postgres
```

**Option B: Restore specific databases**:
```bash
# If you created separate databases, restore to each
cat postgres_db_backup.sql | docker exec -i postgres psql -U postgres -d postgres
```

### 7. Verify Services

Check that all services are running:
```bash
docker compose -p localai ps
```

Access services:
- n8n: http://localhost:5678
- Open WebUI: http://localhost:8080
- Flowise: http://localhost:3001
- PostgreSQL: localhost:5432

### 8. Update Archon Project Connection

Update your Archon project database configuration:

**Old (Supabase API)**:
```
URL: http://localhost:8000
API Key: <anon_key or service_role_key>
```

**New (Direct PostgreSQL)**:
```
Host: localhost
Port: 5432
User: postgres (or from POSTGRES_USER)
Password: <from POSTGRES_PASSWORD>
Database: archon_db (or whatever you named it)
```

### 9. Test Everything

- [ ] n8n workflows execute successfully
- [ ] Flowise flows work
- [ ] Open WebUI can chat
- [ ] Archon project connects to database
- [ ] All data is present

### 10. Set Up Regular Backups

```bash
# Make backup script executable
chmod +x backup-postgres.sh

# Test backup
./backup-postgres.sh

# Set up cron job (Linux/Mac)
crontab -e
# Add: 0 2 * * * /path/to/local-ai-packaged/backup-postgres.sh

# Or Windows Task Scheduler (run backup-postgres.ps1 daily)
```

## Troubleshooting

### PostgreSQL won't start
```bash
# Check logs
docker logs postgres

# If initialization failed, delete volume and try again
docker volume rm localai_postgres_data
python start_services.py --profile <your-profile>
```

### Can't connect from Archon
```bash
# Verify PostgreSQL is exposed on host
docker compose -p localai ps postgres

# Should show: 127.0.0.1:5432->5432/tcp

# Test connection
psql -h localhost -p 5432 -U postgres -d postgres
```

### n8n can't connect to database
```bash
# Check n8n environment variables
docker inspect n8n | grep POSTGRES

# Should show:
# DB_POSTGRESDB_HOST=postgres
# DB_POSTGRESDB_USER=postgres

# Check n8n logs
docker logs n8n
```

### Data is missing after restore
```bash
# List databases
docker exec postgres psql -U postgres -c "\l"

# Check if data exists
docker exec postgres psql -U postgres -d <database_name> -c "\dt"

# Re-run restore if needed
```

## Rollback Plan

If you need to go back to Supabase:

1. Stop new stack: `docker compose -p localai down`
2. Restore old files from your backup
3. Restore `.env.old` to `.env`
4. Use git to restore old `docker-compose.yml` and `start_services.py`
5. Start old stack

## Benefits of New Setup

✅ **Simpler**: One database service instead of 10+ Supabase services
✅ **Faster**: No Kong proxy overhead
✅ **More Reliable**: Fewer dependencies, fewer failure points
✅ **Easier Backups**: Standard PostgreSQL tools
✅ **Better for Development**: Direct database access
✅ **Multiple Databases**: Easy to create isolated databases per project

## Questions?

If you encounter issues, check:
1. Docker logs: `docker logs <service_name>`
2. Database logs: `docker logs postgres`
3. CLAUDE.md for architecture details
4. This project's GitHub issues
