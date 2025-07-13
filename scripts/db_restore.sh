#!/bin/bash

# Database Restore Script for mem0-stack
# Restores PostgreSQL and Neo4j databases from backups

set -euo pipefail

# Configuration
BACKUP_DIR="/home/drj/projects/mem0-stack/backups"
POSTGRES_CONTAINER="postgres-mem0"
NEO4J_CONTAINER="neo4j-mem0"
RESTORE_LOG="/home/drj/projects/mem0-stack/data/restore.log"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$RESTORE_LOG"
}

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] BACKUP_DATE

Restore PostgreSQL and Neo4j databases from backups

OPTIONS:
    -p, --postgres-only     Restore only PostgreSQL
    -n, --neo4j-only       Restore only Neo4j
    -v, --verify           Verify restore integrity (default: true)
    -f, --force            Force restore without confirmation
    -l, --list             List available backups
    -h, --help             Show this help message

BACKUP_DATE:
    Format: YYYYMMDD_HHMMSS or 'latest' for most recent backup

Examples:
    $0 20250109_030000              # Restore from specific backup
    $0 latest                       # Restore from latest backup
    $0 --postgres-only latest       # Restore only PostgreSQL from latest
    $0 --list                       # List available backups

EOF
}

# Function to list available backups
list_backups() {
    log "Listing available backups..."

    echo "PostgreSQL Backups:"
    if ls "$BACKUP_DIR"/postgres/*.backup 2>/dev/null; then
        ls -lh "$BACKUP_DIR"/postgres/*.backup | awk '{print $9, $5, $6, $7, $8}'
    else
        echo "No PostgreSQL backups found"
    fi

    echo
    echo "Neo4j Backups:"
    if ls "$BACKUP_DIR"/neo4j/*.cypher 2>/dev/null; then
        ls -lh "$BACKUP_DIR"/neo4j/*.cypher | awk '{print $9, $5, $6, $7, $8}'
    else
        echo "No Neo4j backups found"
    fi
}

# Function to get latest backup date
get_latest_backup() {
    LATEST_PG=$(ls -t "$BACKUP_DIR"/postgres/*.backup 2>/dev/null | head -1 | sed 's/.*mem0_\([0-9_]*\)\.backup/\1/' || echo "")
    LATEST_NEO4J=$(ls -t "$BACKUP_DIR"/neo4j/*.cypher 2>/dev/null | head -1 | sed 's/.*backup_\([0-9_]*\)\.cypher/\1/' || echo "")

    if [ -n "$LATEST_PG" ] && [ -n "$LATEST_NEO4J" ]; then
        # Return the most recent of the two
        if [ "$LATEST_PG" \> "$LATEST_NEO4J" ]; then
            echo "$LATEST_NEO4J"
        else
            echo "$LATEST_PG"
        fi
    elif [ -n "$LATEST_PG" ]; then
        echo "$LATEST_PG"
    elif [ -n "$LATEST_NEO4J" ]; then
        echo "$LATEST_NEO4J"
    else
        echo ""
    fi
}

# Function to check if container is running
check_container() {
    if ! docker ps | grep -q "$1"; then
        log "ERROR: Container $1 is not running"
        log "Please start the container first: docker-compose up -d $1"
        exit 1
    fi
}

# Function to stop services gracefully
stop_services() {
    log "Stopping dependent services..."
    docker-compose stop mem0 openmemory-mcp openmemory-ui 2>/dev/null || true
    sleep 5
}

# Function to start services
start_services() {
    log "Starting services..."
    docker-compose up -d

    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 10

    # Check health
    for i in {1..30}; do
        if docker exec "$POSTGRES_CONTAINER" pg_isready -U "${POSTGRES_USER:-drj}" -d mem0 >/dev/null 2>&1; then
            log "PostgreSQL is ready"
            break
        fi
        sleep 2
    done

    for i in {1..30}; do
        if docker exec "$NEO4J_CONTAINER" wget -O /dev/null http://localhost:7474/ >/dev/null 2>&1; then
            log "Neo4j is ready"
            break
        fi
        sleep 2
    done
}

# Function to create pre-restore backup
create_pre_restore_backup() {
    log "Creating pre-restore backup..."

    PRE_RESTORE_DATE=$(date +%Y%m%d_%H%M%S)
    PRE_RESTORE_DIR="$BACKUP_DIR/pre_restore_$PRE_RESTORE_DATE"

    mkdir -p "$PRE_RESTORE_DIR"/{postgres,neo4j}

    # Backup current PostgreSQL
    if check_container "$POSTGRES_CONTAINER" >/dev/null 2>&1; then
        docker exec "$POSTGRES_CONTAINER" pg_dump \
            -U "${POSTGRES_USER:-drj}" \
            -d mem0 \
            --format=custom \
            > "$PRE_RESTORE_DIR/postgres/mem0_pre_restore.backup"
        log "Pre-restore PostgreSQL backup created"
    fi

    # Backup current Neo4j
    if check_container "$NEO4J_CONTAINER" >/dev/null 2>&1; then
        docker exec "$NEO4J_CONTAINER" cypher-shell \
            -u neo4j -p "${NEO4J_PASSWORD}" \
            "CALL apoc.export.cypher.all('/var/lib/neo4j/backups/pre_restore.cypher', {
                format: 'cypher-shell'
            })" >/dev/null 2>&1 || true

        docker cp "$NEO4J_CONTAINER:/var/lib/neo4j/backups/pre_restore.cypher" \
            "$PRE_RESTORE_DIR/neo4j/pre_restore.cypher" 2>/dev/null || true

        log "Pre-restore Neo4j backup created"
    fi

    echo "$PRE_RESTORE_DIR" > "/tmp/mem0_pre_restore_path"
    log "Pre-restore backup location: $PRE_RESTORE_DIR"
}

# Function to restore PostgreSQL
restore_postgres() {
    local backup_date="$1"
    local backup_file="$BACKUP_DIR/postgres/mem0_${backup_date}.backup"

    log "Restoring PostgreSQL from $backup_file..."

    if [ ! -f "$backup_file" ]; then
        log "ERROR: PostgreSQL backup file not found: $backup_file"
        return 1
    fi

    check_container "$POSTGRES_CONTAINER"

    # Drop and recreate database
    log "Dropping existing database..."
    docker exec "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'mem0' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true

    docker exec "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d postgres \
        -c "DROP DATABASE IF EXISTS mem0;" >/dev/null 2>&1 || true

    docker exec "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d postgres \
        -c "CREATE DATABASE mem0;" >/dev/null 2>&1

    # Restore from backup
    log "Restoring database from backup..."
    docker exec -i "$POSTGRES_CONTAINER" pg_restore \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        --verbose \
        --clean \
        --if-exists < "$backup_file"

    log "PostgreSQL restore completed"
}

# Function to restore Neo4j
restore_neo4j() {
    local backup_date="$1"
    local backup_file="$BACKUP_DIR/neo4j/backup_${backup_date}.cypher"

    log "Restoring Neo4j from $backup_file..."

    if [ ! -f "$backup_file" ]; then
        log "ERROR: Neo4j backup file not found: $backup_file"
        return 1
    fi

    check_container "$NEO4J_CONTAINER"

    # Clear existing data
    log "Clearing existing Neo4j data..."
    docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u neo4j -p "${NEO4J_PASSWORD}" \
        "MATCH (n) DETACH DELETE n;" >/dev/null 2>&1 || true

    # Copy backup file to container
    docker cp "$backup_file" "$NEO4J_CONTAINER:/var/lib/neo4j/restore.cypher"

    # Restore from backup
    log "Restoring graph data from backup..."
    docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u neo4j -p "${NEO4J_PASSWORD}" \
        -f /var/lib/neo4j/restore.cypher >/dev/null 2>&1

    # Clean up
    docker exec "$NEO4J_CONTAINER" rm -f /var/lib/neo4j/restore.cypher

    log "Neo4j restore completed"
}

# Function to verify restore
verify_restore() {
    log "Verifying restore integrity..."

    # Verify PostgreSQL
    if [ "$RESTORE_POSTGRES" = true ]; then
        PG_TABLES=$(docker exec "$POSTGRES_CONTAINER" psql \
            -U "${POSTGRES_USER:-drj}" \
            -d mem0 \
            -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")

        PG_RECORDS=$(docker exec "$POSTGRES_CONTAINER" psql \
            -U "${POSTGRES_USER:-drj}" \
            -d mem0 \
            -t -c "SELECT count(*) FROM memories;" 2>/dev/null || echo "0")

        log "PostgreSQL verification - Tables: $PG_TABLES, Memory records: $PG_RECORDS"
    fi

    # Verify Neo4j
    if [ "$RESTORE_NEO4J" = true ]; then
        NEO4J_NODES=$(docker exec "$NEO4J_CONTAINER" cypher-shell \
            -u neo4j -p "${NEO4J_PASSWORD}" \
            "MATCH (n) RETURN count(n) as node_count;" 2>/dev/null | tail -1 || echo "0")

        NEO4J_RELS=$(docker exec "$NEO4J_CONTAINER" cypher-shell \
            -u neo4j -p "${NEO4J_PASSWORD}" \
            "MATCH ()-[r]-() RETURN count(r) as rel_count;" 2>/dev/null | tail -1 || echo "0")

        log "Neo4j verification - Nodes: $NEO4J_NODES, Relationships: $NEO4J_RELS"
    fi

    log "Restore verification completed"
}

# Function to rollback restore
rollback_restore() {
    if [ -f "/tmp/mem0_pre_restore_path" ]; then
        PRE_RESTORE_DIR=$(cat "/tmp/mem0_pre_restore_path")
        log "Rolling back to pre-restore state from $PRE_RESTORE_DIR..."

        # Rollback PostgreSQL
        if [ -f "$PRE_RESTORE_DIR/postgres/mem0_pre_restore.backup" ]; then
            log "Rolling back PostgreSQL..."
            docker exec -i "$POSTGRES_CONTAINER" pg_restore \
                -U "${POSTGRES_USER:-drj}" \
                -d mem0 \
                --clean \
                --if-exists < "$PRE_RESTORE_DIR/postgres/mem0_pre_restore.backup"
        fi

        # Rollback Neo4j
        if [ -f "$PRE_RESTORE_DIR/neo4j/pre_restore.cypher" ]; then
            log "Rolling back Neo4j..."
            docker exec "$NEO4J_CONTAINER" cypher-shell \
                -u neo4j -p "${NEO4J_PASSWORD}" \
                "MATCH (n) DETACH DELETE n;" >/dev/null 2>&1 || true

            docker cp "$PRE_RESTORE_DIR/neo4j/pre_restore.cypher" \
                "$NEO4J_CONTAINER:/var/lib/neo4j/rollback.cypher"

            docker exec "$NEO4J_CONTAINER" cypher-shell \
                -u neo4j -p "${NEO4J_PASSWORD}" \
                -f /var/lib/neo4j/rollback.cypher >/dev/null 2>&1

            docker exec "$NEO4J_CONTAINER" rm -f /var/lib/neo4j/rollback.cypher
        fi

        log "Rollback completed"
        rm -f "/tmp/mem0_pre_restore_path"
    else
        log "No pre-restore backup found for rollback"
    fi
}

# Parse command line arguments
RESTORE_POSTGRES=true
RESTORE_NEO4J=true
VERIFY=true
FORCE=false
BACKUP_DATE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--postgres-only)
            RESTORE_POSTGRES=true
            RESTORE_NEO4J=false
            shift
            ;;
        -n|--neo4j-only)
            RESTORE_POSTGRES=false
            RESTORE_NEO4J=true
            shift
            ;;
        -v|--verify)
            VERIFY=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -l|--list)
            list_backups
            exit 0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            if [ -z "$BACKUP_DATE" ]; then
                BACKUP_DATE="$1"
            else
                log "ERROR: Unknown argument: $1"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [ -z "$BACKUP_DATE" ]; then
    log "ERROR: Backup date not specified"
    usage
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    source .env
fi

# Handle 'latest' backup
if [ "$BACKUP_DATE" = "latest" ]; then
    BACKUP_DATE=$(get_latest_backup)
    if [ -z "$BACKUP_DATE" ]; then
        log "ERROR: No backups found"
        exit 1
    fi
    log "Using latest backup: $BACKUP_DATE"
fi

# Check if backup files exist
if [ "$RESTORE_POSTGRES" = true ] && [ ! -f "$BACKUP_DIR/postgres/mem0_${BACKUP_DATE}.backup" ]; then
    log "ERROR: PostgreSQL backup not found: $BACKUP_DIR/postgres/mem0_${BACKUP_DATE}.backup"
    exit 1
fi

if [ "$RESTORE_NEO4J" = true ] && [ ! -f "$BACKUP_DIR/neo4j/backup_${BACKUP_DATE}.cypher" ]; then
    log "ERROR: Neo4j backup not found: $BACKUP_DIR/neo4j/backup_${BACKUP_DATE}.cypher"
    exit 1
fi

# Confirmation prompt
if [ "$FORCE" = false ]; then
    echo
    echo "⚠️  WARNING: This will restore the database from backup!"
    echo "Backup date: $BACKUP_DATE"
    echo "Restore PostgreSQL: $RESTORE_POSTGRES"
    echo "Restore Neo4j: $RESTORE_NEO4J"
    echo
    echo "This will:"
    echo "1. Stop dependent services"
    echo "2. Create a pre-restore backup"
    echo "3. Replace current data with backup data"
    echo "4. Start services"
    echo
    read -p "Do you want to continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log "Restore cancelled by user"
        exit 0
    fi
fi

# Main restore process
log "Starting database restore process..."

# Create pre-restore backup
create_pre_restore_backup

# Stop services
stop_services

# Set up error handling for rollback
trap 'log "ERROR: Restore failed, attempting rollback..."; rollback_restore; start_services; exit 1' ERR

# Perform restore
if [ "$RESTORE_POSTGRES" = true ]; then
    restore_postgres "$BACKUP_DATE"
fi

if [ "$RESTORE_NEO4J" = true ]; then
    restore_neo4j "$BACKUP_DATE"
fi

# Start services
start_services

# Verify restore
if [ "$VERIFY" = true ]; then
    verify_restore
fi

# Clean up
rm -f "/tmp/mem0_pre_restore_path"

log "Database restore completed successfully!"
log "Restored from backup: $BACKUP_DATE"

# Generate restore report
REPORT_FILE="/home/drj/projects/mem0-stack/data/restore_report_$(date +%Y%m%d_%H%M%S).txt"
cat > "$REPORT_FILE" << EOF
Database Restore Report - $(date)
==================================

Restore Details:
- Backup Date: $BACKUP_DATE
- PostgreSQL Restored: $RESTORE_POSTGRES
- Neo4j Restored: $RESTORE_NEO4J
- Verification: $VERIFY

Services Status:
$(docker ps --format "{{.Names}}: {{.Status}}" | grep -E "(postgres-mem0|neo4j-mem0|mem0|openmemory)")

Restore completed at: $(date)
EOF

log "Restore report generated: $REPORT_FILE"
