# Mem0-Stack Brownfield Architecture Document

## Introduction
This document captures the CURRENT STATE of the mem0-stack codebase, including technical debt, workarounds, and real-world patterns. It serves as a reference for AI agents working on enhancements to this personal memory layer system for Large Language Models (LLMs).

The mem0-stack provides a comprehensive memory management solution with OpenMemory (private, portable, open-source memory layer) and the core mem0 library, supporting multi-level memory capabilities with vector storage, graph relationships, and MCP (Model Context Protocol) integration.

### Document Scope
Comprehensive documentation of the entire mem0-stack system architecture, services, and operational patterns.

### Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-01-07 | 1.0 | Initial brownfield analysis | Mary (Business Analyst) |

## Quick Reference - Key Files and Entry Points

### Critical Files for Understanding the System
- **Main Docker Orchestration**: `docker-compose.yml` (5 services: mem0, postgres, neo4j, openmemory-mcp, openmemory-ui)
- **Core mem0 API**: `mem0/server/main.py` (REST API for memory operations)
- **OpenMemory MCP API**: `openmemory/api/main.py` (FastAPI with MCP server integration)
- **OpenMemory UI**: `openmemory/ui/app/layout.tsx` (Next.js frontend)
- **Database Models**: `openmemory/api/app/models.py` (SQLAlchemy models with comprehensive schema)
- **MCP Server**: `openmemory/api/app/mcp_server.py` (18KB implementation)
- **Database Config**: `openmemory/api/app/database.py` (SQLAlchemy setup with fallback to SQLite)

### Key Configuration Files
- **Environment Examples**: `openmemory/api/.env.example`, `openmemory/ui/.env.example`
- **Dependencies**: `openmemory/api/requirements.txt`, `openmemory/ui/package.json`
- **Build Automation**: `openmemory/Makefile` (comprehensive build/dev commands)

### Operational Scripts
- **Database Maintenance**: `scripts/db_maintenance.sh` (354 lines of PostgreSQL/Neo4j maintenance)
- **Database Monitoring**: `scripts/db_monitor.sh` (real-time monitoring)
- **Database Backup**: `scripts/db_backup.sh` (automated backup procedures)

## High Level Architecture

### Technical Summary
The mem0-stack implements a sophisticated multi-service architecture with strong emphasis on performance optimization and operational reliability. The system architecture is well-structured with clear separation of concerns, but shows signs of rapid development with some inconsistencies in patterns between services.

**Architecture Strengths:**
- Comprehensive resource management with Docker limits and health checks
- Production-ready database configurations with optimized parameters
- Robust operational tooling for maintenance and monitoring
- Clear separation between core memory system and user-facing OpenMemory

**Technical Debt Areas:**
- MCP protocol integration required multiple fixes (see `MCP_FIX_SUMMARY.md`)
- Database connection handling uses different patterns between services
- Environment variable management is inconsistent across services

### Actual Tech Stack (from requirements.txt/package.json)
| Category | Technology | Version | Notes |
|----------|------------|---------|--------|
| **Backend Core** | Python | 3.9+ | FastAPI-based services |
| **API Framework** | FastAPI | >=0.68.0 | Main API framework |
| **Web Server** | Uvicorn | >=0.15.0 | ASGI server with 4 workers |
| **Database ORM** | SQLAlchemy | >=1.4.0 | Complex schema with relationships |
| **Vector Database** | pgvector | pg16 | PostgreSQL with vector extensions |
| **Graph Database** | Neo4j | 5.26.4 | With APOC plugins enabled |
| **Memory System** | mem0ai | >=0.1.92 | Core memory management |
| **Frontend** | Next.js | 15.2.4 | React-based UI |
| **React** | React | 19.1.0 | Latest version |
| **UI Library** | Radix UI | Multiple | Comprehensive component library |
| **Styling** | Tailwind CSS | 3.4.17 | Utility-first CSS |
| **State Management** | Redux Toolkit | 2.8.2 | Client-side state |
| **Package Manager** | pnpm | 10.5.2 | Frontend dependency management |
| **MCP Protocol** | mcp[cli] | >=1.3.0 | Model Context Protocol |
| **LLM Integration** | OpenAI | >=1.40.0 | Primary LLM provider |
| **Containerization** | Docker | - | Multi-service orchestration |
| **Reverse Proxy** | Traefik | - | Production routing |

### Repository Structure Reality Check
- **Type**: Monorepo with clear service boundaries
- **Package Manager**: pnpm (frontend), pip (backend)
- **Build System**: Docker Compose + Makefiles
- **Notable**: Sophisticated resource management with CPU/memory limits per service

## Source Tree and Module Organization

### Project Structure (Actual)
```
mem0-stack/
├── mem0/                           # Core mem0 library and server
│   ├── server/main.py             # REST API (236 lines, comprehensive)
│   ├── mem0/                      # Python package
│   │   ├── client/                # Client library
│   │   ├── configs/               # Configuration management
│   │   ├── embeddings/            # Embedding providers
│   │   ├── llms/                  # LLM integrations
│   │   ├── memory/                # Core memory logic
│   │   ├── vector_stores/         # Vector database integrations
│   │   └── graphs/                # Graph database logic
│   ├── docs/                      # Extensive documentation
│   ├── tests/                     # Test suites
│   └── examples/                  # Usage examples
├── openmemory/                    # OpenMemory application
│   ├── api/                       # FastAPI backend
│   │   ├── app/
│   │   │   ├── models.py          # Database models (234 lines, complex)
│   │   │   ├── mcp_server.py      # MCP implementation (443 lines)
│   │   │   ├── database.py        # DB config with SQLite fallback
│   │   │   └── routers/           # API endpoints
│   │   ├── alembic/               # Database migrations
│   │   └── requirements.txt       # 20 dependencies
│   ├── ui/                        # Next.js frontend
│   │   ├── app/                   # App Router structure
│   │   │   ├── memories/          # Memory management UI
│   │   │   ├── apps/              # App management
│   │   │   └── settings/          # Configuration UI
│   │   ├── components/            # React components
│   │   │   ├── ui/                # 50+ Radix UI components
│   │   │   └── shared/            # Custom components
│   │   ├── hooks/                 # React hooks
│   │   └── store/                 # Redux store
│   └── Makefile                   # Build automation (53 lines)
├── scripts/                       # Operational scripts
│   ├── db_maintenance.sh          # 354 lines of DB maintenance
│   ├── db_monitor.sh              # Real-time monitoring
│   ├── db_backup.sh               # Automated backups
│   └── db_restore.sh              # Disaster recovery
├── data/                          # Persistent data volumes
│   ├── postgres/                  # PostgreSQL data
│   ├── neo4j/                     # Neo4j data
│   └── mem0/                      # mem0 history
└── docker-compose.yml             # Multi-service orchestration
```

### Key Modules and Their Purpose
- **mem0 Core**: `mem0/server/main.py` - REST API for memory operations, 236 lines with comprehensive endpoints
- **OpenMemory MCP**: `openmemory/api/app/mcp_server.py` - 443 lines of MCP protocol implementation
- **Database Models**: `openmemory/api/app/models.py` - 234 lines with User, App, Memory, Category models plus audit tables
- **Memory Management**: `openmemory/ui/app/memories/` - React components for memory CRUD operations
- **Authentication**: Environment-based user management (no traditional auth system)
- **Vector Storage**: pgvector integration with optimized PostgreSQL configuration
- **Graph Storage**: Neo4j with APOC plugins for relationship management

## Data Models and APIs

### Data Models
The system implements a comprehensive relational model with audit trails:

**Core Models** (see `openmemory/api/app/models.py`):
- **User Model**: UUID-based with user_id string, metadata JSON field
- **App Model**: Multi-tenant application structure with owner relationships
- **Memory Model**: Core memory storage with vector field, metadata, and state management
- **Category Model**: Automatic categorization with many-to-many relationships

**Audit Models**:
- **MemoryStatusHistory**: Tracks all memory state changes
- **MemoryAccessLog**: Logs all memory access events
- **AccessControl**: Fine-grained access control system
- **ArchivePolicy**: Automated archiving based on criteria

**Notable Technical Debt**:
- Vector field stored as String rather than proper vector type
- Metadata stored as JSON with column name aliasing (`metadata_` -> `metadata`)
- Complex indexing strategy that may need optimization

### API Specifications
**mem0 Core API** (port 8000):
- **Base URL**: `http://localhost:8000`
- **Endpoints**: `/memories`, `/search`, `/configure`, `/health`
- **OpenAPI**: Auto-generated documentation at `/docs`

**OpenMemory MCP API** (port 8765):
- **Base URL**: `http://localhost:8765`
- **MCP Endpoint**: `/mcp/<client>/<transport>/<user_id>`
- **REST API**: Full CRUD operations for memories, apps, stats
- **OpenAPI**: Available at `/docs`

**OpenMemory UI** (port 3000):
- **Base URL**: `http://localhost:3000`
- **Type**: Next.js App Router with client-side routing
- **State**: Redux Toolkit for global state management

## Technical Debt and Known Issues

### Critical Technical Debt

1. **MCP Protocol Implementation**:
   - Location: `openmemory/api/app/mcp_server.py`
   - Issue: Required multiple fixes for Cursor integration (see `MCP_FIX_SUMMARY.md`)
   - Impact: MCP server was "stuck at loading tools" initially
   - Resolution: Created dual implementation (HTTP/SSE + stdio-based)

2. **Database Connection Patterns**:
   - Location: `openmemory/api/app/database.py`
   - Issue: Inconsistent connection handling between services
   - Pattern: Uses SQLite fallback but primary config expects PostgreSQL
   - Impact: Potential production issues if DATABASE_URL misconfigured

3. **Environment Variable Management**:
   - Issue: Different env var patterns across services
   - mem0 server: Direct os.environ.get with defaults
   - OpenMemory: .env file loading with validation
   - Impact: Deployment complexity

4. **Vector Storage Implementation**:
   - Location: `openmemory/api/app/models.py` line ~73
   - Issue: Vector field stored as String type instead of proper vector type
   - Impact: Potential performance issues with large vector datasets

### Workarounds and Gotchas

1. **PostgreSQL Configuration**:
   - **Hardcoded Optimizations**: `docker-compose.yml` includes specific PostgreSQL tuning
   - **Resource Limits**: Each service has explicit CPU/memory limits
   - **Connection Pooling**: Max connections set to 100 (may need adjustment under load)

2. **Neo4j Memory Management**:
   - **Heap Size**: Fixed at 4GB max (NEO4J_server_memory_heap_max__size=4G)
   - **Page Cache**: 2GB allocated (NEO4J_server_memory_pagecache_size=2G)
   - **APOC Plugins**: Enabled with unrestricted procedures

3. **Docker Volume Mounts**:
   - **Development**: `./openmemory/api:/usr/src/openmemory` for hot reload
   - **Production**: Uses named volumes for data persistence
   - **Gotcha**: Data directories must exist before container start

4. **Frontend Development**:
   - **Package Manager**: Must use pnpm (specified in packageManager field)
   - **Build Dependencies**: Requires specific build dependencies for `@parcel/watcher`, `sharp`
   - **Environment**: NEXT_PUBLIC_* variables must be set at build time

## Integration Points and External Dependencies

### External Services
| Service | Purpose | Integration Type | Key Files |
|---------|---------|------------------|-----------|
| **OpenAI** | LLM & Embeddings | REST API | `mem0/server/main.py`, configured via OPENAI_API_KEY |
| **PostgreSQL** | Vector Storage | Direct Connection | pgvector extension, optimized configuration |
| **Neo4j** | Graph Storage | Bolt Protocol | APOC plugins, relationship management |

### Internal Integration Points
- **mem0 ↔ OpenMemory**: Separate services, no direct integration
- **Frontend ↔ MCP API**: REST API calls via axios (`axios@1.10.0`)
- **MCP Protocol**: Dual implementation (HTTP/SSE + stdio)
- **Database Migrations**: Alembic for schema management

### Production Deployment (Traefik Labels)
```yaml
# Actual production routing configuration
mem0.drjlabs.com → mem0:8000
neo4j.drjlabs.com → neo4j:7474
memory.drjlabs.com → openmemory-ui:3000
```

## Development and Deployment

### Local Development Setup
**Prerequisites**:
- Docker and Docker Compose
- Python 3.9+ (for backend development)
- Node.js (for frontend development)
- OpenAI API Key

**Actual Setup Steps**:
1. Clone repository
2. Set environment variables:
   ```bash
   # Copy example files
   cp openmemory/api/.env.example openmemory/api/.env
   cp openmemory/ui/.env.example openmemory/ui/.env
   # Or use Makefile
   make env
   ```
3. Start services:
   ```bash
   make build && make up
   ```

**Known Setup Issues**:
- UI may not start on first run - requires manual `cd ui && pnpm install && pnpm dev`
- Database initialization requires containers to be healthy before dependent services start
- MCP configuration requires specific environment variables for Cursor integration

### Build and Deployment Process
- **Build Command**: `make build` (docker compose build)
- **Development**: `make up` (with hot reload via volume mounts)
- **Production**: Uses Traefik labels for SSL termination and routing
- **Database Migrations**: `make migrate` (alembic upgrade head)

### Resource Management (Production)
```yaml
# Actual resource limits from docker-compose.yml
mem0: 4.0 CPU, 4GB memory
postgres: 4.0 CPU, 8GB memory (4GB reserved)
neo4j: 4.0 CPU, 8GB memory (4GB reserved)
openmemory-mcp: 2.0 CPU, 1GB memory
openmemory-ui: 1.0 CPU, 512MB memory
```

## Testing Reality

### Current Test Coverage
- **mem0 Core**: Comprehensive test suite in `mem0/tests/`
- **OpenMemory API**: Basic pytest setup (`pytest>=7.0.0`)
- **OpenMemory UI**: No test configuration found
- **Integration Tests**: Limited, mostly manual testing

### Running Tests
```bash
# mem0 tests
cd mem0 && python -m pytest

# OpenMemory API tests
cd openmemory/api && pytest

# Test cleanup
make test-clean  # Run tests and clean up volumes
```

### Testing Gaps
- **Frontend Tests**: No Jest/React Testing Library setup
- **End-to-End**: No Playwright/Cypress configuration
- **Integration**: Limited testing of service interactions
- **MCP Protocol**: Manual testing via Cursor integration

## Operational Monitoring and Maintenance

### Database Maintenance (scripts/db_maintenance.sh)
**Automated Tasks**:
- **VACUUM ANALYZE**: PostgreSQL maintenance with size tracking
- **REINDEX**: Automatic reindexing of large tables (>100MB)
- **Statistics Update**: Table statistics refresh
- **Connection Monitoring**: Active connection tracking
- **Neo4j Health**: Store file size monitoring, constraint validation

### Health Checks
**Container Health**:
- **PostgreSQL**: `pg_isready` check every 5 seconds
- **Neo4j**: HTTP endpoint check at port 7474
- **Services**: Built-in health check endpoints

**Monitoring Scripts**:
- **Real-time**: `scripts/db_monitor.sh` (353 lines)
- **Maintenance**: `scripts/db_maintenance.sh` (354 lines)
- **Backup**: `scripts/db_backup.sh` (automated backup procedures)

### Production Considerations
- **Log Management**: Centralized logging via Docker
- **Backup Strategy**: Automated daily backups with retention
- **Performance**: Optimized PostgreSQL and Neo4j configurations
- **Security**: Traefik SSL termination, network isolation

## Known Limitations and Future Improvements

### Current Limitations
1. **Authentication**: Basic environment-based user management
2. **Scaling**: Single-instance deployment pattern
3. **Monitoring**: Limited application-level metrics
4. **Testing**: Insufficient test coverage for UI components

### Performance Bottlenecks
1. **Vector Operations**: String-based vector storage may impact performance
2. **Database Connections**: Fixed connection pool sizes
3. **Memory Usage**: Neo4j memory configuration may need tuning under load

### Recommended Improvements
1. **Implement proper authentication system**
2. **Add comprehensive frontend testing**
3. **Optimize vector storage implementation**
4. **Add application-level monitoring and metrics**
5. **Implement horizontal scaling patterns**

## Appendix - Useful Commands and Scripts

### Development Commands
```bash
# Environment setup
make env                    # Copy .env.example files
make build                  # Build all containers
make up                     # Start all services
make down                   # Stop and clean up

# Database operations
make migrate                # Run database migrations
make shell                  # Open shell in API container
make logs                   # View container logs

# Frontend development
make ui-dev                 # Start frontend in development mode
cd ui && pnpm install       # Install dependencies
cd ui && pnpm dev           # Start development server
```

### Operational Scripts
```bash
# Database maintenance
./scripts/db_maintenance.sh    # Full maintenance routine
./scripts/db_monitor.sh        # Real-time monitoring
./scripts/db_backup.sh         # Backup databases

# Health checks
docker ps                      # Check container status
docker logs postgres-mem0     # View PostgreSQL logs
docker logs neo4j-mem0        # View Neo4j logs
```

### Service URLs (Development)
- **mem0 API**: http://localhost:8000 (docs at /docs)
- **OpenMemory MCP**: http://localhost:8765 (docs at /docs)
- **OpenMemory UI**: http://localhost:3000
- **PostgreSQL**: localhost:5432 (internal)
- **Neo4j**: localhost:7474 (browser), localhost:7687 (bolt)

### Debugging and Troubleshooting
- **Container Issues**: Check `docker compose logs <service>`
- **Database Issues**: Use `make shell` and inspect logs
- **Frontend Issues**: Check browser console and network tab
- **MCP Issues**: Refer to `MCP_FIX_SUMMARY.md` for known fixes

---

*This document reflects the actual state of the mem0-stack system as of January 2025. It should be updated as the system evolves and technical debt is addressed.* 