#!/bin/bash
# PostgreSQL Backup Script for Local AI Package
# This script creates full database backups of all databases in the PostgreSQL container

set -e

# Configuration
BACKUP_DIR="./backups/postgres"
CONTAINER_NAME="postgres"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting PostgreSQL backup at $(date)"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Error: PostgreSQL container '${CONTAINER_NAME}' is not running"
    exit 1
fi

# Backup all databases using pg_dumpall
echo "Creating full backup of all databases..."
docker exec "$CONTAINER_NAME" pg_dumpall -U postgres | gzip > "$BACKUP_DIR/full_backup_$DATE.sql.gz"

if [ $? -eq 0 ]; then
    echo "✓ Full backup created: $BACKUP_DIR/full_backup_$DATE.sql.gz"
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/full_backup_$DATE.sql.gz" | cut -f1)
    echo "  Backup size: $BACKUP_SIZE"
else
    echo "✗ Backup failed!"
    exit 1
fi

# Clean up old backups (keep only last N days)
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "✓ Cleanup complete"

# List recent backups
echo ""
echo "Recent backups:"
ls -lh "$BACKUP_DIR" | tail -n 5

echo ""
echo "Backup completed successfully at $(date)"
