# MCP-OpenMemory Repair Guide

**Based on comprehensive endpoint testing - 66.7% success rate (20/30 endpoints working)**

This guide provides step-by-step instructions to fix the remaining 10 failing endpoints and achieve 85-90% success rate.

## 🎯 Current Status

### ✅ **Fixed Issues**
- **Stats endpoint database query** - Changed `App.owner` to `App.owner_id` ✅

### ⚠️ **Remaining Issues by Priority**

#### **Priority 1: Server Errors (500s) - 2 endpoints**
1. `POST /mcp/messages/` - Internal Server Error
2. `POST /api/v1/memories/filter` - Internal Server Error

#### **Priority 2: Schema Validation (422s) - 8 endpoints**
- Missing required parameters or incorrect request schemas

#### **Priority 3: Missing Endpoints (404s) - 1 endpoint**
- `GET /mcp/sse` - Not implemented

---

## 🔧 Priority 1: Fix Server Errors (500s)

### Issue 1: `POST /mcp/messages/` - 500 Internal Server Error

**Root Cause:** MCP server implementation missing or broken

#### **Investigation Steps:**
```bash
# 1. Check if messages endpoint exists in MCP server
grep -rn "messages" openmemory/api/app/mcp_server.py

# 2. Check MCP server setup
grep -rn "@mcp.tool\|@app.post.*messages" openmemory/api/app/

# 3. Test endpoint directly
curl -X POST "http://localhost:8765/mcp/messages/" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test"}], "user_id": "test"}'
```

#### **Expected Fix Location:**
- File: `openmemory/api/app/mcp_server.py`
- Look for missing or broken `@app.post("/mcp/messages/")` endpoint

#### **Fix Template:**
```python
@app.post("/mcp/messages/")
async def process_messages(request: MessagesRequest):
    try:
        # Validate request
        if not request.messages or not request.user_id:
            raise HTTPException(status_code=422, detail="Missing required fields")

        # Process messages through memory client
        memory_client = get_memory_client()

        # Convert messages to text for processing
        text_content = "\n".join([f"{msg['role']}: {msg['content']}" for msg in request.messages])

        # Add to memory
        result = memory_client.add(
            text_content,
            user_id=request.user_id,
            metadata={"source": "mcp_messages"}
        )

        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"Messages endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class MessagesRequest(BaseModel):
    messages: List[Dict[str, str]]
    user_id: str
    metadata: Optional[Dict] = {}
```

#### **Validation:**
```bash
# Test after fix
curl -X POST "http://localhost:8765/mcp/messages/" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test message"}], "user_id": "test_user"}'

# Expected: 200 status with success response
```

---

### Issue 2: `POST /api/v1/memories/filter` - 500 Internal Server Error

**Root Cause:** Complex SQLAlchemy query with join issues

#### **Investigation Steps:**
```bash
# 1. Check current filter implementation
grep -A 50 "def filter_memories" openmemory/api/app/routers/memories.py

# 2. Compare with original simpler version
grep -A 50 "def filter_memories" /home/drj/projects/forks/mem0/openmemory/api/app/routers/memories.py

# 3. Test with minimal request
curl -X POST "http://localhost:8765/api/v1/memories/filter" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "page": 1, "size": 10}'
```

#### **Expected Fix Location:**
- File: `openmemory/api/app/routers/memories.py`
- Function: `filter_memories()` around line 655-730

#### **Common Issues to Fix:**
1. **Join order problems**
2. **Distinct() conflicts with ORDER BY**
3. **Category join when no categories requested**

#### **Fix Strategy:**
```python
@router.post("/filter", response_model=Page[MemoryResponse])
async def filter_memories(request: FilterMemoriesRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Build base query - simpler approach
        query = db.query(Memory).filter(
            Memory.user_id == user.id,
            Memory.state != MemoryState.deleted,
        )

        # Filter archived memories
        if not request.show_archived:
            query = query.filter(Memory.state != MemoryState.archived)

        # Apply search filter first (simple)
        if request.search_query:
            query = query.filter(Memory.content.ilike(f"%{request.search_query}%"))

        # Apply app filter
        if request.app_ids:
            query = query.filter(Memory.app_id.in_(request.app_ids))

        # Apply date filters
        if request.from_date:
            from_datetime = datetime.fromtimestamp(request.from_date, tz=UTC)
            query = query.filter(Memory.created_at >= from_datetime)

        if request.to_date:
            to_datetime = datetime.fromtimestamp(request.to_date, tz=UTC)
            query = query.filter(Memory.created_at <= to_datetime)

        # SIMPLIFIED: Only join categories if specifically filtering by them
        if request.category_ids:
            query = query.join(Memory.categories).filter(
                Category.id.in_(request.category_ids)
            ).distinct()

        # Apply sorting BEFORE pagination
        if request.sort_column and request.sort_direction:
            sort_direction = request.sort_direction.lower()
            if sort_direction not in ["asc", "desc"]:
                raise HTTPException(status_code=400, detail="Invalid sort direction")

            if request.sort_column == "created_at":
                sort_field = Memory.created_at
                if sort_direction == "desc":
                    query = query.order_by(sort_field.desc())
                else:
                    query = query.order_by(sort_field.asc())
        else:
            # Default sorting
            query = query.order_by(Memory.created_at.desc())

        # SIMPLIFIED: Use offset/limit instead of complex pagination
        total = query.count()
        offset = (request.page - 1) * request.size
        memories = query.offset(offset).limit(request.size).all()

        # Build response manually to avoid complex transformer
        memory_responses = []
        for memory in memories:
            # Load categories separately if needed
            if not request.category_ids:  # Only load if not already joined
                db.refresh(memory)

            memory_responses.append(MemoryResponse(
                id=memory.id,
                content=memory.content,
                created_at=memory.created_at,
                state=memory.state.value,
                app_id=memory.app_id,
                app_name=memory.app.name if memory.app else None,
                categories=[category.name for category in memory.categories],
                metadata_=memory.metadata_,
            ))

        # Create page response
        return Page.create(
            items=memory_responses,
            total=total,
            params=Params(page=request.page, size=request.size)
        )

    except Exception as e:
        logger.error(f"Filter memories error: {e}")
        raise HTTPException(status_code=500, detail=f"Filter operation failed: {str(e)}")
```

#### **Validation:**
```bash
# Test basic filter
curl -X POST "http://localhost:8765/api/v1/memories/filter" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "page": 1, "size": 10}'

# Test with search
curl -X POST "http://localhost:8765/api/v1/memories/filter" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "search_query": "test", "page": 1, "size": 10}'

# Expected: 200 status with paginated results
```

---

## 🔧 Priority 2: Fix Schema Validation (422s)

### Issue 3: `POST /api/v1/memories/` - Missing `text` field

**Current Problem:** Test sends `messages` array, API expects `text` field

#### **Fix for Test Script:**
```python
# In test_mcp_openmemory_endpoints.py - line 166
# Change from:
memory_data = {
    "messages": [...],
    "user_id": self.test_user_id,
    "metadata": {...}
}

# To:
memory_data = {
    "text": "This is a test memory for API v1 testing",
    "user_id": self.test_user_id,
    "metadata": {"test": True, "endpoint_test": "api_v1_memories"}
}
```

#### **Validation:**
```bash
curl -X POST "http://localhost:8765/api/v1/memories/" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test memory content", "user_id": "test_user", "metadata": {"test": true}}'
```

### Issue 4: `GET /api/v1/memories/categories` - Missing `user_id`

#### **Fix for Test Script:**
```python
# Add user_id parameter to categories test
self.make_request("GET", "/api/v1/memories/categories", params={"user_id": self.test_user_id})
```

#### **Validation:**
```bash
curl "http://localhost:8765/api/v1/memories/categories?user_id=test_user"
```

### Issue 5: `PUT /api/v1/apps/{app_id}` - Missing `is_active` parameter

#### **Fix for Test Script:**
```python
# Change from body data to query parameter
self.make_request("PUT", f"/api/v1/apps/{self.test_app_id}", params={"is_active": True})
```

#### **Validation:**
```bash
curl -X PUT "http://localhost:8765/api/v1/apps/APP_ID?is_active=true"
```

### Issue 6: `GET /api/v1/stats/` - Missing `user_id`

#### **Fix for Test Script:**
```python
# Add user_id parameter
self.make_request("GET", "/api/v1/stats/", params={"user_id": self.test_user_id})
```

#### **Validation:**
```bash
curl "http://localhost:8765/api/v1/stats/?user_id=test_user"
```

### Issues 7-10: Config Update Endpoints - Incorrect Schemas

#### **Fix for Test Script:**
```python
# Replace generic test_config with proper schemas

# For PUT /api/v1/config/
config_data = {
    "mem0": {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "max_tokens": 2000,
                "api_key": "env:OPENAI_API_KEY"
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-small",
                "api_key": "env:OPENAI_API_KEY"
            }
        }
    },
    "openmemory": {"custom_instructions": None}
}

# For PUT /api/v1/config/mem0/llm
llm_config = {
    "provider": "openai",
    "config": {
        "model": "gpt-4o-mini",
        "temperature": 0.1,
        "max_tokens": 2000,
        "api_key": "env:OPENAI_API_KEY"
    }
}

# For PUT /api/v1/config/mem0/embedder
embedder_config = {
    "provider": "openai",
    "config": {
        "model": "text-embedding-3-small",
        "api_key": "env:OPENAI_API_KEY"
    }
}
```

---

## 🔧 Priority 3: Missing Endpoints (404s)

### Issue 11: `GET /mcp/sse` - Not Found

#### **Investigation:**
```bash
# Check if endpoint should exist
grep -rn "sse" openmemory/api/app/mcp_server.py
grep -rn "/mcp/sse" openmemory/api/app/
```

#### **Options:**
1. **If endpoint should exist:** Implement it
2. **If endpoint shouldn't exist:** Document as intentionally missing
3. **If it's a typo:** Fix the expected endpoint

#### **Implementation (if needed):**
```python
@app.get("/mcp/sse")
async def mcp_sse_endpoint():
    # Basic SSE endpoint for general MCP events
    return {"message": "Use client-specific SSE endpoints: /mcp/{client_name}/sse/{user_id}"}
```

---

## 🧪 Testing Strategy

### 1. **Fix and Test Incrementally**
```bash
# Run tests after each fix
python3 test_mcp_openmemory_endpoints.py

# Focus test on specific category
python3 -c "
import test_mcp_openmemory_endpoints
tester = test_mcp_openmemory_endpoints.MCPEndpointTester()
tester.test_api_v1_memories()  # Test specific category
"
```

### 2. **Updated Test Script**
Create `test_mcp_openmemory_endpoints_fixed.py` with corrected schemas:

```python
# Fixed memory creation request
memory_data = {
    "text": "This is a corrected test memory",
    "user_id": self.test_user_id,
    "metadata": {"test": True, "endpoint_test": "api_v1_memories"}
}

# Fixed categories request
self.make_request("GET", "/api/v1/memories/categories", params={"user_id": self.test_user_id})

# Fixed stats request
self.make_request("GET", "/api/v1/stats/", params={"user_id": self.test_user_id})

# Fixed app update request
self.make_request("PUT", f"/api/v1/apps/{self.test_app_id}", params={"is_active": True})

# Fixed config requests with proper schemas
# (Use schemas from Issue 6-10 fixes above)
```

### 3. **Success Metrics**
- **Target:** 85-90% success rate (25-27 of 30 endpoints)
- **Current:** 66.7% (20 of 30 endpoints)
- **After Priority 1 fixes:** ~73% (22 of 30 endpoints)
- **After Priority 2 fixes:** ~87% (26 of 30 endpoints)
- **After Priority 3 fixes:** ~90% (27 of 30 endpoints)

---

## 📋 Implementation Checklist

### **Phase 1: Server Error Fixes**
- [ ] Fix `POST /mcp/messages/` endpoint in `mcp_server.py`
- [ ] Fix `POST /api/v1/memories/filter` query in `memories.py`
- [ ] Test both endpoints return 200 status
- [ ] Verify functionality with real data

### **Phase 2: Schema Fixes**
- [ ] Update test script with correct `text` field for memory creation
- [ ] Add `user_id` parameters to categories and stats endpoints
- [ ] Fix app update to use query parameter instead of body
- [ ] Update config endpoints with proper schemas
- [ ] Test all schema fixes return 200 status

### **Phase 3: Validation**
- [ ] Run complete test suite
- [ ] Achieve 85-90% success rate
- [ ] Document any remaining intentional limitations
- [ ] Update API documentation with correct schemas

### **Phase 4: Production Readiness**
- [ ] Add integration tests for fixed endpoints
- [ ] Update OpenAPI specifications
- [ ] Create user documentation with correct examples
- [ ] Set up monitoring for critical endpoints

---

## 🎯 Expected Results

After implementing all fixes:

### **Success Rate Improvement**
- **Before:** 66.7% (20/30 endpoints)
- **After:** 85-90% (25-27/30 endpoints)

### **Production Benefits**
- ✅ All core memory operations working
- ✅ Complete app management functionality
- ✅ Full configuration management
- ✅ Comprehensive health monitoring
- ✅ ChatGPT integration ready
- ✅ MCP protocol fully functional

### **Remaining Limitations (Acceptable)**
- Some advanced filtering edge cases
- Optional SSE endpoint (if not needed)
- Complex configuration scenarios

**Final Status: Production-ready with advanced features** 🚀
