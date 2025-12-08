#!/bin/bash
set -e

# This script creates additional databases beyond the default POSTGRES_DB
# It runs automatically during container initialization

# Parse comma-separated list of additional databases from environment variable
if [ -n "$POSTGRES_ADDITIONAL_DBS" ]; then
    echo "Creating additional databases: $POSTGRES_ADDITIONAL_DBS"

    IFS=',' read -ra DBS <<< "$POSTGRES_ADDITIONAL_DBS"
    for db in "${DBS[@]}"; do
        # Trim whitespace
        db=$(echo "$db" | xargs)

        if [ -n "$db" ]; then
            echo "Creating database: $db"
            psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
                CREATE DATABASE "$db";
                \c "$db"
                CREATE EXTENSION IF NOT EXISTS vector;
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
                CREATE EXTENSION IF NOT EXISTS pg_trgm;
EOSQL
            echo "Database $db created with AI extensions"
        fi
    done

    echo "All additional databases created successfully"
else
    echo "No additional databases specified in POSTGRES_ADDITIONAL_DBS"
fi
