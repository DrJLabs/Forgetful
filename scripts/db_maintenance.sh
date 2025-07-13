#!/bin/bash

# Database Maintenance Script for mem0-stack
# Performs routine maintenance on PostgreSQL and Neo4j

set -euo pipefail

# Configuration
POSTGRES_CONTAINER="postgres-mem0"
NEO4J_CONTAINER="neo4j-mem0"
MAINTENANCE_LOG="/home/drj/projects/mem0-stack/data/maintenance.log"
VACUUM_THRESHOLD_MB=100  # Run full vacuum if dead tuples exceed this
STATS_AGE_HOURS=24      # Update statistics if older than this

# Create log directory
mkdir -p "$(dirname "$MAINTENANCE_LOG")"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MAINTENANCE_LOG"
}

# Function to check if container is running
check_container() {
    if ! docker ps | grep -q "$1"; then
        log "ERROR: Container $1 is not running"
        exit 1
    fi
}

# PostgreSQL maintenance functions
postgres_vacuum_analyze() {
    log "Starting PostgreSQL VACUUM ANALYZE..."
    check_container "$POSTGRES_CONTAINER"

    # Get database size before maintenance
    DB_SIZE_BEFORE=$(docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "SELECT pg_size_pretty(pg_database_size('mem0'))")

    log "Database size before maintenance: $DB_SIZE_BEFORE"

    # Vacuum and analyze all tables
    docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -c "VACUUM (VERBOSE, ANALYZE);"

    # Get database size after maintenance
    DB_SIZE_AFTER=$(docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "SELECT pg_size_pretty(pg_database_size('mem0'))")

    log "Database size after maintenance: $DB_SIZE_AFTER"
    log "PostgreSQL VACUUM ANALYZE completed"
}

postgres_reindex() {
    log "Starting PostgreSQL REINDEX..."

    # Check for bloated indexes
    BLOATED_INDEXES=$(docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "
        SELECT schemaname||'.'||tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        AND pg_total_relation_size(schemaname||'.'||tablename) > 100*1024*1024;
    ")

    if [ -n "$BLOATED_INDEXES" ]; then
        while IFS= read -r table; do
            if [ -n "$table" ]; then
                log "Reindexing table: $table"
                docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql \
                    -U "${POSTGRES_USER:-drj}" \
                    -d mem0 \
                    -c "REINDEX TABLE $table;" || log "Failed to reindex $table"
            fi
        done <<< "$BLOATED_INDEXES"
    else
        log "No large tables found requiring reindexing"
    fi
}

postgres_update_statistics() {
    log "Updating PostgreSQL statistics..."

    # Update table statistics
    docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -c "ANALYZE;"

    log "PostgreSQL statistics updated"
}

postgres_check_connections() {
    log "Checking PostgreSQL connection usage..."

    CONNECTIONS=$(docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "
        SELECT count(*) as active_connections,
               (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections
        FROM pg_stat_activity
        WHERE state = 'active';
    ")

    log "Active connections: $CONNECTIONS"

    # Check for long-running queries
    LONG_QUERIES=$(docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "
        SELECT count(*)
        FROM pg_stat_activity
        WHERE state = 'active'
        AND query_start < now() - interval '5 minutes';
    ")

    if [ "$LONG_QUERIES" -gt 0 ]; then
        log "WARNING: $LONG_QUERIES long-running queries detected"
    fi
}

postgres_cleanup_logs() {
    log "Cleaning up PostgreSQL logs..."

    # Rotate and clean old log files (if accessible)
    docker exec "$POSTGRES_CONTAINER" find /var/log -name "*.log" -mtime +7 -delete 2>/dev/null || true

    log "PostgreSQL log cleanup completed"
}

# Neo4j maintenance functions
neo4j_check_store_files() {
    log "Checking Neo4j store files..."
    check_container "$NEO4J_CONTAINER"

    # Get database statistics
    STATS=$(docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u neo4j -p "${NEO4J_PASSWORD}" \
        "CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Store file sizes') YIELD attributes
         RETURN attributes.TotalStoreSize as total_size,
                attributes.NodeStoreSize as node_size,
                attributes.RelationshipStoreSize as rel_size;" 2>/dev/null || echo "Stats unavailable")

    log "Neo4j store statistics: $STATS"
}

neo4j_check_constraints_indexes() {
    log "Checking Neo4j constraints and indexes..."

    # List all indexes
    INDEXES=$(docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u neo4j -p "${NEO4J_PASSWORD}" \
        "SHOW INDEXES;" 2>/dev/null || echo "No indexes found")

    log "Neo4j indexes: $INDEXES"

    # List all constraints
    CONSTRAINTS=$(docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u neo4j -p "${NEO4J_PASSWORD}" \
        "SHOW CONSTRAINTS;" 2>/dev/null || echo "No constraints found")

    log "Neo4j constraints: $CONSTRAINTS"
}

neo4j_memory_usage() {
    log "Checking Neo4j memory usage..."

    # Get memory usage information
    MEMORY_INFO=$(docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u neo4j -p "${NEO4J_PASSWORD}" \
        "CALL dbms.queryJmx('java.lang:type=Memory') YIELD attributes
         RETURN attributes.HeapMemoryUsage as heap_usage;" 2>/dev/null || echo "Memory info unavailable")

    log "Neo4j memory usage: $MEMORY_INFO"
}

neo4j_transaction_logs() {
    log "Managing Neo4j transaction logs..."

    # Check transaction log size
    LOG_SIZE=$(docker exec "$NEO4J_CONTAINER" du -sh /data/transactions 2>/dev/null || echo "0B")
    log "Neo4j transaction log size: $LOG_SIZE"

    # Transaction logs are managed by Neo4j automatically based on:
    # NEO4J_dbms_tx_log_rotation_retention_policy=1G size
    log "Transaction logs managed by retention policy (1G size)"
}

# Performance monitoring
check_system_resources() {
    log "Checking system resources..."

    # Check disk space
    DISK_USAGE=$(df -h /home/drj/projects/mem0-stack/data | tail -1)
    log "Data directory disk usage: $DISK_USAGE"

    # Check memory usage of containers
    MEM_USAGE=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        postgres-mem0 neo4j-mem0 mem0 openmemory-mcp)
    log "Container resource usage:\n$MEM_USAGE"
}

# Data retention management
cleanup_old_data() {
    log "Checking for old data cleanup..."

    # Check for old memories (example: memories older than 1 year)
    OLD_MEMORIES=$(docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "
        SELECT COUNT(*)
        FROM memories
        WHERE created_at < NOW() - INTERVAL '1 year'
        AND deleted_at IS NULL;
    " 2>/dev/null || echo "0")

    if [ "$OLD_MEMORIES" -gt 0 ]; then
        log "Found $OLD_MEMORIES memories older than 1 year (not automatically deleted)"
    fi

    # Clean up test data (if any)
    TEST_MEMORIES=$(docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "
        SELECT COUNT(*)
        FROM memories
        WHERE metadata::text LIKE '%test%'
        OR metadata::text LIKE '%Test%';
    " 2>/dev/null || echo "0")

    if [ "$TEST_MEMORIES" -gt 0 ]; then
        log "Found $TEST_MEMORIES potential test memories"
    fi
}

# Health checks
run_health_checks() {
    log "Running database health checks..."

    # PostgreSQL health check
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U "${POSTGRES_USER:-drj}" -d mem0; then
        log "PostgreSQL health check: PASSED"
    else
        log "PostgreSQL health check: FAILED"
    fi

    # Neo4j health check
    if docker exec "$NEO4J_CONTAINER" wget -O /dev/null http://localhost:7474/ 2>/dev/null; then
        log "Neo4j health check: PASSED"
    else
        log "Neo4j health check: FAILED"
    fi
}

# Generate maintenance report
generate_report() {
    log "Generating maintenance report..."

    REPORT_FILE="/home/drj/projects/mem0-stack/data/maintenance_report_$(date +%Y%m%d).txt"

    cat > "$REPORT_FILE" << EOF
Database Maintenance Report - $(date)
======================================

System Resources:
$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" postgres-mem0 neo4j-mem0 mem0 openmemory-mcp)

Disk Usage:
$(df -h /home/drj/projects/mem0-stack/data)

PostgreSQL Information:
- Database Size: $(docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql -U "${POSTGRES_USER:-drj}" -d mem0 -t -c "SELECT pg_size_pretty(pg_database_size('mem0'))" 2>/dev/null || echo "Unable to determine")
- Active Connections: $(docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" "$POSTGRES_CONTAINER" psql -U "${POSTGRES_USER:-drj}" -d mem0 -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'" 2>/dev/null || echo "Unable to determine")

Neo4j Information:
- Transaction Log Size: $(docker exec "$NEO4J_CONTAINER" du -sh /data/transactions 2>/dev/null || echo "Unable to determine")

Last Maintenance: $(date)
EOF

    log "Maintenance report generated: $REPORT_FILE"
}

# Main execution function
main() {
    log "Starting database maintenance..."

    # Load environment variables
    if [ -f .env ]; then
        source .env
    fi

    # Run health checks first
    run_health_checks

    # PostgreSQL maintenance
    log "=== PostgreSQL Maintenance ==="
    postgres_vacuum_analyze
    postgres_reindex
    postgres_update_statistics
    postgres_check_connections
    postgres_cleanup_logs

    # Neo4j maintenance
    log "=== Neo4j Maintenance ==="
    neo4j_check_store_files
    neo4j_check_constraints_indexes
    neo4j_memory_usage
    neo4j_transaction_logs

    # System checks
    log "=== System Checks ==="
    check_system_resources
    cleanup_old_data

    # Generate report
    generate_report

    log "Database maintenance completed successfully"
}

# Command line options
case "${1:-maintenance}" in
    "vacuum")
        postgres_vacuum_analyze
        ;;
    "reindex")
        postgres_reindex
        ;;
    "stats")
        postgres_update_statistics
        ;;
    "health")
        run_health_checks
        ;;
    "report")
        generate_report
        ;;
    "maintenance"|*)
        main
        ;;
esac
