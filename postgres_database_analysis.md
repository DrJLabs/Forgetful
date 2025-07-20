# PostgreSQL Database Component Analysis - mem0-stack

## Overview

The mem0-stack project uses PostgreSQL 16 with the pgvector extension as its primary database component. The database supports both the legacy mem0 memory system and the modern OpenMemory API architecture.

## Database Configuration

### Connection Settings
- **Host**: postgres-mem0 (Docker container)
- **Port**: 5432
- **Database Name**: mem0
- **User**: drj (superuser with full privileges)
- **Image**: pgvector/pgvector:pg16

### Performance Configuration
The PostgreSQL instance is configured with optimized settings for memory operations:

| Setting | Value | Purpose |
|---------|-------|---------|
| `shared_buffers` | 2GB | Shared memory for data caching |
| `work_mem` | 256MB | Memory per query operation |
| `maintenance_work_mem` | 1GB | Memory for maintenance operations |
| `effective_cache_size` | 6GB | Planner's cache size assumption |
| `max_connections` | 100 | Maximum concurrent connections |
| `checkpoint_completion_target` | 0.9 | Checkpoint performance tuning |
| `random_page_cost` | 1.1 | Cost estimation for random I/O |
| `seq_page_cost` | 1 | Cost estimation for sequential I/O |
| `max_wal_size` | 4GB | Write-ahead log size limit |
| `min_wal_size` | 1GB | Minimum WAL size |
| `wal_buffers` | 64MB | WAL buffer size |
| `default_statistics_target` | 100 | Query planner statistics |

### Extensions
- **plpgsql** (v1.0): PostgreSQL procedural language
- **vector** (v0.8.0): pgvector extension for vector similarity search

## Database Schema

### Core Tables

#### 1. `users` (14 records)
**Purpose**: Stores user account information
```sql
- id (UUID, Primary Key)
- user_id (VARCHAR, Unique, Indexed) - Human-readable user identifier
- name (VARCHAR, Nullable, Indexed)
- email (VARCHAR, Unique, Nullable, Indexed)
- metadata (JSON) - Additional user data
- created_at (TIMESTAMP, Indexed)
- updated_at (TIMESTAMP)
```

#### 2. `apps` (16 records)
**Purpose**: Stores application contexts for memory organization
```sql
- id (UUID, Primary Key)
- owner_id (UUID, Foreign Key → users.id, Indexed)
- name (VARCHAR, Indexed)
- description (VARCHAR, Nullable)
- metadata (JSON) - Application configuration
- is_active (BOOLEAN, Indexed, Default: true)
- created_at (TIMESTAMP, Indexed)
- updated_at (TIMESTAMP)
```
**Constraints**: Unique constraint on (owner_id, name)

#### 3. `memories` (147 records)
**Purpose**: Main memory storage with vector embeddings
```sql
- id (UUID, Primary Key, Default: gen_random_uuid())
- user_id (UUID, Foreign Key → users.id, Indexed)
- app_id (UUID, Foreign Key → apps.id, Indexed)
- content (TEXT, Not Null) - The actual memory content
- vector (VECTOR(1536), Nullable) - pgvector embedding for similarity search
- metadata (JSONB, Default: '{}') - Structured memory metadata
- state (VARCHAR(20), Default: 'active') - Memory state management
- created_at (TIMESTAMP, Default: CURRENT_TIMESTAMP)
- updated_at (TIMESTAMP, Default: CURRENT_TIMESTAMP)
- archived_at (TIMESTAMP, Nullable)
- deleted_at (TIMESTAMP, Nullable)
- payload (JSONB, Default: '{}') - Legacy compatibility field
```
**Indexes**:
- `memories_vector_idx` (IVFFLAT) - Vector similarity search
- Composite indexes for user+state, app+state, user+app combinations

### Legacy Compatibility Tables

#### 4. `mem0_memories` (1 record)
**Purpose**: Legacy mem0 memory format for backward compatibility
```sql
- id (UUID, Primary Key)
- vector (VECTOR(1536)) - pgvector embedding
- payload (JSONB) - Unstructured memory data
```

#### 5. `openmemory`
**Purpose**: Additional OpenMemory-specific storage
```sql
- id (UUID, Primary Key)
- vector (VECTOR(1536)) - pgvector embedding
- payload (JSONB) - Memory data
```

### Support Tables

#### 6. `categories`
**Purpose**: Memory categorization system
```sql
- id (UUID, Primary Key)
- name (VARCHAR, Unique, Indexed)
- description (VARCHAR, Nullable)
- created_at (TIMESTAMP, Indexed)
- updated_at (TIMESTAMP)
```

#### 7. `memory_categories`
**Purpose**: Many-to-many relationship between memories and categories
```sql
- memory_id (UUID, Foreign Key → memories.id, Primary Key)
- category_id (UUID, Foreign Key → categories.id, Primary Key)
```

### Access Control & Auditing

#### 8. `access_controls`
**Purpose**: Fine-grained access control system
```sql
- id (UUID, Primary Key)
- subject_type (VARCHAR, Indexed) - Type of entity requesting access
- subject_id (UUID, Nullable, Indexed) - ID of requesting entity
- object_type (VARCHAR, Indexed) - Type of resource being accessed
- object_id (UUID, Nullable, Indexed) - ID of resource
- effect (VARCHAR, Indexed) - Allow/Deny
- created_at (TIMESTAMP, Indexed)
```

#### 9. `memory_access_logs`
**Purpose**: Audit trail for memory access
```sql
- id (UUID, Primary Key)
- memory_id (UUID, Foreign Key → memories.id, Indexed)
- app_id (UUID, Foreign Key → apps.id, Indexed)
- accessed_at (TIMESTAMP, Indexed)
- access_type (VARCHAR, Indexed) - Type of access (read, write, delete)
- metadata (JSON) - Additional access context
```

#### 10. `memory_status_history`
**Purpose**: Tracks state changes in memories
```sql
- id (UUID, Primary Key)
- memory_id (UUID, Foreign Key → memories.id, Indexed)
- changed_by (UUID, Foreign Key → users.id, Indexed)
- old_state (MEMORYSTATE ENUM) - Previous state
- new_state (MEMORYSTATE ENUM, Indexed) - New state
- changed_at (TIMESTAMP, Indexed)
```

### Administrative Tables

#### 11. `archive_policies`
**Purpose**: Automated memory archival rules
```sql
- id (UUID, Primary Key)
- criteria_type (VARCHAR, Indexed) - Type of archival criteria
- criteria_id (UUID, Nullable, Indexed) - Specific criteria ID
- days_to_archive (INTEGER) - Days before archival
- created_at (TIMESTAMP, Indexed)
```

#### 12. `configs`
**Purpose**: Application configuration storage
```sql
- id (UUID, Primary Key)
- key (VARCHAR, Unique, Indexed) - Configuration key
- value (JSON) - Configuration value
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

#### 13. `user_id_mapping`
**Purpose**: Maps string user IDs to UUID format
```sql
- id (INTEGER, Primary Key, Auto-increment)
- string_id (VARCHAR(255), Unique, Indexed) - Original string identifier
- uuid_id (UUID, Unique, Indexed) - Generated UUID
- created_at (TIMESTAMP, Default: now())
```

### Migration Support

#### 14. `mem0migrations`
**Purpose**: Tracks database migration state
- Used by Alembic for version control

## Database Users and Permissions

### Primary User: `drj`
- **Role**: Superuser
- **Privileges**: 
  - Can create roles (rolcreaterole: true)
  - Can create databases (rolcreatedb: true)
  - Can login (rolcanlogin: true)
  - Full superuser privileges (rolsuper: true)

### System Roles
Standard PostgreSQL system roles are present with default permissions for monitoring, administration, and security.

## Data Volume Analysis

- **Total Memories**: 147 records
- **Users**: 14 accounts
- **Apps**: 16 applications
- **Legacy mem0_memories**: 1 record

## Key Features

### Vector Search Capabilities
- **pgvector Extension**: Enables similarity search on memory embeddings
- **Vector Dimensions**: 1536 (compatible with OpenAI embeddings)
- **Index Type**: IVFFLAT for efficient similarity queries

### Multi-Schema Support
- **Modern Schema**: OpenMemory API tables with full relational structure
- **Legacy Schema**: mem0_memories for backward compatibility
- **Synchronization**: Triggers maintain data consistency between schemas

### Memory State Management
Supported memory states (ENUM):
- `active`: Normal operational state
- `paused`: Temporarily disabled
- `archived`: Long-term storage
- `deleted`: Soft deletion

### Audit Trail
Complete tracking of:
- Memory access patterns
- State change history
- User activity logs

## Performance Optimizations

### Indexing Strategy
- **Primary Keys**: UUID-based for distributed systems
- **Composite Indexes**: Optimized for common query patterns
- **Vector Index**: IVFFLAT for similarity search performance
- **Foreign Key Indexes**: Ensures efficient joins

### Memory Configuration
- High shared buffer allocation (2GB) for data caching
- Large work memory (256MB) for complex queries
- Optimized checkpoint settings for write performance

## Backup and Migration

### Alembic Integration
- Version-controlled schema migrations
- Environment-specific migration paths
- Support for both SQLite (testing) and PostgreSQL (production)

### Data Consistency
- Foreign key constraints ensure referential integrity
- Triggers maintain synchronization between legacy and modern schemas
- Soft deletion preserves data history

## Monitoring and Maintenance

### Health Checks
- Container health check via `pg_isready`
- Connection pooling with reasonable limits
- Resource limits: 4 CPU cores, 8GB RAM

### Logging and Metrics
- Query performance statistics
- Connection monitoring
- Vector search performance tracking

This PostgreSQL implementation provides a robust foundation for the mem0-stack's memory management capabilities, with strong performance characteristics, comprehensive audit trails, and support for both legacy and modern API patterns. 