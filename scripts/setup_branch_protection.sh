#!/bin/bash

# Branch Protection Setup Script for mem0-stack
# Step 2.3: CI/CD Integration with Quality Gates
# This script configures GitHub branch protection rules to enforce quality gates

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

# Quality Gate Names (must match workflow job names)
QUALITY_GATES=(
    "🧪 Unit Tests (Quality Gate 1)"
    "📋 API Contract Tests (Quality Gate 2)"
    "🔒 Security Tests (Quality Gate 3)"
    "🗄️ Database Tests (Quality Gate 4)"
    "🔗 Integration Tests (Quality Gate 5)"
    "⚡ Performance Tests (Quality Gate 6)"
    "🔍 Code Quality (Quality Gate 7)"
    "🚦 Merge Decision (Final Quality Gate)"
)

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

# Function to build status check contexts JSON
build_contexts_json() {
    local contexts_json=""
    for gate in "${QUALITY_GATES[@]}"; do
        if [[ -z "$contexts_json" ]]; then
            contexts_json="\"$gate\""
        else
            contexts_json="$contexts_json,\"$gate\""
        fi
    done
    echo "[$contexts_json]"
}

# Function to apply branch protection rules
apply_branch_protection() {
    local branch=$1
    local contexts_json=$(build_contexts_json)

    print_colored "${BLUE}" "📋 Applying branch protection rules for: $branch"
    print_colored "${BLUE}" "🔐 Required status checks: ${#QUALITY_GATES[@]} quality gates"

    # Create the JSON payload
    local protection_json=$(cat <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": $contexts_json
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
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
  "required_conversation_resolution": true
}
EOF
)

    # Apply the protection rules
    if gh api "repos/$REPO_OWNER/$REPO_NAME/branches/$branch/protection" \
        --method PUT \
        --input - <<< "$protection_json"; then
        print_colored "${GREEN}" "✅ Branch protection rules applied successfully for $branch"
    else
        print_colored "${RED}" "❌ Failed to apply branch protection rules for $branch"
        return 1
    fi
}

# Function to verify branch protection rules
verify_branch_protection() {
    local branch=$1

    print_colored "${BLUE}" "🔍 Verifying branch protection rules for: $branch"

    # Get current protection rules
    local protection_info=$(gh api "repos/$REPO_OWNER/$REPO_NAME/branches/$branch/protection" 2>/dev/null || echo "")

    if [[ -z "$protection_info" ]]; then
        print_colored "${RED}" "❌ No branch protection rules found for $branch"
        return 1
    fi

    # Extract status checks
    local status_checks=$(echo "$protection_info" | jq -r '.required_status_checks.contexts[]' 2>/dev/null || echo "")

    if [[ -z "$status_checks" ]]; then
        print_colored "${RED}" "❌ No required status checks found for $branch"
        return 1
    fi

    # Verify all quality gates are present
    local missing_gates=()
    for gate in "${QUALITY_GATES[@]}"; do
        if ! echo "$status_checks" | grep -q "^$gate$"; then
            missing_gates+=("$gate")
        fi
    done

    if [[ ${#missing_gates[@]} -gt 0 ]]; then
        print_colored "${RED}" "❌ Missing quality gates for $branch:"
        for gate in "${missing_gates[@]}"; do
            print_colored "${RED}" "   - $gate"
        done
        return 1
    fi

    print_colored "${GREEN}" "✅ All quality gates are properly configured for $branch"
    print_colored "${GREEN}" "📊 Protected status checks: ${#QUALITY_GATES[@]} quality gates"

    return 0
}

# Function to show protection summary
show_protection_summary() {
    print_header "🛡️  Branch Protection Summary"

    print_colored "${BLUE}" "Repository: $REPO_OWNER/$REPO_NAME"
    print_colored "${BLUE}" "Protected Branches: $MAIN_BRANCH, $DEVELOP_BRANCH"
    print_colored "${BLUE}" "Quality Gates: ${#QUALITY_GATES[@]} gates"
    echo ""

    print_colored "${YELLOW}" "Quality Gates Configuration:"
    for i in "${!QUALITY_GATES[@]}"; do
        local gate_num=$((i + 1))
        print_colored "${YELLOW}" "  $gate_num. ${QUALITY_GATES[$i]}"
    done
    echo ""

    print_colored "${YELLOW}" "Merge Blocking Conditions:"
    print_colored "${YELLOW}" "  • Any quality gate fails"
    print_colored "${YELLOW}" "  • Coverage below 80% threshold"
    print_colored "${YELLOW}" "  • Security vulnerabilities detected"
    print_colored "${YELLOW}" "  • API contract violations"
    print_colored "${YELLOW}" "  • Database migration failures"
    print_colored "${YELLOW}" "  • Performance regressions"
    print_colored "${YELLOW}" "  • Code quality violations"
    echo ""

    print_colored "${GREEN}" "🚫 Merges will be BLOCKED until ALL quality gates pass"
    print_colored "${GREEN}" "✅ This ensures zero major bugs reach the main branch"
}

# Function to test branch protection
test_branch_protection() {
    print_header "🧪 Testing Branch Protection"

    local test_passed=true

    for branch in "$MAIN_BRANCH" "$DEVELOP_BRANCH"; do
        print_colored "${BLUE}" "Testing branch: $branch"

        # Test 1: Check if branch exists
        if ! gh api "repos/$REPO_OWNER/$REPO_NAME/branches/$branch" &>/dev/null; then
            print_colored "${RED}" "❌ Branch $branch does not exist"
            test_passed=false
            continue
        fi

        # Test 2: Check if protection is enabled
        if ! gh api "repos/$REPO_OWNER/$REPO_NAME/branches/$branch/protection" &>/dev/null; then
            print_colored "${RED}" "❌ Branch protection not enabled for $branch"
            test_passed=false
            continue
        fi

        # Test 3: Verify quality gates
        if verify_branch_protection "$branch"; then
            print_colored "${GREEN}" "✅ Branch protection working correctly for $branch"
        else
            print_colored "${RED}" "❌ Branch protection issues found for $branch"
            test_passed=false
        fi

        echo ""
    done

    if [[ "$test_passed" == "true" ]]; then
        print_colored "${GREEN}" "🎉 All branch protection tests passed!"
        return 0
    else
        print_colored "${RED}" "❌ Some branch protection tests failed"
        return 1
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Setup GitHub branch protection rules for mem0-stack quality gates.

OPTIONS:
    -h, --help          Show this help message
    -a, --apply         Apply branch protection rules
    -v, --verify        Verify existing branch protection rules
    -t, --test          Test branch protection configuration
    -s, --show          Show protection summary
    --dry-run          Show what would be applied without making changes

EXAMPLES:
    $0 --apply          Apply branch protection rules
    $0 --verify         Verify current rules
    $0 --test           Test protection configuration
    $0 --show           Show protection summary

REQUIREMENTS:
    - GitHub CLI (gh) must be installed and authenticated
    - Repository access permissions for $REPO_OWNER/$REPO_NAME
    - Admin permissions to modify branch protection rules

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
            -a|--apply)
                action="apply"
                shift
                ;;
            -v|--verify)
                action="verify"
                shift
                ;;
            -t|--test)
                action="test"
                shift
                ;;
            -s|--show)
                action="show"
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
        action="show"
    fi

    # Print header
    print_header "🚀 mem0-stack Branch Protection Setup"
    print_colored "${BLUE}" "Step 2.3: CI/CD Integration with Quality Gates"
    print_colored "${BLUE}" "Action: $action"
    if [[ "$dry_run" == "true" ]]; then
        print_colored "${YELLOW}" "Mode: DRY RUN (no changes will be made)"
    fi
    echo ""

    # Check prerequisites
    check_github_cli

    # Execute action
    case "$action" in
        "apply")
            if [[ "$dry_run" == "true" ]]; then
                print_colored "${YELLOW}" "DRY RUN: Would apply branch protection rules"
                show_protection_summary
            else
                print_header "🔐 Applying Branch Protection Rules"
                apply_branch_protection "$MAIN_BRANCH"
                apply_branch_protection "$DEVELOP_BRANCH"
                print_colored "${GREEN}" "✅ Branch protection rules applied successfully"
            fi
            ;;
        "verify")
            print_header "🔍 Verifying Branch Protection Rules"
            verify_branch_protection "$MAIN_BRANCH"
            verify_branch_protection "$DEVELOP_BRANCH"
            ;;
        "test")
            test_branch_protection
            ;;
        "show")
            show_protection_summary
            ;;
        *)
            print_colored "${RED}" "Unknown action: $action"
            show_usage
            exit 1
            ;;
    esac

    echo ""
    print_colored "${GREEN}" "🎉 Branch protection setup completed!"
    print_colored "${GREEN}" "🚫 Merges will now be blocked until ALL quality gates pass"
    print_colored "${GREEN}" "📊 This ensures zero major bugs reach the main branch"
}

# Run main function
main "$@"
