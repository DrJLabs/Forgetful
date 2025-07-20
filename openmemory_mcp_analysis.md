# OpenMemory MCP Container Analysis - localhost:8765

## Overview

The OpenMemory MCP container running on **localhost:8765** is a **dual-purpose FastAPI application** that serves as both a **Model Context Protocol (MCP) server** and a **REST API layer** for the mem0-stack system. It acts as a **bridge between MCP clients (like Cursor, Claude Desktop) and the main mem0 memory system**, providing structured memory management with advanced features like permissions, audit logging, and multi-app support.

## Container Configuration

### Basic Information
- **Host**: localhost:8765
- **Framework**: FastAPI with MCP protocol integration
- **Container Name**: openmemory-mcp
- **Base Image**: mem0/openmemory-mcp (custom built)
- **Architecture**: MCP Server + REST API + Database Management Layer

### Key Dependencies
- **mem0 Library**: Uses the local mem0 library for memory operations
- **PostgreSQL**: Direct connection to postgres-mem0 (same database as main mem0)
- **Neo4j**: Same Neo4j instance as main mem0 system
- **MCP Library**: `mcp[cli]>=1.3.0` for Model Context Protocol support
- **FastMCP**: Framework for building MCP servers with FastAPI

## Core Functions and Architecture

### 1. **Model Context Protocol (MCP) Server**

The primary function is serving as an **MCP server** that provides memory tools to MCP clients.

#### Available MCP Tools:
```python
# 4 Core MCP Tools Available to Clients:
1. add_memories - Store new memories from conversations
2. search_memory - Vector similarity search across memories  
3. list_memories - Retrieve all accessible memories
4. delete_all_memories - Remove all memories for user/agent
```

#### MCP Connection Endpoints:
- **SSE Connection**: `/mcp/sse` (Standard MCP protocol)
- **Legacy SSE**: `/mcp/{client_name}/sse/{user_id}` (Backward compatibility)
- **Health Check**: `/mcp/health` (MCP-specific diagnostics)

#### Client Integration Examples:
```bash
# Cursor/Claude Desktop MCP Configuration
npx @openmemory/install local http://localhost:8765/mcp/cursor/sse/drj --client cursor

# Direct MCP URL for manual configuration
http://localhost:8765/mcp/openmemory/sse/drj
```

### 2. **REST API Layer**

Provides a comprehensive REST API for web applications and direct integration.

#### Memory Management API (`/api/v1/memories/`)
- **POST `/`**: Create memories (integrates with mem0 core)
- **GET `/`**: List memories with pagination and filtering
- **POST `/search`**: Semantic search with scoring
- **GET `/{memory_id}`**: Retrieve specific memory
- **PUT `/{memory_id}`**: Update memory content
- **DELETE `/{memory_id}`**: Delete specific memory
- **POST `/actions/archive`**: Archive memories
- **POST `/actions/pause`**: Pause memory processing

#### Application Management API (`/api/v1/apps/`)
- **GET `/`**: List applications and their statistics
- **GET `/{app_id}`**: Get application details
- **GET `/{app_id}/memories`**: Get memories for specific app
- **GET `/{app_id}/accessed`**: Get access logs for app

#### Configuration Management API (`/api/v1/config/`)
- **GET `/`**: Get current system configuration
- **PUT `/`**: Update configuration (LLM, embeddings, etc.)
- **POST `/reset`**: Reset to default configuration
- **GET/PUT `/mem0/llm`**: Manage LLM settings
- **GET/PUT `/mem0/embedder`**: Manage embedding settings

#### Statistics API (`/api/v1/stats/`)
- **GET `/`**: Get user statistics (memory count, app count, etc.)

### 3. **Integration with Main mem0 System**

**Critical Integration Pattern**: The OpenMemory MCP container **does NOT duplicate** the mem0 functionality but **delegates to the main mem0 system**.

```python
# Key Integration in app/mem0_client.py
def get_config():
    return {
        "vector_store": {
            "provider": "pgvector",
            "config": {
                "host": "postgres-mem0",      # Same PostgreSQL as main mem0
                "collection_name": "memories", # Same table as main mem0
                # ... same configuration
            },
        },
        "graph_store": {
            "provider": "neo4j",
            "config": {
                "url": "neo4j://neo4j-mem0:7687",  # Same Neo4j as main mem0
                # ... same configuration
            },
        },
    }

# Memory operations delegate to mem0 library
memory_client = Memory.from_config(config)
response = memory_client.add(text, user_id=uid, metadata={...})
```

### 4. **Advanced Features Beyond Basic mem0**

#### Multi-App Architecture
- **App Isolation**: Each client/application gets its own namespace
- **App Management**: Active/inactive state control
- **App-specific Access**: Memories are scoped to applications

#### Access Control and Auditing
```python
# Permission System
check_memory_access_permissions(db, memory, app.id)

# Audit Logging
MemoryAccessLog(
    memory_id=memory_id,
    app_id=app.id,
    access_type="search",
    metadata_={"query": query, "score": score}
)

# State History Tracking
MemoryStatusHistory(
    memory_id=memory_id,
    changed_by=user.id,
    old_state=MemoryState.active,
    new_state=MemoryState.deleted
)
```

#### Enhanced Database Models
- **User Management**: UUID-based users with relationships
- **Memory States**: active, archived, deleted with history tracking
- **Categories**: Automatic categorization with many-to-many relationships
- **Access Controls**: Fine-grained permission system
- **Archive Policies**: Automated lifecycle management

### 5. **Data Flow and Integration**

#### Memory Creation Flow:
1. **MCP Client** → Calls `add_memories` tool
2. **OpenMemory MCP** → Validates input and permissions
3. **mem0 Library** → Processes text, extracts facts, generates embeddings
4. **PostgreSQL** → Stores memory vectors (same `memories` table as main mem0)
5. **Neo4j** → Stores entity relationships (same graph as main mem0)
6. **OpenMemory DB** → Creates audit trail and app associations
7. **Response** → Returns combined results to MCP client

#### Search Flow:
1. **MCP Client** → Calls `search_memory` tool
2. **OpenMemory MCP** → Applies access control filters
3. **mem0 Library** → Performs vector similarity search
4. **Access Filtering** → Only returns memories user/app can access
5. **Audit Logging** → Records search access
6. **Response** → Returns filtered, scored results

## Key Differences from Main mem0 Container

| Aspect | Main mem0 (port 8000) | OpenMemory MCP (port 8765) |
|--------|----------------------|----------------------------|
| **Purpose** | Core memory orchestration | MCP bridge + enhanced features |
| **Protocol** | Pure REST API | MCP + REST API |
| **Database** | Direct PostgreSQL + Neo4j | Same databases + additional tables |
| **Access Control** | Basic user/agent/run scoping | Advanced permissions + apps + ACL |
| **Audit Trail** | SQLite history only | Full audit logs + state history |
| **Multi-tenancy** | User/agent/run isolation | App-based isolation + permissions |
| **Configuration** | Static config | Dynamic configuration management |
| **Client Support** | Direct API calls | MCP clients (Cursor, Claude Desktop) |

## Real-World Usage Examples

### MCP Client Integration (Cursor/Claude Desktop):
```json
{
  "mcpServers": {
    "mem0": {
      "command": "npx",
      "args": ["@openmemory/install", "local", "http://localhost:8765/mcp/cursor/sse/username", "--client", "cursor"]
    }
  }
}
```

### Direct API Usage:
```bash
# Create memory via REST API
curl -X POST "http://localhost:8765/api/v1/memories/" \
  -H "Content-Type: application/json" \
  -d '{"text": "User prefers dark mode", "user_id": "drj", "app": "my_app"}'

# Search memories via REST API  
curl -X POST "http://localhost:8765/api/v1/memories/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are user preferences?", "user_id": "drj"}'
```

## Architecture Benefits

### 1. **Unified Memory Backend**
- Both main mem0 and OpenMemory use the **same PostgreSQL and Neo4j databases**
- **No data duplication** - memories created in either system are accessible by both
- **Consistent vector embeddings** and relationship extraction

### 2. **Enhanced Enterprise Features**
- **Multi-app isolation** with permission controls
- **Comprehensive audit trails** for compliance
- **Dynamic configuration** without restarts
- **State management** with history tracking

### 3. **Protocol Flexibility**
- **MCP support** for modern AI clients (Cursor, Claude Desktop)
- **REST API** for traditional web applications
- **Backward compatibility** with legacy clients

### 4. **Operational Excellence**
- **Circuit breaker patterns** for resilience
- **Structured logging** with correlation IDs
- **Performance monitoring** with timing metrics
- **Health checks** for both MCP and REST endpoints

## Summary

The OpenMemory MCP container serves as a **sophisticated bridge and enhancement layer** for the mem0 system, providing:

1. **MCP Protocol Support**: Enables Cursor, Claude Desktop, and other MCP clients to use mem0 memory
2. **Enhanced Enterprise Features**: Adds permissions, audit trails, multi-app support, and configuration management
3. **Unified Backend**: Uses the same PostgreSQL and Neo4j databases as main mem0 for consistency
4. **Dual Protocol Support**: Supports both MCP and REST API for maximum flexibility
5. **Advanced Memory Management**: Provides memory lifecycle management, categorization, and access controls

**Does it replace the main mem0 container?** **No** - it **complements and extends** it. The OpenMemory MCP container **delegates core memory operations** to the mem0 library while adding enterprise-grade features and MCP protocol support. Both containers can operate simultaneously, sharing the same underlying memory databases while serving different types of clients and use cases. 