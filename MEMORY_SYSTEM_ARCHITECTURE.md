# Memory System Architecture

## Overview

This document describes the complete architecture of the mem0-stack memory system, including all components, services, and their interconnections. The system provides scalable long-term memory capabilities for AI agents through a distributed microservices architecture.

## System Components

### Core Services
- **mem0 API Server** (Port 8000): Main memory operations API
- **PostgreSQL** (Vector Storage): Stores memory embeddings and metadata
- **Neo4j** (Graph Database): Manages entity relationships and connections
- **OpenMemory MCP Server** (Port 8765): Model Context Protocol server

### Interface Layer
- **React UI** (Port 3000): Web-based memory management interface
- **MCP Bridge Server** (Port 8081): SSE bridge for Cursor MCP compatibility
- **Secure MCP Server** (Production): Internet-facing secure endpoint

### Infrastructure
- **Traefik**: Reverse proxy and load balancer
- **Nginx**: Proxy container for host-based services
- **Cloudflare Tunnel**: Secure external access without open ports
- **Monitoring Stack**: Prometheus, Grafana, Alertmanager

## Architecture Diagram

```mermaid
graph TD
    %% External Clients
    Cursor[Cursor Editor<br/>MCP Client] --> SSE[SSE Bridge<br/>Port 8081<br/>Host Process]
    ChatGPT[ChatGPT Custom GPT] --> CF[Cloudflare Tunnel<br/>TLS Termination]
    External[External Agents] --> CF
    WebUser[Web Users] --> UI[React UI<br/>Port 3000]

    %% Secure Access Layer
    CF --> Traefik[Traefik<br/>Reverse Proxy]
    Traefik --> SecureMCP[Secure MCP Server<br/>API Key Auth<br/>Rate Limiting]
    Traefik --> NginxProxy[Nginx Proxy<br/>Container]
    NginxProxy --> SSE

    %% MCP Layer
    SSE --> MCPServer[OpenMemory MCP<br/>Port 8765]
    SecureMCP --> MCPServer

    %% Core API Layer
    MCPServer --> MemAPI[mem0 API Server<br/>Port 8000]
    UI --> MemAPI

    %% Data Storage Layer
    MemAPI --> PG[(PostgreSQL<br/>Vector Storage<br/>Embeddings)]
    MemAPI --> Neo4j[(Neo4j<br/>Graph Database<br/>Relationships)]

    %% Monitoring & Backup
    MemAPI --> Prometheus[Prometheus<br/>Metrics Collection]
    PG --> Backup1[PostgreSQL<br/>Backup System]
    Neo4j --> Backup2[Neo4j<br/>Backup System]
    Prometheus --> Grafana[Grafana<br/>Dashboards]
    Prometheus --> AlertManager[Alert Manager<br/>Notifications]

    %% Styling
    classDef external fill:#e1f5fe
    classDef security fill:#ffebee
    classDef core fill:#e8f5e8
    classDef storage fill:#fff3e0
    classDef monitoring fill:#f3e5f5

    class Cursor,ChatGPT,External,WebUser external
    class CF,Traefik,SecureMCP,NginxProxy security
    class SSE,MCPServer,MemAPI,UI core
    class PG,Neo4j,Backup1,Backup2 storage
    class Prometheus,Grafana,AlertManager monitoring
```

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant C as Cursor/ChatGPT
    participant CF as Cloudflare Tunnel
    participant T as Traefik
    participant S as Secure MCP
    participant MCP as MCP Server
    participant API as mem0 API
    participant PG as PostgreSQL
    participant Neo as Neo4j

    Note over C,Neo: Memory Creation Flow
    C->>CF: Memory Request (HTTPS)
    CF->>T: Route to MCP
    T->>S: API Key Validation
    S->>MCP: Authenticated Request
    MCP->>API: Memory Operations
    API->>PG: Store Embeddings
    API->>Neo: Store Relationships
    Neo-->>API: Confirm Storage
    PG-->>API: Confirm Storage
    API-->>MCP: Success Response
    MCP-->>S: Response
    S-->>T: Response
    T-->>CF: Response
    CF-->>C: Memory Stored

    Note over C,Neo: Memory Retrieval Flow
    C->>CF: Search Request
    CF->>T: Route Request
    T->>S: Validate & Route
    S->>MCP: Search Query
    MCP->>API: Search Memory
    API->>PG: Vector Search
    API->>Neo: Graph Query
    PG-->>API: Matching Vectors
    Neo-->>API: Related Entities
    API-->>MCP: Merged Results
    MCP-->>S: Search Results
    S-->>T: Response
    T-->>CF: Response
    CF-->>C: Memory Results
```

## Network Architecture

```mermaid
graph LR
    subgraph "External Access"
        Internet[Internet] --> CF[Cloudflare Tunnel<br/>TLS: 15-year cert]
        CF --> Domain[mem-mcp.onemainarmy.com]
    end

    subgraph "Host Network (172.17.0.1)"
        Domain --> Host[Host Interface<br/>172.17.0.1:8081]
        Host --> MCP81[MCP Bridge Process<br/>PID: 2021938]
    end

    subgraph "Docker Network"
        MCP81 --> DockerNet[Docker Network<br/>172.17.0.0/16]
        DockerNet --> Container1[mem0 API<br/>:8000]
        DockerNet --> Container2[PostgreSQL<br/>:5432]
        DockerNet --> Container3[Neo4j<br/>:7474/:7687]
        DockerNet --> Container4[MCP Server<br/>:8765]
        DockerNet --> Container5[React UI<br/>:3000]
    end

    subgraph "Security Layer"
        CF --> WAF[Web Application Firewall]
        WAF --> RateLimit[Rate Limiting<br/>60 req/min]
        RateLimit --> Auth[API Key Auth<br/>JWT Validation]
    end
```

## Component Details

### mem0 API Server (Port 8000)
- **Purpose**: Core memory operations API
- **Functions**:
  - Memory CRUD operations
  - Vector embeddings generation
  - Memory search and retrieval
  - Memory relationship extraction
- **Dependencies**: PostgreSQL, Neo4j
- **Health Check**: `/health` endpoint

### PostgreSQL (Vector Storage)
- **Purpose**: Store memory embeddings and metadata
- **Schema**:
  - Memory vectors (embeddings)
  - User associations
  - Timestamps and metadata
- **Backup**: Automated daily backups
- **Extensions**: pgvector for vector operations

### Neo4j (Graph Database)
- **Purpose**: Store entity relationships and connections
- **Schema**:
  - Entity nodes (people, places, concepts)
  - Relationship edges (connections, associations)
  - Temporal information
- **Backup**: Automated graph exports
- **Queries**: Cypher for relationship traversal

### MCP Bridge Server (Port 8081)
- **Purpose**: SSE bridge for Cursor MCP compatibility
- **Type**: Host-based Python process
- **Functions**:
  - Server-Sent Events (SSE) streaming
  - Protocol translation
  - Connection management
- **Process**: PID 2021938 (standard_mem0_mcp_server.py)

### Secure MCP Server (Production)
- **Purpose**: Internet-facing secure endpoint
- **Security Features**:
  - API key authentication
  - JWT token validation
  - Rate limiting (60 requests/minute)
  - CORS protection
  - Input validation
  - Security headers
- **Domains**: mem-mcp.onemainarmy.com
- **Allowed Origins**: chat.openai.com, chatgpt.com

### React UI (Port 3000)
- **Purpose**: Web-based memory management interface
- **Features**:
  - Memory browsing and search
  - Memory creation and editing
  - System health monitoring
  - User management
- **Framework**: Next.js with TypeScript

## Security Architecture

```mermaid
graph TD
    subgraph "Internet"
        Attacker[Potential Attacker]
        LegitUser[Legitimate User]
    end

    subgraph "Security Layers"
        WAF[Web Application Firewall<br/>DDoS Protection]
        RateLimit[Rate Limiting<br/>60 req/min]
        Auth[API Key Authentication<br/>JWT Validation]
        CORS[CORS Protection<br/>Allowed Origins Only]
        Input[Input Validation<br/>Schema Enforcement]
        Headers[Security Headers<br/>XSS, CSRF Protection]
    end

    subgraph "Application Layer"
        SecureMCP[Secure MCP Server]
        API[mem0 API]
    end

    LegitUser --> WAF
    Attacker --> WAF
    WAF --> RateLimit
    RateLimit --> Auth
    Auth --> CORS
    CORS --> Input
    Input --> Headers
    Headers --> SecureMCP
    SecureMCP --> API

    classDef security fill:#ffebee
    classDef app fill:#e8f5e8
    classDef threat fill:#ffcdd2

    class WAF,RateLimit,Auth,CORS,Input,Headers security
    class SecureMCP,API app
    class Attacker threat
```

## Deployment Architecture

```mermaid
graph TD
    subgraph "Development Environment"
        DevDocker[Docker Compose<br/>Local Development]
        DevTests[Security Test Suite<br/>Pre-deployment]
    end

    subgraph "Production Deployment"
        Deploy[deploy_production_mcp.sh]
        SystemD[SystemD Service<br/>Auto-restart]
        Monitoring[Health Monitoring<br/>Automated Checks]
    end

    subgraph "External Integration"
        CloudflareSetup[Cloudflare Tunnel<br/>Configuration]
        TraefikConfig[Traefik Routing<br/>Docker Labels]
        ChatGPTConfig[ChatGPT Custom GPT<br/>OpenAPI Schema]
    end

    DevDocker --> DevTests
    DevTests --> Deploy
    Deploy --> SystemD
    SystemD --> Monitoring
    Deploy --> CloudflareSetup
    Deploy --> TraefikConfig
    Deploy --> ChatGPTConfig
```

## Performance Characteristics

| Component | Response Time | Throughput | Scaling |
|-----------|---------------|------------|---------|
| mem0 API | 1.44s avg | 100 req/s | Horizontal |
| PostgreSQL | <100ms | 1000 queries/s | Vertical |
| Neo4j | <200ms | 500 queries/s | Vertical |
| MCP Bridge | <50ms | 200 req/s | Horizontal |
| Secure MCP | <100ms | 60 req/min | Rate Limited |

## Monitoring and Observability

```mermaid
graph LR
    subgraph "Metrics Collection"
        App[Application Metrics] --> Prometheus
        System[System Metrics] --> Prometheus
        Custom[Custom Metrics] --> Prometheus
    end

    subgraph "Storage & Processing"
        Prometheus[Prometheus<br/>Time Series DB]
        Prometheus --> Grafana[Grafana<br/>Dashboards]
        Prometheus --> AlertManager[Alert Manager<br/>Notifications]
    end

    subgraph "Alerting"
        AlertManager --> Email[Email Alerts]
        AlertManager --> Slack[Slack Notifications]
        AlertManager --> PagerDuty[PagerDuty<br/>Critical Alerts]
    end

    subgraph "Dashboards"
        Grafana --> SystemDash[System Overview<br/>Dashboard]
        Grafana --> MemoryDash[Memory Operations<br/>Dashboard]
        Grafana --> SecurityDash[Security Events<br/>Dashboard]
    end
```

## Backup and Recovery

```mermaid
graph TD
    subgraph "Backup Sources"
        PG[PostgreSQL<br/>Memory Data]
        Neo4j[Neo4j<br/>Graph Data]
        Config[Configuration<br/>Files]
    end

    subgraph "Backup Process"
        Schedule[Daily Backup<br/>Cron Job]
        PGDump[pg_dump<br/>SQL Export]
        NeoDump[Neo4j Export<br/>Graph Dump]
        ConfigBackup[Config Backup<br/>File Copy]
    end

    subgraph "Storage"
        Local[Local Storage<br/>/backups/]
        Remote[Remote Storage<br/>Cloud Backup]
        Versioning[Version Control<br/>Git Repository]
    end

    PG --> PGDump
    Neo4j --> NeoDump
    Config --> ConfigBackup
    Schedule --> PGDump
    Schedule --> NeoDump
    Schedule --> ConfigBackup
    PGDump --> Local
    NeoDump --> Local
    ConfigBackup --> Versioning
    Local --> Remote
```

## Configuration Management

### Environment Variables
- `MEM0_API_URL`: mem0 API endpoint
- `POSTGRES_URL`: PostgreSQL connection string
- `NEO4J_URL`: Neo4j connection string
- `MCP_SERVER_URL`: MCP server endpoint
- `API_KEYS`: Secure API keys for authentication
- `JWT_SECRET`: JWT signing secret

### Docker Compose Configuration
```yaml
# Key service configurations
mem0:
  image: mem0/mem0
  ports: ["8000:8000"]
  environment:
    - POSTGRES_URL=${POSTGRES_URL}
    - NEO4J_URL=${NEO4J_URL}

postgres-mem0:
  image: postgres:13
  environment:
    - POSTGRES_DB=mem0
    - POSTGRES_USER=mem0
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

neo4j-mem0:
  image: neo4j:4.4
  environment:
    - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
```

## Security Considerations

### Authentication & Authorization
- API key-based authentication for external access
- JWT tokens for session management
- Role-based access control (RBAC)
- Secure credential storage

### Network Security
- TLS 1.3 encryption for all external communication
- Cloudflare tunnel for secure external access
- Docker network isolation
- Firewall rules for container communication

### Data Protection
- Encryption at rest for sensitive data
- Secure backup procedures
- Regular security audits
- Compliance with data protection regulations

## Troubleshooting Guide

### Common Issues
1. **Connection Timeouts**: Check network connectivity and service health
2. **Authentication Failures**: Verify API keys and JWT tokens
3. **Memory Operation Errors**: Check PostgreSQL and Neo4j connections
4. **Rate Limiting**: Monitor request rates and adjust limits

### Health Checks
```bash
# Check service health
curl http://localhost:8000/health
curl http://localhost:8081/health
curl http://localhost:8765/health

# Check security tests
python security_test_suite.py

# Check deployment
./deploy_production_mcp.sh --test
```

## Future Enhancements

1. **Horizontal Scaling**: Implement load balancing for mem0 API
2. **Advanced Security**: Add OAuth2 and SAML integration
3. **Performance Optimization**: Implement caching layers
4. **Multi-tenancy**: Support for multiple organizations
5. **Advanced Analytics**: Real-time memory analytics and insights

---

*Last Updated: January 2025*
*Version: 1.0*
*Maintainer: Development Team*
