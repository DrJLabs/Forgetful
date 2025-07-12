# Database Maintenance Guide for mem0-stack

This guide documents the comprehensive database maintenance system implemented for the mem0-stack project, which manages both PostgreSQL (with pgvector) and Neo4j databases.

## 📋 **System Overview**

The mem0-stack uses a dual-database architecture:
- **PostgreSQL with pgvector**: Stores memory vectors and metadata
- **Neo4j**: Manages entity relationships and graph data
- **SQLite**: Local history tracking for mem0

## 🛠️ **Maintenance Components**

### **1. Backup System (`scripts/db_backup.sh`)**

**Features:**
- Automated daily backups of both PostgreSQL and Neo4j
- Multiple backup formats (custom binary + SQL for PostgreSQL)
- Backup verification and integrity checks
- 30-day retention policy with automatic cleanup
- Comprehensive logging and error handling

**Usage:**
```bash
# Manual backup
./scripts/db_backup.sh

# Check backup logs
tail -f data/backup.log
```

**Schedule:** Daily at 3:00 AM

### **2. Database Maintenance (`scripts/db_maintenance.sh`)**

**Features:**
- PostgreSQL VACUUM and ANALYZE operations
- Index maintenance and rebuilding
- Statistics updates
- Connection monitoring
- Neo4j store file analysis
- Performance optimization checks
- Resource usage monitoring

**Usage:**
```bash
# Full maintenance
./scripts/db_maintenance.sh

# Specific operations
./scripts/db_maintenance.sh vacuum    # PostgreSQL vacuum only
./scripts/db_maintenance.sh reindex   # Index rebuilding
./scripts/db_maintenance.sh stats     # Update statistics
./scripts/db_maintenance.sh health    # Health checks only
```

**Schedule:**
- Full maintenance: Daily at 2:00 AM
- Vacuum/Analyze: Every 6 hours
- Statistics update: Every 12 hours
- Index rebuild: Weekly on Sundays at 4:00 AM

### **3. Monitoring System (`scripts/db_monitor.sh`)**

**Features:**
- Real-time performance monitoring
- Resource usage tracking (CPU, memory, disk)
- Connection monitoring with alerting
- Long-running query detection
- Cache hit ratio analysis
- Index usage statistics
- Application health checks
- Automated alerting system

**Usage:**
```bash
# Full monitoring cycle
./scripts/db_monitor.sh

# Specific monitoring
./scripts/db_monitor.sh postgres    # PostgreSQL only
./scripts/db_monitor.sh neo4j       # Neo4j only
./scripts/db_monitor.sh resources   # System resources
./scripts/db_monitor.sh report      # Generate report
```

**Schedule:**
- Full monitoring: Every 5 minutes
- Health checks: Every 2 minutes
- Daily reports: 6:00 AM

### **4. Restore System (`scripts/db_restore.sh`)**

**Features:**
- Complete database restoration from backups
- Selective restore (PostgreSQL or Neo4j only)
- Pre-restore backup creation
- Automatic rollback on failure
- Integrity verification
- Service management during restore

**Usage:**
```bash
# List available backups
./scripts/db_restore.sh --list

# Restore from latest backup
./scripts/db_restore.sh latest

# Restore from specific backup
./scripts/db_restore.sh 20250109_030000

# PostgreSQL only restore
./scripts/db_restore.sh --postgres-only latest

# Force restore without confirmation
./scripts/db_restore.sh --force latest
```

### **5. Status Dashboard (`scripts/maintenance_status.sh`)**

**Features:**
- Container status overview
- Disk usage monitoring
- Recent maintenance activity
- Alert summary
- Performance metrics display
- Cron job status

**Usage:**
```bash
./scripts/maintenance_status.sh
```

## ⚙️ **Configuration**

### **Environment Variables**
The maintenance scripts use environment variables from your `.env` file:

```bash
# PostgreSQL Configuration
POSTGRES_USER=drj
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=postgres-mem0

# Neo4j Configuration
NEO4J_AUTH=neo4j/your_password
NEO4J_URI=bolt://neo4j-mem0:7687
```

### **Maintenance Configuration**
Customize settings in `maintenance_config.sh`:

```bash
# Backup settings
export BACKUP_RETENTION_DAYS=30
export BACKUP_VERIFY=true

# Monitoring thresholds
export CPU_THRESHOLD=80
export MEMORY_THRESHOLD=85
export DISK_THRESHOLD=85
export CONNECTION_THRESHOLD=80
export QUERY_TIME_THRESHOLD=30
```

## 📅 **Automated Schedule**

The system uses cron jobs for automation:

| Task | Frequency | Time | Purpose |
|------|-----------|------|---------|
| Health Checks | Every 2 minutes | - | Monitor service availability |
| Monitoring | Every 5 minutes | - | Performance and resource tracking |
| Vacuum/Analyze | Every 6 hours | - | PostgreSQL maintenance |
| Statistics Update | Every 12 hours | - | Query planner optimization |
| Full Maintenance | Daily | 2:00 AM | Comprehensive database maintenance |
| Backup | Daily | 3:00 AM | Full system backup |
| Index Rebuild | Weekly | Sunday 4:00 AM | Index maintenance |
| Reports | Daily | 6:00 AM | Generate monitoring reports |
| Log Cleanup | Monthly | 1st day 5:00 AM | Remove old logs and reports |

## 🔍 **Monitoring and Alerting**

### **Alert Conditions**
The system automatically alerts on:
- Container downtime
- High CPU usage (>80%)
- High memory usage (>85%)
- High disk usage (>85%)
- High connection usage (>80% of max)
- Long-running queries (>30 seconds)
- Blocked/waiting queries
- API health check failures

### **Metrics Collection**
All metrics are stored in CSV format under `data/metrics/`:
- `postgres_metrics.csv`: Database performance metrics
- `neo4j_metrics.csv`: Graph database metrics
- `container_metrics.csv`: Container resource usage
- `system_metrics.csv`: System-level metrics
- `application_metrics.csv`: Application health metrics

### **Log Files**
- `data/maintenance.log`: Maintenance activity log
- `data/monitor.log`: Monitoring activity log
- `data/alerts.log`: Alert notifications
- `data/backup.log`: Backup operation log
- `data/restore.log`: Restore operation log

## 📁 **Directory Structure**

```
mem0-stack/
├── scripts/
│   ├── db_backup.sh              # Backup system
│   ├── db_maintenance.sh         # Maintenance operations
│   ├── db_monitor.sh             # Monitoring system
│   ├── db_restore.sh             # Restore system
│   ├── maintenance_status.sh     # Status dashboard
│   └── setup_maintenance_cron.sh # Installation script
├── data/
│   ├── backups/
│   │   ├── postgres/             # PostgreSQL backups
│   │   └── neo4j/                # Neo4j backups
│   ├── metrics/                  # Performance metrics
│   ├── *.log                     # Log files
│   └── *_report_*.txt           # Generated reports
├── maintenance_config.sh         # Configuration file
└── DATABASE_MAINTENANCE_GUIDE.md # This guide
```

## 🚀 **Setup Instructions**

### **1. Install the Maintenance System**
```bash
./scripts/setup_maintenance_cron.sh
```

This will:
- Make scripts executable
- Install cron jobs
- Create necessary directories
- Set up logging
- Configure monitoring

### **2. Verify Installation**
```bash
# Check cron jobs
crontab -l

# Test scripts
./scripts/maintenance_status.sh
./scripts/db_monitor.sh health
```

### **3. Initial Backup**
```bash
# Create initial backup
./scripts/db_backup.sh

# Verify backup
ls -la data/backups/
```

## 📊 **Performance Optimization Features**

### **PostgreSQL Optimizations**
- **Vacuum Strategy**: Automated VACUUM ANALYZE every 6 hours
- **Index Maintenance**: Weekly REINDEX for large tables (>100MB)
- **Statistics**: Regular ANALYZE to keep query planner updated
- **Connection Monitoring**: Track and alert on connection usage
- **Cache Optimization**: Monitor buffer cache hit ratios

### **Neo4j Optimizations**
- **Memory Management**: Monitor heap usage and page cache
- **Transaction Logs**: Automatic rotation (1GB size limit)
- **Store Compaction**: Monitor store file sizes
- **Index Monitoring**: Track constraint and index usage

### **System Optimizations**
- **Resource Limits**: Proper container resource allocation
- **Disk Monitoring**: Track data directory growth
- **Performance Metrics**: Comprehensive metric collection
- **Alerting**: Proactive issue detection

## 🔧 **Troubleshooting**

### **Common Issues**

#### **1. Backup Failures**
```bash
# Check backup logs
tail -f data/backup.log

# Test database connectivity
docker exec postgres-mem0 pg_isready -U drj -d mem0
docker exec neo4j-mem0 wget -O /dev/null http://localhost:7474/
```

#### **2. High Resource Usage**
```bash
# Check container resources
docker stats

# Check disk usage
df -h data/

# Review maintenance schedule
crontab -l
```

#### **3. Monitoring Alerts**
```bash
# Check recent alerts
tail -20 data/alerts.log

# Review specific metrics
tail -20 data/metrics/postgres_metrics.csv
```

### **Manual Interventions**

#### **Emergency Maintenance**
```bash
# Stop automatic maintenance
sudo service cron stop

# Run manual maintenance
./scripts/db_maintenance.sh

# Restart automation
sudo service cron start
```

#### **Space Recovery**
```bash
# Clean old backups
find data/backups -mtime +30 -delete

# Clean old logs
find data -name "*.log" -mtime +7 -exec truncate -s 0 {} \;

# PostgreSQL space recovery
./scripts/db_maintenance.sh vacuum
```

## 📈 **Best Practices**

### **1. Regular Monitoring**
- Check status dashboard daily: `./scripts/maintenance_status.sh`
- Review alert logs weekly: `tail -50 data/alerts.log`
- Monitor disk usage: Keep below 80%

### **2. Backup Management**
- Test restore procedures monthly
- Verify backup integrity regularly
- Keep offsite backups for critical data

### **3. Performance Tuning**
- Monitor cache hit ratios (target >95%)
- Track index usage (target >80%)
- Watch for long-running queries

### **4. Capacity Planning**
- Monitor data growth trends
- Plan for storage expansion
- Scale container resources as needed

## 🆘 **Emergency Procedures**

### **Database Corruption**
1. Stop all services: `docker-compose stop`
2. Restore from latest backup: `./scripts/db_restore.sh latest`
3. Verify integrity: `./scripts/db_maintenance.sh health`
4. Start services: `docker-compose up -d`

### **Disk Space Crisis**
1. Check usage: `df -h data/`
2. Clean old backups: `find data/backups -mtime +7 -delete`
3. Emergency vacuum: `./scripts/db_maintenance.sh vacuum`
4. Monitor recovery: `./scripts/db_monitor.sh resources`

### **Performance Emergency**
1. Check current load: `docker stats`
2. Identify long queries: `./scripts/db_monitor.sh postgres`
3. Emergency maintenance: `./scripts/db_maintenance.sh`
4. Scale resources if needed

## 📞 **Support and Maintenance**

### **Maintenance Schedule Review**
The maintenance schedule should be reviewed quarterly and adjusted based on:
- Data growth patterns
- Performance requirements
- Resource availability
- Business requirements

### **System Updates**
When updating the mem0-stack:
1. Create full backup: `./scripts/db_backup.sh`
2. Test maintenance scripts
3. Update monitoring thresholds if needed
4. Verify cron jobs: `crontab -l`

---

## 🎯 **Summary**

This comprehensive maintenance system provides:

✅ **Automated backup and restore capabilities**
✅ **Proactive monitoring and alerting**
✅ **Performance optimization**
✅ **Capacity planning support**
✅ **Emergency recovery procedures**
✅ **Comprehensive logging and reporting**

The system is designed to maintain optimal performance of your mem0-stack deployment while providing the tools and information needed for effective database administration.

For questions or issues, refer to the log files in the `data/` directory or run the status dashboard for current system information.