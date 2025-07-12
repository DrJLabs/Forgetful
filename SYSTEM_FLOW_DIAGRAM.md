# mem0-Stack System Flow Documentation

## Overview
The mem0-stack is a comprehensive memory management system with multiple APIs, databases, and interfaces. This document details the flow for each endpoint in the system.

## System Architecture

### Core Services
- **mem0 API** (Port 8000): Main memory management API
- **OpenMemory API** (Port 8765): MCP server and UI backend
- **OpenMemory UI** (Port 3000): React-based web interface
- **PostgreSQL**: Vector storage with pgvector extension
- **Neo4j**: Graph database for relationships

### Data Flow Patterns
1. **UI Request Flow**: User → UI → OpenMemory API → mem0 API → Database
2. **MCP Client Flow**: MCP Client → MCP Server → mem0 API → Database
3. **Direct API Flow**: Client → mem0 API → Database
4. **Vector Search Flow**: Query → Embedding → pgvector → Results
5. **Graph Analysis Flow**: Memory → Neo4j → Relationships

## API Endpoints and Flows

### 1. mem0 API Endpoints (Port 8000)

#### POST /memories
**Purpose**: Create memories from messages
**Flow**:
1. Client sends messages with user_id/agent_id/run_id
2. mem0 API processes messages through LLM
3. Extracts memorable information
4. Generates vector embeddings
5. Stores in PostgreSQL (vectors + metadata)
6. Creates relationships in Neo4j
7. Returns created memory IDs

**Database Operations**:
- INSERT into memories table
- Vector embedding storage in pgvector
- Relationship creation in Neo4j

#### GET /memories
**Purpose**: Retrieve all memories for user/agent/run
**Flow**:
1. Client requests with identifier
2. mem0 API queries PostgreSQL
3. Retrieves memories with metadata
4. Returns paginated results

**Database Operations**:
- SELECT from memories table
- JOIN with metadata tables

#### POST /search
**Purpose**: Vector similarity search
**Flow**:
1. Client sends search query
2. mem0 API generates query embedding
3. Performs vector similarity search in pgvector
4. Returns ranked results with similarity scores

**Database Operations**:
- Vector similarity search using pgvector
- Ranking by cosine similarity

#### GET /memories/{id}
**Purpose**: Get specific memory by ID
**Flow**:
1. Client requests specific memory ID
2. mem0 API queries PostgreSQL
3. Returns memory details with metadata

**Database Operations**:
- SELECT by primary key

#### PUT /memories/{id}
**Purpose**: Update existing memory
**Flow**:
1. Client sends updated memory data
2. mem0 API processes new content
3. Updates vector embedding
4. Updates PostgreSQL record
5. Updates Neo4j relationships

**Database Operations**:
- UPDATE memories table
- Vector re-embedding
- Graph relationship updates

#### DELETE /memories/{id}
**Purpose**: Delete specific memory
**Flow**:
1. Client requests memory deletion
2. mem0 API removes from PostgreSQL
3. Removes Neo4j relationships
4. Returns confirmation

**Database Operations**:
- DELETE from memories table
- Remove Neo4j relationships

#### DELETE /memories
**Purpose**: Bulk delete memories
**Flow**:
1. Client requests bulk deletion with filters
2. mem0 API identifies matching memories
3. Removes from both databases
4. Returns deletion count

**Database Operations**:
- Batch DELETE operations
- Cascade relationship removal

#### GET /memories/{id}/history
**Purpose**: Get memory modification history
**Flow**:
1. Client requests memory history
2. mem0 API queries history table
3. Returns chronological changes

**Database Operations**:
- SELECT from history/audit tables

#### POST /configure
**Purpose**: Configure system settings
**Flow**:
1. Client sends configuration
2. mem0 API validates settings
3. Updates internal configuration
4. Reinitializes connections

**Database Operations**:
- Configuration persistence

#### GET /health
**Purpose**: Health check
**Flow**:
1. Client requests health status
2. mem0 API checks database connections
3. Returns service status

**Database Operations**:
- Connection health checks

### 2. OpenMemory API Endpoints (Port 8765)

#### GET /api/v1/memories
**Purpose**: List memories with pagination
**Flow**:
1. UI requests memory list
2. OpenMemory API queries PostgreSQL directly
3. Applies filters and pagination
4. Returns formatted results

**Database Operations**:
- SELECT with JOIN on apps, users, categories
- Pagination with LIMIT/OFFSET

#### POST /api/v1/memories/filter
**Purpose**: Advanced memory filtering
**Flow**:
1. UI sends filter criteria
2. OpenMemory API builds dynamic query
3. Applies filters (date, category, app, search)
4. Returns filtered results

**Database Operations**:
- Complex SELECT with multiple JOINs
- WHERE clause with multiple conditions

#### POST /api/v1/memories
**Purpose**: Create new memory
**Flow**:
1. UI sends memory creation request
2. OpenMemory API validates user/app
3. Bridges to mem0 API for storage
4. Updates local metadata tables

**Database Operations**:
- INSERT into memories table
- UPDATE app statistics

#### GET /api/v1/apps
**Purpose**: List user applications
**Flow**:
1. UI requests app list
2. OpenMemory API queries apps table
3. Calculates memory counts
4. Returns app details

**Database Operations**:
- SELECT from apps table
- COUNT queries for statistics

#### GET /api/v1/stats
**Purpose**: Get user statistics
**Flow**:
1. UI requests user stats
2. OpenMemory API queries multiple tables
3. Calculates aggregated metrics
4. Returns statistics

**Database Operations**:
- Multiple COUNT queries
- Aggregate calculations

#### GET /api/v1/config
**Purpose**: Get system configuration
**Flow**:
1. UI requests current config
2. OpenMemory API reads from config table
3. Returns configuration settings

**Database Operations**:
- SELECT from config table

### 3. MCP Server Tools

#### add_memories
**Purpose**: Store new information via MCP
**Flow**:
1. MCP client calls add_memories
2. MCP server forwards to mem0 API
3. Memory stored in databases
4. Returns success/failure

**Database Operations**:
- Same as POST /memories

#### search_memory
**Purpose**: Find relevant memories
**Flow**:
1. MCP client searches memories
2. MCP server forwards to mem0 API
3. Vector search performed
4. Returns relevant memories

**Database Operations**:
- Same as POST /search

#### list_memories
**Purpose**: View all memories
**Flow**:
1. MCP client requests list
2. MCP server forwards to mem0 API
3. Retrieves all memories
4. Returns formatted list

**Database Operations**:
- Same as GET /memories

#### delete_all_memories
**Purpose**: Clear memory storage
**Flow**:
1. MCP client requests deletion
2. MCP server forwards to mem0 API
3. Bulk deletion performed
4. Returns confirmation

**Database Operations**:
- Same as DELETE /memories

### 4. UI User Interactions

#### Browse Memories
**Flow**: User → UI → GET /api/v1/memories → Database → Results

#### Create Memory
**Flow**: User → UI → POST /api/v1/memories → mem0 API → Database

#### Search Memories
**Flow**: User → UI → POST /api/v1/memories/filter → Database → Results

#### View Apps
**Flow**: User → UI → GET /api/v1/apps → Database → App List

#### Configure System
**Flow**: User → UI → PUT /api/v1/config → Database → Config Update

## Database Schema

### PostgreSQL Tables
- **memories**: Core memory storage with vectors
- **apps**: Application metadata
- **users**: User information
- **categories**: Memory categorization
- **config**: System configuration
- **memory_access_logs**: Access tracking
- **memory_status_history**: Change history

### Neo4j Graph
- **Memory nodes**: Individual memories
- **Relationship edges**: Connections between memories
- **Entity graphs**: User, app, and memory relationships

## Error Handling

### Common Error Scenarios
1. **Database Connection Issues**: Graceful fallback to limited functionality
2. **Vector Store Unavailable**: Database-only mode
3. **Graph Store Unavailable**: Skip relationship operations
4. **API Rate Limiting**: Queue requests and retry
5. **Memory Client Failures**: Return error messages with context

## Security and Access Control

### Authentication
- User-based access control
- App-specific permissions
- Memory access restrictions

### API Security
- CORS policies
- Rate limiting
- Input validation
- SQL injection prevention

## Performance Considerations

### Optimization Strategies
- Vector index optimization
- Connection pooling
- Caching layers
- Batch operations
- Async processing

### Monitoring
- Health check endpoints
- Database performance metrics
- API response times
- Error rate tracking

## Configuration Management

### Environment Variables
- Database connection strings
- API keys and secrets
- Service configurations
- Feature flags

### Runtime Configuration
- LLM model settings
- Embedding model configuration
- Vector store parameters
- Graph store settings