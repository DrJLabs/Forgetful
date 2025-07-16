#!/usr/bin/env python3
"""
Advanced GitHub Projects v2 GraphQL Automation
Comprehensive project management using GitHub's GraphQL API
"""

import argparse
import json
import subprocess
import sys
from typing import Any, Dict, List


class GitHubProjectManager:
    """Advanced GitHub Projects v2 management using GraphQL API"""

    def __init__(self, org_login: str = "DrJLabs", project_number: int = 4):
        self.org_login = org_login
        self.project_number = project_number
        self.project_id = "PVT_kwDODJoJJc4A9rrb"

        # Field mappings
        self.fields = {
            "component": "PVTSSF_lADODJoJJc4A9rrbzgxUAn8",
            "priority": "PVTSSF_lADODJoJJc4A9rrbzgxUApU",
            "epic": "PVTSSF_lADODJoJJc4A9rrbzgxUAqU",
            "effort": "PVTSSF_lADODJoJJc4A9rrbzgxUAsU",
            "sprint": "PVTSSF_lADODJoJJc4A9rrbzgxUAto",
            "status": "PVTSSF_lADODJoJJc4A9rrbzgxUAhA",
        }

        # Option mappings
        self.options = {
            "component": {
                "mem0_api": "e60054b6",
                "openmemory_api": "e09ac68e",
                "openmemory_ui": "99fec49c",
                "database_postgresql": "e86c4042",
                "database_neo4j": "4bc0e5f6",
                "infrastructure": "d1503f05",
                "monitoring": "befa2169",
                "testing": "cdff6a2b",
                "documentation": "0c613697",
                "security": "55f30032",
                "performance": "663c6b5e",
                "deployment": "f7ca4036",
            },
            "priority": {
                "critical": "29b94610",
                "high": "4d33ba47",
                "medium": "d08cd073",
                "low": "d8430c60",
            },
            "status": {
                "todo": "f75ad846",
                "in_progress": "47fc9ee4",
                "done": "98236657",
            },
        }

    def run_graphql_query(self, query: str, variables: Dict[str, Any] = None) -> Dict:
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

    def get_project_overview(self) -> Dict:
        """Get comprehensive project overview"""
        query = """
        query($orgLogin: String!, $projectNumber: Int!) {
            organization(login: $orgLogin) {
                projectV2(number: $projectNumber) {
                    title
                    url
                    readme
                    shortDescription
                    public
                    closed
                    createdAt
                    updatedAt
                    items(first: 100) {
                        totalCount
                        nodes {
                            id
                            type
                            createdAt
                            fieldValues(first: 20) {
                                nodes {
                                    ... on ProjectV2ItemFieldTextValue {
                                        text
                                        field {
                                            ... on ProjectV2FieldCommon {
                                                name
                                            }
                                        }
                                    }
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
                                    createdAt
                                    updatedAt
                                    assignees(first: 5) {
                                        nodes {
                                            login
                                        }
                                    }
                                    labels(first: 10) {
                                        nodes {
                                            name
                                            color
                                        }
                                    }
                                }
                            }
                        }
                    }
                    fields(first: 20) {
                        nodes {
                            ... on ProjectV2FieldCommon {
                                id
                                name
                                dataType
                            }
                            ... on ProjectV2SingleSelectField {
                                id
                                name
                                dataType
                                options {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        variables = {"orgLogin": self.org_login, "projectNumber": self.project_number}

        return self.run_graphql_query(query, variables)

    def generate_project_analytics(self) -> Dict:
        """Generate comprehensive project analytics"""
        data = self.get_project_overview()

        if not data or "data" not in data:
            return {}

        project = data["data"]["organization"]["projectV2"]
        items = project["items"]["nodes"]

        analytics = {
            "overview": {
                "title": project["title"],
                "total_items": project["items"]["totalCount"],
                "url": project["url"],
                "created_at": project["createdAt"],
                "updated_at": project["updatedAt"],
                "public": project["public"],
                "closed": project["closed"],
            },
            "distribution": {},
            "health_metrics": {},
            "trends": {},
        }

        # Analyze field distributions
        field_distributions = {}
        for item in items:
            for field_value in item["fieldValues"]["nodes"]:
                field_name = field_value.get("field", {}).get("name")
                if field_name:
                    if field_name not in field_distributions:
                        field_distributions[field_name] = {}

                    value = field_value.get("name") or field_value.get(
                        "text", "Unassigned"
                    )
                    field_distributions[field_name][value] = (
                        field_distributions[field_name].get(value, 0) + 1
                    )

        analytics["distribution"] = field_distributions

        # Calculate health metrics
        total_items = len(items)
        if total_items > 0:
            # Status health
            status_dist = field_distributions.get("Status", {})
            done_count = status_dist.get("Done", 0)
            in_progress_count = status_dist.get("In Progress", 0)
            todo_count = status_dist.get("Todo", 0)

            analytics["health_metrics"] = {
                "completion_rate": round((done_count / total_items) * 100, 2),
                "in_progress_rate": round((in_progress_count / total_items) * 100, 2),
                "backlog_rate": round((todo_count / total_items) * 100, 2),
                "assigned_rate": round(
                    (
                        (
                            total_items
                            - field_distributions.get("Status", {}).get("Unassigned", 0)
                        )
                        / total_items
                    )
                    * 100,
                    2,
                ),
            }

            # Priority distribution analysis
            priority_dist = field_distributions.get("Priority", {})
            critical_high = priority_dist.get("Critical", 0) + priority_dist.get(
                "High", 0
            )
            analytics["health_metrics"]["priority_focus"] = round(
                (critical_high / total_items) * 100, 2
            )

        return analytics

    def create_sprint_board_view(self, sprint_name: str) -> Dict:
        """Create a virtual sprint board view"""
        data = self.get_project_overview()

        if not data or "data" not in data:
            return {}

        items = data["data"]["organization"]["projectV2"]["items"]["nodes"]

        # Filter items for the specified sprint
        sprint_items = []
        for item in items:
            for field_value in item["fieldValues"]["nodes"]:
                if (
                    field_value.get("field", {}).get("name") == "Sprint"
                    and field_value.get("name", "").lower() == sprint_name.lower()
                ):
                    sprint_items.append(item)
                    break

        # Organize by status
        board = {"Todo": [], "In Progress": [], "Done": []}

        for item in sprint_items:
            status = "Todo"  # default
            component = "Unknown"
            priority = "Medium"

            for field_value in item["fieldValues"]["nodes"]:
                field_name = field_value.get("field", {}).get("name")
                if field_name == "Status":
                    status = field_value.get("name", "Todo")
                elif field_name == "Component":
                    component = field_value.get("name", "Unknown")
                elif field_name == "Priority":
                    priority = field_value.get("name", "Medium")

            item_info = {
                "id": item["id"],
                "title": item["content"]["title"] if item["content"] else "Draft Issue",
                "number": item["content"]["number"] if item["content"] else None,
                "url": item["content"]["url"] if item["content"] else None,
                "component": component,
                "priority": priority,
                "assignees": (
                    [a["login"] for a in item["content"]["assignees"]["nodes"]]
                    if item["content"] and item["content"]["assignees"]
                    else []
                ),
            }

            if status in board:
                board[status].append(item_info)

        return {
            "sprint": sprint_name,
            "board": board,
            "summary": {
                "total": len(sprint_items),
                "todo": len(board["Todo"]),
                "in_progress": len(board["In Progress"]),
                "done": len(board["Done"]),
            },
        }

    def bulk_update_items(self, updates: List[Dict]) -> Dict:
        """Bulk update multiple project items"""
        results = {"success": [], "failed": []}

        for update in updates:
            item_id = update.get("item_id")
            field_updates = update.get("fields", {})

            for field_name, value in field_updates.items():
                if field_name in self.fields and value in self.options.get(
                    field_name, {}
                ):
                    success = self.update_item_field(
                        item_id,
                        self.fields[field_name],
                        self.options[field_name][value],
                    )

                    if success:
                        results["success"].append(
                            {"item_id": item_id, "field": field_name, "value": value}
                        )
                    else:
                        results["failed"].append(
                            {
                                "item_id": item_id,
                                "field": field_name,
                                "value": value,
                                "error": "Update failed",
                            }
                        )

        return results

    def update_item_field(self, item_id: str, field_id: str, option_id: str) -> bool:
        """Update a single field for a project item"""
        mutation = """
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
        }
        """

        variables = {
            "projectId": self.project_id,
            "itemId": item_id,
            "fieldId": field_id,
            "optionId": option_id,
        }

        result = self.run_graphql_query(mutation, variables)
        return bool(
            result
            and "data" in result
            and result["data"]["updateProjectV2ItemFieldValue"]
        )

    def generate_velocity_report(self, weeks: int = 4) -> Dict:
        """Generate velocity report for the last N weeks"""
        data = self.get_project_overview()

        if not data or "data" not in data:
            return {}

        items = data["data"]["organization"]["projectV2"]["items"]["nodes"]

        # Calculate velocity based on completed items
        completed_items = []
        for item in items:
            status = None
            effort = None

            for field_value in item["fieldValues"]["nodes"]:
                field_name = field_value.get("field", {}).get("name")
                if field_name == "Status":
                    status = field_value.get("name")
                elif field_name == "Effort":
                    effort = field_value.get("name")

            if status == "Done":
                completed_items.append(
                    {
                        "title": (
                            item["content"]["title"] if item["content"] else "Draft"
                        ),
                        "effort": effort,
                        "completed_date": (
                            item["content"]["updatedAt"]
                            if item["content"]
                            else item["createdAt"]
                        ),
                    }
                )

        # Map effort to story points
        effort_points = {
            "XS (1 hour)": 1,
            "S (2-4 hours)": 2,
            "M (1-2 days)": 5,
            "L (3-5 days)": 8,
            "XL (1-2 weeks)": 13,
            "XXL (3+ weeks)": 21,
        }

        total_points = sum(
            effort_points.get(item["effort"], 3) for item in completed_items
        )

        return {
            "period_weeks": weeks,
            "completed_items": len(completed_items),
            "total_story_points": total_points,
            "average_velocity": round(total_points / weeks, 2) if weeks > 0 else 0,
            "items": completed_items,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Advanced GitHub Projects v2 GraphQL Manager"
    )
    parser.add_argument(
        "command",
        choices=["analytics", "sprint-board", "velocity", "overview", "health-check"],
        help="Command to execute",
    )
    parser.add_argument("--sprint", help="Sprint name for sprint-board command")
    parser.add_argument(
        "--weeks", type=int, default=4, help="Number of weeks for velocity report"
    )
    parser.add_argument(
        "--format", choices=["json", "pretty"], default="pretty", help="Output format"
    )

    args = parser.parse_args()

    manager = GitHubProjectManager()

    try:
        if args.command == "analytics":
            result = manager.generate_project_analytics()

        elif args.command == "sprint-board":
            if not args.sprint:
                print("--sprint parameter is required for sprint-board command")
                sys.exit(1)
            result = manager.create_sprint_board_view(args.sprint)

        elif args.command == "velocity":
            result = manager.generate_velocity_report(args.weeks)

        elif args.command == "overview":
            raw_data = manager.get_project_overview()
            result = (
                raw_data["data"]["organization"]["projectV2"]
                if raw_data and "data" in raw_data
                else {}
            )

        elif args.command == "health-check":
            analytics = manager.generate_project_analytics()
            result = analytics.get("health_metrics", {})

        # Output results
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            # Pretty print based on command
            if args.command == "analytics":
                print_analytics(result)
            elif args.command == "sprint-board":
                print_sprint_board(result)
            elif args.command == "velocity":
                print_velocity_report(result)
            elif args.command == "health-check":
                print_health_check(result)
            else:
                print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error executing command: {e}")
        sys.exit(1)


def print_analytics(analytics: Dict):
    """Pretty print analytics data"""
    print("📊 PROJECT ANALYTICS")
    print("=" * 50)

    overview = analytics.get("overview", {})
    print(f"📋 Project: {overview.get('title', 'Unknown')}")
    print(f"🔗 URL: {overview.get('url', 'N/A')}")
    print(f"📈 Total Items: {overview.get('total_items', 0)}")
    print(f"🌍 Public: {'Yes' if overview.get('public') else 'No'}")

    print("\n📊 FIELD DISTRIBUTIONS")
    print("-" * 30)

    distributions = analytics.get("distribution", {})
    for field_name, values in distributions.items():
        print(f"\n{field_name}:")
        for value, count in values.items():
            print(f"  • {value}: {count}")

    print("\n🎯 HEALTH METRICS")
    print("-" * 30)

    metrics = analytics.get("health_metrics", {})
    for metric, value in metrics.items():
        print(f"• {metric.replace('_', ' ').title()}: {value}%")


def print_sprint_board(board_data: Dict):
    """Pretty print sprint board"""
    print(f"🏃 SPRINT BOARD: {board_data.get('sprint', 'Unknown')}")
    print("=" * 50)

    summary = board_data.get("summary", {})
    print(f"📊 Summary: {summary.get('total', 0)} total items")
    print(f"   • Todo: {summary.get('todo', 0)}")
    print(f"   • In Progress: {summary.get('in_progress', 0)}")
    print(f"   • Done: {summary.get('done', 0)}")

    board = board_data.get("board", {})

    for status, items in board.items():
        print(f"\n📋 {status.upper()} ({len(items)} items)")
        print("-" * 30)

        for item in items:
            assignees = (
                ", ".join(item["assignees"]) if item["assignees"] else "Unassigned"
            )
            priority_emoji = {
                "Critical": "🔴",
                "High": "🟠",
                "Medium": "🟡",
                "Low": "🟢",
            }.get(item["priority"], "⚪")

            print(f"{priority_emoji} #{item['number']} - {item['title']}")
            print(f"   Component: {item['component']} | Assignees: {assignees}")


def print_velocity_report(velocity: Dict):
    """Pretty print velocity report"""
    print(f"🚀 VELOCITY REPORT ({velocity.get('period_weeks', 0)} weeks)")
    print("=" * 50)

    print(f"✅ Completed Items: {velocity.get('completed_items', 0)}")
    print(f"📈 Total Story Points: {velocity.get('total_story_points', 0)}")
    print(f"⚡ Average Velocity: {velocity.get('average_velocity', 0)} points/week")

    print("\n📋 COMPLETED ITEMS")
    print("-" * 30)

    for item in velocity.get("items", []):
        effort_emoji = {
            "XS (1 hour)": "🟢",
            "S (2-4 hours)": "🟡",
            "M (1-2 days)": "🟠",
        }.get(item["effort"], "🔴")
        print(f"{effort_emoji} {item['title']} - {item['effort']}")


def print_health_check(health: Dict):
    """Pretty print health check"""
    print("🏥 PROJECT HEALTH CHECK")
    print("=" * 30)

    for metric, value in health.items():
        status_emoji = "🟢" if value >= 70 else "🟡" if value >= 40 else "🔴"
        print(f"{status_emoji} {metric.replace('_', ' ').title()}: {value}%")


if __name__ == "__main__":
    main()
