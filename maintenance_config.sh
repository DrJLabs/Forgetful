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
