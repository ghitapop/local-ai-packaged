#!/bin/bash
# PostgreSQL Restore Script for Local AI Package
# This script restores databases from a backup file

set -e

# Configuration
BACKUP_DIR="./backups/postgres"
CONTAINER_NAME="postgres"

# Check if backup file is provided
if [ -z "$1" ]; then
    echo "Usage: ./restore-postgres.sh <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "No backups found in $BACKUP_DIR"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file '$BACKUP_FILE' not found"
    exit 1
fi

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Error: PostgreSQL container '${CONTAINER_NAME}' is not running"
    exit 1
fi

# Warning
echo "WARNING: This will restore the database from backup."
echo "Backup file: $BACKUP_FILE"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Restore cancelled"
    exit 0
fi

echo ""
echo "Starting restore at $(date)"

# Stop services that depend on PostgreSQL
echo "Stopping dependent services..."
docker compose -p localai stop n8n flowise langfuse-web langfuse-worker

# Restore database
echo "Restoring database..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U postgres
else
    cat "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U postgres
fi

if [ $? -eq 0 ]; then
    echo "✓ Database restored successfully"
else
    echo "✗ Restore failed!"
    exit 1
fi

# Restart services
echo "Restarting dependent services..."
docker compose -p localai start n8n flowise langfuse-web langfuse-worker

echo ""
echo "Restore completed successfully at $(date)"
echo "Services have been restarted"
