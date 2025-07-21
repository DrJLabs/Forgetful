#!/usr/bin/env python3
"""
GitHub Projects v2 Workflow Automation
Demonstrates integration with webhooks and automated workflows
"""

import argparse
import json
import subprocess
import sys
from typing import Any


class ProjectWorkflowManager:
    """Manage automated workflows for GitHub Projects v2"""

    def __init__(self, org_login: str = "DrJLabs", project_number: int = 4):
        self.org_login = org_login
        self.project_number = project_number
        self.project_id = "PVT_kwDODJoJJc4A9rrb"

        # Workflow templates
        self.workflow_templates = {
            "issue_auto_assign": {
                "name": "Auto-assign issues to project",
                "description": "Automatically add new issues to the project with default values",
                "trigger": "issues.opened",
            },
            "pr_auto_link": {
                "name": "Auto-link PRs to project items",
                "description": "Automatically link PRs to related project items based on keywords",
                "trigger": "pull_request.opened",
            },
            "status_sync": {
                "name": "Sync issue/PR status with project",
                "description": "Keep project item status in sync with issue/PR state",
                "trigger": ["issues.closed", "pull_request.merged"],
            },
        }

    def run_graphql_query(self, query: str, variables: dict[str, Any] = None) -> dict:
        """Execute a GraphQL query using GitHub CLI"""
        cmd = ["gh", "api", "graphql", "-f", f"query={query}"]

        if variables:
            for key, value in variables.items():
                if isinstance(value, int):
                    cmd.extend(["-F", f"{key}={value}"])
                else:
                    cmd.extend(["-f", f"{key}={value}"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"GraphQL query failed: {e.stderr}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            return {}

    def create_automation_rules(self) -> dict:
        """Create project automation rules using GraphQL"""

        # Example: Create a workflow that automatically moves items to "In Progress"
        # when a linked PR is opened

        # Since we can't actually create workflows via GraphQL (they're configured in the UI),
        # let's demonstrate by creating comprehensive automation scripts instead

        automation_config = {
            "auto_assignment_rules": {
                "component_mapping": {
                    "backend": "mem0_api",
                    "frontend": "openmemory_ui",
                    "database": "database_postgresql",
                    "infra": "infrastructure",
                    "test": "testing",
                    "security": "security",
                },
                "priority_keywords": {
                    "critical": ["critical", "urgent", "blocking", "security"],
                    "high": ["important", "high", "priority"],
                    "medium": ["enhancement", "feature"],
                    "low": ["cleanup", "refactor", "documentation"],
                },
                "effort_estimation": {
                    "xs": ["typo", "comment", "small"],
                    "s": ["minor", "quick", "simple"],
                    "m": ["feature", "enhancement"],
                    "l": ["complex", "major", "integration"],
                    "xl": ["epic", "architecture", "migration"],
                    "xxl": ["platform", "redesign", "complete"],
                },
            }
        }

        return automation_config

    def simulate_webhook_processing(self, webhook_event: dict) -> dict:
        """Simulate processing a GitHub webhook event"""

        event_type = webhook_event.get("action")
        issue_data = webhook_event.get("issue", {})
        pr_data = webhook_event.get("pull_request", {})

        results = {"actions_taken": [], "recommendations": []}

        if event_type == "opened" and issue_data:
            # Process new issue
            actions = self.process_new_issue(issue_data)
            results["actions_taken"].extend(actions)

        elif event_type == "opened" and pr_data:
            # Process new PR
            actions = self.process_new_pr(pr_data)
            results["actions_taken"].extend(actions)

        elif event_type in ["closed", "merged"]:
            # Process completion
            actions = self.process_completion(issue_data or pr_data)
            results["actions_taken"].extend(actions)

        return results

    def process_new_issue(self, issue_data: dict) -> list[str]:
        """Process a new issue and determine automation actions"""
        actions = []

        title = issue_data.get("title", "").lower()
        body = issue_data.get("body", "").lower()
        labels = [label["name"].lower() for label in issue_data.get("labels", [])]

        # Auto-assign component based on title/labels
        component = self.detect_component(title, body, labels)
        if component:
            actions.append(f"Would assign component: {component}")

        # Auto-assign priority based on keywords
        priority = self.detect_priority(title, body, labels)
        if priority:
            actions.append(f"Would assign priority: {priority}")

        # Auto-estimate effort
        effort = self.estimate_effort(title, body)
        if effort:
            actions.append(f"Would estimate effort: {effort}")

        # Auto-assign to current sprint if high priority
        if priority in ["critical", "high"]:
            actions.append("Would assign to current sprint")

        # Add to project
        actions.append("Would add issue to project")

        return actions

    def process_new_pr(self, pr_data: dict) -> list[str]:
        """Process a new PR and determine automation actions"""
        actions = []

        pr_data.get("title", "").lower()
        body = pr_data.get("body", "").lower()

        # Try to link to existing project items based on keywords
        linked_issues = self.find_linked_issues(body)
        if linked_issues:
            actions.append(f"Would link to issues: {linked_issues}")

        # Auto-move linked items to "In Progress"
        if linked_issues:
            actions.append("Would move linked items to 'In Progress'")

        return actions

    def process_completion(self, item_data: dict) -> list[str]:
        """Process completion of issue/PR"""
        actions = []

        state = item_data.get("state")

        if state == "closed":
            actions.append("Would move project item to 'Done'")
            actions.append("Would update completion metrics")

        return actions

    def detect_component(self, title: str, body: str, labels: list[str]) -> str:
        """Detect component based on content analysis"""

        component_keywords = {
            "mem0_api": ["mem0", "api", "server", "backend"],
            "openmemory_api": ["openmemory", "mcp", "protocol"],
            "openmemory_ui": ["ui", "frontend", "react", "interface"],
            "database_postgresql": ["database", "postgres", "sql", "db"],
            "infrastructure": ["docker", "deploy", "infra", "devops"],
            "monitoring": ["monitoring", "metrics", "observability"],
            "testing": ["test", "testing", "coverage", "qa"],
            "security": ["security", "auth", "encryption", "vulnerability"],
        }

        text = f"{title} {body} {' '.join(labels)}"

        for component, keywords in component_keywords.items():
            if any(keyword in text for keyword in keywords):
                return component

        return "unknown"

    def detect_priority(self, title: str, body: str, labels: list[str]) -> str:
        """Detect priority based on keywords"""

        priority_keywords = {
            "critical": ["critical", "urgent", "blocking", "security", "production"],
            "high": ["important", "high", "priority", "bug"],
            "medium": ["enhancement", "feature", "improvement"],
            "low": ["cleanup", "refactor", "documentation", "minor"],
        }

        text = f"{title} {body} {' '.join(labels)}"

        # Check labels first (they're usually more reliable)
        for label in labels:
            for priority, keywords in priority_keywords.items():
                if any(keyword in label for keyword in keywords):
                    return priority

        # Then check title and body
        for priority, keywords in priority_keywords.items():
            if any(keyword in text for keyword in keywords):
                return priority

        return "medium"

    def estimate_effort(self, title: str, body: str) -> str:
        """Estimate effort based on content complexity"""

        text = f"{title} {body}".lower()

        # Simple heuristic: longer descriptions = more effort
        word_count = len(text.split())

        if word_count < 10:
            return "xs"
        elif word_count < 30:
            return "s"
        elif word_count < 100:
            return "m"
        elif word_count < 200:
            return "l"
        else:
            return "xl"

    def find_linked_issues(self, pr_body: str) -> list[str]:
        """Find issue numbers mentioned in PR body"""
        import re

        # Look for patterns like "fixes #123", "closes #456", etc.
        patterns = [
            r"(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+#(\d+)",
            r"#(\d+)",
        ]

        linked_issues = []
        for pattern in patterns:
            matches = re.findall(pattern, pr_body.lower())
            linked_issues.extend(matches)

        return list(set(linked_issues))  # Remove duplicates

    def generate_automation_report(self) -> dict:
        """Generate a report on current automation capabilities"""

        report = {
            "automation_summary": {
                "available_workflows": len(self.workflow_templates),
                "supported_events": [
                    "issues.opened",
                    "issues.closed",
                    "pull_request.opened",
                    "pull_request.merged",
                    "project_v2_item.created",
                    "project_v2_item.edited",
                ],
            },
            "workflow_templates": self.workflow_templates,
            "automation_rules": self.create_automation_rules(),
            "graphql_capabilities": {
                "mutations": [
                    "addProjectV2ItemById",
                    "updateProjectV2ItemFieldValue",
                    "archiveProjectV2Item",
                    "deleteProjectV2Item",
                ],
                "queries": [
                    "organization.projectV2",
                    "repository.issue.projectItems",
                    "repository.pullRequest.projectItems",
                ],
            },
            "webhook_integration": {
                "supported_events": ["issues", "pull_request", "project_v2_item"],
                "automation_actions": [
                    "Auto-assign to project",
                    "Set default field values",
                    "Link related items",
                    "Update status based on state",
                    "Generate analytics",
                ],
            },
        }

        return report


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Projects v2 Workflow Automation"
    )
    parser.add_argument(
        "command",
        choices=["report", "simulate-webhook", "create-rules", "test-automation"],
        help="Command to execute",
    )
    parser.add_argument("--event-file", help="JSON file containing webhook event data")
    parser.add_argument(
        "--format", choices=["json", "pretty"], default="pretty", help="Output format"
    )

    args = parser.parse_args()

    manager = ProjectWorkflowManager()

    try:
        if args.command == "report":
            result = manager.generate_automation_report()

        elif args.command == "simulate-webhook":
            if not args.event_file:
                # Create a sample webhook event for demonstration
                sample_event = {
                    "action": "opened",
                    "issue": {
                        "title": "Critical security vulnerability in mem0 API authentication",
                        "body": "We've discovered a critical security issue in the authentication flow of the mem0 API that could allow unauthorized access. This needs immediate attention and should be fixed in the current sprint.",
                        "labels": [
                            {"name": "security"},
                            {"name": "critical"},
                            {"name": "backend"},
                        ],
                    },
                }
            else:
                with open(args.event_file) as f:
                    sample_event = json.load(f)

            result = manager.simulate_webhook_processing(sample_event)

        elif args.command == "create-rules":
            result = manager.create_automation_rules()

        elif args.command == "test-automation":
            # Test various automation scenarios
            test_cases = [
                {
                    "action": "opened",
                    "issue": {
                        "title": "Add database connection pooling",
                        "body": "Implement connection pooling for PostgreSQL to improve performance",
                        "labels": [{"name": "enhancement"}, {"name": "database"}],
                    },
                },
                {
                    "action": "opened",
                    "pull_request": {
                        "title": "Fix authentication bug",
                        "body": "This PR fixes #123 and resolves the authentication issue",
                    },
                },
            ]

            result = {"test_results": []}
            for i, test_case in enumerate(test_cases):
                test_result = manager.simulate_webhook_processing(test_case)
                result["test_results"].append(
                    {f"test_case_{i + 1}": test_case, "automation_result": test_result}
                )

        # Output results
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            print_workflow_report(result, args.command)

    except Exception as e:
        print(f"Error executing command: {e}")
        sys.exit(1)


def print_workflow_report(data: dict, command: str):
    """Pretty print workflow automation reports"""

    if command == "report":
        print("🤖 GITHUB PROJECTS v2 AUTOMATION REPORT")
        print("=" * 50)

        summary = data.get("automation_summary", {})
        print(f"📊 Available Workflows: {summary.get('available_workflows', 0)}")
        print(f"🎯 Supported Events: {len(summary.get('supported_events', []))}")

        print("\n🔧 WORKFLOW TEMPLATES")
        print("-" * 30)
        for name, template in data.get("workflow_templates", {}).items():
            print(f"• {template['name']}")
            print(f"  Description: {template['description']}")
            print(f"  Trigger: {template['trigger']}")

        print("\n🔗 GRAPHQL CAPABILITIES")
        print("-" * 30)
        capabilities = data.get("graphql_capabilities", {})
        print("Mutations:")
        for mutation in capabilities.get("mutations", []):
            print(f"  • {mutation}")
        print("Queries:")
        for query in capabilities.get("queries", []):
            print(f"  • {query}")

    elif command == "simulate-webhook":
        print("🔄 WEBHOOK SIMULATION RESULTS")
        print("=" * 40)

        actions = data.get("actions_taken", [])
        print(f"✅ Actions Taken ({len(actions)}):")
        for action in actions:
            print(f"  • {action}")

        recommendations = data.get("recommendations", [])
        if recommendations:
            print(f"\n💡 Recommendations ({len(recommendations)}):")
            for rec in recommendations:
                print(f"  • {rec}")

    elif command == "test-automation":
        print("🧪 AUTOMATION TEST RESULTS")
        print("=" * 40)

        for i, test_result in enumerate(data.get("test_results", [])):
            print(f"\n🔬 Test Case {i + 1}")
            print("-" * 20)

            test_case = test_result[f"test_case_{i + 1}"]
            automation_result = test_result["automation_result"]

            print(f"Event: {test_case.get('action')}")
            if "issue" in test_case:
                print(f"Issue: {test_case['issue']['title']}")
            elif "pull_request" in test_case:
                print(f"PR: {test_case['pull_request']['title']}")

            print("Actions:")
            for action in automation_result.get("actions_taken", []):
                print(f"  ✓ {action}")


if __name__ == "__main__":
    main()
