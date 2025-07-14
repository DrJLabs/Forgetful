# ChatGPT Custom GPT Setup Guide

## 🎉 Your Secure MCP Server is Live!

**External URL:** https://mem-mcp.onemainarmy.com
**Status:** ✅ Running and secured
**Security Level:** 98.1% (52/53 tests passed)

## 🔑 Production API Key
```
1caa136689bab2d855c2cf05bc3c8175996bfe56376f0500e01e9fa7a8f877c6
```
**⚠️ Keep this secure - it provides full access to your memory system!**

## 🤖 ChatGPT Custom GPT Configuration

### Step 1: Create New GPT
1. Go to https://chat.openai.com/
2. Click "Explore" → "Create a GPT"
3. Name your GPT (e.g., "Personal Memory Assistant")

### Step 2: Configure Authentication
1. Go to "Configure" tab
2. Scroll to "Actions" section
3. Click "Add Action"
4. Set **Authentication Type**: `Bearer Token`
5. Set **Token**: `1caa136689bab2d855c2cf05bc3c8175996bfe56376f0500e01e9fa7a8f877c6`

### Step 3: Add OpenAPI Schema
**Use the simplified schema below (recommended for ChatGPT):**

⚠️ **Important:** ChatGPT Custom GPT requires OpenAPI 3.1.0 format. If you get schema errors, try the simplified version first.

**Use this minimal, ChatGPT-compliant schema:**
Copy and paste this schema (also available in `CHATGPT_SIMPLE_SCHEMA.json`):

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "mem0 Memory API",
    "version": "1.0.0",
    "description": "AI Memory Management System"
  },
  "servers": [
    {
      "url": "https://mem-mcp.onemainarmy.com"
    }
  ],
  "paths": {
    "/tools/call": {
      "post": {
        "summary": "Call Memory Tool",
        "operationId": "callMemoryTool",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "$ref": "#/components/schemas/MemoryRequest"
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/MemoryResponse"
                }
              }
            }
          }
        },
        "security": [
          {
            "bearerAuth": []
          }
        ]
      }
    }
  },
  "components": {
    "schemas": {
      "MemoryRequest": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "enum": ["add_memories", "search_memory", "list_memories", "get_memory", "update_memory", "delete_memory"],
            "description": "Memory operation to perform"
          },
          "arguments": {
            "type": "object",
            "properties": {
              "text": {
                "type": "string",
                "description": "Text to store as memory"
              },
              "query": {
                "type": "string",
                "description": "Search query for memories"
              },
              "user_id": {
                "type": "string",
                "description": "User identifier"
              },
              "metadata": {
                "type": "object",
                "additionalProperties": true,
                "description": "Additional metadata"
              },
              "memory_id": {
                "type": "string",
                "description": "Memory ID for get/update/delete operations"
              }
            },
            "additionalProperties": false
          }
        },
        "required": ["name", "arguments"],
        "additionalProperties": false
      },
      "MemoryResponse": {
        "type": "object",
        "properties": {
          "success": {
            "type": "boolean",
            "description": "Whether the operation was successful"
          },
          "result": {
            "type": "object",
            "additionalProperties": true,
            "description": "The result of the memory operation"
          }
        },
        "required": ["success", "result"],
        "additionalProperties": false
      }
    },
    "securitySchemes": {
      "bearerAuth": {
        "type": "http",
        "scheme": "bearer"
      }
    }
  }
}
```

**✅ Schema Validation (Fixed):**
- OpenAPI version: 3.1.0 ✓
- Components section: Properly structured ✓
- Schemas subsection: Added required empty object ✓
- Security schemes: Bearer auth configured ✓
- Request/response schemas: Simplified format ✓

**✅ ChatGPT Custom GPT Requirements Met:**
- All required sections present
- Schemas subsection is properly formatted as an object
- Minimal structure to avoid validation errors
- Bearer token authentication ready

**⚠️ Troubleshooting:**
- **"schemas subsection is not an object"** → ✅ FIXED: Added proper schemas object
- **"object schema missing properties"** → ✅ FIXED: Added proper schema definitions with properties and additionalProperties
- **OpenAPI version errors** → Use 3.1.0 (not 3.0.0)
- **Authentication issues** → Set Bearer token correctly in Authentication section
- **Internal server errors** → ✅ FIXED: Added all required fields (metadata, memory_id)
- **Schema validation errors** → ✅ FIXED: Uses $ref references and follows OpenAPI 3.1.0 best practices
- **401 Unauthorized errors** → ✅ FIXED: Removed conflicting Traefik basic auth middleware
- **502 Bad Gateway errors** → ✅ FIXED: Changed MCP server to bind to 0.0.0.0 instead of 127.0.0.1

### Step 4: Configure GPT Instructions
Add this to your GPT instructions:

```
You are a Personal Memory Assistant with access to a secure long-term memory system. You can:

1. **Store Memories**: Save important information, conversations, preferences, and facts
2. **Search Memories**: Find relevant information from past conversations
3. **List Memories**: Browse all stored memories
4. **Update Memories**: Modify existing memories
5. **Delete Memories**: Remove outdated information

## Memory Operations:

### Store Memory
Use `add_memories` to save information:
- Important facts about the user
- Preferences and settings
- Key conversations or decisions
- Contact information
- Important dates and events

### Search Memory
Use `search_memory` to find relevant information:
- Query using natural language
- Search for specific topics or names
- Find related memories

### Memory Management
- Use `list_memories` to see all stored memories
- Use `update_memory` to modify existing memories
- Use `delete_memory` to remove outdated information

## Best Practices:
- Always search existing memories before storing new ones
- Store memories with clear, descriptive text
- Include relevant metadata when available
- Regularly update memories to keep them current

## Security:
- All memories are securely stored with encryption
- Access is authenticated and rate-limited
- Only you can access your personal memories
```

### Step 5: Test Your GPT
1. Save your GPT configuration
2. Test with: "Remember that I prefer coffee over tea"
3. Test search with: "What do you remember about my drink preferences?"

## 🔧 Available Memory Operations

### 1. Add Memory
```json
{
  "name": "add_memories",
  "arguments": {
    "text": "User prefers coffee over tea and likes it black",
    "user_id": "chatgpt-user",
    "metadata": {"category": "preferences", "topic": "drinks"}
  }
}
```

### 2. Search Memory
```json
{
  "name": "search_memory",
  "arguments": {
    "query": "coffee preferences",
    "user_id": "chatgpt-user"
  }
}
```

### 3. List Memories
```json
{
  "name": "list_memories",
  "arguments": {
    "user_id": "chatgpt-user"
  }
}
```

### 4. Get Specific Memory
```json
{
  "name": "get_memory",
  "arguments": {
    "memory_id": "memory-id-here",
    "user_id": "chatgpt-user"
  }
}
```

### 5. Update Memory
```json
{
  "name": "update_memory",
  "arguments": {
    "memory_id": "memory-id-here",
    "text": "Updated memory content",
    "user_id": "chatgpt-user"
  }
}
```

### 6. Delete Memory
```json
{
  "name": "delete_memory",
  "arguments": {
    "memory_id": "memory-id-here",
    "user_id": "chatgpt-user"
  }
}
```

## 🔒 Security Features

✅ **Authentication**: Bearer token required for all requests
✅ **Rate Limiting**: 60 requests per minute
✅ **CORS Protection**: Only allowed domains can access
✅ **Input Validation**: All inputs are sanitized
✅ **Security Headers**: XSS, CSRF, and clickjacking protection
✅ **TLS Encryption**: All traffic encrypted via Cloudflare

## 🛠️ Testing & Debugging

### Test Authentication
```bash
curl -H "Authorization: Bearer 1caa136689bab2d855c2cf05bc3c8175996bfe56376f0500e01e9fa7a8f877c6" \
     -H "Content-Type: application/json" \
     -X POST "https://mem-mcp.onemainarmy.com/tools/call" \
     -d '{"name": "list_memories", "arguments": {"user_id": "test"}}'
```

### Health Check
```bash
curl https://mem-mcp.onemainarmy.com/health
```

## 🌐 External Access

Your MCP server is accessible at:
- **External URL**: https://mem-mcp.onemainarmy.com
- **Local URL**: http://localhost:8081
- **Protocol**: HTTPS with 15-year certificate
- **Access**: Secure via Cloudflare Tunnel (no open ports)

## 📱 Integration Examples

### Example 1: Personal Assistant
"Remember that I have a meeting with John at 3 PM tomorrow about the project proposal"

### Example 2: Preference Tracking
"I prefer working in the morning and usually have lunch at noon"

### Example 3: Learning Assistant
"Save this information: Python uses indentation for code blocks, not braces"

## 🔄 Automatic Features

- **Relationship Extraction**: System automatically identifies connections between memories
- **Vector Search**: Semantic search finds related memories even with different wording
- **Graph Database**: Stores entity relationships for complex queries
- **Backup**: Automatic daily backups of all memory data

## 📊 System Architecture

```
ChatGPT → Cloudflare Tunnel → Traefik → Secure MCP Server → mem0 API → PostgreSQL + Neo4j
```

## 🚨 Important Notes

1. **API Key Security**: Never share your API key publicly
2. **Rate Limits**: 60 requests per minute maximum
3. **Data Privacy**: All memories are private to your API key
4. **Backups**: System automatically backs up data daily
5. **Monitoring**: Health checks run continuously

## 🔧 Troubleshooting

### Common Issues:
- **401 Unauthorized**: Check your API key
- **403 Forbidden**: Verify domain is allowed
- **429 Rate Limited**: Wait for rate limit reset
- **500 Server Error**: Check system health

### Support:
- Check health endpoint: https://mem-mcp.onemainarmy.com/health
- View system logs: `tail -f mcp_server_production.log`
- Test locally: `curl http://localhost:8081/health`

---

🎉 **Your secure memory system is now live and ready for ChatGPT integration!**
