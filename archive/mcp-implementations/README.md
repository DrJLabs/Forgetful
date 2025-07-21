# Archived MCP Implementations

**Date Archived:** July 21, 2025
**Reason:** Consolidation and cleanup after successful Cursor MCP integration

## Files in this Archive

### 1. `test_mcp_functionality.py`
- **Original Location:** `./tests/`
- **Purpose:** Test file for MCP functionality
- **Reason Archived:** Root-level test file, functionality tested elsewhere

### 2. `mcp_server_old_location.py`
- **Original Location:** `./mem0/openmemory/api/app/mcp_server.py`
- **Purpose:** Duplicate of MCP server from old directory structure
- **Reason Archived:** Duplicate file after project reorganization

### 3. `test_mcp_server.py`
- **Original Location:** `./openmemory/api/tests/`
- **Purpose:** Test file for MCP server functionality
- **Reason Archived:** Unused test file

### 4. `mcp_standalone.py`
- **Original Location:** `./openmemory/api/`
- **Purpose:** Standalone MCP server implementation using native MCP library
- **Reason Archived:** Replaced by stdio-based implementation for better Cursor compatibility

### 5. `test_mcp_openmemory_endpoints.py`
- **Original Location:** `./` (root)
- **Purpose:** Test file for OpenMemory MCP endpoints
- **Reason Archived:** Root-level test file, functionality covered by other tests

## Currently Active MCP Files

The following MCP files remain in active use:

1. **`openmemory/api/mcp_stdio_server.py`**
   - **Purpose:** Stdio-based MCP server for Cursor integration
   - **Status:** ✅ Active (used in Cursor configuration)

2. **`openmemory/api/app/mcp_server.py`**
   - **Purpose:** FastAPI-integrated MCP server with SSE support
   - **Status:** ✅ Active (imported in main.py)

3. **`openmemory/api/app/mcp_cursor_fix.py`**
   - **Purpose:** Cursor-specific MCP compatibility fixes
   - **Status:** ✅ Active (imported in main.py)

## Notes

- These archived files can be restored if needed for reference or development
- The stdio-based approach (`mcp_stdio_server.py`) proved most reliable with Cursor
- The FastAPI-integrated approach continues to work for other clients
- All MCP functionality is preserved in the active implementations

## Recovery Instructions

If you need to restore any of these files:

```bash
# Example: Restore the standalone implementation
cp archive/mcp-implementations/mcp_standalone.py openmemory/api/

# Example: Restore test files
cp archive/mcp-implementations/test_mcp_*.py tests/
```
