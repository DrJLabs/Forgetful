#!/bin/bash

# Database Monitoring Script for mem0-stack
# Monitors PostgreSQL and Neo4j performance and health

set -euo pipefail

# Configuration
POSTGRES_CONTAINER="postgres-mem0"
NEO4J_CONTAINER="neo4j-mem0"
MONITOR_LOG="/home/drj/projects/mem0-stack/data/monitor.log"
ALERT_LOG="/home/drj/projects/mem0-stack/data/alerts.log"
METRICS_DIR="/home/drj/projects/mem0-stack/data/metrics"

# Thresholds for alerting
CPU_THRESHOLD=80          # Alert if CPU usage > 80%
MEMORY_THRESHOLD=85       # Alert if memory usage > 85%
DISK_THRESHOLD=85         # Alert if disk usage > 85%
CONNECTION_THRESHOLD=80   # Alert if connections > 80% of max
QUERY_TIME_THRESHOLD=30   # Alert if queries run longer than 30 seconds

# Create directories
mkdir -p "$METRICS_DIR" "$(dirname "$MONITOR_LOG")" "$(dirname "$ALERT_LOG")"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MONITOR_LOG"
}

# Function to log alerts
alert() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALERT: $1" | tee -a "$ALERT_LOG"
    log "ALERT: $1"
}

# Function to check if container is running
check_container() {
    if ! docker ps | grep -q "$1"; then
        alert "Container $1 is not running"
        return 1
    fi
    return 0
}

# PostgreSQL monitoring functions
monitor_postgres_performance() {
    log "Monitoring PostgreSQL performance..."

    if ! check_container "$POSTGRES_CONTAINER"; then
        return 1
    fi

    # Database size and growth
    DB_SIZE=$(docker exec "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "SELECT pg_size_pretty(pg_database_size('mem0'))" 2>/dev/null || echo "Unknown")

    # Active connections
    ACTIVE_CONN=$(docker exec "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'" 2>/dev/null || echo "0")

    MAX_CONN=$(docker exec "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "SELECT setting FROM pg_settings WHERE name = 'max_connections'" 2>/dev/null || echo "100")

    CONN_PERCENT=$(( ACTIVE_CONN * 100 / MAX_CONN ))

    # Check connection threshold
    if [ "$CONN_PERCENT" -gt "$CONNECTION_THRESHOLD" ]; then
        alert "PostgreSQL connections at ${CONN_PERCENT}% of maximum ($ACTIVE_CONN/$MAX_CONN)"
    fi

    # Long-running queries
    LONG_QUERIES=$(docker exec "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "
        SELECT count(*)
        FROM pg_stat_activity
        WHERE state = 'active'
        AND query_start < now() - interval '$QUERY_TIME_THRESHOLD seconds'
        AND query NOT LIKE '%pg_stat_activity%';" 2>/dev/null || echo "0")

    if [ "$LONG_QUERIES" -gt 0 ]; then
        alert "PostgreSQL has $LONG_QUERIES long-running queries (>${QUERY_TIME_THRESHOLD}s)"
    fi

    # Cache hit ratio
    CACHE_HIT_RATIO=$(docker exec "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "
        SELECT round(
            100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read))
        , 2) as cache_hit_ratio
        FROM pg_stat_database;" 2>/dev/null || echo "0")

    # Index usage
    INDEX_USAGE=$(docker exec "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "
        SELECT round(
            100.0 * sum(idx_scan) / (sum(seq_scan) + sum(idx_scan))
        , 2) as index_usage
        FROM pg_stat_user_tables
        WHERE seq_scan + idx_scan > 0;" 2>/dev/null || echo "0")

    # Write metrics to file
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$TIMESTAMP,postgres,db_size,$DB_SIZE" >> "$METRICS_DIR/postgres_metrics.csv"
    echo "$TIMESTAMP,postgres,active_connections,$ACTIVE_CONN" >> "$METRICS_DIR/postgres_metrics.csv"
    echo "$TIMESTAMP,postgres,connection_percent,$CONN_PERCENT" >> "$METRICS_DIR/postgres_metrics.csv"
    echo "$TIMESTAMP,postgres,long_queries,$LONG_QUERIES" >> "$METRICS_DIR/postgres_metrics.csv"
    echo "$TIMESTAMP,postgres,cache_hit_ratio,$CACHE_HIT_RATIO" >> "$METRICS_DIR/postgres_metrics.csv"
    echo "$TIMESTAMP,postgres,index_usage,$INDEX_USAGE" >> "$METRICS_DIR/postgres_metrics.csv"

    log "PostgreSQL metrics - Size: $DB_SIZE, Connections: $ACTIVE_CONN/$MAX_CONN (${CONN_PERCENT}%), Cache hit: ${CACHE_HIT_RATIO}%, Index usage: ${INDEX_USAGE}%"
}

monitor_postgres_locks() {
    log "Checking PostgreSQL locks..."

    # Check for blocked queries
    BLOCKED_QUERIES=$(docker exec "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "
        SELECT count(*)
        FROM pg_stat_activity
        WHERE waiting = true OR wait_event IS NOT NULL;" 2>/dev/null || echo "0")

    if [ "$BLOCKED_QUERIES" -gt 0 ]; then
        alert "PostgreSQL has $BLOCKED_QUERIES blocked/waiting queries"
    fi

    # Check for deadlocks (from log)
    DEADLOCKS=$(docker exec "$POSTGRES_CONTAINER" psql \
        -U "${POSTGRES_USER:-drj}" \
        -d mem0 \
        -t -c "SELECT deadlocks FROM pg_stat_database WHERE datname = 'mem0';" 2>/dev/null || echo "0")

    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$TIMESTAMP,postgres,blocked_queries,$BLOCKED_QUERIES" >> "$METRICS_DIR/postgres_metrics.csv"
    echo "$TIMESTAMP,postgres,deadlocks,$DEADLOCKS" >> "$METRICS_DIR/postgres_metrics.csv"
}

# Neo4j monitoring functions
monitor_neo4j_performance() {
    log "Monitoring Neo4j performance..."

    if ! check_container "$NEO4J_CONTAINER"; then
        return 1
    fi

    # Get basic statistics
    NODE_COUNT=$(docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u neo4j -p "${NEO4J_PASSWORD}" \
        "MATCH (n) RETURN count(n) as node_count;" 2>/dev/null | tail -1 || echo "0")

    REL_COUNT=$(docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u neo4j -p "${NEO4J_PASSWORD}" \
        "MATCH ()-[r]-() RETURN count(r) as rel_count;" 2>/dev/null | tail -1 || echo "0")

    # Memory usage (if available)
    HEAP_USED=$(docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u neo4j -p "${NEO4J_PASSWORD}" \
        "CALL dbms.queryJmx('java.lang:type=Memory') YIELD attributes
         RETURN attributes.HeapMemoryUsage.used as heap_used;" 2>/dev/null | tail -1 || echo "0")

    # Store file sizes
    STORE_SIZE=$(docker exec "$NEO4J_CONTAINER" du -sb /data/databases 2>/dev/null | cut -f1 || echo "0")

    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$TIMESTAMP,neo4j,node_count,$NODE_COUNT" >> "$METRICS_DIR/neo4j_metrics.csv"
    echo "$TIMESTAMP,neo4j,relationship_count,$REL_COUNT" >> "$METRICS_DIR/neo4j_metrics.csv"
    echo "$TIMESTAMP,neo4j,heap_used,$HEAP_USED" >> "$METRICS_DIR/neo4j_metrics.csv"
    echo "$TIMESTAMP,neo4j,store_size,$STORE_SIZE" >> "$METRICS_DIR/neo4j_metrics.csv"

    log "Neo4j metrics - Nodes: $NODE_COUNT, Relationships: $REL_COUNT, Store size: $(echo $STORE_SIZE | numfmt --to=iec)"
}

# Container resource monitoring
monitor_container_resources() {
    log "Monitoring container resources..."

    # Get container stats
    CONTAINER_STATS=$(docker stats --no-stream --format "{{.Container}},{{.CPUPerc}},{{.MemPerc}},{{.MemUsage}}" \
        postgres-mem0 neo4j-mem0 mem0 openmemory-mcp 2>/dev/null || echo "")

    if [ -n "$CONTAINER_STATS" ]; then
        while IFS=',' read -r container cpu_percent mem_percent mem_usage; do
            # Remove % symbol and convert to integer
            cpu_num=$(echo "$cpu_percent" | sed 's/%//' | cut -d. -f1)
            mem_num=$(echo "$mem_percent" | sed 's/%//' | cut -d. -f1)

            # Check thresholds
            if [ "$cpu_num" -gt "$CPU_THRESHOLD" ]; then
                alert "Container $container CPU usage at $cpu_percent (threshold: ${CPU_THRESHOLD}%)"
            fi

            if [ "$mem_num" -gt "$MEMORY_THRESHOLD" ]; then
                alert "Container $container memory usage at $mem_percent (threshold: ${MEMORY_THRESHOLD}%)"
            fi

            TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
            echo "$TIMESTAMP,$container,cpu_percent,$cpu_num" >> "$METRICS_DIR/container_metrics.csv"
            echo "$TIMESTAMP,$container,memory_percent,$mem_num" >> "$METRICS_DIR/container_metrics.csv"
            echo "$TIMESTAMP,$container,memory_usage,$mem_usage" >> "$METRICS_DIR/container_metrics.csv"

        done <<< "$CONTAINER_STATS"
    fi
}

# Disk space monitoring
monitor_disk_space() {
    log "Monitoring disk space..."

    # Check data directory disk usage
    DISK_USAGE=$(df /home/drj/projects/mem0-stack/data | tail -1 | awk '{print $5}' | sed 's/%//')

    if [ "$DISK_USAGE" -gt "$DISK_THRESHOLD" ]; then
        alert "Data directory disk usage at ${DISK_USAGE}% (threshold: ${DISK_THRESHOLD}%)"
    fi

    # Check individual data directories
    POSTGRES_SIZE=$(du -sb /home/drj/projects/mem0-stack/data/postgres 2>/dev/null | cut -f1 || echo "0")
    NEO4J_SIZE=$(du -sb /home/drj/projects/mem0-stack/data/neo4j 2>/dev/null | cut -f1 || echo "0")

    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$TIMESTAMP,system,disk_usage_percent,$DISK_USAGE" >> "$METRICS_DIR/system_metrics.csv"
    echo "$TIMESTAMP,system,postgres_data_size,$POSTGRES_SIZE" >> "$METRICS_DIR/system_metrics.csv"
    echo "$TIMESTAMP,system,neo4j_data_size,$NEO4J_SIZE" >> "$METRICS_DIR/system_metrics.csv"

    log "Disk usage: ${DISK_USAGE}%, PostgreSQL data: $(echo $POSTGRES_SIZE | numfmt --to=iec), Neo4j data: $(echo $NEO4J_SIZE | numfmt --to=iec)"
}

# Application-specific monitoring
monitor_memory_operations() {
    log "Monitoring memory operations..."

    # Check memory API health
    if curl -s -f "http://localhost:8000/health" > /dev/null 2>&1; then
        MEM0_HEALTH="UP"
    else
        MEM0_HEALTH="DOWN"
        alert "mem0 API health check failed"
    fi

    # Check OpenMemory API health
    if curl -s -f "http://localhost:8765/health" > /dev/null 2>&1; then
        OPENMEMORY_HEALTH="UP"
    else
        OPENMEMORY_HEALTH="DOWN"
        alert "OpenMemory API health check failed"
    fi

    # Get memory count (if PostgreSQL is available)
    if check_container "$POSTGRES_CONTAINER"; then
        MEMORY_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql \
            -U "${POSTGRES_USER:-drj}" \
            -d mem0 \
            -t -c "SELECT count(*) FROM memories WHERE deleted_at IS NULL;" 2>/dev/null || echo "0")
    else
        MEMORY_COUNT="0"
    fi

    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$TIMESTAMP,application,mem0_health,$MEM0_HEALTH" >> "$METRICS_DIR/application_metrics.csv"
    echo "$TIMESTAMP,application,openmemory_health,$OPENMEMORY_HEALTH" >> "$METRICS_DIR/application_metrics.csv"
    echo "$TIMESTAMP,application,memory_count,$MEMORY_COUNT" >> "$METRICS_DIR/application_metrics.csv"

    log "Application health - mem0: $MEM0_HEALTH, OpenMemory: $OPENMEMORY_HEALTH, Memory count: $MEMORY_COUNT"
}

# Generate monitoring report
generate_monitoring_report() {
    REPORT_FILE="/home/drj/projects/mem0-stack/data/monitoring_report_$(date +%Y%m%d_%H%M%S).txt"

    cat > "$REPORT_FILE" << EOF
Database Monitoring Report - $(date)
=====================================

System Overview:
- Disk Usage: $(df -h /home/drj/projects/mem0-stack/data | tail -1)
- Container Status: $(docker ps --format "{{.Names}}: {{.Status}}" | grep -E "(postgres-mem0|neo4j-mem0|mem0|openmemory)")

Recent Alerts (last 24 hours):
$(tail -100 "$ALERT_LOG" 2>/dev/null | grep "$(date --date='24 hours ago' '+%Y-%m-%d')" || echo "No alerts")

Performance Summary:
- PostgreSQL: $(tail -1 "$METRICS_DIR/postgres_metrics.csv" 2>/dev/null | cut -d, -f4 || echo "No data") active connections
- Neo4j: $(tail -1 "$METRICS_DIR/neo4j_metrics.csv" 2>/dev/null | grep node_count | cut -d, -f4 || echo "No data") nodes
- Memory Operations: $(tail -1 "$METRICS_DIR/application_metrics.csv" 2>/dev/null | grep memory_count | cut -d, -f4 || echo "No data") memories

Last Updated: $(date)
EOF

    log "Monitoring report generated: $REPORT_FILE"
}

# Main monitoring function
main() {
    log "Starting database monitoring cycle..."

    # Load environment variables
    if [ -f .env ]; then
        source .env
    fi

    # Run all monitoring functions
    monitor_postgres_performance
    monitor_postgres_locks
    monitor_neo4j_performance
    monitor_container_resources
    monitor_disk_space
    monitor_memory_operations

    # Generate report if requested
    if [ "${1:-}" = "report" ]; then
        generate_monitoring_report
    fi

    log "Database monitoring cycle completed"
}

# Command line options
case "${1:-monitor}" in
    "postgres")
        monitor_postgres_performance
        monitor_postgres_locks
        ;;
    "neo4j")
        monitor_neo4j_performance
        ;;
    "resources")
        monitor_container_resources
        monitor_disk_space
        ;;
    "health")
        monitor_memory_operations
        ;;
    "report")
        generate_monitoring_report
        ;;
    "monitor"|*)
        main "$@"
        ;;
esac
