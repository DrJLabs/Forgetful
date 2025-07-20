# Complete mem0 Core Components Reset Strategy

## 📖 Overview

This document provides a comprehensive strategy for completely resetting the core mem0 components while preserving your enterprise-grade testing infrastructure, monitoring systems, and operational features. This reset is designed for scenarios requiring a complete fresh start of memory data without losing any of the sophisticated operational infrastructure you've built.

## 🎯 Reset Objectives

### **What Gets Reset (Core Components):**
- **mem0 API Server** (Port 8000): Complete application state and memory data
- **PostgreSQL with pgvector** (pg16): All vector embeddings, memory tables, and user data
- **Neo4j 5.26.4**: Graph relationships, entity connections, and graph data
- **OpenMemory MCP Server** (Port 8765): MCP protocol service state and cached data
- **OpenMemory UI** (Port 3000): React interface state and cached data

### **What Gets Preserved (Infrastructure):**
- **Testing Framework**: 100+ tests across pytest, Jest, React Testing Library, Playwright E2E
- **Monitoring Stack**: 12-service architecture with Prometheus, Grafana, Alertmanager, ELK, Jaeger
- **Operational Scripts**: 25+ automation scripts in `/scripts/` directory
- **Documentation**: 68+ files covering architecture, runbooks, testing strategies
- **CI/CD Pipeline**: GitHub Actions with 7 quality gates and automated workflows
- **Security Infrastructure**: SSL certificates, authentication systems, audit logging
- **Configuration Management**: Docker Compose, environment templates, Traefik routing

## 🏗️ System Architecture Understanding

### **Data Persistence Layer:**
```
PostgreSQL (pgvector)
├── Volume: ./data/postgres:/var/lib/postgresql/data
├── Optimized Config: shared_buffers=2GB, work_mem=256MB
├── Extensions: pgvector for embedding storage
└── Health Check: pg_isready

Neo4j 5.26.4
├── Volume: ./data/neo4j:/data
├── APOC Plugins: Enabled for data export/import
├── Memory Config: heap_max=4G, pagecache=2G
└── Health Check: HTTP endpoint on port 7474

mem0 Application Data
├── Volume: ./data/mem0/history:/app/history
├── SQLite History: Local transaction logging
└── Application State: Memory processing logs
```

### **Service Dependencies:**
```
┌─────────────────────────────────────────┐
│                 UI Layer                │
├─────────────────────────────────────────┤
│ OpenMemory UI (3000) ←→ OpenMemory MCP  │
│                        (8765)           │
├─────────────────────────────────────────┤
│            API Layer                    │
├─────────────────────────────────────────┤
│ mem0 API Server (8000) ←→ OpenMemory    │
│                         MCP (8765)      │
├─────────────────────────────────────────┤
│            Data Layer                   │
├─────────────────────────────────────────┤
│ PostgreSQL (5432) ←→ Neo4j (7687/7474)  │
└─────────────────────────────────────────┘
```

## 🔧 Reset Strategy Components

### **1. Comprehensive Backup System**

The reset strategy leverages your existing sophisticated backup infrastructure:

**PostgreSQL Backup:**
- Custom binary format for fast restore
- SQL format for portability and inspection
- Schema-only backup for structure recreation
- Automatic verification and integrity checks

**Neo4j Backup:**
- APOC Cypher export for complete data preservation
- Data directory backup for full system state
- GraphML export for external tool compatibility
- Transaction log preservation

**Application Data Backup:**
- mem0 history and state preservation
- Configuration file snapshots
- Environment variable backups
- Docker compose state capture

### **2. Service Management Strategy**

**Shutdown Sequence (Dependency-Aware):**
```bash
1. OpenMemory UI (Port 3000)        # Frontend interface
2. OpenMemory MCP (Port 8765)       # Protocol service
3. mem0 API Server (Port 8000)      # Core API
4. Neo4j (Ports 7687/7474)          # Graph database
5. PostgreSQL (Port 5432)           # Vector database
```

**Startup Sequence (Health-Check Driven):**
```bash
1. PostgreSQL + Neo4j (parallel)    # Databases first
2. mem0 API Server                  # Core service
3. OpenMemory MCP + UI (parallel)   # Interface services
```

### **3. Data Reset Procedures**

**PostgreSQL Reset:**
```sql
-- Terminate connections
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE datname = 'mem0' AND pid <> pg_backend_pid();

-- Drop and recreate database
DROP DATABASE IF EXISTS "mem0";
CREATE DATABASE "mem0";

-- Recreate pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
```

**Neo4j Reset:**
```bash
# Physical data directory reset
sudo rm -rf ./data/neo4j/*

# Service restart with clean state
docker-compose up -d neo4j

# Verification
MATCH (n) RETURN count(n) as node_count;
```

**mem0 Application Reset:**
```bash
# Clear history data
rm -rf ./data/mem0/history/*

# Recreate directory structure
mkdir -p ./data/mem0/history
```

## 🚀 Execution Strategy

### **Phase 1: Pre-Reset Preparation (5-10 minutes)**

1. **Environment Validation:**
   - Verify all services are running
   - Check disk space for backups
   - Validate environment variables
   - Confirm network connectivity

2. **Comprehensive Backup:**
   - PostgreSQL: Custom + SQL formats
   - Neo4j: Cypher export + data directory
   - Application data: History + configurations
   - Create restore inventory and metadata

3. **Testing Infrastructure Verification:**
   - Confirm test suites are intact
   - Verify monitoring dashboards accessible
   - Check operational scripts functionality

### **Phase 2: Core Reset Execution (10-15 minutes)**

1. **Service Shutdown:**
   - Graceful shutdown in dependency order
   - Health check confirmations
   - Resource cleanup verification

2. **Database Reset:**
   - PostgreSQL: Drop/recreate with pgvector
   - Neo4j: Data directory reset + restart
   - Application data: History cleanup

3. **Service Restart:**
   - Health-driven startup sequence
   - Connection verification
   - Service dependency confirmation

### **Phase 3: Verification & Validation (5-10 minutes)**

1. **Service Health Checks:**
   - Endpoint availability tests
   - Database connection verification
   - Memory operation functionality

2. **Integration Testing:**
   - Memory creation/retrieval tests
   - Cross-service communication verification
   - UI functionality confirmation

3. **Infrastructure Verification:**
   - Testing framework accessibility
   - Monitoring system functionality
   - Operational script execution

## 📋 Operational Procedures

### **Using the Reset Script**

The `reset_mem0_core.sh` script provides multiple execution modes:

```bash
# Full reset with backup (recommended)
./reset_mem0_core.sh

# Backup only (for safety)
./reset_mem0_core.sh --backup-only

# Dry run (see what would happen)
./reset_mem0_core.sh --dry-run

# Verification only
./reset_mem0_core.sh --verify-only

# Restore from backup
./reset_mem0_core.sh --restore /path/to/backup
```

### **Environment Requirements**

**System Requirements:**
- Docker and Docker Compose functional
- At least 10GB free disk space for backups
- Network connectivity to all service ports
- Appropriate user permissions for data directories

**Runtime Dependencies:**
- PostgreSQL container with pgvector
- Neo4j container with APOC plugins
- All service containers built and available
- Environment variables properly configured

### **Safety Mechanisms**

**Automatic Backup Creation:**
- Pre-reset backup always created
- Multiple backup formats for redundancy
- Backup verification and integrity checks
- Comprehensive restore procedures

**Rollback Capabilities:**
- Complete system restore from backup
- Service-specific rollback procedures
- Configuration restoration
- Health verification after rollback

**Error Handling:**
- Graceful failure handling at each step
- Detailed logging and error reporting
- Automatic cleanup on failure
- Safe exit with restoration options

## 🔍 Verification Procedures

### **Service Health Verification**

```bash
# API Endpoints
curl -f http://localhost:8000/health    # mem0 API
curl -f http://localhost:8765/health    # OpenMemory MCP
curl -f http://localhost:3000           # OpenMemory UI

# Database Connections
docker exec postgres-mem0 pg_isready -U drj
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1"
```

### **Memory Operations Testing**

```bash
# Create memory test
curl -X POST -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Reset verification test"}], "user_id": "reset_test"}' \
  http://localhost:8000/memories

# Search test
curl -X POST -H "Content-Type: application/json" \
  -d '{"query": "verification", "user_id": "reset_test"}' \
  http://localhost:8000/search
```

### **Infrastructure Verification**

```bash
# Test framework accessibility
python -m pytest --version
npm test --version

# Monitoring system check
curl -f http://localhost:9090/-/healthy  # Prometheus
curl -f http://localhost:3001/api/health # Grafana

# Operational scripts verification
./scripts/ci_health_check.sh --quick
./scripts/db_monitor.sh --status
```

## 📊 Post-Reset Validation

### **Data Verification**

1. **Empty State Confirmation:**
   - PostgreSQL: No memories table entries
   - Neo4j: Zero node count verification
   - Application: Clean history directories

2. **Service Integration:**
   - Cross-service communication tests
   - Memory creation and retrieval workflow
   - UI-to-API connectivity verification

3. **Performance Baseline:**
   - Response time measurements
   - Resource utilization checks
   - Database performance verification

### **Infrastructure Verification**

1. **Preserved Systems Check:**
   - All test suites executable
   - Monitoring dashboards accessible
   - Operational scripts functional
   - Documentation integrity maintained

2. **Configuration Verification:**
   - Environment variables correct
   - Service configurations intact
   - Network routing operational
   - Security settings preserved

## 🛡️ Recovery Procedures

### **Complete System Restore**

If the reset fails or issues are discovered:

```bash
# Restore from the automatically created backup
./reset_mem0_core.sh --restore /path/to/backup_directory

# Manual restore process
./scripts/db_restore.sh --date YYYYMMDD_HHMMSS
```

### **Partial Recovery**

For specific component issues:

```bash
# PostgreSQL only
docker exec -i postgres-mem0 pg_restore \
  -U drj -d mem0 --clean --if-exists < backup.backup

# Neo4j only
docker cp backup.cypher neo4j-mem0:/var/lib/neo4j/
docker exec neo4j-mem0 cypher-shell -f /var/lib/neo4j/backup.cypher
```

### **Emergency Procedures**

**If Services Won't Start:**
1. Check Docker system resources and clean if needed
2. Verify port availability and network configuration
3. Review service logs for specific error messages
4. Consider restoring from backup and debugging separately

**If Data Corruption Detected:**
1. Immediately stop all services
2. Restore from the most recent backup
3. Verify data integrity post-restore
4. Investigate root cause before attempting reset again

## 📈 Integration with Existing Infrastructure

### **Monitoring Integration**

The reset preserves all monitoring infrastructure:
- **Prometheus**: Continues collecting metrics
- **Grafana**: Dashboards remain accessible
- **Alertmanager**: Alert rules continue functioning
- **ELK Stack**: Log aggregation uninterrupted
- **Jaeger**: Tracing infrastructure preserved

### **Testing Integration**

All testing infrastructure remains intact:
- **pytest**: Backend API tests (100+ tests)
- **Jest**: JavaScript/TypeScript unit tests
- **React Testing Library**: UI component tests
- **Playwright**: End-to-end integration tests
- **CI/CD**: GitHub Actions workflows preserved

### **Operational Integration**

Operational scripts continue working:
- **Database maintenance**: `scripts/db_maintenance.sh`
- **Monitoring setup**: `scripts/start_monitoring.sh`
- **Health checks**: `scripts/ci_health_check.sh`
- **Backup procedures**: `scripts/db_backup.sh`
- **Security audits**: `scripts/security_audit.sh`

## 🎯 Success Criteria

### **Technical Success Indicators**

✅ **All core services running and healthy**
✅ **Database connectivity verified**
✅ **Memory operations functional**
✅ **UI accessibility confirmed**
✅ **Cross-service communication working**

### **Infrastructure Success Indicators**

✅ **Testing framework fully operational**
✅ **Monitoring dashboards accessible**
✅ **Operational scripts executable**
✅ **Documentation integrity maintained**
✅ **CI/CD pipeline functional**

### **Operational Success Indicators**

✅ **Backup created and verified**
✅ **Restore procedures tested**
✅ **Performance within baseline**
✅ **Security settings preserved**
✅ **Configuration integrity maintained**

## 📞 Support and Troubleshooting

### **Common Issues and Solutions**

**Service Startup Failures:**
- Check Docker system resources: `docker system df`
- Review service logs: `docker-compose logs [service]`
- Verify port availability: `netstat -tulpn | grep [port]`
- Check environment variables: `source .env && env | grep -E "(DATABASE|NEO4J|OPENAI)"`

**Database Connection Issues:**
- Verify containers are healthy: `docker-compose ps`
- Check network connectivity: `docker network ls`
- Review database logs: `docker-compose logs postgres neo4j`
- Test manual connections with provided verification commands

**Memory Operation Failures:**
- Verify API endpoint accessibility
- Check OpenAI API key configuration
- Review mem0 service logs for errors
- Test with simplified memory creation requests

### **Log Locations**

- **Reset Script Logs**: `./data/reset_YYYYMMDD_HHMMSS.log`
- **Service Logs**: `docker-compose logs [service_name]`
- **Database Logs**: Available through Docker logging
- **Application Logs**: Service-specific logging within containers

### **Emergency Contacts**

For critical issues:
1. **Immediate**: Use backup restore procedures
2. **Investigation**: Review logs and run verification tests
3. **Recovery**: Follow provided recovery procedures
4. **Documentation**: Update procedures based on lessons learned

---

## 🏁 Conclusion

This comprehensive reset strategy provides a robust, safe, and efficient method for completely resetting mem0 core components while preserving your sophisticated operational infrastructure. The strategy leverages existing backup systems, maintains infrastructure integrity, and provides multiple safety mechanisms to ensure successful execution and recovery capabilities.

The preservation of testing infrastructure, monitoring systems, and operational scripts ensures that your development and operational capabilities remain intact throughout the reset process, allowing for immediate productivity and continued system reliability.
