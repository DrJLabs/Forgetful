#!/bin/bash

# Setup script for automated database maintenance
# Configures cron jobs for backup, maintenance, and monitoring

set -euo pipefail

SCRIPT_DIR="/home/drj/projects/mem0-stack/scripts"
PROJECT_DIR="/home/drj/projects/mem0-stack"

# Make scripts executable
chmod +x "$SCRIPT_DIR/db_backup.sh"
chmod +x "$SCRIPT_DIR/db_maintenance.sh"
chmod +x "$SCRIPT_DIR/db_monitor.sh"

echo "Setting up database maintenance automation..."

# Create cron jobs file
CRON_FILE="/tmp/mem0_maintenance_cron"

cat > "$CRON_FILE" << 'EOF'
# mem0-stack Database Maintenance Cron Jobs
# Generated by setup_maintenance_cron.sh

# Environment
PATH=/usr/local/bin:/usr/bin:/bin
SHELL=/bin/bash

# Change to project directory for all jobs
# This ensures .env file and relative paths work correctly

# Database Monitoring - Every 5 minutes
*/5 * * * * cd /home/drj/projects/mem0-stack && ./scripts/db_monitor.sh >/dev/null 2>&1

# Health Checks - Every 2 minutes
*/2 * * * * cd /home/drj/projects/mem0-stack && ./scripts/db_monitor.sh health >/dev/null 2>&1

# Vacuum and analyze - Every 6 hours
0 */6 * * * cd /home/drj/projects/mem0-stack && ./scripts/db_maintenance.sh vacuum >/dev/null 2>&1

# Update statistics - Every 12 hours
0 */12 * * * cd /home/drj/projects/mem0-stack && ./scripts/db_maintenance.sh stats >/dev/null 2>&1

# Full maintenance - Daily at 2 AM
0 2 * * * cd /home/drj/projects/mem0-stack && ./scripts/db_maintenance.sh >/dev/null 2>&1

# Database backup - Daily at 3 AM
0 3 * * * cd /home/drj/projects/mem0-stack && ./scripts/db_backup.sh >/dev/null 2>&1

# Weekly full reindex - Sundays at 4 AM
0 4 * * 0 cd /home/drj/projects/mem0-stack && ./scripts/db_maintenance.sh reindex >/dev/null 2>&1

# Generate daily monitoring report - At 6 AM
0 6 * * * cd /home/drj/projects/mem0-stack && ./scripts/db_monitor.sh report >/dev/null 2>&1

# Cleanup old logs and reports - Monthly on 1st day at 5 AM
0 5 1 * * cd /home/drj/projects/mem0-stack && find ./data -name "*.log" -mtime +30 -delete && find ./data -name "*_report_*.txt" -mtime +30 -delete >/dev/null 2>&1

EOF

# Install cron jobs
echo "Installing cron jobs..."
crontab "$CRON_FILE"

# Clean up
rm "$CRON_FILE"

# Create maintenance configuration file
cat > "$PROJECT_DIR/maintenance_config.sh" << 'EOF'
#!/bin/bash
# Database Maintenance Configuration for mem0-stack

# Backup Configuration
export BACKUP_RETENTION_DAYS=30
export BACKUP_VERIFY=true
export BACKUP_COMPRESS=true

# Maintenance Configuration
export VACUUM_THRESHOLD_MB=100
export STATS_AGE_HOURS=24
export REINDEX_THRESHOLD_MB=100

# Monitoring Configuration
export CPU_THRESHOLD=80
export MEMORY_THRESHOLD=85
export DISK_THRESHOLD=85
export CONNECTION_THRESHOLD=80
export QUERY_TIME_THRESHOLD=30

# Notification Configuration (optional)
export ALERT_EMAIL=""
export SLACK_WEBHOOK=""

# PostgreSQL Configuration
export POSTGRES_CONTAINER="postgres-mem0"
export POSTGRES_USER="drj"
export POSTGRES_DB="mem0"

# Neo4j Configuration
export NEO4J_CONTAINER="neo4j-mem0"
export NEO4J_USERNAME="neo4j"

echo "Maintenance configuration loaded"
EOF

chmod +x "$PROJECT_DIR/maintenance_config.sh"

# Create maintenance log directory with proper permissions
mkdir -p "$PROJECT_DIR/data/"{backups,metrics}
mkdir -p "$PROJECT_DIR/data/backups/"{postgres,neo4j}

# Create initial log files
touch "$PROJECT_DIR/data/maintenance.log"
touch "$PROJECT_DIR/data/monitor.log"
touch "$PROJECT_DIR/data/alerts.log"

# Set proper permissions
chmod 755 "$PROJECT_DIR/data"
chmod 644 "$PROJECT_DIR/data"/*.log

echo "Creating maintenance status dashboard..."

# Create a simple status dashboard script
cat > "$SCRIPT_DIR/maintenance_status.sh" << 'EOF'
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
EOF

chmod +x "$SCRIPT_DIR/maintenance_status.sh"

echo
echo "✅ Database maintenance automation setup completed!"
echo
echo "📋 Summary:"
echo "   - Backup: Daily at 3 AM (30-day retention)"
echo "   - Maintenance: Daily at 2 AM"
echo "   - Monitoring: Every 5 minutes"
echo "   - Health checks: Every 2 minutes"
echo "   - Vacuum: Every 6 hours"
echo "   - Statistics: Every 12 hours"
echo "   - Reindex: Weekly on Sundays"
echo "   - Reports: Daily at 6 AM"
echo
echo "📁 Files created:"
echo "   - $SCRIPT_DIR/db_backup.sh"
echo "   - $SCRIPT_DIR/db_maintenance.sh"
echo "   - $SCRIPT_DIR/db_monitor.sh"
echo "   - $SCRIPT_DIR/maintenance_status.sh"
echo "   - $PROJECT_DIR/maintenance_config.sh"
echo
echo "🔧 Usage:"
echo "   - Check status: ./scripts/maintenance_status.sh"
echo "   - Manual backup: ./scripts/db_backup.sh"
echo "   - Manual maintenance: ./scripts/db_maintenance.sh"
echo "   - Manual monitoring: ./scripts/db_monitor.sh"
echo
echo "📊 View cron jobs: crontab -l"
echo "📈 Monitor logs: tail -f data/maintenance.log"
echo "🚨 Check alerts: tail -f data/alerts.log"
echo
echo "⚠️  Note: Ensure containers are running before maintenance tasks execute"
