# mem0-Stack Rollback Procedures

## Overview

This document provides detailed rollback procedures for each optimization epic in the mem0-stack project. These procedures ensure system stability and provide clear recovery paths if optimizations cause issues.

## Rollback Triggers

### Automatic Rollback Conditions
- **Response Time Degradation**: > 200ms for memory operations (2x baseline)
- **Error Rate Increase**: > 1% error rate for memory operations
- **Resource Exhaustion**: > 90% memory utilization for any service
- **Service Unavailability**: Service down for > 30 seconds

### Manual Rollback Conditions
- **User-Reported Issues**: Autonomous AI agents reporting memory failures
- **Data Integrity Concerns**: Suspicious memory retrieval results
- **Performance Regression**: Sustained performance below baseline

## Epic 1: Memory System Reliability & Performance - Rollback Procedures

### 1.1 Multi-Layer Caching Rollback

**Rollback Trigger**: Cache hit ratio < 50% OR cache-related errors

**Quick Rollback (< 5 minutes)**:
```bash
# Disable caching layers
docker exec mem0 sed -i 's/ENABLE_CACHING=true/ENABLE_CACHING=false/g' /app/.env
docker exec openmemory-mcp sed -i 's/ENABLE_CACHING=true/ENABLE_CACHING=false/g' /usr/src/openmemory/.env
docker restart mem0 openmemory-mcp
```

**Full Rollback (< 15 minutes)**:
```bash
# Restore original configuration
git checkout HEAD~1 -- docker-compose.yml
git checkout HEAD~1 -- .env
docker-compose down
docker-compose up -d
```

### 1.2 Database Query Optimization Rollback

**Rollback Trigger**: Query response time > 100ms OR database errors

**PostgreSQL Index Rollback**:
```sql
-- Connect to postgres
docker exec -it postgres-mem0 psql -U $POSTGRES_USER -d mem0

-- Drop optimized indexes
DROP INDEX IF EXISTS idx_memory_vector_hnsw;
DROP INDEX IF EXISTS idx_memory_user_timestamp;
DROP INDEX IF EXISTS idx_memory_metadata_gin;

-- Restore original indexes
CREATE INDEX idx_memory_vector_original ON memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_memory_user_original ON memories (user_id);
```

**Neo4j Query Rollback**:
```cypher
// Connect to Neo4j
docker exec -it neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD

// Drop optimized indexes
DROP INDEX memory_user_idx IF EXISTS;
DROP INDEX memory_timestamp_idx IF EXISTS;

// Restore original structure
CREATE INDEX FOR (m:Memory) ON (m.id);
```

### 1.3 Connection Pool Optimization Rollback

**Rollback Trigger**: Connection pool exhaustion OR connection timeouts

**Quick Configuration Rollback**:
```bash
# Restore original connection settings
docker exec postgres-mem0 pg_ctl reload -D /var/lib/postgresql/data
docker restart neo4j-mem0
```

**Full Connection Pool Rollback**:
```bash
# Restore original docker-compose.yml
git checkout HEAD~1 -- docker-compose.yml
docker-compose down
docker-compose up -d postgres neo4j
```

## Epic 2: Intelligent Memory Management - Rollback Procedures

### 2.1 Memory Storage Logic Rollback

**Rollback Trigger**: Memory deduplication errors OR incorrect categorization

**Algorithm Rollback**:
```bash
# Restore original memory processing
docker exec mem0 cp /app/backup/memory_original.py /app/packages/mem0/memory/
docker restart mem0
```

**Data Cleanup**:
```bash
# Remove problematic memory entries
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "DELETE FROM memories WHERE created_at > '$(date -d '1 hour ago' '+%Y-%m-%d %H:%M:%S')';"
```

### 2.2 Context-Aware Retrieval Rollback

**Rollback Trigger**: Irrelevant search results OR search timeout

**Search Algorithm Rollback**:
```bash
# Restore original search implementation
docker exec mem0 cp /app/backup/search_original.py /app/packages/mem0/memory/
docker restart mem0
```

**Index Rollback**:
```sql
-- Restore original vector search indexes
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "
DROP INDEX IF EXISTS idx_memory_vector_hnsw;
CREATE INDEX idx_memory_vector_original ON memories USING ivfflat (embedding vector_cosine_ops);
"
```

## Epic 3: MCP Integration Optimization - Rollback Procedures

### 3.1 MCP Server Performance Rollback

**Rollback Trigger**: MCP connection failures OR timeout errors

**MCP Server Rollback**:
```bash
# Restore original MCP server implementation
git checkout HEAD~1 -- openmemory/api/app/mcp_server.py
docker restart openmemory-mcp
```

**Connection Configuration Rollback**:
```bash
# Restore original connection settings
docker exec openmemory-mcp sed -i 's/WORKERS=8/WORKERS=4/g' /usr/src/openmemory/.env
docker restart openmemory-mcp
```

### 3.2 Autonomous Operation Patterns Rollback

**Rollback Trigger**: Autonomous operation failures OR unexpected behavior

**Pattern Rollback**:
```bash
# Disable autonomous features
docker exec openmemory-mcp sed -i 's/AUTONOMOUS_MODE=true/AUTONOMOUS_MODE=false/g' /usr/src/openmemory/.env
docker restart openmemory-mcp
```

**Cursor Integration Rollback**:
```bash
# Restore original Cursor MCP configuration
cp ~/.cursor/mcp_settings_backup.json ~/.cursor/mcp_settings.json
# Restart Cursor IDE
```

## Epic 4: Production Hardening - Rollback Procedures

### 4.1 Monitoring Stack Rollback

**Rollback Trigger**: Monitoring system failures OR performance impact

**Monitoring Rollback**:
```bash
# Disable enhanced monitoring
docker-compose down prometheus grafana elasticsearch logstash kibana
# Restore original monitoring
git checkout HEAD~1 -- monitoring/
docker-compose up -d
```

### 4.2 Alerting System Rollback

**Rollback Trigger**: False alerts OR alert fatigue

**Alert Configuration Rollback**:
```bash
# Restore original alert rules
git checkout HEAD~1 -- monitoring/alert_rules.yml
docker restart prometheus alertmanager
```

## Database Backup and Recovery

### Pre-Optimization Backup Creation

**PostgreSQL Backup**:
```bash
# Create pre-optimization backup
docker exec postgres-mem0 pg_dump -U $POSTGRES_USER mem0 > backup/mem0_pre_optimization.sql
docker exec postgres-mem0 pg_dump -U $POSTGRES_USER -Fc mem0 > backup/mem0_pre_optimization.backup
```

**Neo4j Backup**:
```bash
# Create pre-optimization backup
docker exec neo4j-mem0 neo4j-admin database dump --database=neo4j --to-path=/backup/
cp -r data/neo4j backup/neo4j_pre_optimization/
```

### Database Recovery Procedures

**PostgreSQL Recovery**:
```bash
# Stop services
docker-compose stop mem0 openmemory-mcp

# Restore database
docker exec postgres-mem0 dropdb -U $POSTGRES_USER mem0
docker exec postgres-mem0 createdb -U $POSTGRES_USER mem0
docker exec -i postgres-mem0 psql -U $POSTGRES_USER mem0 < backup/mem0_pre_optimization.sql

# Restart services
docker-compose start mem0 openmemory-mcp
```

**Neo4j Recovery**:
```bash
# Stop services
docker-compose stop mem0 openmemory-mcp neo4j

# Restore data
rm -rf data/neo4j/*
cp -r backup/neo4j_pre_optimization/* data/neo4j/

# Restart services
docker-compose start neo4j
# Wait for Neo4j to be healthy
docker-compose start mem0 openmemory-mcp
```

## Emergency Response Procedures

### System-Wide Emergency Rollback

**When to Use**: Complete system failure or critical data integrity issues

**Full System Rollback**:
```bash
#!/bin/bash
# Emergency rollback script

echo "Starting emergency rollback..."

# Stop all services
docker-compose down

# Restore configurations
git checkout HEAD~1 -- docker-compose.yml
git checkout HEAD~1 -- .env
git checkout HEAD~1 -- openmemory/

# Restore databases
docker-compose up -d postgres neo4j
sleep 30

# Restore data if needed
if [ -f "backup/emergency_restore.flag" ]; then
    echo "Restoring emergency backup..."
    # PostgreSQL restore
    docker exec postgres-mem0 dropdb -U $POSTGRES_USER mem0
    docker exec postgres-mem0 createdb -U $POSTGRES_USER mem0
    docker exec -i postgres-mem0 psql -U $POSTGRES_USER mem0 < backup/mem0_emergency.sql

    # Neo4j restore
    docker-compose stop neo4j
    rm -rf data/neo4j/*
    cp -r backup/neo4j_emergency/* data/neo4j/
    docker-compose start neo4j
    sleep 30
fi

# Start services
docker-compose up -d

echo "Emergency rollback complete"
```

### Autonomous AI Operation Emergency Stop

**When to Use**: Autonomous AI agents causing system issues

**Emergency Stop Procedure**:
```bash
# Stop autonomous operations immediately
docker exec openmemory-mcp pkill -f "autonomous"
docker exec mem0 pkill -f "autonomous"

# Disable autonomous features
docker exec openmemory-mcp sed -i 's/AUTONOMOUS_MODE=true/AUTONOMOUS_MODE=false/g' /usr/src/openmemory/.env
docker exec mem0 sed -i 's/AUTONOMOUS_MODE=true/AUTONOMOUS_MODE=false/g' /app/.env

# Restart services in safe mode
docker restart openmemory-mcp mem0
```

## Recovery Validation

### Post-Rollback Validation Checklist

**Service Health Validation**:
```bash
# Test service endpoints
curl -f http://localhost:8000/health || echo "mem0 API failed"
curl -f http://localhost:8765/health || echo "MCP API failed"
curl -f http://localhost:3000 || echo "UI failed"

# Test database connections
docker exec postgres-mem0 pg_isready -U $POSTGRES_USER
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1"
```

**Performance Validation**:
```bash
# Test memory operations
curl -X POST -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test"}], "user_id": "test"}' \
  http://localhost:8000/memories

# Test search operations
curl -X POST -H "Content-Type: application/json" \
  -d '{"query": "test", "user_id": "test"}' \
  http://localhost:8000/search
```

**Data Integrity Validation**:
```bash
# Verify data consistency
docker exec postgres-mem0 psql -U $POSTGRES_USER -d mem0 -c "SELECT COUNT(*) FROM memories;"
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "MATCH (n:Memory) RETURN count(n)"
```

## Documentation and Communication

### Rollback Incident Report Template

```markdown
# Rollback Incident Report

**Date**: [DATE]
**Time**: [TIME]
**Epic**: [EPIC_NUMBER]
**Rollback Type**: [QUICK/FULL/EMERGENCY]

## Incident Details
- **Trigger**: [WHAT_CAUSED_ROLLBACK]
- **Impact**: [AFFECTED_SERVICES/USERS]
- **Detection**: [HOW_DETECTED]

## Rollback Actions Taken
- [LIST_OF_ACTIONS]
- [TIMELINE_OF_ACTIONS]

## Validation Results
- [SERVICE_STATUS]
- [PERFORMANCE_METRICS]
- [DATA_INTEGRITY_CHECK]

## Root Cause Analysis
- [WHAT_WENT_WRONG]
- [WHY_IT_HAPPENED]

## Prevention Measures
- [WHAT_WILL_PREVENT_RECURRENCE]
- [MONITORING_IMPROVEMENTS]
```

### Communication Plan

**Immediate Communication** (< 5 minutes):
- Update system status page
- Notify autonomous AI agents via status endpoint
- Log incident in monitoring system

**Follow-up Communication** (< 30 minutes):
- Complete incident report
- Update operational documentation
- Schedule post-mortem if needed

## Testing and Validation

### Rollback Procedure Testing

**Monthly Rollback Drills**:
```bash
# Test rollback procedures monthly
./scripts/test_rollback_procedures.sh

# Validate recovery times
./scripts/validate_recovery_times.sh

# Update procedures based on findings
./scripts/update_rollback_procedures.sh
```

**Automated Rollback Testing**:
```bash
# Automated rollback validation
crontab -l | grep -q "rollback_test" || echo "0 2 * * 1 /path/to/rollback_test.sh" | crontab -
```

---

**Document Version**: 1.0
**Last Updated**: January 11, 2025
**Next Review**: February 11, 2025
**Owner**: Winston (Architect)
**Approval**: Pending PO Review
