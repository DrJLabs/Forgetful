#!/bin/bash

# Database Maintenance Status Dashboard
# Shows current status of all maintenance activities

PROJECT_DIR="/home/drj/projects/mem0-stack"
METRICS_DIR="$PROJECT_DIR/data/metrics"

echo "==============================================="
echo "mem0-stack Database Maintenance Status"
echo "==============================================="
echo "Generated: $(date)"
echo

# Container Status
echo "=== Container Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}" | grep -E "(postgres-mem0|neo4j-mem0|mem0|openmemory)"
echo

# Disk Usage
echo "=== Disk Usage ==="
df -h "$PROJECT_DIR/data" | tail -1
echo "PostgreSQL data: $(du -sh $PROJECT_DIR/data/postgres 2>/dev/null | cut -f1 || echo 'N/A')"
echo "Neo4j data: $(du -sh $PROJECT_DIR/data/neo4j 2>/dev/null | cut -f1 || echo 'N/A')"
echo "Backups: $(du -sh $PROJECT_DIR/data/backups 2>/dev/null | cut -f1 || echo 'N/A')"
echo

# Recent Activity
echo "=== Recent Maintenance Activity ==="
echo "Last backup: $(ls -lt $PROJECT_DIR/data/backups/postgres/*.backup 2>/dev/null | head -1 | awk '{print $6, $7, $8}' || echo 'No backups found')"
echo "Last maintenance: $(tail -1 $PROJECT_DIR/data/maintenance.log 2>/dev/null | cut -d'] ' -f1 | tr -d '[' || echo 'Never')"
echo "Last monitoring: $(tail -1 $PROJECT_DIR/data/monitor.log 2>/dev/null | cut -d'] ' -f1 | tr -d '[' || echo 'Never')"
echo

# Recent Alerts
echo "=== Recent Alerts (Last 24 Hours) ==="
if [ -f "$PROJECT_DIR/data/alerts.log" ]; then
    TODAY=$(date +%Y-%m-%d)
    YESTERDAY=$(date --date='1 day ago' +%Y-%m-%d)
    grep -E "($TODAY|$YESTERDAY)" "$PROJECT_DIR/data/alerts.log" | tail -5 || echo "No recent alerts"
else
    echo "No alert log found"
fi
echo

# Performance Metrics (if available)
echo "=== Current Performance ==="
if [ -f "$METRICS_DIR/postgres_metrics.csv" ]; then
    LATEST_PG=$(tail -1 "$METRICS_DIR/postgres_metrics.csv" 2>/dev/null)
    echo "PostgreSQL connections: $(echo $LATEST_PG | grep active_connections | cut -d, -f4 || echo 'N/A')"
fi

if [ -f "$METRICS_DIR/neo4j_metrics.csv" ]; then
    LATEST_NEO4J=$(tail -1 "$METRICS_DIR/neo4j_metrics.csv" 2>/dev/null)
    echo "Neo4j nodes: $(echo $LATEST_NEO4J | grep node_count | cut -d, -f4 || echo 'N/A')"
fi

# Cron Job Status
echo
echo "=== Scheduled Maintenance ==="
echo "Cron jobs installed: $(crontab -l 2>/dev/null | grep -c mem0 || echo '0')"
echo

echo "==============================================="
echo "For detailed logs, check:"
echo "- Maintenance: $PROJECT_DIR/data/maintenance.log"
echo "- Monitoring: $PROJECT_DIR/data/monitor.log" 
echo "- Alerts: $PROJECT_DIR/data/alerts.log"
echo "==============================================="
