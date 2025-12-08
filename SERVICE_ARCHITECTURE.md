# Service Architecture & Analysis

This document provides a comprehensive overview of all services in the Local AI Packaged stack, their purposes, relationships, and use cases.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Service Catalog](#service-catalog)
- [Service Dependencies](#service-dependencies)
- [Resource Usage](#resource-usage)
- [Use Cases](#use-cases)

---

## Architecture Overview

The Local AI Packaged stack is a complete self-hosted AI development environment organized into four layers:

### Layer 1: Infrastructure Services
Core services providing databases, caching, storage, and networking.

### Layer 2: AI Core
LLM inference engine and model management.

### Layer 3: AI Applications
User-facing interfaces and workflow automation tools.

### Layer 4: Data & Search
Vector databases, graph databases, and search engines for RAG and knowledge management.

### Layer 5: Observability
Production monitoring and tracing for LLM applications.

---

## Service Catalog

### Infrastructure Services

#### PostgreSQL (`postgres`)
**Image**: `pgvector/pgvector:pg17`
**Purpose**: Shared relational database with pgvector extension for vector operations
**Port**: 5432 (internal)
**Storage**: `postgres_data` volume

**Used By**:
- n8n (workflow metadata, credentials)
- Flowise (flow definitions, chatflows)
- Langfuse (traces, observations, metrics)

**Features**:
- pgvector extension for embedding storage
- Supports multiple databases via `POSTGRES_ADDITIONAL_DBS`
- Initialization scripts in `postgres-init/` directory
- Version controlled via `POSTGRES_VERSION` environment variable

**Configuration**:
- Health checks every 5s
- Automatic database creation for n8n, Flowise, Langfuse
- Extensions: vector, uuid-ossp, pg_trgm

---

#### Redis/Valkey (`redis`)
**Image**: `valkey/valkey:8-alpine`
**Purpose**: In-memory cache and queue system
**Port**: 6379 (internal)
**Storage**: `valkey-data` volume

**Used By**:
- Langfuse (job queues, worker coordination)
- SearXNG (search result caching)

**Features**:
- Persistence enabled (save every 30 seconds with 1+ change)
- Memory policy: `noeviction` (required for Langfuse queues)
- No authentication by default (internal only)

**Memory Optimization**:
- With optimization: 512MB limit, 400MB maxmemory
- Without optimization: No limit

---

#### ClickHouse (`clickhouse`)
**Image**: `clickhouse/clickhouse-server`
**Purpose**: OLAP database for analytics and time-series data
**Ports**: 8123 (HTTP), 9000 (native protocol)
**Storage**: `langfuse_clickhouse_data`, `langfuse_clickhouse_logs`

**Used By**:
- Langfuse only (trace analytics, aggregations, dashboards)

**Features**:
- Columnar storage for fast analytical queries
- Handles high-volume ingestion from Langfuse worker
- Health checks via HTTP ping endpoint

**Memory Optimization**:
- With optimization: 3GB limit
- Without optimization: No limit

---

#### MinIO (`minio`)
**Image**: `minio/minio`
**Purpose**: S3-compatible object storage
**Ports**: 9000 (API), 9001 (console)
**Storage**: `langfuse_minio_data` volume

**Used By**:
- Langfuse only (event uploads, media storage, batch exports)

**Features**:
- S3-compatible API
- Auto-creates 'langfuse' bucket on startup
- Web console on port 9001

**Memory Optimization**:
- With optimization: 512MB limit
- Without optimization: No limit

---

#### Caddy (`caddy`)
**Image**: `caddy:2-alpine`
**Purpose**: Reverse proxy with automatic HTTPS
**Ports**: 80 (HTTP), 443 (HTTPS)
**Storage**: `caddy-data`, `caddy-config` volumes

**Routes**:
- n8n → Port 8001 or custom domain
- Open WebUI → Port 8002 or custom domain
- Flowise → Port 8003 or custom domain
- Ollama → Port 8004 or custom domain
- SearXNG → Port 8006 or custom domain
- Langfuse → Port 8007 or custom domain
- Neo4j Browser → Port 8008 or custom domain

**Features**:
- Automatic HTTPS with Let's Encrypt (production mode)
- Configuration in `Caddyfile`
- Custom configurations via `caddy-addon/*.conf`
- Environment variable-based routing

**Configuration Modes**:
- **Private** (default): Binds to localhost, ports 8001-8008
- **Public**: Routes via domain names, ports 80/443 only

---

### AI Core Services

#### Ollama (`ollama-cpu`, `ollama-gpu`, `ollama-gpu-amd`)
**Image**: `ollama/ollama:latest` (or `:rocm` for AMD)
**Purpose**: Local LLM inference engine
**Port**: 11434 (internal)
**Storage**: `ollama_storage` volume

**Profiles**:
- `cpu`: CPU-only inference
- `gpu-nvidia`: NVIDIA GPU acceleration
- `gpu-amd`: AMD ROCm GPU acceleration
- `none`: For Mac users running Ollama natively

**Configuration**:
- Context length: 8192 tokens
- Flash attention enabled
- KV cache: Q8_0 quantization
- Max loaded models: 2 simultaneously

**Used By**:
- Open WebUI (chat interface)
- n8n (workflow LLM nodes)
- Flowise (chatflows, agents)

**Memory Optimization**:
- With optimization: 8GB limit, 4096 context
- Without optimization: No limit, 8192 context

---

#### Ollama Model Pullers (`ollama-pull-llama-*`)
**Purpose**: Init containers to download models on first startup
**Models Downloaded**:
- `qwen2.5:7b-instruct-q4_K_M` (7B parameter chat model)
- `nomic-embed-text` (embedding model for RAG)

**Behavior**:
- Runs once after Ollama starts
- Exits after models are downloaded
- Shares storage with main Ollama container

---

### AI Application Services

#### Open WebUI (`open-webui`)
**Image**: `ghcr.io/open-webui/open-webui:main`
**Purpose**: ChatGPT-like web interface for LLMs
**Port**: 8080 (internal)
**Storage**: `open-webui` volume

**Features**:
- Multi-user with authentication
- Model management and switching
- Conversation history
- Function/Tool calling support
- Custom prompts and templates
- Document upload for RAG
- Integration with n8n via pipes (see `n8n_pipe.py`)

**Memory Optimization**:
- With optimization: 1.5GB limit (increased due to usage)
- Without optimization: No limit

---

#### n8n (`n8n`)
**Image**: `n8nio/n8n:latest`
**Purpose**: Workflow automation with AI integration
**Port**: 5678 (internal)
**Storage**: `n8n_storage` volume

**Features**:
- Visual workflow builder
- 400+ pre-built integrations
- AI agent orchestration
- RAG workflow support
- PostgreSQL persistence
- Runners mode for enhanced execution
- Shared folder at `/data/shared` (maps to `./shared`)

**Pre-configured Workflows**:
- V1: Basic RAG with Qdrant vector store
- V2: RAG using PostgreSQL pgvector (Supabase pattern)
- V3: Agentic RAG with tool usage

**Used With**:
- Ollama (LLM inference)
- Qdrant/PostgreSQL (vector storage)
- SearXNG (web search)
- PostgreSQL (metadata storage)

**Memory Optimization**:
- With optimization: 512MB limit
- Without optimization: No limit

---

#### n8n-import (`n8n-import`)
**Purpose**: One-time import of pre-configured workflows and credentials
**Runs**: Once on first startup
**Source**: `./n8n/backup/workflows/` and `./n8n/backup/credentials/`

**Imports**:
- Credentials (Ollama, PostgreSQL, Qdrant connections)
- Demo workflows (V1, V2, V3 RAG examples)

---

#### Flowise (`flowise`)
**Image**: `flowiseai/flowise:latest`
**Purpose**: Visual low-code AI workflow builder
**Port**: 3001 (internal)
**Storage**: `flowise_data`, `flowise_storage` volumes

**Features**:
- Drag-and-drop chatflow builder
- Pre-built AI components (chains, agents, tools)
- LangChain integration
- PostgreSQL persistence
- More AI-focused than n8n, simpler interface

**Relationship with n8n**:
- Similar purpose (workflow automation)
- Flowise is AI-specific, visual
- n8n is general-purpose, more integrations
- Both can coexist for different use cases

**Memory Optimization**:
- With optimization: 512MB limit, Node heap 448MB
- Without optimization: No limit

**Node.js Configuration**:
- `NODE_OPTIONS=--max-old-space-size=448` to prevent OOM errors

---

### Data & Search Services

#### Qdrant (`qdrant`)
**Image**: `qdrant/qdrant`
**Purpose**: Vector database for embeddings and similarity search
**Ports**: 6333 (HTTP API), 6334 (gRPC)
**Storage**: `qdrant_storage` volume

**Used By**:
- n8n workflows (RAG, semantic search)
- Flowise chatflows (vector storage)
- Any service needing embedding search

**Features**:
- High-performance vector similarity search
- Support for multiple collections
- REST and gRPC APIs
- Filtering and metadata support

**Use Cases**:
- Document embeddings for RAG
- Semantic search
- Recommendation systems

**Memory Optimization**:
- With optimization: 1.5GB limit (increased due to usage)
- Without optimization: No limit

---

#### Neo4j (`neo4j`)
**Image**: `neo4j:latest`
**Purpose**: Graph database for knowledge graphs and GraphRAG
**Ports**: 7474 (HTTP), 7473 (HTTPS), 7687 (Bolt)
**Storage**: `./neo4j/` directory (data, logs, config, plugins)

**Used By**:
- Advanced RAG workflows (GraphRAG, LightRAG)
- Knowledge graph applications
- Relationship-based queries

**Features**:
- Cypher query language
- Web browser interface (port 7474)
- Graph algorithms library
- APOC procedures support

**Use Cases**:
- Knowledge graph construction
- GraphRAG (graph-based retrieval)
- Complex relationship queries
- Entity relationship mapping

**Memory Optimization**:
- With optimization: 2GB limit
- Without optimization: No limit

---

#### SearXNG (`searxng`)
**Image**: `searxng/searxng:latest`
**Purpose**: Privacy-focused meta-search engine
**Port**: 8080 (internal)
**Storage**: `./searxng/` directory for config

**Used By**:
- n8n workflows needing web search
- AI agents requiring current information
- Any service needing search capabilities

**Features**:
- Meta-search (aggregates results from multiple engines)
- No tracking, no ads
- JSON API for programmatic access
- Configurable search engines
- Redis caching for performance

**Configuration**:
- Settings in `./searxng/settings.yml`
- Secret key generated automatically
- Disabled engines: ahmia, torch, radio browser (Tor/unreliable)

**Memory Optimization**:
- With optimization: 1GB limit, 2 workers, 2 threads
- Without optimization: No limit, 4 workers, 4 threads

---

### Observability Services

#### Langfuse Web (`langfuse-web`)
**Image**: `langfuse/langfuse:3`
**Purpose**: LLM observability platform web interface
**Port**: 3000 (internal)

**Features**:
- Trace LLM calls (prompts, completions, latency)
- Cost tracking and analytics
- User feedback collection
- Prompt versioning and management
- Team collaboration
- Dashboard and visualizations

**Dependencies**:
- PostgreSQL (metadata storage)
- ClickHouse (analytics queries)
- MinIO (object storage)
- Redis (queue coordination)

**Use Cases**:
- Production LLM monitoring
- Cost analysis
- Prompt optimization
- Performance debugging
- User behavior analysis

**Memory Optimization**:
- With optimization: 1.5GB limit
- Without optimization: No limit

---

#### Langfuse Worker (`langfuse-worker`)
**Image**: `langfuse/langfuse-worker:3`
**Purpose**: Background processing for Langfuse
**Port**: 3030 (internal)

**Functions**:
- Process ingestion queue
- Write to ClickHouse
- Handle batch exports
- Execute background jobs
- Process integrations (PostHog, Mixpanel)

**Queue Types**:
- ingestion-queue (trace ingestion)
- trace-upsert (database writes)
- evaluation-execution-queue (eval runs)
- batch-export-queue (data exports)
- webhook-queue (external notifications)

**Memory Optimization**:
- With optimization: 1.5GB limit
- Without optimization: No limit

---

## Service Dependencies

### Dependency Graph

```
Caddy (reverse proxy)
├── Open WebUI
│   └── Ollama (LLM)
├── n8n
│   ├── PostgreSQL (storage)
│   ├── Ollama (LLM)
│   ├── Qdrant (vectors)
│   ├── Neo4j (graph, optional)
│   └── SearXNG (search)
├── Flowise
│   ├── PostgreSQL (storage)
│   ├── Ollama (LLM)
│   └── Qdrant (vectors)
├── Langfuse Web
│   ├── PostgreSQL (metadata)
│   ├── ClickHouse (analytics)
│   ├── MinIO (storage)
│   └── Redis (queues)
└── SearXNG
    └── Redis (cache)

Ollama
└── ollama-pull-llama-* (init)

Langfuse Worker
├── PostgreSQL (metadata)
├── ClickHouse (analytics)
├── MinIO (storage)
└── Redis (queues)
```

### Critical Dependencies

**Must Start First**:
1. PostgreSQL (required by n8n, Flowise, Langfuse)
2. Redis (required by Langfuse, SearXNG)
3. ClickHouse (required by Langfuse)
4. MinIO (required by Langfuse)
5. Ollama (required by AI applications)

**Can Start Anytime**:
- Qdrant (standalone vector DB)
- Neo4j (standalone graph DB)
- SearXNG (depends on Redis)

**Depend on Others**:
- n8n (needs PostgreSQL)
- Flowise (needs PostgreSQL)
- Langfuse Web/Worker (needs PostgreSQL, ClickHouse, MinIO, Redis)
- Open WebUI (standalone, but connects to Ollama)

---

## Resource Usage

### Memory Usage Estimates

#### Without Memory Optimization
| Service | Typical Usage | Notes |
|---------|---------------|-------|
| PostgreSQL | 4-6 GB | Shared by multiple services |
| Ollama | 8-16 GB | Depends on model size |
| ClickHouse | 4-6 GB | Analytics workload |
| Neo4j | 2-4 GB | Graph storage |
| Redis | 100-500 MB | Cache + queues |
| Open WebUI | 1-2 GB | Web interface |
| n8n | 500 MB - 1 GB | Workflow execution |
| Flowise | 500 MB - 1 GB | AI flows |
| Qdrant | 1-3 GB | Vector storage |
| Langfuse Web | 1-2 GB | Next.js app |
| Langfuse Worker | 1-2 GB | Background processing |
| SearXNG | 500 MB - 1 GB | Search aggregation |
| MinIO | 500 MB - 1 GB | Object storage |
| Caddy | 50-100 MB | Reverse proxy |
| **Total** | **~60-70 GB** | Full stack |

#### With Memory Optimization (`--memory-optimized`)
| Service | Memory Limit | Optimization Applied |
|---------|--------------|---------------------|
| Ollama | 8 GB | Context 4096, single model |
| PostgreSQL | 4 GB | Shared buffers tuned |
| ClickHouse | 3 GB | Hard limit |
| Neo4j | 2 GB | Hard limit |
| Open WebUI | 1.5 GB | Hard limit |
| Qdrant | 1.5 GB | Hard limit |
| Langfuse Web | 1.5 GB | Hard limit |
| Langfuse Worker | 1.5 GB | Hard limit |
| SearXNG | 1 GB | 2 workers, 2 threads |
| Flowise | 512 MB | Node heap 448MB |
| n8n | 512 MB | Hard limit |
| Redis | 512 MB | Maxmemory 400MB |
| MinIO | 512 MB | Hard limit |
| Caddy | 256 MB | Hard limit |
| **Total Cap** | **~27 GB** | Significant reduction |

### Storage Requirements

**Volumes**:
- `postgres_data`: 5-20 GB (depends on usage)
- `ollama_storage`: 10-50 GB (model files)
- `langfuse_clickhouse_data`: 5-50 GB (trace analytics)
- `qdrant_storage`: 1-10 GB (embeddings)
- `neo4j/data`: 1-10 GB (graph data)
- `langfuse_minio_data`: 5-20 GB (events/media)
- Other volumes: <1 GB each

**Minimum Recommended**: 100 GB free disk space
**Production Recommended**: 500 GB+ for growth

### CPU Requirements

**Minimum**:
- 4 cores for basic operation
- 8 cores recommended for comfortable use

**With GPU**:
- CPU: 4-8 cores
- GPU: NVIDIA (CUDA) or AMD (ROCm)
- VRAM: 8+ GB for 7B models

**Production**:
- 8-16 cores
- 64+ GB RAM (without optimization)
- 32+ GB RAM (with optimization)

---

## Use Cases

### Use Case 1: Local Development & Experimentation
**Services Needed**:
- Ollama (LLM)
- Open WebUI (chat interface)
- PostgreSQL (storage)
- Redis (cache)
- Caddy (routing)

**Optional**:
- n8n or Flowise (workflow building)
- Qdrant (RAG experiments)
- SearXNG (web search)

**Memory**: ~15-18 GB

---

### Use Case 2: RAG Application Development
**Services Needed**:
- All from Use Case 1
- Qdrant (vector storage)
- n8n (RAG workflows)
- SearXNG (web search augmentation)

**Optional**:
- Neo4j (for GraphRAG experiments)
- Flowise (visual RAG builder)

**Memory**: ~20-25 GB

---

### Use Case 3: Advanced GraphRAG & Knowledge Graphs
**Services Needed**:
- All from Use Case 2
- Neo4j (graph database)

**Memory**: ~22-27 GB

---

### Use Case 4: Production LLM Deployment
**Services Needed**:
- All from Use Case 2 or 3
- Langfuse Web + Worker (observability)
- ClickHouse (analytics)
- MinIO (object storage)

**Configuration**:
- Use `--environment public` for production
- Set custom domains in `.env`
- Enable HTTPS via Caddy + Let's Encrypt

**Memory**: ~27-30 GB (with optimization)
**Memory**: ~60-70 GB (without optimization)

---

### Use Case 5: Multi-Platform AI Development
**Services Needed**:
- All infrastructure services
- n8n AND Flowise (different tools for different needs)
- Both Qdrant and Neo4j (vector + graph)
- Full observability stack

**Use When**:
- Large team with varied preferences
- Multiple projects with different requirements
- Production + development environments

**Memory**: ~27-30 GB (with optimization)

---

## Service Recommendations by Scenario

### Scenario: Limited RAM (16-32 GB)
**Enable**: `--memory-optimized`
**Keep**:
- Core: PostgreSQL, Redis, Ollama, Caddy
- UI: Open WebUI, n8n
- Data: Qdrant
- Search: SearXNG

**Skip/Disable**:
- Flowise (use n8n instead)
- Neo4j (unless specifically needed)
- Langfuse stack (use for production only)

---

### Scenario: Development Machine (32-64 GB)
**Enable**: `--memory-optimized` (optional)
**Keep**:
- All services except Langfuse stack
- Keep Flowise if experimenting with different tools

**Use**:
- Langfuse only when testing observability features

---

### Scenario: Production Server (64+ GB)
**Disable**: Memory optimization (better performance)
**Keep**: All services
**Configure**:
- Public mode with custom domains
- HTTPS enabled
- Monitoring via Langfuse
- Regular backups via `backup-postgres.sh`

---

## Architecture Diagrams

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└──────────────────────────┬──────────────────────────────────┘
                           │ (HTTPS: 443 / HTTP: 80)
                           │
                    ┌──────▼──────┐
                    │    Caddy    │ Reverse Proxy + HTTPS
                    └──────┬──────┘
                           │
    ┏━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━━━┓
    ┃         Frontend Applications              ┃
    ┣━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┫
    ┃ Open    ┃   n8n   ┃ Flowise ┃  Langfuse  ┃
    ┃ WebUI   ┃ :5678   ┃  :3001  ┃   :3000    ┃
    ┃ :8080   ┃         ┃         ┃            ┃
    ┗━━━┯━━━━━┻━━━━┯━━━━┻━━━━┯━━━━┻━━━━━┯━━━━━━┛
        │            │         │          │
        │            └────┬────┘          │
        │                 │               │
    ┌───▼───────────────┐ │ ┌─────────────▼──────────┐
    │     Ollama        │ │ │  Langfuse Worker       │
    │  LLM Inference    │ │ │  Background Jobs       │
    │     :11434        │ │ │       :3030            │
    └───────────────────┘ │ └────────────────────────┘
                          │
        ┏━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━┓
        ┃        Data Layer                 ┃
        ┣━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━┫
        ┃ Qdrant┃ Neo4j ┃SearXNG┃ MinIO   ┃
        ┃Vector ┃ Graph ┃Search ┃S3 Store ┃
        ┃ :6333 ┃:7474  ┃ :8080 ┃  :9000  ┃
        ┗━━━━━━━┻━━━━━━━┻━━━━━━━┻━━━━━━━━━┛
                          │
        ┏━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━┓
        ┃     Infrastructure Layer          ┃
        ┣━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┫
        ┃Postgres┃  Redis  ┃  ClickHouse   ┃
        ┃ :5432  ┃  :6379  ┃   :8123       ┃
        ┗━━━━━━━━┻━━━━━━━━━┻━━━━━━━━━━━━━━━┛
```

### Data Flow: RAG Query

```
User Question
     │
     ▼
┌─────────────┐
│ Open WebUI  │
│  or n8n     │
└──────┬──────┘
       │ 1. Query
       ▼
┌─────────────┐
│   Ollama    │ ──┐
│  Embedding  │   │ 2. Generate embedding
└──────┬──────┘   │
       │          │
       ▼          │
┌─────────────┐   │
│   Qdrant    │◄──┘
│   Search    │ 3. Find similar vectors
└──────┬──────┘
       │ 4. Return relevant docs
       ▼
┌─────────────┐
│   Ollama    │
│  LLM Gen    │ 5. Generate answer with context
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   User      │ 6. Display answer
└─────────────┘
       │
       ▼
┌─────────────┐
│  Langfuse   │ 7. Log trace (optional)
└─────────────┘
```

### Data Flow: Workflow Automation

```
┌─────────────┐
│  Webhook    │
│  or Trigger │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│     n8n     │
│  Workflow   │
└──────┬──────┘
       │
       ├──────────────┐
       │              │
       ▼              ▼
┌─────────────┐  ┌──────────┐
│  SearXNG    │  │  Ollama  │
│  Search     │  │   LLM    │
└──────┬──────┘  └─────┬────┘
       │                │
       └────────┬───────┘
                │
                ▼
         ┌─────────────┐
         │   Qdrant    │
         │   Store     │
         └──────┬──────┘
                │
                ▼
         ┌─────────────┐
         │ PostgreSQL  │
         │   Persist   │
         └─────────────┘
```

---

## Environment Configuration

### Critical Environment Variables

**Database**:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `POSTGRES_ADDITIONAL_DBS` - Create separate databases

**Security**:
- `N8N_ENCRYPTION_KEY` - n8n credential encryption
- `N8N_USER_MANAGEMENT_JWT_SECRET` - n8n JWT
- `NEO4J_AUTH` - Neo4j username/password
- `LANGFUSE_SALT`, `ENCRYPTION_KEY`, `NEXTAUTH_SECRET` - Langfuse security
- `CLICKHOUSE_PASSWORD`, `MINIO_ROOT_PASSWORD` - Service passwords

**Public Deployment**:
- `N8N_HOSTNAME`, `WEBUI_HOSTNAME`, `FLOWISE_HOSTNAME`, etc.
- `LETSENCRYPT_EMAIL` - For HTTPS certificates

**Optional**:
- `POSTGRES_VERSION` - PostgreSQL version (default: pg17)
- `N8N_DB`, `FLOWISE_DB`, `LANGFUSE_DB` - Database names

---

## Conclusion

This stack provides a complete, production-ready AI development environment with:

✅ **Flexibility**: Choose between n8n and Flowise, vector and graph databases
✅ **Scalability**: Memory optimization for development, full power for production
✅ **Observability**: Built-in monitoring with Langfuse
✅ **Privacy**: Fully self-hosted, no external APIs required
✅ **Integration**: All services work together seamlessly

**Development**: Use memory-optimized mode with core services
**Production**: Run all services with monitoring enabled

For questions or issues, refer to `CLAUDE.md` for operational procedures.
