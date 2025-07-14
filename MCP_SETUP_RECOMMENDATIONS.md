# mem0 MCP Setup Recommendations (Updated)

After analyzing your current mem0 repository, I've determined that **your mem0 repo does not contain a built-in MCP server**. The standard mem0 MCP method requires a separate repository. However, we can leverage your existing setup to create the standard SSE endpoints.

## 🔍 Analysis Results

**Your mem0 Repository Contains:**
- ✅ Full mem0 Python library with Memory class
- ✅ FastAPI server (`mem0/server/main.py`) - your current mem0 API at port 8000
- ✅ MCP SDK dependencies in TypeScript version
- ✅ Documentation about MCP integration
- ❌ **No standalone MCP server implementation**
- ✅ Working openmemory-mcp container that bridges to mem0 API

## 🎯 **Updated Recommendation: Modified Option 1** ⭐

Since your mem0 repository doesn't include the MCP server, but you have a working setup, here's the **best approach**:

**Use:** `./scripts/start_mem0_mcp_modified.sh`

**What it does:**
- ✅ Creates a standard SSE endpoint at `http://localhost:8080/sse`
- ✅ Uses your existing mem0 API (port 8000) as the backend
- ✅ Provides standard mem0 MCP compatibility
- ✅ No need to clone external repositories
- ✅ Leverages your existing virtual environment
- ✅ Maintains all your current data and configuration

## 🚀 Quick Start (Recommended)

1. **Start your services:**
   ```bash
   docker-compose up -d mem0 postgres-mem0 neo4j-mem0 openmemory-mcp
   ```

2. **Run the modified MCP server:**
   ```bash
   ./scripts/start_mem0_mcp_modified.sh
   ```

3. **Configure your MCP client:**
   ```json
   {
     "mem0": {
       "url": "http://localhost:8080/sse",
       "type": "sse"
     }
   }
   ```

4. **Test the connection:**
   ```bash
   curl -I http://localhost:8080/sse
   ```

## 🔧 **MCP Configuration for Your Setup:**

### For Cursor IDE (`~/.cursor/mcp.json`)
```json
{
  "mem0": {
    "url": "http://localhost:8080/sse",
    "type": "sse"
  }
}
```

### For Claude Desktop (`~/.claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "mem0": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8080/sse"]
    }
  }
}
```

### For Windsurf
```json
{
  "mcpServers": {
    "mem0": {
      "serverUrl": "http://localhost:8080/sse"
    }
  }
}
```

## 📊 **Architecture Overview**

```
MCP Client (Cursor/Claude/Windsurf)
    ↓ (SSE)
Standard MCP Server (Port 8080)  ← NEW
    ↓ (HTTP API)
mem0 API (Port 8000)             ← EXISTING
    ↓
PostgreSQL + Neo4j               ← EXISTING
```

## 🚀 **Alternative Options**

### Option 2: Enhanced Current Setup

**Use this for:** Keeping your current stdio setup but with SSE option

**Script:** `./scripts/start_mem0_mcp_enhanced.sh`

**Usage:**
```bash
# Start stdio server (current method)
./scripts/start_mem0_mcp_enhanced.sh stdio

# Start SSE server (standard method)
./scripts/start_mem0_mcp_enhanced.sh sse

# Start both servers
./scripts/start_mem0_mcp_enhanced.sh both
```

### Option 3: Original External Repository Method

**Use this for:** Using the official mem0-mcp repository

**Script:** `./scripts/start_mem0_mcp_standard.sh`

**What it does:**
- Clones `https://github.com/mem0ai/mem0-mcp`
- Configures it to use your local mem0 instance
- Requires additional setup and dependencies

## 📋 **Advantages of Modified Option 1**

1. **✅ No External Dependencies:** Uses only your existing setup
2. **✅ Standard Compliance:** Provides `/sse` endpoint that all MCP clients expect
3. **✅ Existing Data:** Works with your current PostgreSQL and Neo4j data
4. **✅ Virtual Environment:** Uses your mem0/.venv if available
5. **✅ Same Backend:** Connects to the same mem0 API you're already using
6. **✅ Health Checks:** Monitors both mem0 and openmemory services
7. **✅ Easy Configuration:** Simple SSE URL for all clients

## 🔍 **Command Reference**

```bash
# Start the modified standard MCP server
./scripts/start_mem0_mcp_modified.sh

# Check if services are ready
./scripts/start_mem0_mcp_modified.sh check

# Show configuration templates
./scripts/start_mem0_mcp_modified.sh config

# Test endpoints
curl http://localhost:8080/health
curl -I http://localhost:8080/sse
```

## 🛠 **Troubleshooting**

### Service Health Check
```bash
# Check all services
./scripts/start_mem0_mcp_modified.sh check

# Check individual services
curl -s http://localhost:8000/health  # mem0 API
curl -s http://localhost:8080/health  # Standard MCP Server
curl -s http://localhost:8765/health  # Current MCP Server
```

### Port Usage
- **8000**: mem0 API (existing)
- **8080**: Standard SSE MCP Server (new)
- **8765**: Current stdio MCP Server (existing)

### Common Issues

1. **Port 8080 in use:** Change `MCP_PORT=8080` in the script
2. **Virtual environment issues:** Script will fall back to system Python
3. **Service not running:** Run `docker-compose up -d` first
4. **Client connection:** Ensure you're using `http://localhost:8080/sse`

## 📚 **Files Created by Modified Setup**

1. **`standard_mem0_mcp_server.py`** - The SSE MCP server implementation
2. **`standard_mcp_requirements.txt`** - Python dependencies
3. **`scripts/start_mem0_mcp_modified.sh`** - Startup script

## 🤝 **Support**

The modified approach gives you:
- **Standard mem0 MCP compliance** ✅
- **Your existing data and setup** ✅
- **All MCP client compatibility** ✅
- **No external repository dependencies** ✅

This is the **optimal solution** given that your mem0 repository doesn't contain the MCP server implementation, but you have a fully functional memory system running.
