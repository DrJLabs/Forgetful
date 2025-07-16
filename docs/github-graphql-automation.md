# GitHub Projects v2 GraphQL Automation Suite

## 🚀 Overview

This comprehensive automation suite leverages GitHub's GraphQL API to provide advanced project management capabilities for GitHub Projects v2. The suite includes intelligent field management, sprint tracking, analytics, and workflow automation.

## 📋 Table of Contents

- [Installation & Setup](#installation--setup)
- [Available Tools](#available-tools)
- [GraphQL Automation Scripts](#graphql-automation-scripts)
- [Advanced Features](#advanced-features)
- [Workflow Integration](#workflow-integration)
- [API Examples](#api-examples)
- [Best Practices](#best-practices)

## 🛠️ Installation & Setup

### Prerequisites

- **GitHub CLI**: `gh` command installed and authenticated
- **Python 3.8+**: For advanced scripts
- **jq**: For JSON processing in shell scripts
- **GitHub Project**: Access to organization project with appropriate permissions

### Authentication

Ensure GitHub CLI is authenticated with project permissions:

```bash
gh auth refresh -s project
gh auth status
```

### Required Scopes

Your GitHub token needs these scopes:
- `project` - Full project access
- `read:project` - Read project data
- `repo` - Repository access for issue/PR integration

## 🔧 Available Tools

### 1. Basic GraphQL Automation (`gh_project_automation.sh`)

**Purpose**: Comprehensive project item management using shell scripting and GraphQL.

**Key Features**:
- Intelligent field value assignment based on issue content
- Bulk sprint management
- Project analytics and dashboard
- Draft issue creation
- Status synchronization

**Usage Examples**:

```bash
# Configure all project items with smart field values
./scripts/gh_project_automation.sh configure

# Display project dashboard
./scripts/gh_project_automation.sh dashboard

# Move issues to specific sprint
./scripts/gh_project_automation.sh sprint sprint1 18 19 23

# Create a draft issue
./scripts/gh_project_automation.sh draft "New Feature" "Description here"

# Get project analytics
./scripts/gh_project_automation.sh analytics
```

### 2. Advanced Python Manager (`gh_project_advanced.py`)

**Purpose**: Advanced analytics and project management with rich data processing.

**Key Features**:
- Comprehensive project analytics
- Sprint board visualization
- Velocity reporting
- Health metrics calculation
- Smart data aggregation

**Usage Examples**:

```bash
# Generate detailed analytics
python3 scripts/gh_project_advanced.py analytics

# View sprint board
python3 scripts/gh_project_advanced.py sprint-board --sprint "Sprint 1"

# Calculate team velocity
python3 scripts/gh_project_advanced.py velocity --weeks 4

# Project health check
python3 scripts/gh_project_advanced.py health-check

# Get raw project overview
python3 scripts/gh_project_advanced.py overview --format json
```

### 3. Workflow Automation (`gh_project_workflow.py`)

**Purpose**: Simulate and manage automated workflows with webhook integration.

**Key Features**:
- Webhook event simulation
- Automated field assignment based on content analysis
- PR-to-issue linking
- Status synchronization rules
- Component detection algorithms

**Usage Examples**:

```bash
# Generate automation report
python3 scripts/gh_project_workflow.py report

# Simulate webhook processing
python3 scripts/gh_project_workflow.py simulate-webhook

# Test automation scenarios
python3 scripts/gh_project_workflow.py test-automation

# Create automation rules
python3 scripts/gh_project_workflow.py create-rules
```

## 🎯 GraphQL Automation Scripts

### Project Structure Query

```graphql
query ProjectOverview($orgLogin: String!, $projectNumber: Int!) {
  organization(login: $orgLogin) {
    projectV2(number: $projectNumber) {
      id
      title
      fields(first: 20) {
        nodes {
          ... on ProjectV2FieldCommon {
            id
            name
          }
          ... on ProjectV2SingleSelectField {
            id
            name
            options {
              id
              name
            }
          }
        }
      }
      items(first: 100) {
        nodes {
          id
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
              title
              number
              url
              state
              labels(first: 10) {
                nodes {
                  name
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### Update Project Item Mutation

```graphql
mutation UpdateProjectItem($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
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
}
```

### Add Issue to Project Mutation

```graphql
mutation AddIssueToProject($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(
    input: {
      projectId: $projectId
      contentId: $contentId
    }
  ) {
    item {
      id
    }
  }
}
```

## 🚀 Advanced Features

### 1. Intelligent Field Assignment

The automation suite includes smart algorithms for:

- **Component Detection**: Analyzes issue titles, descriptions, and labels to assign appropriate components
- **Priority Assessment**: Uses keyword analysis to determine priority levels
- **Effort Estimation**: Estimates effort based on content complexity and keywords
- **Sprint Assignment**: Automatically assigns high-priority items to current sprint

### 2. Analytics Dashboard

Comprehensive analytics including:

- **Distribution Analysis**: Field value distributions across all project items
- **Health Metrics**: Completion rates, progress tracking, priority focus
- **Velocity Reporting**: Team velocity calculation with story point mapping
- **Sprint Analytics**: Per-sprint progress and completion metrics

### 3. Workflow Automation

Simulated automation workflows for:

- **Issue Auto-Assignment**: Automatically add new issues to project with default values
- **PR Linking**: Link pull requests to related project items based on keywords
- **Status Synchronization**: Keep project status in sync with issue/PR states
- **Field Updates**: Automatically update fields based on external events

## 🔄 Workflow Integration

### Webhook Event Processing

The suite can process various GitHub webhook events:

```json
{
  "action": "opened",
  "issue": {
    "title": "Critical security vulnerability in mem0 API",
    "body": "Security issue requiring immediate attention...",
    "labels": [
      {"name": "security"},
      {"name": "critical"},
      {"name": "backend"}
    ]
  }
}
```

**Automated Actions**:
- Assign component: `mem0_api`
- Set priority: `critical`
- Estimate effort: `l` (3-5 days)
- Add to current sprint
- Set status: `todo`

### GitHub Actions Integration

Example workflow file (`.github/workflows/project-automation.yml`):

```yaml
name: Project Automation
on:
  issues:
    types: [opened, closed]
  pull_request:
    types: [opened, merged]

jobs:
  project-automation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup GitHub CLI
        uses: actions/setup-gh@v1
      - name: Run Project Automation
        run: |
          ./scripts/gh_project_automation.sh configure
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 📊 API Examples

### Real-time Project Analytics

```bash
# Get current project health
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     -d '{"query":"query{organization(login:\"DrJLabs\"){projectV2(number:4){items{totalCount}}}}"}' \
     https://api.github.com/graphql
```

### Bulk Field Updates

```bash
# Update multiple items at once
python3 scripts/gh_project_advanced.py bulk-update \
  --items '[{"item_id":"PVTI_...", "fields":{"priority":"high","component":"mem0_api"}}]'
```

### Sprint Planning

```bash
# Plan Sprint 2 with specific issues
./scripts/gh_project_automation.sh sprint sprint2 20 21 24
```

## 🏆 Best Practices

### 1. GraphQL Query Optimization

- **Use Fragments**: Reuse common field selections
- **Pagination**: Handle large datasets with proper pagination
- **Field Selection**: Only request needed fields to reduce response size
- **Rate Limiting**: Implement proper rate limiting (5000 points/hour)

### 2. Error Handling

```python
def safe_graphql_query(query, variables=None):
    try:
        result = run_graphql_query(query, variables)
        if 'errors' in result:
            log_error(f"GraphQL errors: {result['errors']}")
            return None
        return result['data']
    except Exception as e:
        log_error(f"Query failed: {e}")
        return None
```

### 3. Automation Guidelines

- **Incremental Updates**: Update fields incrementally rather than bulk operations
- **Validation**: Validate field values before updates
- **Logging**: Comprehensive logging for audit trails
- **Rollback**: Implement rollback mechanisms for failed operations

### 4. Performance Optimization

- **Caching**: Cache field IDs and option mappings
- **Batching**: Batch multiple updates when possible
- **Async Operations**: Use asynchronous operations for large datasets
- **Monitoring**: Monitor API usage and performance metrics

## 🔍 Monitoring & Analytics

### Project Health Dashboard

The suite provides comprehensive project health monitoring:

```bash
# Current project health
python3 scripts/gh_project_advanced.py health-check
```

**Output**:
```
🏥 PROJECT HEALTH CHECK
==============================
🟢 Completion Rate: 85.7%
🟡 In Progress Rate: 14.3%
🟢 Backlog Rate: 0.0%
🟢 Assigned Rate: 100.0%
🟢 Priority Focus: 71.4%
```

### Velocity Tracking

```bash
# Team velocity over last 4 weeks
python3 scripts/gh_project_advanced.py velocity --weeks 4
```

### Sprint Analytics

```bash
# Sprint 1 board view
python3 scripts/gh_project_advanced.py sprint-board --sprint "Sprint 1"
```

## 🚧 Future Enhancements

### Planned Features

1. **Machine Learning Integration**: Smart effort estimation using ML models
2. **Predictive Analytics**: Project completion date predictions
3. **Resource Optimization**: Team capacity planning and workload distribution
4. **Integration APIs**: Connect with external tools (Slack, email, etc.)
5. **Custom Dashboards**: Configurable dashboard views
6. **Automated Reporting**: Scheduled reports and notifications

### API Roadmap

- **Real-time Webhooks**: Live project updates via websockets
- **Advanced Queries**: Complex filtering and search capabilities
- **Bulk Operations**: Enhanced bulk update capabilities
- **Version Control**: Track project configuration changes
- **Export/Import**: Project configuration backup and restore

## 📚 Resources

### Documentation Links

- [GitHub GraphQL API Documentation](https://docs.github.com/en/graphql)
- [GitHub Projects v2 API Reference](https://docs.github.com/en/graphql/reference/objects#projectv2)
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)

### Example Queries

See the `/examples` directory for more GraphQL query examples and use cases.

### Support

For issues and questions:
1. Check the troubleshooting section in this document
2. Review GitHub GraphQL API documentation
3. Create an issue in this repository

---

**Created with GitHub GraphQL API automation suite**
*Leveraging the power of GitHub's GraphQL API for advanced project management*
