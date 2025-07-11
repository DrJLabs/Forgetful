# mem0-Stack Operational Runbooks

## Overview

This document provides operational procedures for managing and troubleshooting the mem0-stack system after optimization implementations. These runbooks support autonomous AI operations and provide clear escalation paths for issues.

## Quick Reference

### Emergency Contacts
- **System Owner**: Winston (Architect)
- **Primary On-Call**: [TBD]
- **Secondary On-Call**: [TBD]
- **Escalation**: [TBD]

### Critical Service URLs
- **mem0 API**: http://localhost:8000 (Production: mem0.drjlabs.com)
- **OpenMemory MCP**: http://localhost:8765
- **OpenMemory UI**: http://localhost:3000 (Production: memory.drjlabs.com)
- **Neo4j Browser**: http://localhost:7474 (Production: neo4j.drjlabs.com)
- **Monitoring**: [Grafana/Prometheus URLs]

### Critical Thresholds
- **Response Time**: > 100ms requires investigation
- **Error Rate**: > 1% triggers alerts
- **Memory Usage**: > 80% requires action
- **CPU Usage**: > 70% sustained for 5 minutes

## Service Management

### 1. Service Health Monitoring

#### Health Check Procedures

**Quick Health Check**:
```bash
#!/bin/bash
# health_check.sh

echo "=== mem0-Stack Health Check ==="
echo "Timestamp: $(date)"
echo

# Service availability
echo "Service Availability:"
curl -s -o /dev/null -w "mem0 API: %{http_code} (%{time_total}s)\n" http://localhost:8000/health
curl -s -o /dev/null -w "MCP API: %{http_code} (%{time_total}s)\n" http://localhost:8765/docs
curl -s -o /dev/null -w "UI: %{http_code} (%{time_total}s)\n" http://localhost:3000/

# Database connectivity
echo -e "\nDatabase Connectivity:"
docker exec postgres-mem0 pg_isready -U $POSTGRES_USER && echo "PostgreSQL: OK" || echo "PostgreSQL: FAILED"
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1" > /dev/null 2>&1 && echo "Neo4j: OK" || echo "Neo4j: FAILED"

# Resource usage
echo -e "\nResource Usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "mem0|postgres|neo4j|openmemory"
```

**Detailed Health Assessment**:
```bash
#!/bin/bash
# detailed_health_check.sh

# Run basic health check
./health_check.sh

# Performance metrics
echo -e "\n=== Performance Metrics ==="
curl -s -w "Memory Create: %{time_total}s\n" -X POST -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "health check"}], "user_id": "health"}' \
  http://localhost:8000/memories -o /dev/null

curl -s -w "Memory Search: %{time_total}s\n" -X POST -H "Content-Type: application/json" \
  -d '{"query": "health", "user_id": "health"}' \
  http://localhost:8000/search -o /dev/null

# Database performance
echo -e "\nDatabase Performance:"
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT count(*) as memory_count FROM memories;"
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "MATCH (n:Memory) RETURN count(n) as memory_count"

# Disk usage
echo -e "\nDisk Usage:"
docker exec postgres-mem0 df -h /var/lib/postgresql/data
docker exec neo4j-mem0 df -h /data
```

#### Automated Health Monitoring

**Monitoring Script** (runs every 5 minutes):
```bash
#!/bin/bash
# automated_health_monitor.sh

LOG_FILE="/var/log/mem0-health.log"
ALERT_THRESHOLD=3

check_service() {
    local service=$1
    local url=$2
    local timeout=5
    
    if curl -s -f --max-time $timeout "$url" > /dev/null 2>&1; then
        echo "$(date): $service OK" >> $LOG_FILE
        return 0
    else
        echo "$(date): $service FAILED" >> $LOG_FILE
        return 1
    fi
}

# Check all services
failed_services=0

check_service "mem0" "http://localhost:8000/health" || ((failed_services++))
check_service "mcp" "http://localhost:8765/docs" || ((failed_services++))
check_service "ui" "http://localhost:3000" || ((failed_services++))

# Alert if threshold exceeded
if [ $failed_services -ge $ALERT_THRESHOLD ]; then
    echo "$(date): ALERT - $failed_services services failed" >> $LOG_FILE
    # Send alert (implement notification system)
    # ./send_alert.sh "mem0-stack" "$failed_services services failed"
fi

# Cleanup old logs (keep last 7 days)
find /var/log -name "mem0-health.log" -mtime +7 -delete
```

### 2. Performance Troubleshooting

#### High Response Time Investigation

**When**: Response times > 100ms sustained for 5 minutes

**Investigation Steps**:
1. **Check System Resources**:
   ```bash
   # CPU and memory usage
   docker stats --no-stream | grep -E "mem0|postgres|neo4j|openmemory"
   
   # Check for resource contention
   docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
   ```

2. **Analyze Database Performance**:
   ```bash
   # PostgreSQL slow queries
   docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
   
   # Neo4j performance
   docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "CALL dbms.listQueries() YIELD query, elapsedTimeMillis WHERE elapsedTimeMillis > 1000 RETURN query, elapsedTimeMillis"
   ```

3. **Check Cache Performance**:
   ```bash
   # Cache hit ratios
   docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio FROM pg_statio_user_tables;"
   ```

4. **Network Analysis**:
   ```bash
   # Check network latency between services
   docker exec mem0 ping -c 3 postgres-mem0
   docker exec mem0 ping -c 3 neo4j-mem0
   ```

**Resolution Actions**:
- **High CPU**: Scale resources or optimize queries
- **High Memory**: Check for memory leaks, restart services if needed
- **Slow Queries**: Optimize indexes, update statistics
- **Network Issues**: Check Docker network configuration

#### High Error Rate Investigation

**When**: Error rate > 1% for 5 minutes

**Investigation Steps**:
1. **Check Error Logs**:
   ```bash
   # Service logs
   docker logs mem0 --tail 100 | grep -i error
   docker logs openmemory-mcp --tail 100 | grep -i error
   
   # Database logs
   docker exec postgres-mem0 tail -100 /var/log/postgresql/postgresql.log
   docker logs neo4j-mem0 --tail 100 | grep -i error
   ```

2. **Analyze Error Patterns**:
   ```bash
   # Common error patterns
   docker logs mem0 --since="1h" | grep -i "error\|exception\|failed" | sort | uniq -c | sort -nr
   ```

3. **Check External Dependencies**:
   ```bash
   # OpenAI API connectivity
   curl -s -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models > /dev/null && echo "OpenAI: OK" || echo "OpenAI: FAILED"
   ```

**Resolution Actions**:
- **API Errors**: Check external service status, verify API keys
- **Database Errors**: Check connections, disk space, corruption
- **Memory Errors**: Restart services, check for memory leaks
- **Network Errors**: Verify service connectivity

### 3. Database Management

#### PostgreSQL Operations

**Database Maintenance**:
```bash
#!/bin/bash
# postgres_maintenance.sh

echo "Starting PostgreSQL maintenance..."

# Update statistics
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "ANALYZE;"

# Vacuum operations
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "VACUUM ANALYZE;"

# Reindex if needed
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "REINDEX DATABASE mem0;"

# Check for bloat
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT schemaname, tablename, n_dead_tup, n_live_tup, ROUND(n_dead_tup::float / (n_dead_tup + n_live_tup) * 100, 2) as dead_percentage FROM pg_stat_user_tables WHERE n_dead_tup > 0 ORDER BY dead_percentage DESC;"

echo "PostgreSQL maintenance completed"
```

**Performance Monitoring**:
```bash
#!/bin/bash
# postgres_performance.sh

echo "=== PostgreSQL Performance Report ==="
echo "Timestamp: $(date)"

# Connection stats
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';"

# Cache hit ratio
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio FROM pg_statio_user_tables;"

# Top queries by time
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5;"

# Database size
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT pg_size_pretty(pg_database_size('mem0')) as database_size;"

# Table sizes
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(tablename::regclass) DESC;"
```

#### Neo4j Operations

**Database Maintenance**:
```bash
#!/bin/bash
# neo4j_maintenance.sh

echo "Starting Neo4j maintenance..."

# Check database consistency
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "CALL db.checkConsistency()"

# Update statistics
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "CALL db.resampleIndex('memory_user_idx')"

# Check memory usage
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "CALL dbms.listPools() YIELD poolName, used, total WHERE used > 0 RETURN poolName, used, total"

echo "Neo4j maintenance completed"
```

**Performance Monitoring**:
```bash
#!/bin/bash
# neo4j_performance.sh

echo "=== Neo4j Performance Report ==="
echo "Timestamp: $(date)"

# Active queries
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "CALL dbms.listQueries() YIELD query, elapsedTimeMillis, status RETURN query, elapsedTimeMillis, status"

# Node and relationship counts
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "MATCH (n) RETURN count(n) as node_count"
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "MATCH ()-[r]->() RETURN count(r) as relationship_count"

# Memory usage
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "CALL dbms.listPools() YIELD poolName, used, total WHERE poolName CONTAINS 'heap' RETURN poolName, used, total"

# Database size
docker exec neo4j-mem0 du -sh /data/databases/neo4j
```

### 4. Autonomous AI Operations Management

#### MCP Server Operations

**MCP Server Health**:
```bash
#!/bin/bash
# mcp_health.sh

echo "=== MCP Server Health Check ==="

# Check MCP server status
curl -s http://localhost:8765/docs > /dev/null && echo "MCP Server: OK" || echo "MCP Server: FAILED"

# Check worker processes
docker exec openmemory-mcp ps aux | grep uvicorn

# Check memory usage
docker exec openmemory-mcp cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable"

# Check active connections
docker exec openmemory-mcp ss -tuln | grep 8765
```

**MCP Performance Monitoring**:
```bash
#!/bin/bash
# mcp_performance.sh

echo "=== MCP Performance Report ==="

# Response time testing
curl -s -w "MCP Response Time: %{time_total}s\n" http://localhost:8765/docs -o /dev/null

# Worker utilization
docker exec openmemory-mcp top -b -n 1 | grep uvicorn

# Connection pool status
docker exec openmemory-mcp cat /proc/net/sockstat | grep TCP
```

#### Autonomous Operation Monitoring

**Autonomous Agent Health**:
```bash
#!/bin/bash
# autonomous_health.sh

echo "=== Autonomous AI Operations Health ==="

# Check for stuck operations
docker exec openmemory-mcp ps aux | grep -E "autonomous|agent" | grep -v grep

# Memory operation success rate
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT COUNT(*) as total_operations, SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_operations FROM operation_log WHERE created_at > NOW() - INTERVAL '1 hour';"

# Check for error patterns
docker logs openmemory-mcp --since="1h" | grep -i "autonomous\|agent" | grep -i error | wc -l
```

### 5. Backup and Recovery Operations

#### Backup Procedures

**Daily Backup Script**:
```bash
#!/bin/bash
# daily_backup.sh

BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

echo "Starting daily backup to $BACKUP_DIR..."

# PostgreSQL backup
docker exec postgres-mem0 pg_dump -U $POSTGRES_USER -Fc mem0 > $BACKUP_DIR/mem0_$(date +%Y%m%d_%H%M%S).backup
docker exec postgres-mem0 pg_dump -U $POSTGRES_USER mem0 > $BACKUP_DIR/mem0_$(date +%Y%m%d_%H%M%S).sql

# Neo4j backup
docker exec neo4j-mem0 neo4j-admin database dump --database=neo4j --to-path=/backup/
cp /var/lib/docker/volumes/mem0-stack_neo4j-data/_data/databases/neo4j/neo4j.db $BACKUP_DIR/

# Configuration backup
cp -r .env docker-compose.yml openmemory/ $BACKUP_DIR/

# Cleanup old backups (keep 30 days)
find /backup -type d -name "????????" -mtime +30 -exec rm -rf {} \;

echo "Daily backup completed"
```

**Emergency Backup Script**:
```bash
#!/bin/bash
# emergency_backup.sh

BACKUP_DIR="/backup/emergency_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "Starting emergency backup to $BACKUP_DIR..."

# Quick database dumps
docker exec postgres-mem0 pg_dump -U $POSTGRES_USER -Fc mem0 > $BACKUP_DIR/mem0_emergency.backup
docker exec neo4j-mem0 neo4j-admin database dump --database=neo4j --to-path=$BACKUP_DIR/

# Configuration snapshot
cp -r .env docker-compose.yml openmemory/ $BACKUP_DIR/

# Create restore flag
touch $BACKUP_DIR/emergency_restore.flag

echo "Emergency backup completed: $BACKUP_DIR"
```

#### Recovery Procedures

**Database Recovery**:
```bash
#!/bin/bash
# database_recovery.sh

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

echo "Starting database recovery from $BACKUP_FILE..."

# Stop services
docker-compose stop mem0 openmemory-mcp

# PostgreSQL recovery
docker exec postgres-mem0 dropdb -U $POSTGRES_USER mem0
docker exec postgres-mem0 createdb -U $POSTGRES_USER mem0
docker exec -i postgres-mem0 pg_restore -U $POSTGRES_USER -d mem0 < $BACKUP_FILE

# Neo4j recovery (if needed)
# docker-compose stop neo4j
# rm -rf data/neo4j/*
# cp -r $BACKUP_DIR/neo4j/* data/neo4j/
# docker-compose start neo4j

# Start services
docker-compose start mem0 openmemory-mcp

echo "Database recovery completed"
```

### 6. Monitoring and Alerting

#### Custom Metrics Collection

**System Metrics Script**:
```bash
#!/bin/bash
# collect_metrics.sh

METRICS_FILE="/var/log/mem0-metrics.log"
TIMESTAMP=$(date +%s)

# Service response times
MEM0_RESPONSE=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:8000/health)
MCP_RESPONSE=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:8765/docs)

# Resource usage
MEM0_CPU=$(docker stats --no-stream --format "{{.CPUPerc}}" mem0 | sed 's/%//')
MEM0_MEM=$(docker stats --no-stream --format "{{.MemPerc}}" mem0 | sed 's/%//')
POSTGRES_CPU=$(docker stats --no-stream --format "{{.CPUPerc}}" postgres-mem0 | sed 's/%//')
NEO4J_CPU=$(docker stats --no-stream --format "{{.CPUPerc}}" neo4j-mem0 | sed 's/%//')

# Database metrics
MEMORY_COUNT=$(docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -t -c "SELECT count(*) FROM memories;" | tr -d ' ')
ACTIVE_CONNECTIONS=$(docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" | tr -d ' ')

# Log metrics
echo "$TIMESTAMP,mem0_response_time,$MEM0_RESPONSE" >> $METRICS_FILE
echo "$TIMESTAMP,mcp_response_time,$MCP_RESPONSE" >> $METRICS_FILE
echo "$TIMESTAMP,mem0_cpu,$MEM0_CPU" >> $METRICS_FILE
echo "$TIMESTAMP,mem0_memory,$MEM0_MEM" >> $METRICS_FILE
echo "$TIMESTAMP,postgres_cpu,$POSTGRES_CPU" >> $METRICS_FILE
echo "$TIMESTAMP,neo4j_cpu,$NEO4J_CPU" >> $METRICS_FILE
echo "$TIMESTAMP,memory_count,$MEMORY_COUNT" >> $METRICS_FILE
echo "$TIMESTAMP,active_connections,$ACTIVE_CONNECTIONS" >> $METRICS_FILE
```

#### Alert Rules

**Performance Alerts**:
```bash
#!/bin/bash
# check_performance_alerts.sh

ALERT_LOG="/var/log/mem0-alerts.log"

# Check response times
MEM0_RESPONSE=$(curl -s -w "%{time_total}" -o /dev/null http://localhost:8000/health)
if (( $(echo "$MEM0_RESPONSE > 0.1" | bc -l) )); then
    echo "$(date): ALERT - mem0 response time: ${MEM0_RESPONSE}s" >> $ALERT_LOG
    # Send notification
fi

# Check CPU usage
MEM0_CPU=$(docker stats --no-stream --format "{{.CPUPerc}}" mem0 | sed 's/%//')
if (( $(echo "$MEM0_CPU > 70" | bc -l) )); then
    echo "$(date): ALERT - mem0 CPU usage: ${MEM0_CPU}%" >> $ALERT_LOG
    # Send notification
fi

# Check memory usage
MEM0_MEM=$(docker stats --no-stream --format "{{.MemPerc}}" mem0 | sed 's/%//')
if (( $(echo "$MEM0_MEM > 80" | bc -l) )); then
    echo "$(date): ALERT - mem0 memory usage: ${MEM0_MEM}%" >> $ALERT_LOG
    # Send notification
fi

# Check error rates
ERROR_COUNT=$(docker logs mem0 --since="5m" | grep -i error | wc -l)
if [ $ERROR_COUNT -gt 10 ]; then
    echo "$(date): ALERT - Error count in last 5 minutes: $ERROR_COUNT" >> $ALERT_LOG
    # Send notification
fi
```

### 7. Troubleshooting Guide

#### Common Issues and Solutions

**Issue**: mem0 service won't start
**Symptoms**: Container keeps restarting, connection errors
**Investigation**:
```bash
docker logs mem0 --tail 50
docker exec postgres-mem0 pg_isready -U $POSTGRES_USER
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1"
```
**Solution**: Check database connectivity, verify environment variables

**Issue**: High memory usage
**Symptoms**: OOM errors, slow performance
**Investigation**:
```bash
docker stats --no-stream
docker exec mem0 cat /proc/meminfo
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT * FROM pg_stat_activity;"
```
**Solution**: Restart services, optimize queries, increase memory limits

**Issue**: MCP connection failures
**Symptoms**: Cursor IDE can't connect, timeout errors
**Investigation**:
```bash
docker logs openmemory-mcp --tail 50
curl -v http://localhost:8765/docs
docker exec openmemory-mcp ps aux | grep uvicorn
```
**Solution**: Restart MCP server, check network configuration, verify Cursor settings

**Issue**: Slow query performance
**Symptoms**: High response times, timeout errors
**Investigation**:
```bash
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "CALL db.indexes()"
```
**Solution**: Optimize indexes, update statistics, analyze query plans

### 8. Maintenance Schedules

#### Daily Tasks
- Run health checks
- Collect performance metrics
- Review error logs
- Check backup completion

#### Weekly Tasks
- Database maintenance (vacuum, analyze)
- Review performance trends
- Update documentation
- Test rollback procedures

#### Monthly Tasks
- Full system backup
- Security updates
- Performance optimization review
- Disaster recovery testing

## Emergency Procedures

### System Down Emergency

**Immediate Actions**:
1. Check service status: `docker-compose ps`
2. Review logs: `docker-compose logs --tail 100`
3. Attempt restart: `docker-compose restart`
4. If restart fails: `docker-compose down && docker-compose up -d`

### Data Corruption Emergency

**Immediate Actions**:
1. Stop all services: `docker-compose stop`
2. Create emergency backup: `./emergency_backup.sh`
3. Assess corruption extent
4. Restore from backup if needed: `./database_recovery.sh`

### Security Incident

**Immediate Actions**:
1. Stop exposed services
2. Review access logs
3. Change API keys and passwords
4. Update security configurations
5. Restart services with new credentials

---

**Document Version**: 1.0  
**Last Updated**: January 11, 2025  
**Next Review**: February 11, 2025  
**Owner**: Winston (Architect)  
**Approval**: Pending PO Review 