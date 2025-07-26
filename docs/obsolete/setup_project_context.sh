#!/bin/bash
# Project Context Setup Script for Mem0 MCP Server
# This script helps configure automatic project sorting in Cursor

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Mem0 Project Context Setup ===${NC}"
echo "This script will help you configure automatic project sorting in Cursor"
echo

# Function to detect current project
detect_project() {
    local project_name=""

    # Try to get git repository name
    if git remote get-url origin &>/dev/null; then
        local git_remote=$(git remote get-url origin 2>/dev/null)
        if [[ -n "$git_remote" ]]; then
            project_name=$(basename "$git_remote" .git)
            echo -e "${GREEN}✓ Detected git project: $project_name${NC}" >&2
        fi
    fi

    # Fallback to directory name
    if [[ -z "$project_name" ]]; then
        project_name=$(basename "$(pwd)")
        echo -e "${YELLOW}! Using directory name as project: $project_name${NC}" >&2
    fi

    echo "$project_name"
}

# Function to detect current run/branch
detect_run() {
    local run_id=""

    # Try to get current branch
    if git rev-parse --is-inside-work-tree &>/dev/null; then
        local branch=$(git branch --show-current 2>/dev/null)
        if [[ -n "$branch" && "$branch" != "main" && "$branch" != "master" ]]; then
            run_id="$branch"
            echo -e "${GREEN}✓ Detected branch/run: $run_id${NC}" >&2
        fi
    fi

    echo "$run_id"
}

# Function to update cursor configuration
update_cursor_config() {
    local project_id="$1"
    local run_id="$2"
    local config_file="$HOME/.cursor/mcp.json"

    # Check if config file exists
    if [[ ! -f "$config_file" ]]; then
        echo -e "${RED}✗ Cursor MCP config not found at $config_file${NC}"
        echo "Please ensure Cursor MCP is properly set up first."
        return 1
    fi

    # Create backup
    cp "$config_file" "$config_file.backup"
    echo -e "${GREEN}✓ Created backup: $config_file.backup${NC}"

    # Update the configuration using jq
    if command -v jq &>/dev/null; then
        jq --arg project_id "$project_id" --arg run_id "$run_id" \
           '.mcpServers.mem0.env.PROJECT_ID = $project_id | .mcpServers.mem0.env.RUN_ID = $run_id' \
           "$config_file" > "$config_file.tmp" && mv "$config_file.tmp" "$config_file"
        echo -e "${GREEN}✓ Updated Cursor MCP configuration${NC}"
    else
        echo -e "${YELLOW}! jq not found, please manually update $config_file${NC}"
        echo "Set PROJECT_ID=\"$project_id\" and RUN_ID=\"$run_id\""
    fi
}

# Function to test the configuration
test_configuration() {
    echo -e "${BLUE}=== Testing MCP Configuration ===${NC}"

    # Test if MCP server is running
    if pgrep -f "mcp_standalone.py" &>/dev/null; then
        echo -e "${GREEN}✓ MCP server is running${NC}"
    else
        echo -e "${YELLOW}! MCP server not running, starting now...${NC}"
        # You might need to restart Cursor for changes to take effect
        echo "Please restart Cursor for changes to take effect"
    fi
}

# Function to show project context examples
show_examples() {
    echo -e "${BLUE}=== Project Context Usage Examples ===${NC}"
    echo
    echo "1. Automatic Project Detection:"
    echo "   When you work in different directories, memories are automatically sorted by project"
    echo
    echo "2. Cross-Project Search:"
    echo "   Use 'search across all projects' to find memories from any project"
    echo
    echo "3. Branch/Run Isolation:"
    echo "   Memories can be isolated by git branch for feature-specific context"
    echo
    echo "4. Manual Project Override:"
    echo "   You can manually specify project_id in memory operations"
    echo
    echo -e "${GREEN}Available MCP Tools:${NC}"
    echo "• add_memories - Store memories with automatic project context"
    echo "• search_memory - Search with project filtering"
    echo "• list_memories - List memories by project"
    echo "• get_project_context - View current project context"
    echo "• delete_all_memories - Delete memories (with confirmation)"
    echo
}

# Main execution
main() {
    echo "Current directory: $(pwd)"
    echo

    # Detect current project and run (capture clean values)
    PROJECT_ID=$(detect_project)
    RUN_ID=$(detect_run)

    echo
    echo -e "${BLUE}Detected Context:${NC}"
    echo "• Project ID: $PROJECT_ID"
    echo "• Run ID: $RUN_ID"
    echo "• User ID: drj"
    echo "• Org ID: drj-org"
    echo "• Agent ID: cursor"
    echo

    # Ask for confirmation
    read -p "Update Cursor configuration with this context? (y/n): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        update_cursor_config "$PROJECT_ID" "$RUN_ID"
        echo
        test_configuration
        echo
        show_examples
    else
        echo -e "${YELLOW}Configuration not updated${NC}"
    fi

    echo
    echo -e "${GREEN}=== Setup Complete ===${NC}"
    echo "To use the project context features:"
    echo "1. Restart Cursor for configuration changes to take effect"
    echo "2. Use MCP tools to store and retrieve project-specific memories"
    echo "3. Run this script in different project directories to switch contexts"
}

# Run main function
main "$@"
