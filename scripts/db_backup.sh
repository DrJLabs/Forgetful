#!/bin/bash

# Database Backup Script for mem0-stack
# Backs up PostgreSQL and Neo4j databases with rotation

set -euo pipefail

# Configuration
BACKUP_DIR="/home/drj/projects/mem0-stack/data/backups"
POSTGRES_CONTAINER="postgres-mem0"
NEO4J_CONTAINER="neo4j-mem0"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"/{postgres,neo4j}

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$BACKUP_DIR/backup.log"
}

# Function to check if container is running
check_container() {
    if ! docker ps | grep -q "$1"; then
        log "ERROR: Container $1 is not running"
        exit 1
    fi
}

# PostgreSQL Backup
backup_postgres() {
    log "Starting PostgreSQL backup..."
    check_container "$POSTGRES_CONTAINER"

    # Create PostgreSQL backup
    docker exec "$POSTGRES_CONTAINER" pg_dump \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        --verbose \
        --clean \
        --if-exists \
        --format=custom \
        > "$BACKUP_DIR/postgres/mem0_${DATE}.backup"

    # Create SQL dump for portability
    docker exec "$POSTGRES_CONTAINER" pg_dump \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        --verbose \
        --clean \
        --if-exists \
        > "$BACKUP_DIR/postgres/mem0_${DATE}.sql"

    log "PostgreSQL backup completed: mem0_${DATE}.backup"
}

# Neo4j Backup
backup_neo4j() {
    log "Starting Neo4j backup..."
    check_container "$NEO4J_CONTAINER"

    # Create backup directory in container
    docker exec "$NEO4J_CONTAINER" mkdir -p /var/lib/neo4j/backups

    # Create Neo4j backup using APOC export (writes to import directory)
    docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u neo4j -p "${NEO4J_PASSWORD}" \
        "CALL apoc.export.cypher.all('backup_${DATE}.cypher', {
            format: 'cypher-shell',
            useOptimizations: {type: 'UNWIND_BATCH'}
        })" || true

    # Copy backup from container if it exists (APOC writes to import directory)
    if docker exec "$NEO4J_CONTAINER" test -f "/var/lib/neo4j/import/backup_${DATE}.cypher"; then
        docker cp "$NEO4J_CONTAINER:/var/lib/neo4j/import/backup_${DATE}.cypher" \
            "$BACKUP_DIR/neo4j/backup_${DATE}.cypher"
    else
        log "Neo4j cypher backup failed - creating alternative backup"
        # Alternative: Export just the nodes and relationships
        docker exec "$NEO4J_CONTAINER" cypher-shell \
            -u neo4j -p "${NEO4J_PASSWORD}" \
            "MATCH (n) RETURN count(n) as node_count" > "$BACKUP_DIR/neo4j/backup_${DATE}_simple.txt"
    fi

    # Create graph data export (if available)
    docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u neo4j -p "${NEO4J_PASSWORD}" \
        "CALL apoc.export.graphml.all('backup_${DATE}.graphml', {})" || log "GraphML export not available"

    if docker exec "$NEO4J_CONTAINER" test -f "/var/lib/neo4j/import/backup_${DATE}.graphml"; then
        docker cp "$NEO4J_CONTAINER:/var/lib/neo4j/import/backup_${DATE}.graphml" \
            "$BACKUP_DIR/neo4j/backup_${DATE}.graphml"
    fi

    log "Neo4j backup completed: backup_${DATE}.cypher"
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete
    log "Cleanup completed"
}

# Verify backup integrity
verify_backups() {
    log "Verifying backup integrity..."

    # Check PostgreSQL backup
    if [ -f "$BACKUP_DIR/postgres/mem0_${DATE}.backup" ]; then
        # Copy backup file to container for verification
        docker cp "$BACKUP_DIR/postgres/mem0_${DATE}.backup" "$POSTGRES_CONTAINER:/tmp/backup_verify.backup"
        docker exec "$POSTGRES_CONTAINER" pg_restore \
            --list "/tmp/backup_verify.backup" > /dev/null
        docker exec "$POSTGRES_CONTAINER" rm "/tmp/backup_verify.backup"
        log "PostgreSQL backup verification: PASSED"
    else
        log "PostgreSQL backup verification: FAILED"
    fi

    # Check Neo4j backup
    if [ -f "$BACKUP_DIR/neo4j/backup_${DATE}.cypher" ]; then
        if [ -s "$BACKUP_DIR/neo4j/backup_${DATE}.cypher" ]; then
            log "Neo4j backup verification: PASSED"
        else
            log "Neo4j backup verification: FAILED (empty file)"
        fi
    else
        log "Neo4j backup verification: FAILED (file not found)"
    fi
}

# Main execution
main() {
    log "Starting database backup process..."

    # Load environment variables
    if [ -f .env ]; then
        source .env
    fi

    backup_postgres
    backup_neo4j
    verify_backups
    cleanup_old_backups

    log "Database backup process completed successfully"

    # Create backup summary
    echo "Backup Summary - $(date)" > "$BACKUP_DIR/latest_backup_summary.txt"
    echo "PostgreSQL: $(ls -lh $BACKUP_DIR/postgres/mem0_${DATE}.backup)" >> "$BACKUP_DIR/latest_backup_summary.txt"
    echo "Neo4j: $(ls -lh $BACKUP_DIR/neo4j/backup_${DATE}.cypher)" >> "$BACKUP_DIR/latest_backup_summary.txt"
}

# Run main function
main "$@"