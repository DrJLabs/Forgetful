# ChatGPT Actions Bridge - Systematic Troubleshooting Roadmap

**Date**: July 17, 2025
**Status**: Code updated, container restarted - ready for systematic verification
**Objective**: Verify full end-to-end functionality from ChatGPT through bridge to memory storage/retrieval

## 🎯 **TESTING STRATEGY**

This document provides a **step-by-step verification process** to identify exactly where the ChatGPT Actions integration breaks down. Each step must be **fully verified** before proceeding to the next.

---

## 📋 **PHASE 1: INFRASTRUCTURE VERIFICATION**

### ✅ **Step 1.1: Container Health Check**
**Objective**: Verify all required services are running and healthy

**Commands to Run**:
```bash
# Check service status
docker compose ps | grep -E "(gpt-actions-bridge|openmemory-mcp|mem0|postgres|neo4j)"

# Check container health
docker compose logs gpt-actions-bridge --tail=5
docker compose logs openmemory-mcp --tail=5
```

**Expected Results**:
- All containers showing "Up" status
- gpt-actions-bridge showing "(healthy)" status
- No error messages in recent logs

**Pass Criteria**: ✅ All services healthy with no errors

---

### ✅ **Step 1.2: Network Connectivity**
**Objective**: Verify internal Docker network communication

**Commands to Run**:
```bash
# Test bridge -> OpenMemory connectivity
docker exec gpt-actions-bridge curl -s http://openmemory-mcp:8765/health

# Test bridge -> mem0 connectivity
docker exec gpt-actions-bridge curl -s http://mem0:8000/docs

# Test external access
curl -s https://mem-mcp.onemainarmy.com/health
```

**Expected Results**:
- Internal health checks return 200 OK
- External HTTPS access working
- No connection timeouts or DNS failures

**Pass Criteria**: ✅ All network paths functional

---

## 📋 **PHASE 2: AUTHENTICATION & AUTHORIZATION**

### ✅ **Step 2.1: API Key Validation**
**Objective**: Verify bridge authentication is working correctly

**Commands to Run**:
```bash
# Test valid API key
curl -H "Authorization: Bearer gpt_your_api_key_here_replace_with_actual_token" \
  "https://mem-mcp.onemainarmy.com/health"

# Test invalid API key (should fail)
curl -H "Authorization: Bearer invalid_key" \
  "https://mem-mcp.onemainarmy.com/health"

# Test missing API key (should fail)
curl "https://mem-mcp.onemainarmy.com/health"
```

**Expected Results**:
- Valid key: 200 OK with health status
- Invalid key: 401 Unauthorized
- Missing key: 401 Unauthorized

**Pass Criteria**: ✅ Authentication properly enforced

---

### ✅ **Step 2.2: Request Routing**
**Objective**: Verify requests are properly routed through the bridge

**Commands to Run**:
```bash
# Check bridge logs while making request
docker compose logs gpt-actions-bridge --follow &
curl -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  "https://mem-mcp.onemainarmy.com/memories?user_id=test_routing"
pkill -f "docker compose logs"
```

**Expected Results**:
- Bridge logs show incoming request
- Request forwarded to backend services
- Response returned to client

**Pass Criteria**: ✅ Request routing functioning

---

## 📋 **PHASE 3: BACKEND SERVICE VERIFICATION**

### ✅ **Step 3.1: OpenMemory Service Health**
**Objective**: Verify OpenMemory MCP service is fully operational

**Commands to Run**:
```bash
# Direct health check
docker exec gpt-actions-bridge curl -v http://openmemory-mcp:8765/health

# Check OpenAI API configuration
docker compose logs openmemory-mcp --tail=20 | grep -i openai

# Test direct API access
docker exec gpt-actions-bridge curl -s "http://openmemory-mcp:8765/api/v1/memories?user_id=health_test"
```

**Expected Results**:
- Health endpoint returns 200 OK
- OpenAI API key loaded correctly
- Direct API access working

**Pass Criteria**: ✅ OpenMemory service fully functional

---

### ✅ **Step 3.2: Database Connectivity**
**Objective**: Verify PostgreSQL and Neo4j connections

**Commands to Run**:
```bash
# Check PostgreSQL connection
docker exec postgres-mem0 psql -U $DATABASE_USER -d mem0 -c "\dt"

# Check Neo4j connection
docker exec neo4j-mem0 cypher-shell -u neo4j -p $NEO4J_PASSWORD "MATCH (n) RETURN count(n) LIMIT 1"

# Check OpenMemory database connections
docker compose logs openmemory-mcp | grep -i "connection\|database\|postgres\|neo4j"
```

**Expected Results**:
- PostgreSQL shows memory-related tables
- Neo4j connection successful
- No database connection errors in logs

**Pass Criteria**: ✅ All databases accessible

---

## 📋 **PHASE 4: ENDPOINT FUNCTIONALITY TESTING**

### ✅ **Step 4.1: Memory Listing (GET /memories)**
**Objective**: Verify memory retrieval endpoint works correctly

**Commands to Run**:
```bash
# Test with existing user
curl -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  "https://mem-mcp.onemainarmy.com/memories?user_id=test_user" | jq

# Test with non-existent user
curl -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  "https://mem-mcp.onemainarmy.com/memories?user_id=nonexistent_user_123" | jq

# Check bridge logs during request
docker compose logs gpt-actions-bridge --tail=10
```

**Expected Results**:
- Existing user: Returns memory list (may be empty)
- Non-existent user: Returns empty list or creates user
- No 500 errors or exceptions

**Pass Criteria**: ✅ Memory listing functional

---

### ✅ **Step 4.2: Memory Search (POST /memories/search)**
**Objective**: Verify memory search functionality

**Commands to Run**:
```bash
# Test basic search
curl -X POST -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  -H "Content-Type: application/json" \
  -d '{"query":"test search","user_id":"test_user","limit":5}' \
  "https://mem-mcp.onemainarmy.com/memories/search" | jq

# Test search with non-existent user
curl -X POST -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  -H "Content-Type: application/json" \
  -d '{"query":"test","user_id":"search_test_user","limit":3}' \
  "https://mem-mcp.onemainarmy.com/memories/search" | jq

# Check OpenMemory logs
docker compose logs openmemory-mcp --tail=10
```

**Expected Results**:
- Search returns structured response
- No OpenAI API errors
- No database connection issues

**Pass Criteria**: ✅ Memory search functional

---

### ✅ **Step 4.3: Memory Creation (POST /memories)**
**Objective**: Verify memory creation pipeline works end-to-end

**Commands to Run**:
```bash
# Test with existing user
curl -X POST -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  -H "Content-Type: application/json" \
  -d '{
    "messages":[
      {"role":"user","content":"I love pizza with pepperoni"},
      {"role":"assistant","content":"Great! I'\''ll remember your pizza preference."}
    ],
    "user_id":"test_user",
    "metadata":{"category":"food_preferences","test":"endpoint_verification"}
  }' \
  "https://mem-mcp.onemainarmy.com/memories" | jq

# Test with new user (auto-creation)
curl -X POST -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  -H "Content-Type: application/json" \
  -d '{
    "messages":[
      {"role":"user","content":"Testing memory creation for new user"}
    ],
    "user_id":"creation_test_user_$(date +%s)",
    "metadata":{"test":"new_user_creation"}
  }' \
  "https://mem-mcp.onemainarmy.com/memories" | jq

# Monitor all service logs during creation
docker compose logs --follow gpt-actions-bridge openmemory-mcp &
# Run test above, then stop logs
pkill -f "docker compose logs"
```

**Expected Results**:
- Memory creation returns success response
- No OpenAI API errors in logs
- User auto-creation working if needed
- Memory IDs returned in response

**Pass Criteria**: ✅ Memory creation fully functional

---

## 📋 **PHASE 5: CHATGPT INTEGRATION TESTING**

### ✅ **Step 5.1: OpenAPI Schema Validation**
**Objective**: Verify ChatGPT can import and validate the API schema

**Commands to Run**:
```bash
# Get OpenAPI schema
curl -s "https://mem-mcp.onemainarmy.com/openapi.json" | jq '.servers'

# Validate schema structure
curl -s "https://mem-mcp.onemainarmy.com/openapi.json" | jq '.paths | keys'

# Check authentication setup
curl -s "https://mem-mcp.onemainarmy.com/openapi.json" | jq '.components.securitySchemes'
```

**Expected Results**:
- Server URL shows correct HTTPS endpoint
- All expected paths present (/memories, /memories/search, /health)
- Bearer token authentication properly defined

**Pass Criteria**: ✅ OpenAPI schema valid for ChatGPT

---

### ✅ **Step 5.2: Production Request Simulation**
**Objective**: Simulate exact requests ChatGPT would make

**Commands to Run**:
```bash
# Simulate ChatGPT memory creation request
curl -X POST "https://mem-mcp.onemainarmy.com/memories" \
  -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  -H "Content-Type: application/json" \
  -H "User-Agent: ChatGPT-Actions/1.0" \
  -d '{
    "messages": [
      {"role": "user", "content": "I prefer TypeScript over JavaScript for large projects"},
      {"role": "assistant", "content": "Understood! I'\''ll remember your preference for TypeScript in large projects."}
    ],
    "user_id": "chatgpt_user_simulation",
    "metadata": {
      "source": "chatgpt_actions",
      "session_id": "test_session_123"
    }
  }' | jq

# Simulate ChatGPT memory search request
curl -X POST "https://mem-mcp.onemainarmy.com/memories/search" \
  -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  -H "Content-Type: application/json" \
  -H "User-Agent: ChatGPT-Actions/1.0" \
  -d '{
    "query": "programming language preferences",
    "user_id": "chatgpt_user_simulation",
    "limit": 5
  }' | jq
```

**Expected Results**:
- Both requests succeed with 200 OK
- Memory creation works end-to-end
- Search returns relevant results

**Pass Criteria**: ✅ Production simulation successful

---

## 📋 **PHASE 6: ERROR HANDLING & EDGE CASES**

### ✅ **Step 6.1: Error Response Testing**
**Objective**: Verify proper error handling and responses

**Commands to Run**:
```bash
# Test malformed JSON
curl -X POST "https://mem-mcp.onemainarmy.com/memories" \
  -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  -H "Content-Type: application/json" \
  -d '{invalid json}' -v

# Test missing required fields
curl -X POST "https://mem-mcp.onemainarmy.com/memories" \
  -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  -H "Content-Type: application/json" \
  -d '{"messages":[]}' -v

# Test rate limiting (if configured)
for i in {1..10}; do
  curl -X POST "https://mem-mcp.onemainarmy.com/memories/search" \
    -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
    -H "Content-Type: application/json" \
    -d '{"query":"rate test","user_id":"rate_test"}' &
done
wait
```

**Expected Results**:
- Malformed JSON: 400 Bad Request with clear error message
- Missing fields: 422 Validation Error with field details
- Rate limiting: Appropriate 429 responses if configured

**Pass Criteria**: ✅ Error handling appropriate

---

## 📋 **PHASE 7: PERFORMANCE & MONITORING**

### ✅ **Step 7.1: Response Time Testing**
**Objective**: Verify acceptable performance for ChatGPT integration

**Commands to Run**:
```bash
# Test response times
time curl -X POST "https://mem-mcp.onemainarmy.com/memories" \
  -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Performance test"}],"user_id":"perf_test"}'

# Test concurrent requests
for i in {1..5}; do
  curl -X POST "https://mem-mcp.onemainarmy.com/memories/search" \
    -H "Authorization: Bearer gpt_2d52fe5a917fe9ffcea22d2f782c37e1637a66f2dffd965e5b946e6f9902dd14" \
    -H "Content-Type: application/json" \
    -d '{"query":"concurrent test","user_id":"concurrent_'$i'"}' &
done
wait
```

**Expected Results**:
- Response times under 5 seconds for memory creation
- Response times under 2 seconds for search
- Concurrent requests handled without errors

**Pass Criteria**: ✅ Performance acceptable

---

## 📋 **TROUBLESHOOTING CHECKLIST**

### 🚨 **Common Failure Points**

1. **Authentication Failures**
   - Check API key format and validity
   - Verify Authorization header format
   - Check bridge authentication middleware

2. **OpenAI API Issues**
   - Verify `OPENAI_API_KEY` environment variable
   - Check `OPENAI_MODEL=gpt-4o-mini` configuration
   - Monitor OpenAI API rate limits and quota

3. **Database Connection Issues**
   - Verify PostgreSQL and Neo4j health
   - Check database credentials and connection strings
   - Monitor connection pool exhaustion

4. **Network/Docker Issues**
   - Verify service discovery between containers
   - Check Docker network configuration
   - Verify Traefik routing and Cloudflare tunnel

5. **User Management Issues**
   - Check user auto-creation logic
   - Verify user existence before operations
   - Monitor user-related database operations

---

## 📝 **NEXT STEPS AFTER VERIFICATION**

1. **If All Tests Pass**: Document the working configuration and integrate with ChatGPT
2. **If Tests Fail**: Identify the specific failure point and fix root cause
3. **Performance Issues**: Optimize slow endpoints and add caching if needed
4. **Error Handling**: Improve error messages and add better logging

---

**Status**: 🟡 Ready for systematic verification
**Last Updated**: July 17, 2025
**Container Status**: Rebuilt and restarted with latest code
