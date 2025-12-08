-- Initialize PostgreSQL with required extensions for AI workloads
-- This script runs automatically when the database is first created

-- Enable pgvector extension for vector embeddings (RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID extension for generating unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for text search and similarity
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL initialized with AI extensions: vector, uuid-ossp, pg_trgm';
END $$;
