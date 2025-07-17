# 🧠 ChatGPT Custom GPT Configuration Guide

This guide explains how to create a custom GPT in ChatGPT that can interact with your mem0 memory system through the secure GPT Actions bridge.

## 📋 Prerequisites

- ChatGPT Plus or Enterprise subscription (required for custom GPTs)
- Deployed GPT Actions bridge (see `DEPLOYMENT_GUIDE.md`)
- Valid API key for the bridge service

## 🎯 Step 1: Create Custom GPT

1. Go to [ChatGPT](https://chat.openai.com/)
2. Navigate to **"Explore"** in the sidebar
3. Click **"Create a GPT"**
4. Choose **"Configure"** tab for manual setup

## ⚙️ Step 2: Basic Configuration

### GPT Name
```
Memory Assistant
```

### Description
```
An AI assistant with persistent memory that can store and recall information across conversations using an external memory system.
```

### Instructions
```
You are a Memory Assistant powered by a persistent memory system. You can:

1. **Store Memories**: Automatically store important information from conversations
2. **Recall Information**: Search and retrieve relevant memories from past interactions
3. **Manage Memories**: View, update, and organize stored information

## Core Behaviors:

### Automatic Memory Storage
- Store user preferences, facts, and important context automatically
- Include relevant metadata like categories and timestamps
- Focus on information that would be useful in future conversations

### Memory Search
- Before responding to questions, search your memory for relevant context
- Use the information to provide personalized and contextual responses
- Cite when you're using information from your memory

### Memory Management
- Help users review and organize their stored memories
- Suggest when to update or remove outdated information
- Provide statistics about memory usage

## Response Guidelines:

1. **Be Transparent**: Always mention when you're using stored memories
2. **Be Helpful**: Proactively suggest storing important information
3. **Be Accurate**: Only store factual information, not assumptions
4. **Be Respectful**: Ask before storing sensitive information

## Example Interactions:

**User**: "I prefer my coffee black with no sugar"
**You**: "I'll remember your coffee preference! *[Stores: User prefers black coffee with no sugar]* I've saved this to your memory for future reference."

**User**: "What did I tell you about my morning routine?"
**You**: "*[Searching memory for morning routine...]* Based on our previous conversations, you mentioned you like to start with black coffee and prefer to exercise before work."

Always use your memory actions to provide the best possible assistance!
```

### Conversation Starters
```
1. "What do you remember about me?"
2. "Store this information for later: [your information]"
3. "Help me organize my stored memories"
4. "Search my memories for [topic]"
```

## 🔧 Step 3: Configure Actions

1. In the GPT configuration, scroll to **"Actions"**
2. Click **"Create new action"**
3. In the schema editor, paste the following OpenAPI schema:

```yaml
openapi: 3.1.0
info:
  title: Mem0 Memory System - GPT Actions API
  version: 1.0.0
  description: |
    Secure API bridge for ChatGPT to interact with the mem0 memory system.
    Provides core memory operations: create, search, retrieve, update, and delete memories.

servers:
  - url: https://mem-mcp.onemainarmy.com
    description: Production GPT Actions Bridge

paths:
  /memories:
    get:
      operationId: listMemories
      summary: List all memories for a user
      description: Retrieve all stored memories with optional filtering and pagination
      parameters:
        - name: user_id
          in: query
          required: false
          description: User identifier (defaults to authenticated user)
          schema:
            type: string
            default: chatgpt_user
        - name: limit
          in: query
          required: false
          description: Maximum number of memories to return
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
      responses:
        '200':
          description: List of memories retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  memories:
                    type: array
                    items:
                      type: object

    post:
      operationId: createMemory
      summary: Create new memories from messages
      description: Process messages through the mem0 system to extract and store meaningful information
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - messages
              properties:
                messages:
                  type: array
                  items:
                    type: object
                    required:
                      - role
                      - content
                    properties:
                      role:
                        type: string
                        enum: [user, assistant, system]
                      content:
                        type: string
                user_id:
                  type: string
                  default: chatgpt_user
      responses:
        '200':
          description: Memory created successfully

  /memories/search:
    post:
      operationId: searchMemories
      summary: Search memories using semantic similarity
      description: Perform vector-based semantic search to find relevant memories
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - query
              properties:
                query:
                  type: string
                  description: Search query to find relevant memories
                user_id:
                  type: string
                  default: chatgpt_user
                limit:
                  type: integer
                  default: 10
      responses:
        '200':
          description: Search completed successfully

  /health:
    get:
      operationId: healthCheck
      summary: Health check endpoint
      description: Check the health status of the memory system
      responses:
        '200':
          description: System is healthy

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      description: Use your API key as the bearer token

security:
  - BearerAuth: []
```

## 🔐 Step 4: Configure Authentication

1. After adding the schema, scroll to **"Authentication"**
2. Select **"API Key"**
3. Configure as follows:
   - **Auth Type**: `Bearer`
   - **API Key**: `gpt_your_64_character_api_key_here`
4. Click **"Test"** to verify authentication

## ✅ Step 5: Test the Configuration

1. Click **"Test"** next to each action to verify they work
2. Expected responses:
   - **healthCheck**: Should return `{"status": "healthy"}`
   - **listMemories**: Should return memories array (may be empty initially)
   - **searchMemories**: Should return search results

## 🚀 Step 6: Save and Publish

1. Click **"Save"** to save your configuration
2. Click **"Publish"** and choose your publishing option:
   - **Only me**: Private GPT for personal use
   - **Anyone with a link**: Share with specific people
   - **Public**: Make available in the GPT store

## 🎮 Usage Examples

Once configured, you can interact with your Memory Assistant like this:

### Storing Information
```
User: "I'm allergic to shellfish and prefer vegetarian restaurants"
Assistant: I'll remember your dietary preferences! *[Storing memory...]*
I've saved that you're allergic to shellfish and prefer vegetarian restaurants.
```

### Retrieving Information
```
User: "What restaurants should I avoid?"
Assistant: *[Searching memories for dietary restrictions...]*
Based on your preferences, you should avoid restaurants that serve shellfish,
and you prefer vegetarian options.
```

### Managing Memories
```
User: "What do you remember about me?"
Assistant: *[Listing memories...]* Here's what I have stored about you:
- Dietary: Allergic to shellfish, prefers vegetarian restaurants
- Coffee: Likes black coffee with no sugar
- Work: Software developer who prefers remote work
```

## 🔧 Advanced Configuration

### Custom User IDs
To separate memories for different contexts, you can modify the `user_id` parameter:
- Personal: `chatgpt_personal`
- Work: `chatgpt_work`
- Projects: `chatgpt_project_[name]`

### Memory Categories
Use metadata to categorize memories:
```json
{
  "metadata": {
    "category": "preferences",
    "type": "dietary",
    "priority": "high"
  }
}
```

## 🔍 Troubleshooting

### Authentication Errors
- **Problem**: `401 Unauthorized`
- **Solution**: Verify API key format and validity

### Connection Errors
- **Problem**: Cannot reach the API
- **Solution**: Check that the bridge service is running and accessible

### Rate Limiting
- **Problem**: `429 Too Many Requests`
- **Solution**: Reduce request frequency (max 30/minute)

### Memory Not Found
- **Problem**: Search returns no results
- **Solution**: Store some memories first, check user_id consistency

## 📊 Monitoring Usage

### View API Usage
Check the bridge service logs:
```bash
docker-compose logs gpt-actions-bridge | grep "INFO"
```

### Memory Statistics
Ask your GPT: "Show me my memory statistics" to get usage info.

## 🛡️ Privacy and Security

- **Data Isolation**: Each user_id maintains separate memory space
- **Encryption**: All communications use HTTPS/TLS
- **Access Control**: API key required for all operations
- **Rate Limiting**: Prevents abuse and ensures fair usage

## 🚀 Next Steps

1. **Test Thoroughly**: Try various memory operations
2. **Customize Instructions**: Adapt the GPT behavior to your needs
3. **Monitor Performance**: Watch for errors or slow responses
4. **Scale Usage**: Consider multiple GPTs for different purposes

---

**🎉 Success!** Your Memory Assistant is now connected to your persistent memory system and ready to help you remember everything across conversations!

## 💡 Pro Tips

- **Be Specific**: The more context you provide, the better the memory system works
- **Regular Cleanup**: Periodically review and clean old memories
- **Category Usage**: Use categories to organize different types of information
- **Multiple GPTs**: Create specialized GPTs for different domains (work, personal, projects)
