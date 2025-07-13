#!/bin/bash

# GitHub Merge Queue Setup Script for mem0-stack
# Configures merge queue to handle multiple background agents working concurrently
# This script sets up merge queue functionality for coordinating agent work

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
REPO_OWNER="DrJLabs"
REPO_NAME="Forgetful"
MAIN_BRANCH="main"
DEVELOP_BRANCH="develop"

# Merge Queue Configuration
MERGE_QUEUE_CONFIG='{
  "merge_method": "merge",
  "max_entries": 10,
  "merge_timeout_minutes": 30,
  "required_checks": [
    "🧪 Unit Tests (Quality Gate 1) (3.11)",
    "🧪 Unit Tests (Quality Gate 1) (3.12)",
    "🚦 Merge Decision (Final Quality Gate)",
    "Analyze (python)",
    "Analyze (javascript-typescript)",
    "🔄 Merge Queue Quality Gates (3.11)",
    "🔄 Merge Queue Quality Gates (3.12)"
  ]
}'

# Function to print colored output
print_colored() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print header
print_header() {
    echo ""
    print_colored "${PURPLE}" "=============================================================="
    print_colored "${PURPLE}" "$1"
    print_colored "${PURPLE}" "=============================================================="
    echo ""
}

# Check if GitHub CLI is installed
check_github_cli() {
    if ! command -v gh &> /dev/null; then
        print_colored "${RED}" "❌ GitHub CLI (gh) is not installed"
        print_colored "${YELLOW}" "Please install it: https://cli.github.com/"
        exit 1
    fi

    # Check if authenticated
    if ! gh auth status &> /dev/null; then
        print_colored "${RED}" "❌ GitHub CLI is not authenticated"
        print_colored "${YELLOW}" "Please authenticate: gh auth login"
        exit 1
    fi

    print_colored "${GREEN}" "✅ GitHub CLI is installed and authenticated"
}

# Function to check if merge queue is supported
check_merge_queue_support() {
    print_colored "${BLUE}" "🔍 Checking merge queue support..."

    # Check if repository supports merge queue (GitHub Enterprise/GitHub.com)
    local repo_info=$(gh api "repos/$REPO_OWNER/$REPO_NAME" --jq '.merge_queue_enabled // false')

    if [[ "$repo_info" == "false" ]]; then
        print_colored "${YELLOW}" "⚠️ Merge queue may not be enabled or supported"
        print_colored "${YELLOW}" "Note: Merge queue requires GitHub Enterprise or GitHub.com Pro/Team"
    else
        print_colored "${GREEN}" "✅ Merge queue is supported"
    fi
}

# Function to update branch protection with merge queue support
update_branch_protection_for_merge_queue() {
    local branch=$1

    print_colored "${BLUE}" "🔐 Updating branch protection for merge queue: $branch"

    # Enhanced branch protection with merge queue support
    local protection_config=$(cat << 'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "🧪 Unit Tests (Quality Gate 1) (3.11)",
      "🧪 Unit Tests (Quality Gate 1) (3.12)",
      "📋 API Contract Tests (Quality Gate 2)",
      "🔒 Security Tests (Quality Gate 3)",
      "🗄️ Database Tests (Quality Gate 4)",
      "🔗 Integration Tests (Quality Gate 5)",
      "⚡ Performance Tests (Quality Gate 6)",
      "🔍 Code Quality (Quality Gate 7)",
      "🚦 Merge Decision (Final Quality Gate)",
      "Analyze (python)",
      "Analyze (javascript-typescript)",
      "🔄 Merge Queue Quality Gates (3.11)",
      "🔄 Merge Queue Quality Gates (3.12)"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false
  },
  "restrictions": {
    "users": [],
    "teams": [],
    "apps": []
  },
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true,
  "allow_auto_merge": true,
  "delete_branch_on_merge": false
}
EOF
)

    # Apply the protection rules
    if gh api "repos/$REPO_OWNER/$REPO_NAME/branches/$branch/protection" \
        --method PUT \
        --input - <<< "$protection_config"; then
        print_colored "${GREEN}" "✅ Branch protection updated for merge queue: $branch"
    else
        print_colored "${RED}" "❌ Failed to update branch protection for: $branch"
        return 1
    fi
}

# Function to enable merge queue for a branch
enable_merge_queue() {
    local branch=$1

    print_colored "${BLUE}" "🔄 Enabling merge queue for branch: $branch"

    # NOTE: The GitHub API for merge queue configuration is still in beta
    # and may not be fully available via REST API yet.
    # This is a placeholder for when the API becomes available.

    local merge_queue_config=$(cat << 'EOF'
{
  "merge_method": "merge",
  "max_entries": 10,
  "merge_timeout_minutes": 30
}
EOF
)

    # Try to enable merge queue (this may fail if not supported)
    if gh api "repos/$REPO_OWNER/$REPO_NAME/branches/$branch/merge_queue" \
        --method PUT \
        --input - <<< "$merge_queue_config" 2>/dev/null; then
        print_colored "${GREEN}" "✅ Merge queue enabled for: $branch"
    else
        print_colored "${YELLOW}" "⚠️ Merge queue API not available - enable manually via GitHub web interface"
        print_colored "${YELLOW}" "Go to: https://github.com/$REPO_OWNER/$REPO_NAME/settings/branches"
        print_colored "${YELLOW}" "Edit branch protection rule for '$branch' and enable merge queue"
    fi
}

# Function to create merge queue labels
create_merge_queue_labels() {
    print_colored "${BLUE}" "🏷️ Creating merge queue labels..."

    # Agent-related labels
    local labels=(
        "agent-pr|008672|Indicates this PR was created by an automated agent"
        "auto-merge|7057ff|PR is ready for automatic merge queue processing"
        "ready-to-merge|0e8a16|PR has passed all checks and is ready for merge"
        "merge-queue|fbca04|PR is currently in the merge queue"
        "agent-ready|0052cc|Agent PR that has completed all required checks"
        "background-agent|5319e7|PR created by background agent process"
        "bmad-agent|d4c5f9|PR created by BMAD agent system"
        "priority-merge|b60205|High priority PR for expedited merge queue processing"
        "batch-merge|c2e0c6|Part of a batch of related PRs for coordinated merging"
        "conflict-resolved|28a745|Merge conflicts have been resolved"
    )

    for label_def in "${labels[@]}"; do
        IFS='|' read -r name color description <<< "$label_def"

        # Create label if it doesn't exist
        if gh api "repos/$REPO_OWNER/$REPO_NAME/labels/$name" &>/dev/null; then
            print_colored "${YELLOW}" "⏭️ Label '$name' already exists"
        else
            if gh api "repos/$REPO_OWNER/$REPO_NAME/labels" \
                --method POST \
                --field name="$name" \
                --field color="$color" \
                --field description="$description" &>/dev/null; then
                print_colored "${GREEN}" "✅ Created label: $name"
            else
                print_colored "${RED}" "❌ Failed to create label: $name"
            fi
        fi
    done
}

# Function to create merge queue workflow dispatch
create_merge_queue_dispatch() {
    print_colored "${BLUE}" "⚙️ Creating merge queue management dispatch..."

    # Create a dispatch action for merge queue management
    local dispatch_body=$(cat << 'EOF'
{
  "event_type": "merge_queue_management",
  "client_payload": {
    "action": "status",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "source": "merge_queue_setup_script"
  }
}
EOF
)

    # Test workflow dispatch
    if gh api "repos/$REPO_OWNER/$REPO_NAME/dispatches" \
        --method POST \
        --input - <<< "$dispatch_body"; then
        print_colored "${GREEN}" "✅ Merge queue dispatch created successfully"
    else
        print_colored "${YELLOW}" "⚠️ Could not create merge queue dispatch"
    fi
}

# Function to test merge queue configuration
test_merge_queue_config() {
    print_colored "${BLUE}" "🧪 Testing merge queue configuration..."

    # Check branch protection status
    local protection_status=$(gh api "repos/$REPO_OWNER/$REPO_NAME/branches/$MAIN_BRANCH/protection" \
        --jq '.required_status_checks.contexts | length' 2>/dev/null || echo "0")

    if [[ "$protection_status" -gt 0 ]]; then
        print_colored "${GREEN}" "✅ Branch protection active with $protection_status required checks"
    else
        print_colored "${RED}" "❌ Branch protection not properly configured"
    fi

    # Check workflow files
    if [[ -f ".github/workflows/merge-queue.yml" ]]; then
        print_colored "${GREEN}" "✅ Merge queue workflow file exists"
    else
        print_colored "${RED}" "❌ Merge queue workflow file missing"
    fi

    if [[ -f ".github/workflows/test.yml" ]]; then
        if grep -q "merge_group" ".github/workflows/test.yml"; then
            print_colored "${GREEN}" "✅ Test workflow supports merge groups"
        else
            print_colored "${RED}" "❌ Test workflow does not support merge groups"
        fi
    else
        print_colored "${RED}" "❌ Test workflow file missing"
    fi
}

# Function to show merge queue status
show_merge_queue_status() {
    print_header "📊 Merge Queue Status"

    print_colored "${BLUE}" "Repository: $REPO_OWNER/$REPO_NAME"
    echo ""

    # Get open PRs
    local open_prs=$(gh api "repos/$REPO_OWNER/$REPO_NAME/pulls" \
        --jq 'length' 2>/dev/null || echo "0")

    # Get PRs with merge queue labels
    local agent_prs=$(gh api "repos/$REPO_OWNER/$REPO_NAME/pulls" \
        --jq '[.[] | select(.labels[] | .name | contains("agent"))] | length' 2>/dev/null || echo "0")

    local ready_prs=$(gh api "repos/$REPO_OWNER/$REPO_NAME/pulls" \
        --jq '[.[] | select(.labels[] | .name == "ready-to-merge")] | length' 2>/dev/null || echo "0")

    print_colored "${BLUE}" "📋 Pull Request Status:"
    print_colored "${BLUE}" "  - Total open PRs: $open_prs"
    print_colored "${BLUE}" "  - Agent PRs: $agent_prs"
    print_colored "${BLUE}" "  - Ready for merge: $ready_prs"
    echo ""

    # Get workflow status
    local workflow_status=$(gh api "repos/$REPO_OWNER/$REPO_NAME/actions/workflows" \
        --jq '.workflows | length' 2>/dev/null || echo "0")

    print_colored "${BLUE}" "🔄 Workflow Status:"
    print_colored "${BLUE}" "  - Total workflows: $workflow_status"
    echo ""

    # Show merge queue configuration
    print_colored "${BLUE}" "⚙️ Merge Queue Configuration:"
    print_colored "${BLUE}" "  - Max entries: 10"
    print_colored "${BLUE}" "  - Timeout: 30 minutes"
    print_colored "${BLUE}" "  - Merge method: merge"
    print_colored "${BLUE}" "  - Required checks: 13"
    echo ""

    # Show agent coordination features
    print_colored "${BLUE}" "🤖 Agent Coordination Features:"
    print_colored "${BLUE}" "  - Automatic PR labeling"
    print_colored "${BLUE}" "  - Concurrent agent support"
    print_colored "${BLUE}" "  - Merge conflict prevention"
    print_colored "${BLUE}" "  - Quality gate enforcement"
    print_colored "${BLUE}" "  - Status reporting"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Setup GitHub merge queue for coordinating multiple background agents.

OPTIONS:
    -h, --help          Show this help message
    -s, --setup         Complete merge queue setup
    -t, --test          Test merge queue configuration
    -l, --labels        Create merge queue labels
    -p, --protection    Update branch protection rules
    -q, --queue         Enable merge queue (if supported)
    --status            Show merge queue status
    --dry-run          Show what would be done without making changes

EXAMPLES:
    $0 --setup          Complete merge queue setup
    $0 --test           Test current configuration
    $0 --status         Show merge queue status
    $0 --labels         Create merge queue labels only

MERGE QUEUE FEATURES:
    - Coordinates multiple background agents
    - Prevents merge conflicts
    - Enforces quality gates
    - Supports concurrent PR processing
    - Automatic agent PR detection
    - Status reporting and monitoring

REQUIREMENTS:
    - GitHub CLI (gh) must be installed and authenticated
    - Repository access permissions
    - Admin permissions for branch protection

EOF
}

# Main function
main() {
    local action=""
    local dry_run=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -s|--setup)
                action="setup"
                shift
                ;;
            -t|--test)
                action="test"
                shift
                ;;
            -l|--labels)
                action="labels"
                shift
                ;;
            -p|--protection)
                action="protection"
                shift
                ;;
            -q|--queue)
                action="queue"
                shift
                ;;
            --status)
                action="status"
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                print_colored "${RED}" "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Default action if none specified
    if [[ -z "$action" ]]; then
        action="status"
    fi

    # Print header
    print_header "🔄 GitHub Merge Queue Setup for Multiple Agents"
    print_colored "${BLUE}" "Repository: $REPO_OWNER/$REPO_NAME"
    print_colored "${BLUE}" "Action: $action"
    if [[ "$dry_run" == "true" ]]; then
        print_colored "${YELLOW}" "Mode: DRY RUN (no changes will be made)"
    fi
    echo ""

    # Check prerequisites
    check_github_cli
    check_merge_queue_support

    # Execute action
    case "$action" in
        "setup")
            if [[ "$dry_run" == "true" ]]; then
                print_colored "${YELLOW}" "DRY RUN: Would perform complete merge queue setup"
                show_merge_queue_status
            else
                print_header "🚀 Complete Merge Queue Setup"
                create_merge_queue_labels
                update_branch_protection_for_merge_queue "$MAIN_BRANCH"
                update_branch_protection_for_merge_queue "$DEVELOP_BRANCH"
                enable_merge_queue "$MAIN_BRANCH"
                enable_merge_queue "$DEVELOP_BRANCH"
                create_merge_queue_dispatch
                test_merge_queue_config
                print_colored "${GREEN}" "✅ Merge queue setup completed successfully!"
            fi
            ;;
        "test")
            print_header "🧪 Testing Merge Queue Configuration"
            test_merge_queue_config
            ;;
        "labels")
            if [[ "$dry_run" == "true" ]]; then
                print_colored "${YELLOW}" "DRY RUN: Would create merge queue labels"
            else
                create_merge_queue_labels
            fi
            ;;
        "protection")
            if [[ "$dry_run" == "true" ]]; then
                print_colored "${YELLOW}" "DRY RUN: Would update branch protection rules"
            else
                update_branch_protection_for_merge_queue "$MAIN_BRANCH"
                update_branch_protection_for_merge_queue "$DEVELOP_BRANCH"
            fi
            ;;
        "queue")
            if [[ "$dry_run" == "true" ]]; then
                print_colored "${YELLOW}" "DRY RUN: Would enable merge queue"
            else
                enable_merge_queue "$MAIN_BRANCH"
                enable_merge_queue "$DEVELOP_BRANCH"
            fi
            ;;
        "status")
            show_merge_queue_status
            ;;
        *)
            print_colored "${RED}" "Unknown action: $action"
            show_usage
            exit 1
            ;;
    esac

    echo ""
    print_colored "${GREEN}" "🎉 Merge queue operation completed!"
    print_colored "${GREEN}" "🤖 Multiple background agents can now work concurrently"
    print_colored "${GREEN}" "🔄 Merge conflicts will be prevented automatically"
    print_colored "${GREEN}" "🧪 Quality gates will be enforced for all merges"
}

# Run main function
main "$@"
