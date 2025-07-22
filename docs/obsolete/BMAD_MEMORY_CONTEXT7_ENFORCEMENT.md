# BMad mem0 & Context7 Enforcement Implementation

## 🎯 Overview

This document outlines the complete implementation of enforcing mem0 memory system and Context7 MCP server usage across all BMad agents. The enforcement ensures that agents cannot operate without these external services being accessible and actively used.

## 📋 What Was Changed

### 1. **Core Configuration (.bmad-core/core-config.yaml)**

Added external services configuration and agent defaults:

```yaml
# External Services Configuration - MANDATORY for all agents
externalServices:
  mem0:
    enabled: true
    apiUrl: "http://localhost:8000"
    enforceUsage: true
    defaultUserId: "drj"
    searchBeforeResponse: true
    healthCheckRequired: true
  context7:
    enabled: true
    enforceDocLookup: true
    serverUrl: "http://localhost:8765"
    lookupBeforeTechnical: true
    healthCheckRequired: true

# Agent Behavior Defaults - Applied to all BMad agents
agentDefaults:
  memoryEnabled: true
  contextLookupRequired: true
  healthCheckRequired: true
  preExecutionChecks:
    - validateMem0Service
    - validateContext7Service
  mandatoryOperations:
    - searchMemoryBeforeResponse
    - lookupDocsForTechnical
    - storeImportantContext
```

### 2. **BMad Orchestrator Agent (.bmad-core/agents/bmad-orchestrator.md)**

**Added to activation-instructions:**
- Service validation before operations
- Mandatory memory search before responses
- Mandatory Context7 lookup for technical queries
- Enforcement inheritance for transformed agents

**Added to core_principles:**
- MANDATORY mem0 memory search (user_id: "drj")
- MANDATORY Context7 MCP usage for technical documentation
- Service accessibility validation
- Context storage after interactions

### 3. **BMad Master Agent (.bmad-core/agents/bmad-master.md)**

**Added identical enforcement to:**
- activation-instructions
- core_principles

Both agents now enforce the same requirements for consistency.

### 4. **Service Validation Scripts**

Created two validation scripts:

#### **Python Script (validate_bmad_services.py)**
- Comprehensive service validation
- Detailed error reporting
- JSON-formatted results
- Timeout handling
- Uses correct endpoints: `/docs` for mem0, `/api/v1/config/` for Context7

#### **Shell Script (validate_bmad_services.sh)**
- Quick validation with colored output
- Clear instructions for fixing issues
- Exit codes for automation
- Uses correct endpoints: `/docs` for mem0, `/api/v1/config/` for Context7

## 🔧 How It Works

### **Enforcement Flow:**
1. **Agent Activation**: Agents validate services before operations
2. **Pre-Response Check**: Memory search occurs before every response
3. **Technical Queries**: Context7 lookup required for technical documentation
4. **Post-Interaction**: Important context stored in mem0
5. **Transformation**: Enforcement inherited by all transformed agents

### **Service Dependencies:**
- **mem0 API**: `http://localhost:8000` (validates via `/docs` endpoint)
- **Context7 MCP**: `http://localhost:8765` (validates via `/api/v1/config/` endpoint)
- **Required Services**: mem0, postgres-mem0, neo4j-mem0, openmemory-mcp

## 🚀 How to Use

### **1. Start Required Services**
```bash
# Start mem0 stack
docker-compose up -d mem0 postgres-mem0 neo4j-mem0

# Start Context7 MCP server
docker-compose up -d openmemory-mcp
```

### **2. Validate Services**
```bash
# Quick validation
./validate_bmad_services.sh

# Detailed validation
python validate_bmad_services.py
```

### **3. Use BMad Agents**
```bash
# BMad Orchestrator
@bmad-orchestrator

# BMad Master
@bmad-master
```

## ⚠️ Important Notes

### **Service Validation:**
- Agents will **halt operations** if services are not accessible
- Clear error messages guide users to start required services
- Validation occurs at agent activation and before critical operations

### **Memory Operations:**
- All agent responses include memory search
- Important context automatically stored
- User ID defaults to "drj" but can be configured

### **Context7 Operations:**
- Technical queries automatically trigger documentation lookup
- Framework/library mentions require Context7 consultation
- Official documentation cited in responses

### **Enforcement Inheritance:**
- BMad Orchestrator enforces requirements on transformed agents
- All agents in the ecosystem inherit these requirements
- Consistent behavior across all BMad operations

## 🔍 Validation Examples

### **Successful Validation:**
```bash
🔍 BMad Service Validation
=========================
📁 mem0 Memory System:
  Checking mem0 API... ✅ Accessible
📚 Context7 MCP Server:
  Checking Context7 MCP... ✅ Accessible

🎯 Overall Status:
✅ All services accessible - BMad operations can proceed!
```

### **Failed Validation:**
```bash
🔍 BMad Service Validation
=========================
📁 mem0 Memory System:
  Checking mem0 API... ❌ Not accessible
📚 Context7 MCP Server:
  Checking Context7 MCP... ❌ Not accessible

🎯 Overall Status:
❌ Some services not accessible - BMad operations should not proceed

⚠️  Required Actions:
  🚀 Start mem0 services:
     docker-compose up -d mem0 postgres-mem0 neo4j-mem0
  🚀 Start Context7 MCP server:
     docker-compose up -d openmemory-mcp
```

## 🎯 Key Benefits

1. **Enforced Memory Usage**: All agents automatically use persistent memory
2. **Up-to-Date Documentation**: Context7 ensures current official documentation
3. **Consistent Behavior**: All agents follow the same requirements
4. **Service Reliability**: Validation prevents operations with broken services
5. **Clear Error Messages**: Users know exactly what to fix

## 🔧 Customization Options

### **User ID Configuration:**
Change the default user ID in core-config.yaml:
```yaml
externalServices:
  mem0:
    defaultUserId: "your-user-id"
```

### **Service URLs:**
Update service URLs in core-config.yaml:
```yaml
externalServices:
  mem0:
    apiUrl: "http://your-mem0-host:8000"
  context7:
    serverUrl: "http://your-context7-host:8765"
```

### **Enforcement Level:**
Adjust enforcement strictness:
```yaml
agentDefaults:
  healthCheckRequired: true    # Strict validation
  memoryEnabled: true          # Always use memory
  contextLookupRequired: true  # Always lookup docs
```

## 📝 Files Modified

1. `.bmad-core/core-config.yaml` - External services configuration
2. `.bmad-core/agents/bmad-orchestrator.md` - Master orchestrator enforcement
3. `.bmad-core/agents/bmad-master.md` - Master executor enforcement
4. `validate_bmad_services.py` - Python validation script
5. `validate_bmad_services.sh` - Shell validation script
6. `BMAD_MEMORY_CONTEXT7_ENFORCEMENT.md` - This documentation

## ✅ Testing

### **Test Service Validation:**
```bash
# Test with services down
docker-compose down
./validate_bmad_services.sh  # Should show errors

# Test with services up
docker-compose up -d mem0 postgres-mem0 neo4j-mem0 openmemory-mcp
./validate_bmad_services.sh  # Should show success
```

### **Test Agent Enforcement:**
```bash
# This should trigger service validation
@bmad-orchestrator
# Agent should validate services before proceeding
```

## 🏆 Success Criteria

The enforcement is working correctly when:
- ✅ Agents validate services before operations
- ✅ Memory search occurs before responses
- ✅ Context7 lookup happens for technical queries
- ✅ Clear error messages when services are down
- ✅ Agents halt operations with broken services
- ✅ All BMad agents inherit these requirements

**Your BMad system now enforces mem0 and Context7 usage across all agents!** 🎯
