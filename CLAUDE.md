# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a self-hosted AI development environment that combines multiple AI and low-code platforms using Docker Compose. It provides a complete local AI stack including n8n workflows, Ollama for LLMs, Open WebUI for chat interfaces, PostgreSQL with pgvector for database/RAG, and additional services like Flowise, Neo4j, Langfuse, and SearXNG.

All services run under a unified Docker Compose project named "localai" with a single PostgreSQL instance serving as the shared database for all components.

**Documentation**: For a comprehensive analysis of all services, their purposes, relationships, and architecture, see `SERVICE_ARCHITECTURE.md`.

## Development Commands

### Starting Services

The primary entry point is `start_services.py` which supports modular profiles for different service combinations:

```bash
# Core services only (databases + utilities, no Ollama)
python start_services.py

# Core + Ollama with Nvidia GPU + Open WebUI
python start_services.py --profile gpu-nvidia

# Core + Ollama with AMD GPU + Open WebUI
python start_services.py --profile gpu-amd

# Core + Ollama on CPU + Open WebUI
python start_services.py --profile cpu

# Core + Langfuse (LLM observability)
python start_services.py --profile langfuse

# Core + n8n (workflow automation)
python start_services.py --profile n8n

# Core + Flowise (no-code AI builder)
python start_services.py --profile flowise

# Combine multiple profiles
python start_services.py --profile gpu-nvidia --profile langfuse --profile n8n

# For production/public deployment
python start_services.py --profile gpu-nvidia --environment public
```

**Core services** (always running, no profile needed):
- PostgreSQL, Redis, Qdrant, Neo4j, SearXNG, Caddy

**Important**: The script automatically:
- Generates SearXNG secret keys
- Handles SearXNG's first-run `cap_drop` issue
- Starts all services with proper health checks and dependencies

### Stopping Services

```bash
# Stop all services
docker compose -p localai down

# Stop and remove all volumes (WARNING: deletes all data)
docker compose -p localai down -v
```

### Upgrading Containers

```bash
# Stop services
docker compose -p localai down

# Pull latest versions (include all profiles you use)
docker compose -p localai -f docker-compose.yml --profile langfuse pull
# Or with multiple profiles:
docker compose -p localai -f docker-compose.yml --profile gpu-nvidia --profile langfuse pull

# Restart with your profiles
python start_services.py --profile langfuse
# Or with multiple profiles:
python start_services.py --profile gpu-nvidia --profile langfuse
```

Note: The pull command with a profile pulls both core services AND that profile's services.

### Viewing Logs

```bash
# View logs for all services
docker compose -p localai logs -f

# View logs for specific service
docker logs <service-name>
docker logs -f <service-name>  # Follow mode

# Common service names: postgres, n8n, ollama, open-webui, flowise, langfuse-server
```

### Memory Optimization

By default, Docker containers have no memory limits and can consume all available system RAM. The `--memory-optimized` flag applies resource limits to reduce memory usage.

**Enable memory optimization**:
```bash
python start_services.py --profile <profile> --memory-optimized
```

**Memory limits per service** (when optimization enabled):
| Service | Memory Limit | Optimization Applied |
|---------|--------------|---------------------|
| Ollama | 8GB | Context reduced to 4096, single model loading |
| PostgreSQL | 4GB | Shared buffers and cache tuning |
| ClickHouse | 3GB | Hard memory cap |
| Neo4j | 2GB | Hard memory cap |
| Langfuse (web + worker) | 3GB total | 1.5GB each |
| SearXNG | 1GB | Workers: 4→2, Threads: 4→2 |
| Redis/Valkey | 512MB | Max memory 400MB with LRU eviction |
| Open WebUI, Qdrant | 1.5GB each | Hard memory caps (increased due to high usage) |
| n8n, Flowise | 512MB each | Hard memory caps |
| Caddy, MinIO | 256-512MB | Hard memory caps |

**Expected impact**:
- **Without optimization**: ~60-70GB RAM usage
- **With optimization**: ~30-45GB RAM usage (memory cap ~27GB)

**Monitor memory usage**:
```bash
# One-time snapshot
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Real-time monitoring
docker stats --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

**When to use**:
- Systems with 16GB-32GB RAM (highly recommended)
- Systems with 64GB+ RAM experiencing memory pressure
- Production environments where predictable resource usage is important

**Trade-offs**:
- Slightly reduced performance under heavy load
- Services may be OOM killed if limits are too restrictive
- Can increase specific service limits by editing `docker-compose.override.memory-optimized.yml`

### Accessing Services (Private/Development Mode)

When running with `--environment private` (default):
- **n8n**: http://localhost:5678
- **Open WebUI**: http://localhost:8080
- **Flowise**: http://localhost:3001
- **Langfuse**: http://localhost:3000
- **Neo4j Browser**: http://localhost:7474
- **Ollama**: http://localhost:11434
- **SearXNG**: http://localhost:8081
- **Qdrant**: http://localhost:6333
- **PostgreSQL**: localhost:5432 (user: postgres)

## Architecture

### Docker Compose Structure

The project uses a multi-file Docker Compose setup:

- **`docker-compose.yml`**: Main services definition for all services
- **`docker-compose.override.private.yml`**: Port mappings for local development (127.0.0.1 bindings)
- **`docker-compose.override.public.yml`**: Removes public port exposure for production deployments

### Service Profiles

Services use Docker Compose profiles for modular deployment:

**Core Services** (always running, no profile needed):
- `postgres` - PostgreSQL database with pgvector
- `redis` - Redis/Valkey cache and queue
- `qdrant` - Vector database
- `neo4j` - Graph database
- `searxng` - Web search engine
- `caddy` - Reverse proxy

**Ollama Profiles** (GPU selection):
- **`cpu`**: Ollama on CPU + Open WebUI
- **`gpu-nvidia`**: Ollama with NVIDIA GPU + Open WebUI
- **`gpu-amd`**: Ollama with AMD GPU (ROCm) + Open WebUI

**Optional Service Profiles**:
- **`n8n`**: n8n workflow automation
- **`flowise`**: Flowise no-code AI builder
- **`langfuse`**: Langfuse observability (includes ClickHouse + MinIO)

Each Ollama profile includes a corresponding `ollama-pull-llama-*` service that automatically downloads the default model (`qwen2.5:7b-instruct-q4_K_M`) and embedding model (`nomic-embed-text`) on first run.

**Profile Examples**:
| Command | Services Started |
|---------|------------------|
| `python start_services.py` | Core only (6 services) |
| `python start_services.py --profile gpu-nvidia` | Core + Ollama + Open WebUI |
| `python start_services.py --profile langfuse` | Core + Langfuse stack |
| `python start_services.py --profile gpu-nvidia --profile langfuse` | Core + Ollama + Langfuse |

### Key Services

**PostgreSQL**:
- Single PostgreSQL instance with pgvector extension for RAG/embeddings
- Serves all services: n8n, Flowise, Langfuse, and can host your Archon database
- Version pinned via `POSTGRES_VERSION` env var (default: pg17)
- Initialized with extensions: vector, uuid-ossp, pg_trgm
- Supports creating multiple databases on first startup via `POSTGRES_ADDITIONAL_DBS`
- Data persisted in `postgres_data` volume
- Initialization scripts in `postgres-init/` directory

**n8n Workflow Automation**:
- Uses PostgreSQL for persistence (database configurable via `N8N_DB`)
- Imports pre-configured workflows from `n8n/backup/workflows/` on startup via `n8n-import` service
- Shared folder mounted at `/data/shared` for local file access
- Runners mode enabled for enhanced workflow execution

**Ollama**:
- Configured with 8192 context length, flash attention, and Q8_0 KV cache
- Max 2 loaded models simultaneously
- Storage persisted in `ollama_storage` volume

**Langfuse**:
- Observability platform for LLM applications
- Uses shared PostgreSQL database, plus dedicated ClickHouse and MinIO services
- Worker and web services with Redis for queue management

**Neo4j**:
- Knowledge graph database for GraphRAG/LightRAG workflows
- HTTP/HTTPS browser on ports 7473/7474, Bolt protocol on 7687

**Caddy**:
- Reverse proxy for all services
- Automatic HTTPS with Let's Encrypt for production domains
- Configuration in `Caddyfile` with environment variable-based routing
- Custom configurations can be added in `caddy-addon/*.conf` (imported automatically)

### Network Architecture

All services share the default Docker Compose network and can communicate using service names (e.g., `postgres`, `ollama`, `qdrant`).

For production (`--environment public`):
- Only ports 80 and 443 are exposed
- All service access goes through Caddy reverse proxy
- Hostname environment variables control routing (e.g., `N8N_HOSTNAME`, `WEBUI_HOSTNAME`)

### Database Architecture

The PostgreSQL instance supports:
- **Multiple databases**: Create separate databases for different purposes using `POSTGRES_ADDITIONAL_DBS`
- **Service-specific databases**: Each service can use its own database (controlled by `N8N_DB`, `FLOWISE_DB`, `LANGFUSE_DB`)
- **Shared database**: All services can share the default `postgres` database if preferred
- **Direct connections**: Your Archon project can connect directly to `localhost:5432` (in private mode)

### Data Persistence

Named volumes are used for persistence:
- `postgres_data`: **All PostgreSQL databases** (n8n, Flowise, Langfuse, Archon, etc.)
- `n8n_storage`: n8n configuration and data
- `ollama_storage`: Ollama models
- `qdrant_storage`: Vector database
- `open-webui`: Open WebUI data
- `flowise_data` and `flowise_storage`: Flowise configuration
- `langfuse_clickhouse_data`, `langfuse_minio_data`: Langfuse analytics and storage

Local directories mapped:
- `./postgres-init`: Database initialization scripts (run only on first startup)
- `./n8n/backup`: Credentials and workflows for import
- `./shared`: Accessible in n8n at `/data/shared`
- `./neo4j/`: Neo4j data, logs, config, plugins
- `./searxng`: SearXNG configuration

### Backup and Restore

Use the provided scripts to backup and restore PostgreSQL:

**Linux/Mac**:
```bash
# Create backup (saved to ./backups/postgres/)
./backup-postgres.sh

# Restore from backup
./restore-postgres.sh ./backups/postgres/full_backup_YYYYMMDD_HHMMSS.sql.gz
```

**Windows (PowerShell)**:
```powershell
# Create backup
.\backup-postgres.ps1

# Restore (use the Linux script with Git Bash or WSL)
```

**Manual backup**:
```bash
# Backup all databases
docker exec postgres pg_dumpall -U postgres > backup.sql

# Backup specific database
docker exec postgres pg_dump -U postgres -d database_name > database_backup.sql

# Restore
cat backup.sql | docker exec -i postgres psql -U postgres
```

### Environment Configuration

Configuration is managed through `.env` file (copy from `.env.example`). Critical variables:

**Required**:
- `N8N_ENCRYPTION_KEY`, `N8N_USER_MANAGEMENT_JWT_SECRET`: Generate with `openssl rand -hex 32`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`: PostgreSQL credentials
- `POSTGRES_DB`: Main database name (default: postgres)
- `NEO4J_AUTH`: Format `username/password`
- `CLICKHOUSE_PASSWORD`, `MINIO_ROOT_PASSWORD`, `LANGFUSE_SALT`, `NEXTAUTH_SECRET`, `ENCRYPTION_KEY`: Langfuse secrets

**Optional Database Configuration**:
- `POSTGRES_ADDITIONAL_DBS`: Comma-separated list of databases to create (e.g., `n8n_db,flowise_db,archon_db`)
- `N8N_DB`, `FLOWISE_DB`, `LANGFUSE_DB`: Specify which database each service uses
- `POSTGRES_VERSION`: PostgreSQL version (format: `pg17`, `pg16`, etc.)

**Production Only**:
- Hostname variables for Caddy routing (e.g., `N8N_HOSTNAME=n8n.yourdomain.com`)
- `LETSENCRYPT_EMAIL`: Email for Let's Encrypt certificates

**Database Connections**:
- **Inside Docker network**: Host is `postgres` (service name)
- **From host machine**: `localhost:5432` (in private mode)
- **Connection string example**: `postgresql://postgres:password@postgres:5432/database_name`

### n8n Integration

Pre-configured workflows demonstrate:
- **V1**: Basic RAG with Qdrant vector store
- **V2**: RAG using Supabase pgvector
- **V3**: Agentic RAG with tool usage

Credentials setup in n8n:
- **Ollama**: `http://ollama:11434`
- **PostgreSQL**: Host is `postgres`, use credentials from `.env`
- **Qdrant**: `http://qdrant:6333`

For Mac users running Ollama locally, update n8n credentials to use `http://host.docker.internal:11434` and set `OLLAMA_HOST=host.docker.internal:11434` in docker-compose environment.

### Open WebUI Integration

The `n8n_pipe.py` file contains an Open WebUI pipe/function that connects Open WebUI to n8n workflows:
- Install as a function in Open WebUI (Workspace -> Functions)
- Configure with n8n webhook production URL
- Enables chat interface to n8n AI agents with session management

## Important Notes

### PostgreSQL Initialization
On first startup, PostgreSQL will:
1. Run initialization scripts from `postgres-init/` directory
2. Install extensions: pgvector, uuid-ossp, pg_trgm
3. Create additional databases specified in `POSTGRES_ADDITIONAL_DBS`
These scripts run only once when the database is first created.

### SearXNG First Run
SearXNG requires special handling on first run - the script automatically comments out `cap_drop: - ALL` until `uwsgi.ini` is generated, then re-enables it for security.

### PostgreSQL Version
PostgreSQL version is controlled by `POSTGRES_VERSION` env var (default: `pg17`). The pgvector image is used for built-in vector support.

### Creating Multiple Databases
To create separate databases for each service:
1. Set in `.env`: `POSTGRES_ADDITIONAL_DBS=n8n_db,flowise_db,langfuse_db,archon_db`
2. Optionally specify which database each service uses:
   ```
   N8N_DB=n8n_db
   FLOWISE_DB=flowise_db
   LANGFUSE_DB=langfuse_db
   ```
3. For Archon, connect to `localhost:5432` with database `archon_db`

### Known Issues
- **Docker Desktop users**: Enable "Expose daemon on tcp://localhost:2375 without TLS" in Docker Desktop settings
- **SearXNG restart loop**: Run `chmod 755 searxng` from project root (Linux/Mac only)
- **PostgreSQL initialization fails**: Delete the volume and restart:
  ```bash
  docker compose -p localai down
  docker volume rm localai_postgres_data
  python start_services.py --profile <profile>
  ```
- **start_services.py fails on first run**: If the script fails with "shutil not found", this is a known issue. The script works correctly on subsequent runs
- **High memory usage / System slowdown**: If experiencing excessive RAM usage (70%+ on systems with 32GB or less), use the `--memory-optimized` flag to apply resource limits
- **Container OOM killed**: If a service is killed due to out-of-memory, check Docker logs and either:
  1. Increase the memory limit for that specific service in `docker-compose.override.memory-optimized.yml`
  2. Run without `--memory-optimized` if you have sufficient RAM (64GB+)
  3. Close other applications to free up memory

### Connecting External Applications (Archon)
Your Archon project can connect to PostgreSQL:
- **Host**: `localhost` (from host machine) or `postgres` (from Docker)
- **Port**: `5432`
- **User**: Value of `POSTGRES_USER` from `.env`
- **Password**: Value of `POSTGRES_PASSWORD` from `.env`
- **Database**: Either `postgres` (default) or a specific DB from `POSTGRES_ADDITIONAL_DBS`

### File Paths in n8n
When using file-related nodes in n8n (Read/Write Files, Local File Trigger, Execute Command), use `/data/shared` as the base path. This maps to `./shared` in the project directory.

### Security
- Never commit `.env` file (already in `.gitignore`)
- Generate secure random values for all secrets before production deployment
- In public mode, ensure firewall only allows ports 80 and 443
- Note: ufw does not shield Docker-published ports; traffic must flow through Caddy

### GPU Support
- **Windows**: Requires WSL 2 backend in Docker Desktop
- **Linux (NVIDIA)**: Follow Ollama Docker GPU setup instructions
- **Linux (AMD)**: ROCm support via `gpu-amd` profile
- **Mac**: Cannot expose GPU to Docker; run Ollama natively with `--profile none`

### Platform-Specific Notes

**Windows**:
- Use Git Bash or PowerShell for running scripts
- Paths use backslashes but Docker requires forward slashes in volume mounts
- The `start_services.py` script handles SearXNG secret generation via PowerShell automatically

**Linux/Mac**:
- File permissions matter: ensure `searxng` directory has `755` permissions
- Use `chmod +x` to make shell scripts executable before running them
- The `start_services.py` script uses `sed` and `openssl` for SearXNG setup
