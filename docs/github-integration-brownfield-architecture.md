# Mem0-Stack GitHub Integration Brownfield Architecture Document

## Introduction
This document captures the CURRENT STATE of the mem0-stack codebase and defines the architecture for integrating GitHub project tracking capabilities. This integration will provide proper project tracking for mem0-stack development without modifying the existing OpenMemory system.

### Document Scope
Focused on integrating GitHub project tracking for mem0-stack development workflow, specifically targeting the "Forgetful" repository for bidirectional synchronization.

### Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2024-01-15 | 1.0 | Initial brownfield analysis for GitHub integration | Mary (Business Analyst) |

## Quick Reference - Key Files and Entry Points

### Current System Architecture
- **Main Services**: mem0, openmemory-mcp, openmemory-ui, postgres-mem0, neo4j-mem0
- **Service Orchestration**: `docker-compose.yml` - 5 containerized services
- **API Gateway**: FastAPI application in `openmemory/api/`
- **Frontend**: Next.js 15.2.4 in `openmemory/ui/`
- **Database**: PostgreSQL with pgvector + Neo4j for graph relationships

### GitHub Integration Impact Areas
**New Service Required**: Separate GitHub project tracking service
- **Integration Points**: API endpoints, database schema, authentication
- **Data Flow**: GitHub API ↔ New Service ↔ Project Database
- **No Impact**: OpenMemory UI/API (per user requirement)

## High Level Architecture

### Technical Summary
The mem0-stack is a well-architected multi-service system with clean separation of concerns. The addition of GitHub project tracking will require a new microservice that operates independently of the existing OpenMemory components.

### Current Tech Stack
| Category | Technology | Version | Integration Notes |
|----------|------------|---------|------------------|
| Container Platform | Docker Compose | Latest | Will add new service |
| API Framework | FastAPI | Latest | GitHub service will use same |
| Frontend | Next.js | 15.2.4 | No changes needed initially |
| Database | PostgreSQL | 16 (pgvector) | Will add new schemas |
| Graph Database | Neo4j | 5.26.4 | May store project relationships |
| Reverse Proxy | Traefik | Latest | Will expose new service |
| Memory Engine | mem0 | Custom | Not affected by integration |

### Repository Structure Reality Check
- **Type**: Monorepo with service-specific folders
- **Package Management**: npm/pnpm for UI, pip for Python services
- **Container Strategy**: Each service has dedicated Dockerfile
- **Notable**: Clean separation between mem0 core and OpenMemory services

## Current System Components

### Service Architecture (Docker Compose)
```yaml
services:
  mem0:                  # Port 8000 - Core memory processing
  postgres-mem0:         # PostgreSQL with pgvector
  neo4j-mem0:           # Graph database
  openmemory-mcp:       # Port 8765 - MCP protocol API
  openmemory-ui:        # Port 3000 - React frontend
  # NEW: github-tracker  # Port 8080 - GitHub project integration
```

### OpenMemory API Structure
```
openmemory/api/
├── app/
│   ├── routers/
│   │   ├── memories.py      # Memory CRUD operations
│   │   ├── apps.py          # Application management
│   │   ├── config.py        # Configuration management
│   │   └── stats.py         # Statistics endpoints
│   ├── models/              # SQLAlchemy models
│   └── utils/               # Utility functions
├── main.py                  # FastAPI application entry
└── requirements.txt         # Python dependencies
```

### OpenMemory UI Structure
```
openmemory/ui/
├── app/                     # Next.js app router
│   ├── memories/            # Memory management pages
│   ├── settings/            # Configuration pages
│   └── layout.tsx           # Root layout
├── components/              # React components
│   ├── ui/                  # Shadcn/ui components
│   └── shared/              # Shared components
└── package.json             # Node.js dependencies
```

## GitHub Integration Architecture

### New Service Design
**Service Name**: `github-tracker`
**Purpose**: Bidirectional sync with "Forgetful" repository
**Technology**: FastAPI (consistent with existing services)

### GitHub Integration Service Structure
```
github-tracker/
├── app/
│   ├── routers/
│   │   ├── projects.py      # GitHub Projects API
│   │   ├── issues.py        # GitHub Issues API
│   │   ├── milestones.py    # GitHub Milestones API
│   │   └── sync.py          # Synchronization endpoints
│   ├── models/
│   │   ├── github_models.py # GitHub data models
│   │   └── sync_models.py   # Sync state tracking
│   ├── services/
│   │   ├── github_client.py # GitHub API client
│   │   ├── sync_service.py  # Bidirectional sync logic
│   │   └── webhook_service.py # Webhook handling
│   └── utils/
│       ├── auth.py          # GitHub authentication
│       └── rate_limiter.py  # API rate limiting
├── main.py                  # FastAPI application
├── Dockerfile              # Container configuration
└── requirements.txt        # Python dependencies
```

### Database Schema Extensions
**New PostgreSQL Tables** (separate from OpenMemory):
```sql
-- GitHub project tracking tables
CREATE TABLE github_projects (
    id UUID PRIMARY KEY,
    github_id INTEGER UNIQUE NOT NULL,
    repository_full_name VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    state VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    synced_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE github_issues (
    id UUID PRIMARY KEY,
    github_id INTEGER UNIQUE NOT NULL,
    repository_full_name VARCHAR(255) NOT NULL,
    number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    state VARCHAR(20) NOT NULL,
    assignees JSONB,
    labels JSONB,
    milestone_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    synced_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE github_milestones (
    id UUID PRIMARY KEY,
    github_id INTEGER UNIQUE NOT NULL,
    repository_full_name VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    state VARCHAR(20) NOT NULL,
    due_on TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    synced_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE sync_state (
    id UUID PRIMARY KEY,
    resource_type VARCHAR(50) NOT NULL,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_sync_cursor VARCHAR(255),
    sync_status VARCHAR(20) NOT NULL,
    error_message TEXT
);
```

## Technical Integration Points

### Data Flow Architecture
```
GitHub API (Forgetful repo) 
    ↕ (Webhooks + Polling)
GitHub Tracker Service
    ↕ (Database writes)
PostgreSQL (GitHub tables)
    ↕ (Optional: Graph relationships)
Neo4j (Project relationships)
```

### API Integration Points
**GitHub APIs Required**:
- **Projects API v2**: `/repos/{owner}/{repo}/projects`
- **Issues API**: `/repos/{owner}/{repo}/issues`
- **Milestones API**: `/repos/{owner}/{repo}/milestones`
- **Webhooks API**: `/repos/{owner}/{repo}/hooks`

**New Service Endpoints**:
```
GET  /api/v1/projects          # List GitHub projects
GET  /api/v1/issues            # List GitHub issues
GET  /api/v1/milestones        # List GitHub milestones
POST /api/v1/sync/trigger      # Manual sync trigger
GET  /api/v1/sync/status       # Sync status
POST /api/v1/webhooks/github   # GitHub webhook endpoint
```

## Technical Debt and Constraints

### Current System Constraints
1. **Service Isolation**: GitHub tracker must be completely separate from OpenMemory
2. **Database Separation**: New tables in existing PostgreSQL instance
3. **Port Allocation**: Must use available ports (8080 suggested)
4. **Container Resources**: Additional resource allocation needed

### GitHub API Constraints
1. **Rate Limiting**: 5000 requests/hour for authenticated requests
2. **Webhook Reliability**: Must handle failed deliveries and retries
3. **Data Consistency**: GitHub API eventual consistency considerations
4. **Authentication**: GitHub App vs OAuth vs Personal Access Token decision

### Integration Gotchas
- **GitHub Projects v2**: New GraphQL-based API, different from legacy Projects
- **Webhook Security**: Must verify GitHub webhook signatures
- **Sync Conflicts**: Bidirectional sync requires conflict resolution
- **Repository Scope**: Only "Forgetful" repo initially, architecture must support expansion

## Deployment and Configuration

### Docker Compose Integration
```yaml
# Addition to existing docker-compose.yml
services:
  github-tracker:
    build:
      context: ./github-tracker
      dockerfile: Dockerfile
    container_name: github-tracker
    restart: unless-stopped
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
      - POSTGRES_HOST=postgres-mem0
      - POSTGRES_DB=mem0
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    ports:
      - "127.0.0.1:8080:8080"
    depends_on:
      postgres:
        condition: service_healthy
    networks: [traefik]
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.github-tracker.rule=Host(`github.drjlabs.com`)"
      - "traefik.http.routers.github-tracker.entrypoints=websecure"
      - "traefik.http.routers.github-tracker.tls=true"
      - "traefik.http.services.github-tracker.loadbalancer.server.port=8080"
```

### Environment Variables
```bash
# GitHub Integration
GITHUB_TOKEN=ghp_xxx                    # Personal Access Token or GitHub App token
GITHUB_WEBHOOK_SECRET=webhook_secret    # Webhook verification secret  
GITHUB_REPO_OWNER=your-username         # Repository owner
GITHUB_REPO_NAME=Forgetful              # Repository name

# Service Configuration
GITHUB_TRACKER_PORT=8080                # Service port
SYNC_INTERVAL_MINUTES=15                # Polling interval
MAX_RETRIES=3                           # Webhook retry attempts
```

## Implementation Recommendations

### Authentication Strategy
**Recommended**: GitHub App (most secure and scalable)
- Pros: Fine-grained permissions, higher rate limits, webhook integration
- Cons: More complex setup
- Alternative: Personal Access Token (simpler for single-user setup)

### Sync Strategy
**Recommended**: Hybrid approach
- **Real-time**: GitHub webhooks for immediate updates
- **Backup**: Periodic polling (every 15 minutes) for missed events
- **Full Sync**: Daily full synchronization for data integrity

### Error Handling
**Required Patterns**:
- Exponential backoff for GitHub API rate limits
- Webhook signature verification
- Idempotent sync operations
- Conflict resolution for bidirectional changes

## Files That Will Need Modification

### New Files/Modules Needed
- `github-tracker/` - Complete new service directory
- `docker-compose.yml` - Add new service configuration
- `.env` - Add GitHub authentication variables
- `scripts/setup-github-integration.sh` - Setup script

### Existing Files to Modify
- `docker-compose.yml` - Add github-tracker service
- `.env.example` - Document new environment variables
- `README.md` - Update with GitHub integration documentation
- `scripts/health-check.sh` - Include github-tracker health check

## Integration Testing Strategy

### Testing Requirements
1. **GitHub API Integration**: Mock GitHub API responses
2. **Webhook Processing**: Test webhook signature verification
3. **Sync Logic**: Test bidirectional synchronization
4. **Error Handling**: Test rate limiting and retry logic
5. **Database Integration**: Test PostgreSQL schema changes

### Test Data Requirements
- Sample GitHub project data from "Forgetful" repo
- Webhook payload examples
- Rate limit and error response scenarios

## Security Considerations

### GitHub Authentication
- Store GitHub tokens securely (environment variables)
- Use GitHub App with minimal required permissions
- Implement token rotation if using Personal Access Tokens

### Webhook Security
- Verify GitHub webhook signatures
- Use HTTPS for webhook endpoints
- Implement replay attack protection

### Data Security
- Encrypt sensitive GitHub data at rest
- Implement proper access controls
- Log security events for audit trail

## Performance Considerations

### GitHub API Rate Limits
- Implement intelligent rate limiting
- Use conditional requests with ETags
- Batch operations where possible
- Cache frequently accessed data

### Database Performance
- Index GitHub ID fields for fast lookups
- Implement database connection pooling
- Use batch inserts for sync operations

## Monitoring and Observability

### Required Metrics
- GitHub API request rates and errors
- Sync operation success/failure rates
- Webhook processing latency
- Database query performance

### Logging Strategy
- Structured logging with correlation IDs
- GitHub API request/response logging
- Sync operation audit trail
- Error tracking and alerting

## Next Steps

### Phase 1: Core Integration
1. Set up GitHub API authentication
2. Implement basic project/issue sync
3. Create database schema
4. Set up Docker service

### Phase 2: Real-time Sync
1. Implement GitHub webhooks
2. Add conflict resolution
3. Implement retry logic
4. Add monitoring and alerting

### Phase 3: Enhancement
1. Add milestone tracking
2. Implement advanced filtering
3. Add sync status dashboard
4. Performance optimization

---
*This document reflects the actual state of the mem0-stack system and provides a roadmap for GitHub project tracking integration without impacting the existing OpenMemory functionality.* 