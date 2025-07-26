# Mem0 Project Context Guide

## Overview

The enhanced Mem0 MCP server now supports **automatic project sorting** and **cross-project memory access**. This enables intelligent memory management across different codebases, branches, and development contexts.

## 🚀 Key Features

### 1. **Automatic Project Detection**
- Detects project name from git repository or directory name
- Isolates memories by project automatically
- No manual configuration required for basic usage

### 2. **Branch/Run-Based Context**
- Separates memories by git branch for feature-specific context
- Useful for isolating experimental work or feature branches
- Automatically detects current branch as `run_id`

### 3. **Cross-Project Search**
- Search memories across all projects for the same user
- Maintain project isolation while enabling knowledge sharing
- Useful for finding patterns across different codebases

### 4. **Flexible Context Override**
- Manual override of project context when needed
- Support for custom org/project/run/agent hierarchies
- Fine-grained control over memory organization

## 📋 Quick Setup

### 1. Enable Project Context Features

```bash
# Run the setup script in your project directory
./setup_project_context.sh
```

### 2. Restart Cursor
After configuration changes, restart Cursor for the MCP server to pick up the new settings.

### 3. Test the Configuration

Use the `get_project_context` tool to verify your setup:

```json
{
  "name": "get_project_context",
  "arguments": {}
}
```

## 🔧 Configuration Details

### Environment Variables

The MCP server now supports these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `USER_ID` | `"drj"` | User identifier |
| `ORG_ID` | `"drj-org"` | Organization identifier |
| `PROJECT_ID` | Auto-detected | Project identifier (git repo or directory name) |
| `RUN_ID` | Auto-detected | Run/session identifier (git branch) |
| `AGENT_ID` | `"cursor"` | Agent identifier |
| `CLIENT_NAME` | `"cursor"` | Client name for metadata |

### Auto-Detection Logic

1. **Project Detection**:
   - First tries to get repository name from `git remote get-url origin`
   - Falls back to current directory name
   - Example: `mem0-stack` from `/home/drj/projects/mem0-stack`

2. **Run Detection**:
   - Gets current git branch from `git branch --show-current`
   - Only uses branch name if not `main` or `master`
   - Example: `feature/project-context` branch becomes `run_id`

## 🛠️ MCP Tools Reference

### 1. `add_memories`
Store memories with automatic project context.

```json
{
  "name": "add_memories",
  "arguments": {
    "text": "This project uses TypeScript with strict mode enabled",
    "project_id": "optional-override",
    "run_id": "optional-override",
    "agent_id": "optional-override"
  }
}
```

### 2. `search_memory`
Search memories with project filtering.

```json
{
  "name": "search_memory",
  "arguments": {
    "query": "TypeScript configuration",
    "project_id": "specific-project",
    "run_id": "specific-branch",
    "cross_project": false
  }
}
```

**Cross-Project Search**:
```json
{
  "name": "search_memory",
  "arguments": {
    "query": "database connection patterns",
    "cross_project": true
  }
}
```

### 3. `list_memories`
List memories with project context filtering.

```json
{
  "name": "list_memories",
  "arguments": {
    "project_id": "mem0-stack",
    "run_id": "feature-branch",
    "cross_project": false
  }
}
```

### 4. `get_project_context`
View current project context information.

```json
{
  "name": "get_project_context",
  "arguments": {}
}
```

### 5. `delete_all_memories`
Delete memories with project context filtering.

```json
{
  "name": "delete_all_memories",
  "arguments": {
    "project_id": "old-project",
    "run_id": "completed-branch",
    "confirm": true
  }
}
```

## 🎯 Usage Patterns

### 1. **Single Project Development**
```bash
# Navigate to project directory
cd /path/to/my-project

# Run setup script
./setup_project_context.sh

# Memories are automatically isolated to this project
```

### 2. **Multi-Project Development**
```bash
# Project A
cd /path/to/project-a
./setup_project_context.sh

# Project B
cd /path/to/project-b
./setup_project_context.sh

# Each project has isolated memories
```

### 3. **Feature Branch Development**
```bash
# Main branch
git checkout main
# Memories stored with run_id: null

# Feature branch
git checkout -b feature/new-feature
# Memories stored with run_id: "feature/new-feature"
```

### 4. **Cross-Project Knowledge Sharing**
```json
{
  "name": "search_memory",
  "arguments": {
    "query": "error handling patterns",
    "cross_project": true
  }
}
```

## 🔍 Memory Organization

Memories are organized in a hierarchical structure:

```
User: drj
├── Organization: drj-org
    ├── Project: mem0-stack
    │   ├── Run: feature/project-context
    │   │   └── Agent: cursor
    │   └── Run: main
    │       └── Agent: cursor
    ├── Project: another-project
    │   └── Run: main
    │       └── Agent: cursor
    └── Cross-Project Memories
        └── Agent: cursor
```

## 📊 Example Workflow

### 1. **Starting a New Project**
```bash
# Navigate to project
cd ~/projects/my-new-app

# Initialize git (if not already done)
git init
git remote add origin https://github.com/user/my-new-app.git

# Setup project context
./setup_project_context.sh
# Detected project: my-new-app
# Run ID: (none, on main branch)
```

### 2. **Working on a Feature**
```bash
# Create feature branch
git checkout -b feature/user-auth

# Setup context for this branch
./setup_project_context.sh
# Detected project: my-new-app
# Run ID: feature/user-auth

# Store feature-specific memories
# They will be isolated to this branch context
```

### 3. **Searching Across Projects**
```json
{
  "name": "search_memory",
  "arguments": {
    "query": "authentication implementation",
    "cross_project": true
  }
}
```

### 4. **Switching Between Projects**
```bash
# Project A
cd ~/projects/frontend-app
./setup_project_context.sh

# Project B
cd ~/projects/backend-api
./setup_project_context.sh

# Each project maintains separate memory context
```

## 🔧 Advanced Configuration

### Manual Project Override

You can manually specify project context in your Cursor MCP configuration:

```json
{
  "mcpServers": {
    "mem0": {
      "env": {
        "PROJECT_ID": "custom-project-name",
        "RUN_ID": "custom-session-id",
        "ORG_ID": "custom-org"
      }
    }
  }
}
```

### Multiple Organizations

For enterprise use, you can configure different organizations:

```json
{
  "mcpServers": {
    "mem0": {
      "env": {
        "ORG_ID": "company-org",
        "PROJECT_ID": "client-project",
        "USER_ID": "drj"
      }
    }
  }
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Project Not Detected**
   - Ensure you're in a git repository or the directory name is meaningful
   - Check that git is installed and working
   - Manually set `PROJECT_ID` in configuration if needed

2. **Memories Not Isolated**
   - Verify that `PROJECT_ID` is being set correctly
   - Check MCP server logs for context detection
   - Restart Cursor after configuration changes

3. **Cross-Project Search Not Working**
   - Ensure `cross_project: true` is set in search arguments
   - Verify that memories exist in other projects
   - Check that `USER_ID` is consistent across projects

### Debug Commands

```bash
# Check git configuration
git remote get-url origin
git branch --show-current

# Test project detection
./setup_project_context.sh

# Check MCP server logs
docker logs openmemory-mcp
```

## 📈 Best Practices

1. **Use Meaningful Project Names**
   - Use descriptive git repository names
   - Avoid generic directory names like "test" or "temp"

2. **Leverage Branch Context**
   - Create feature branches for experimental work
   - Use branch-specific memories for temporary context

3. **Regular Context Updates**
   - Run `setup_project_context.sh` when switching projects
   - Update configuration when project structure changes

4. **Strategic Cross-Project Searches**
   - Use cross-project search for finding reusable patterns
   - Keep project-specific details in project-isolated memories

5. **Clean Up Old Contexts**
   - Delete memories from completed branches
   - Archive old project memories when projects are finished

## 🎉 Success Metrics

After setup, you should see:

✅ **Automatic Project Detection**: Memories are automatically sorted by project
✅ **Branch Isolation**: Feature branch memories are separate from main branch
✅ **Cross-Project Search**: Can find relevant memories across all projects
✅ **Context Switching**: Easy switching between project contexts
✅ **Clean Organization**: Memories are properly organized by hierarchy

## 💡 Tips for Cursor Integration

1. **Custom Prompts**: Create project-specific prompts that leverage project context
2. **Template Usage**: Use project memories to maintain consistent coding patterns
3. **Knowledge Sharing**: Share common patterns across projects while maintaining isolation
4. **Workflow Integration**: Integrate project context switching into your development workflow

## 🔗 Related Documentation

- [Mem0 Official Documentation](https://docs.mem0.ai)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Cursor MCP Integration Guide](https://cursor.com/docs/mcp)
