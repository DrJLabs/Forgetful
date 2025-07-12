# Mem0 MCP Server Setup Guide

## Overview

The Mem0 MCP (Model Context Protocol) server provides seamless integration between Cursor IDE and the Mem0 memory system. This eliminates the need for manual API calls and provides native tool integration within Cursor.

## Quick Setup

### 1. Verify MCP Server is Running

```bash
docker ps | grep openmemory-mcp
```

Expected output:
```
9a854e58f855 mem0/openmemory-mcp openmemory-mcp
```

### 2. Configure Cursor IDE

1. Open Cursor Settings (`Cmd/Ctrl + ,`)
2. Navigate to: **Features** → **MCP Servers**
3. Click **"Add new MCP server"**
4. Configure with these settings:
   - **Name**: `mem0`
   - **Type**: `SSE`
   - **Endpoint**: `http://localhost:8765/mcp/messages/`
5. Save and restart Cursor

### 3. Verify Configuration

After restarting Cursor, the following MCP tools should be automatically available:
- `add_memories` - Store new information
- `search_memory` - Find relevant memories (auto-called)
- `list_memories` - View all stored memories
- `delete_all_memories` - Clear memory storage

## MCP vs API Comparison

| Feature | MCP Server | Direct API |
|---------|------------|------------|
| **Integration** | Native Cursor tools | Manual curl/HTTP calls |
| **Context** | Automatic user/project detection | Manual parameter passing |
| **Error Handling** | Built-in resilience | Manual error checking |
| **Token Usage** | Minimal (tools only) | High (verbose commands) |
| **Setup** | One-time configuration | Per-rule setup |

## Updated Cursor Rule

The MCP-focused rule (`.cursor/rules/mem0-external-memory.mdc`) is now:
- **Concise**: Under 50 lines (vs 183 lines previously)
- **Context-aware**: Uses `description` field for smart loading
- **Action-focused**: Describes behaviors, not implementation
- **Token-efficient**: No verbose curl commands

## Usage Examples

### Automatic Memory Storage
When you share information:
```
User: "I prefer using TypeScript with strict mode enabled"
AI: [Automatically calls add_memories tool]
```

### Automatic Context Retrieval
When you ask questions:
```
User: "What coding standards did we establish?"
AI: [search_memory automatically called, retrieves preferences]
```

### Manual Memory Operations
```
User: "Show me all my stored memories"
AI: [Calls list_memories tool]
```

## Verification Test Results

All MCP functionality tests passed ✅:
- Endpoint accessibility: **PASS**
- Memory creation: **PASS**
- Memory search: **PASS**
- Backend consistency: **PASS**

## Benefits of MCP Integration

1. **Seamless Experience**: No manual commands needed
2. **Automatic Context**: Every query triggers memory search
3. **Better Error Handling**: Graceful degradation if services unavailable
4. **Token Efficiency**: Reduces context window usage by ~90%
5. **Type Safety**: Structured tool interfaces

## Troubleshooting

### MCP Tools Not Available
1. Ensure MCP server is running: `docker ps | grep openmemory-mcp`
2. Check Cursor MCP configuration
3. Restart Cursor after configuration changes

### Connection Issues
1. Verify endpoint: `curl -I http://localhost:8765/mcp/messages/`
2. Check Docker logs: `docker logs openmemory-mcp`
3. Ensure all required services are running

### Memory Not Persisting
1. Check PostgreSQL is running: `docker ps | grep postgres-mem0`
2. Verify Neo4j is running: `docker ps | grep neo4j-mem0`
3. Test API directly: `python test_mcp_functionality.py`

## Architecture

```
Cursor IDE
    ↓ (MCP Protocol)
MCP Server (:8765)
    ↓ (Same Backend)
Mem0 Memory Client
    ↓
PostgreSQL + Neo4j
```

Both MCP and API interfaces use the exact same backend, ensuring consistency across all access methods.