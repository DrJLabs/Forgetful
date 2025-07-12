#!/bin/bash
# GitHub Projects v2 GraphQL Automation Script
# Comprehensive project management automation using the GitHub GraphQL API

set -e

# Project Configuration
PROJECT_ID="PVT_kwDODJoJJc4A9rrb"
ORG_LOGIN="DrJLabs"
REPO_OWNER="DrJLabs"
REPO_NAME="Forgetful"

# Field IDs
COMPONENT_FIELD_ID="PVTSSF_lADODJoJJc4A9rrbzgxUAn8"
PRIORITY_FIELD_ID="PVTSSF_lADODJoJJc4A9rrbzgxUApU"
EPIC_FIELD_ID="PVTSSF_lADODJoJJc4A9rrbzgxUAqU"
EFFORT_FIELD_ID="PVTSSF_lADODJoJJc4A9rrbzgxUAsU"
SPRINT_FIELD_ID="PVTSSF_lADODJoJJc4A9rrbzgxUAto"
STATUS_FIELD_ID="PVTSSF_lADODJoJJc4A9rrbzgxUAhA"

# Option IDs for Component field
declare -A COMPONENT_OPTIONS=(
    ["mem0_api"]="e60054b6"
    ["openmemory_api"]="e09ac68e"
    ["openmemory_ui"]="99fec49c"
    ["database_postgresql"]="e86c4042"
    ["database_neo4j"]="4bc0e5f6"
    ["infrastructure"]="d1503f05"
    ["monitoring"]="befa2169"
    ["testing"]="cdff6a2b"
    ["documentation"]="0c613697"
    ["security"]="55f30032"
    ["performance"]="663c6b5e"
    ["deployment"]="f7ca4036"
)

# Option IDs for Priority field
declare -A PRIORITY_OPTIONS=(
    ["critical"]="29b94610"
    ["high"]="4d33ba47"
    ["medium"]="d08cd073"
    ["low"]="d8430c60"
)

# Option IDs for Epic field
declare -A EPIC_OPTIONS=(
    ["service_development"]="e6274667"
    ["infrastructure_devops"]="28798428"
    ["database_management"]="c6e57ab0"
    ["observability_monitoring"]="85eb592f"
    ["testing_quality"]="37d5174e"
    ["documentation"]="6fbd5fdf"
    ["security_compliance"]="da4f0d2d"
    ["performance_optimization"]="701fd251"
    ["deployment_cicd"]="ab07416e"
    ["project_management"]="c7d5186c"
)

# Option IDs for Effort field
declare -A EFFORT_OPTIONS=(
    ["xs"]="3cba95ac"  # XS (1 hour)
    ["s"]="4d2713d2"   # S (2-4 hours)
    ["m"]="e861f4da"   # M (1-2 days)
    ["l"]="9410ca49"   # L (3-5 days)
    ["xl"]="7ebb7f86"  # XL (1-2 weeks)
    ["xxl"]="92517ed0" # XXL (3+ weeks)
)

# Option IDs for Sprint field
declare -A SPRINT_OPTIONS=(
    ["backlog"]="e4e86d0f"
    ["sprint1"]="43faa0dd"
    ["sprint2"]="e87ff7d2"
    ["sprint3"]="cb89f4e5"
    ["sprint4"]="8abfcbb3"
    ["sprint5"]="6007fcc5"
    ["sprint6"]="698b839e"
    ["done"]="ae59001e"
)

# Option IDs for Status field
declare -A STATUS_OPTIONS=(
    ["todo"]="f75ad846"
    ["in_progress"]="47fc9ee4"
    ["done"]="98236657"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "\n${PURPLE}=== $1 ===${NC}"
}

# Function to update a project item field
update_project_item_field() {
    local item_id="$1"
    local field_id="$2"
    local option_id="$3"
    local field_name="$4"

    log_info "Updating field '$field_name' for item $item_id"

    gh api graphql -f query='
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
            updateProjectV2ItemFieldValue(
                input: {
                    projectId: $projectId
                    itemId: $itemId
                    fieldId: $fieldId
                    value: {
                        singleSelectOptionId: $optionId
                    }
                }
            ) {
                projectV2Item {
                    id
                }
            }
        }' \
        -f projectId="$PROJECT_ID" \
        -f itemId="$item_id" \
        -f fieldId="$field_id" \
        -f optionId="$option_id" \
        > /dev/null

    if [ $? -eq 0 ]; then
        log_success "Updated $field_name successfully"
    else
        log_error "Failed to update $field_name"
        return 1
    fi
}

# Function to get all project items
get_project_items() {
    log_info "Fetching all project items..."

    gh api graphql -f query='
        query($orgLogin: String!, $projectNumber: Int!) {
            organization(login: $orgLogin) {
                projectV2(number: $projectNumber) {
                    items(first: 50) {
                        nodes {
                            id
                            content {
                                ... on Issue {
                                    title
                                    number
                                    url
                                }
                            }
                        }
                    }
                }
            }
        }' \
        -f orgLogin="$ORG_LOGIN" \
        -F projectNumber=4 \
        --jq '.data.organization.projectV2.items.nodes[]'
}

# Function to configure project items based on issue content
configure_project_items() {
    log_header "Configuring Project Items with Smart Field Values"

    # Define item configurations based on issue titles
    declare -A ITEM_CONFIGS=(
        ["mem0 API Service Enhancements"]="component:mem0_api priority:high epic:service_development effort:xl sprint:sprint1"
        ["OpenMemory MCP Server Integration Optimization"]="component:openmemory_api priority:high epic:service_development effort:l sprint:sprint1"
        ["Infrastructure and DevOps Optimization"]="component:infrastructure priority:high epic:infrastructure_devops effort:xl sprint:sprint2"
        ["Database Management and Performance Optimization"]="component:database_postgresql priority:medium epic:database_management effort:l sprint:sprint2"
        ["Observability and Monitoring System Enhancement"]="component:monitoring priority:medium epic:observability_monitoring effort:l sprint:sprint3"
        ["Comprehensive Testing Framework Implementation"]="component:testing priority:high epic:testing_quality effort:xl sprint:sprint1"
        ["Security and Compliance Enhancement"]="component:security priority:high epic:security_compliance effort:l sprint:sprint2"
    )

    # Get all project items
    local items_json
    items_json=$(get_project_items)

    # Process each item
    while IFS= read -r item; do
        local item_id=$(echo "$item" | jq -r '.id')
        local title=$(echo "$item" | jq -r '.content.title // empty')
        local number=$(echo "$item" | jq -r '.content.number // empty')

        if [ -z "$title" ] || [ "$title" = "null" ]; then
            log_warning "Skipping item $item_id - no title found"
            continue
        fi

        log_info "Processing: Issue #$number - $title"

        # Get configuration for this item
        local config="${ITEM_CONFIGS[$title]}"
        if [ -z "$config" ]; then
            log_warning "No configuration found for: $title"
            continue
        fi

        # Parse and apply configuration
        for setting in $config; do
            IFS=':' read -r field_type value <<< "$setting"

            case "$field_type" in
                "component")
                    update_project_item_field "$item_id" "$COMPONENT_FIELD_ID" "${COMPONENT_OPTIONS[$value]}" "Component"
                    ;;
                "priority")
                    update_project_item_field "$item_id" "$PRIORITY_FIELD_ID" "${PRIORITY_OPTIONS[$value]}" "Priority"
                    ;;
                "epic")
                    update_project_item_field "$item_id" "$EPIC_FIELD_ID" "${EPIC_OPTIONS[$value]}" "Epic"
                    ;;
                "effort")
                    update_project_item_field "$item_id" "$EFFORT_FIELD_ID" "${EFFORT_OPTIONS[$value]}" "Effort"
                    ;;
                "sprint")
                    update_project_item_field "$item_id" "$SPRINT_FIELD_ID" "${SPRINT_OPTIONS[$value]}" "Sprint"
                    ;;
            esac
            sleep 0.5  # Rate limiting
        done

        # Set default status to Todo
        update_project_item_field "$item_id" "$STATUS_FIELD_ID" "${STATUS_OPTIONS[todo]}" "Status"

        log_success "Configured item: $title"
        echo
    done <<< "$items_json"
}

# Function to create a draft issue in the project
create_draft_issue() {
    local title="$1"
    local body="$2"

    log_info "Creating draft issue: $title"

    gh api graphql -f query='
        mutation($projectId: ID!, $title: String!, $body: String!) {
            addProjectV2DraftIssue(
                input: {
                    projectId: $projectId
                    title: $title
                    body: $body
                }
            ) {
                projectItem {
                    id
                }
            }
        }' \
        -f projectId="$PROJECT_ID" \
        -f title="$title" \
        -f body="$body"
}

# Function to get project analytics
get_project_analytics() {
    log_header "Project Analytics & Insights"

    gh api graphql -f query='
        query($orgLogin: String!, $projectNumber: Int!) {
            organization(login: $orgLogin) {
                projectV2(number: $projectNumber) {
                    title
                    items(first: 100) {
                        totalCount
                        nodes {
                            fieldValues(first: 20) {
                                nodes {
                                    ... on ProjectV2ItemFieldSingleSelectValue {
                                        name
                                        field {
                                            ... on ProjectV2FieldCommon {
                                                name
                                            }
                                        }
                                    }
                                }
                            }
                            content {
                                ... on Issue {
                                    state
                                    createdAt
                                }
                            }
                        }
                    }
                }
            }
        }' \
        -f orgLogin="$ORG_LOGIN" \
        -F projectNumber=4 \
        --jq '
            .data.organization.projectV2 as $project |
            {
                title: $project.title,
                totalItems: $project.items.totalCount,
                itemsByStatus: [
                    $project.items.nodes[] |
                    .fieldValues.nodes[] |
                    select(.field.name == "Status") |
                    .name
                ] | group_by(.) | map({status: .[0], count: length}),
                itemsByPriority: [
                    $project.items.nodes[] |
                    .fieldValues.nodes[] |
                    select(.field.name == "Priority") |
                    .name
                ] | group_by(.) | map({priority: .[0], count: length}),
                itemsByComponent: [
                    $project.items.nodes[] |
                    .fieldValues.nodes[] |
                    select(.field.name == "Component") |
                    .name
                ] | group_by(.) | map({component: .[0], count: length})
            }'
}

# Function to bulk update sprint assignments
bulk_update_sprint() {
    local sprint_name="$1"
    local issue_numbers=("${@:2}")

    log_header "Bulk Update: Moving Issues to $sprint_name"

    if [ -z "${SPRINT_OPTIONS[${sprint_name,,}]}" ]; then
        log_error "Invalid sprint name: $sprint_name"
        return 1
    fi

    local sprint_option_id="${SPRINT_OPTIONS[${sprint_name,,}]}"

    for issue_num in "${issue_numbers[@]}"; do
        log_info "Finding project item for issue #$issue_num"

        # Get the project item ID for this issue
        local item_id
        item_id=$(gh api graphql -f query='
            query($orgLogin: String!, $projectNumber: Int!) {
                organization(login: $orgLogin) {
                    projectV2(number: $projectNumber) {
                        items(first: 100) {
                            nodes {
                                id
                                content {
                                    ... on Issue {
                                        number
                                    }
                                }
                            }
                        }
                    }
                }
            }' \
            -f orgLogin="$ORG_LOGIN" \
            -F projectNumber=4 \
            --jq ".data.organization.projectV2.items.nodes[] | select(.content.number == $issue_num) | .id")

        if [ -n "$item_id" ] && [ "$item_id" != "null" ]; then
            update_project_item_field "$item_id" "$SPRINT_FIELD_ID" "$sprint_option_id" "Sprint"
            log_success "Moved issue #$issue_num to $sprint_name"
        else
            log_warning "Could not find project item for issue #$issue_num"
        fi
    done
}

# Function to show project dashboard
show_project_dashboard() {
    log_header "Project Dashboard"

    local analytics
    analytics=$(get_project_analytics)

    echo -e "${CYAN}Project Overview:${NC}"
    echo "$analytics" | jq -r '"Total Items: \(.totalItems)"'

    echo -e "\n${CYAN}Status Distribution:${NC}"
    echo "$analytics" | jq -r '.itemsByStatus[]? | "  \(.status // "Unassigned"): \(.count)"'

    echo -e "\n${CYAN}Priority Distribution:${NC}"
    echo "$analytics" | jq -r '.itemsByPriority[]? | "  \(.priority // "Unassigned"): \(.count)"'

    echo -e "\n${CYAN}Component Distribution:${NC}"
    echo "$analytics" | jq -r '.itemsByComponent[]? | "  \(.component // "Unassigned"): \(.count)"'
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if gh CLI is installed
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed"
        exit 1
    fi

    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed"
        exit 1
    fi

    # Check GitHub CLI authentication
    if ! gh auth status --hostname github.com &> /dev/null; then
        log_error "GitHub CLI is not authenticated"
        exit 1
    fi

    log_success "All prerequisites met"
}

# Main execution function
main() {
    local command="${1:-help}"

    check_prerequisites

    case "$command" in
        "configure")
            configure_project_items
            ;;
        "analytics")
            get_project_analytics | jq '.'
            ;;
        "dashboard")
            show_project_dashboard
            ;;
        "sprint")
            if [ $# -lt 3 ]; then
                log_error "Usage: $0 sprint <sprint_name> <issue_number> [issue_number...]"
                exit 1
            fi
            bulk_update_sprint "${@:2}"
            ;;
        "draft")
            if [ $# -lt 3 ]; then
                log_error "Usage: $0 draft <title> <body>"
                exit 1
            fi
            create_draft_issue "$2" "$3"
            ;;
        "help"|*)
            echo -e "${PURPLE}GitHub Projects v2 GraphQL Automation${NC}"
            echo
            echo "Usage: $0 <command> [options]"
            echo
            echo "Commands:"
            echo "  configure              - Configure all project items with smart field values"
            echo "  analytics             - Get project analytics in JSON format"
            echo "  dashboard             - Show formatted project dashboard"
            echo "  sprint <name> <nums>  - Move issues to specified sprint"
            echo "  draft <title> <body>  - Create a draft issue in the project"
            echo "  help                  - Show this help message"
            echo
            echo "Examples:"
            echo "  $0 configure"
            echo "  $0 dashboard"
            echo "  $0 sprint sprint1 18 19 23"
            echo "  $0 draft 'New Feature' 'Feature description'"
            ;;
    esac
}

# Run main function with all arguments
main "$@"