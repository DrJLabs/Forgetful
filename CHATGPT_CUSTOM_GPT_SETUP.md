# ChatGPT Custom GPT Setup Guide

## Overview

This guide shows how to create a custom ChatGPT that can access your mem0 MCP server to store and retrieve memories.

## Prerequisites

1. **ChatGPT Plus subscription** (required for custom GPTs)
2. **Deployed MCP server** at `https://mem-mcp.onemainarmy.com`
3. **API key** from your MCP server deployment

## Step-by-Step Setup

### 1. Create a New Custom GPT

1. Go to [ChatGPT](https://chat.openai.com)
2. Click on your profile → "My GPTs"
3. Click "Create a GPT"
4. Switch to "Configure" tab

### 2. Basic Configuration

**Name**: `Mem0 Memory Assistant`

**Description**:
```
I can help you store and retrieve memories using your personal mem0 memory system. I can:
- Store new memories from our conversations
- Search through your stored memories
- List all your memories
- Help you organize and recall information
```

**Instructions**:
```
You are a memory assistant powered by mem0. You can help users store, search, and retrieve memories from their personal memory system.

Key capabilities:
- add_memories: Store new information or insights from conversations
- search_memory: Find relevant memories based on queries
- list_memories: Show all stored memories

Always be helpful and explain what you're doing when storing or retrieving memories. When storing memories, make them clear and useful for future reference.
```

### 3. Actions Configuration

1. In the "Actions" section, click "Create new action"
2. Click "Import from URL" and enter: `https://mem-mcp.onemainarmy.com/openapi.json`

   OR copy and paste the OpenAPI schema from `chatgpt_custom_gpt_config.json`

### 4. Authentication Setup

1. In the Authentication section, select "API Key"
2. Set:
   - **API Key**: Your MCP server API key
   - **Auth Type**: Bearer
   - **Custom Header Name**: `Authorization`
   - **Custom Header Value**: `Bearer YOUR_API_KEY`

### 5. Privacy Settings

Set to "Only me" for personal use, or configure sharing as needed.

### 6. Test Your GPT

Try these example prompts:

**Test 1 - Store a memory**:
```
Remember that I prefer Python over JavaScript for backend development
```

**Test 2 - Search memories**:
```
What do you remember about my programming preferences?
```

**Test 3 - List memories**:
```
Show me all my stored memories
```

## Advanced Configuration

### Custom Actions

If you want more control, you can define custom actions:

#### Add Memory Action
```yaml
name: add_memory
description: Store a new memory
parameters:
  text:
    type: string
    description: The memory to store
    required: true
```

#### Search Memory Action
```yaml
name: search_memory
description: Search for memories
parameters:
  query:
    type: string
    description: Search query
    required: true
```

#### List Memories Action
```yaml
name: list_memories
description: List all memories
parameters: {}
```

### Error Handling

The GPT should handle common errors:
- **401 Unauthorized**: Invalid API key
- **429 Rate Limited**: Too many requests
- **500 Server Error**: Backend issues

## Example Conversations

### Storing Information
```
User: I just learned that FastAPI is great for building APIs in Python
GPT: I'll store that information for you. [calls add_memories]
     ✅ Stored: "FastAPI is great for building APIs in Python"
```

### Retrieving Information
```
User: What do I know about Python frameworks?
GPT: Let me search your memories... [calls search_memory]
     I found: "FastAPI is great for building APIs in Python"
```

### Listing All Memories
```
User: What have I stored in my memory system?
GPT: Here are all your stored memories: [calls list_memories]
     1. FastAPI is great for building APIs in Python
     2. I prefer Python over JavaScript for backend development
```

## Troubleshooting

### Common Issues

1. **"Action failed"**: Check API key is correct
2. **"Rate limited"**: Wait before making more requests
3. **"Server error"**: Check if MCP server is running

### Debug Steps

1. **Test API directly**:
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" \
        https://mem-mcp.onemainarmy.com/health
   ```

2. **Check server logs**:
   ```bash
   tail -f mcp_server_production.log
   ```

3. **Verify CORS**: Make sure `chat.openai.com` is in allowed origins

## Security Considerations

1. **API Key Security**: Never share your API key
2. **Private GPT**: Keep your custom GPT private
3. **Memory Content**: Be mindful of what you store
4. **Rate Limits**: Respect the 60 requests/minute limit

## Tips for Better Memory Management

1. **Clear Descriptions**: Store memories with clear, searchable text
2. **Regular Cleanup**: Periodically review and clean up memories
3. **Organized Storage**: Use consistent terminology
4. **Context**: Include relevant context when storing memories

## Example Use Cases

### Personal Assistant
- Store meeting notes and action items
- Remember preferences and settings
- Track project progress

### Learning Companion
- Store key concepts and insights
- Remember useful resources
- Track learning progress

### Research Helper
- Store research findings
- Remember important quotes
- Track information sources

---

🤖 **Your ChatGPT now has persistent memory powered by mem0!**

For support, check the main deployment guide or server logs.
