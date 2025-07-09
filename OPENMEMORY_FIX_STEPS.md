# OpenMemory Monitoring Connection Fix Guide

## 🚨 Critical Issues Found
- OpenMemory MCP API container failing to start
- OpenAI API key invalid/expired
- UI-API connection broken

## 🔧 Step-by-Step Fix Instructions

### Step 1: Fix OpenAI API Key (Critical)
```bash
# 1. Update the .env file with a valid OpenAI API key
nano .env

# Replace the OPENAI_API_KEY line with a valid key:
# OPENAI_API_KEY=sk-your-valid-key-here

# 2. Restart the containers
docker-compose restart mem0
```

### Step 2: Fix OpenMemory MCP Container (Critical)
```bash
# 1. Stop the failing container
docker stop openmemory-openmemory-mcp-1

# 2. Remove the container
docker rm openmemory-openmemory-mcp-1

# 3. Pull the latest image
docker pull mem0/openmemory-mcp:latest

# 4. Restart the OpenMemory services
docker-compose up -d openmemory-mcp

# 5. Check if it's working
docker logs openmemory-openmemory-mcp-1 --tail 20
```

### Step 3: Test the Connection
```bash
# 1. Test OpenMemory MCP API
curl -s http://localhost:8765/api/v1/memories/?user_id=test

# 2. Test main mem0 API
curl -s http://localhost:8000/memories?user_id=test

# 3. Check UI accessibility
curl -s http://localhost:3000 | grep -i "openmemory"
```

### Step 4: Verify Monitoring Endpoints
```bash
# 1. Check if health endpoints are working
curl -s http://localhost:8765/health || echo "Health endpoint not available"

# 2. Test memory operations
curl -s -H "Content-Type: application/json" -X POST "http://localhost:8765/api/v1/memories/" \
  -d '{"user_id": "test", "text": "Test memory", "app": "monitoring"}'

# 3. Test search functionality
curl -s -H "Content-Type: application/json" -X GET "http://localhost:8765/api/v1/memories/?user_id=test&search_query=test"
```

## 🏥 Health Check Script

Create a monitoring script to continuously check the connection:

```bash
#!/bin/bash
# Save as: check_openmemory_health.sh

echo "🔍 OpenMemory Health Check"
echo "=========================="

# Check UI
echo "1. Checking UI (Port 3000)..."
if curl -s http://localhost:3000 >/dev/null 2>&1; then
    echo "   ✅ UI is accessible"
else
    echo "   ❌ UI is not accessible"
fi

# Check OpenMemory MCP API
echo "2. Checking OpenMemory MCP API (Port 8765)..."
if curl -s http://localhost:8765/api/v1/memories/?user_id=test >/dev/null 2>&1; then
    echo "   ✅ OpenMemory MCP API is responding"
else
    echo "   ❌ OpenMemory MCP API is not responding"
fi

# Check Main Mem0 API
echo "3. Checking Main Mem0 API (Port 8000)..."
if curl -s http://localhost:8000/memories?user_id=test >/dev/null 2>&1; then
    echo "   ✅ Main Mem0 API is responding"
else
    echo "   ❌ Main Mem0 API is not responding"
fi

# Check containers
echo "4. Checking Docker containers..."
if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(mem0|openmemory)"; then
    echo "   ✅ Containers are running"
else
    echo "   ❌ Some containers are not running"
fi

echo "=========================="
echo "Health check complete!"
```

## 🔄 Quick Recovery Commands

If the system is completely broken:

```bash
# Nuclear option - restart everything
docker-compose down
docker-compose pull
docker-compose up -d

# Wait for services to start
sleep 30

# Check status
docker-compose ps

# Test endpoints
curl -s http://localhost:3000 | grep -i "openmemory"
curl -s http://localhost:8765/api/v1/memories/?user_id=test
curl -s http://localhost:8000/memories?user_id=test
```

## 📊 Monitoring Dashboard URLs

Once fixed, these URLs should work:

- **OpenMemory UI**: http://localhost:3000
- **OpenMemory API Docs**: http://localhost:8765/docs (if available)
- **Main Mem0 API Docs**: http://localhost:8000/docs
- **Memory Management**: http://localhost:3000/memories
- **Settings**: http://localhost:3000/settings

## 🚨 Emergency Contacts

If the above steps don't work:

1. Check Docker logs: `docker logs <container_name>`
2. Verify environment variables: `docker exec <container> env`
3. Check network connectivity: `docker network ls`
4. Review docker-compose.yml configuration

## ✅ Success Indicators

You'll know it's working when:
- ✅ All containers show "Up" status
- ✅ UI loads without errors
- ✅ API endpoints respond with JSON
- ✅ Memory operations work through UI
- ✅ No "Cannot import module" errors in logs

---
*Fix guide for mem0-stack OpenMemory monitoring system* 