#!/usr/bin/env python3
"""
Comprehensive test suite for MCP-OpenMemory endpoints at localhost:8765
Tests all available endpoints systematically and generates a detailed report.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys

class MCPEndpointTester:
    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url
        self.test_results = []
        self.session = requests.Session()
        self.test_user_id = "test_user_drj"
        self.test_memory_id = None
        self.test_app_id = None

    def log_test(self, method: str, endpoint: str, status: str,
                 response_code: Optional[int] = None,
                 response_data: Optional[Dict] = None,
                 error: Optional[str] = None):
        """Log test result"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "endpoint": endpoint,
            "status": status,
            "response_code": response_code,
            "response_data": response_data,
            "error": error
        }
        self.test_results.append(result)
        print(f"[{status}] {method} {endpoint} - {response_code}")
        if error:
            print(f"   Error: {error}")

    def make_request(self, method: str, endpoint: str,
                    data: Optional[Dict] = None,
                    params: Optional[Dict] = None) -> Dict:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, params=params)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, params=params)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response_data = None
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            if response.status_code < 400:
                self.log_test(method, endpoint, "PASS", response.status_code, response_data)
            else:
                self.log_test(method, endpoint, "FAIL", response.status_code, response_data)

            return {
                "status_code": response.status_code,
                "data": response_data,
                "success": response.status_code < 400
            }

        except Exception as e:
            self.log_test(method, endpoint, "ERROR", None, None, str(e))
            return {"status_code": None, "data": None, "success": False, "error": str(e)}

    def test_health_endpoints(self):
        """Test health check endpoints"""
        print("\n=== Testing Health Endpoints ===")

        # Basic health check
        self.make_request("GET", "/health")

        # MCP health check
        self.make_request("GET", "/mcp/health")

    def test_mcp_core_endpoints(self):
        """Test core MCP endpoints"""
        print("\n=== Testing MCP Core Endpoints ===")

        # Get MCP tools
        self.make_request("GET", "/mcp/tools")

        # Test memory creation
        memory_data = {
            "messages": [
                {"role": "user", "content": "This is a test memory for MCP endpoint testing"},
                {"role": "assistant", "content": "I understand this is a test memory."}
            ],
            "user_id": self.test_user_id,
            "metadata": {"test": True, "endpoint_test": "mcp_memories"}
        }
        create_result = self.make_request("POST", "/mcp/memories", data=memory_data)

        # Store memory ID for later tests
        if create_result["success"] and create_result["data"]:
            memories = create_result["data"].get("memories", [])
            if memories:
                self.test_memory_id = memories[0].get("id")

        # Get memories
        self.make_request("GET", "/mcp/memories", params={"user_id": self.test_user_id})

        # Test memory search
        search_data = {
            "query": "test memory",
            "user_id": self.test_user_id
        }
        self.make_request("POST", "/mcp/search", data=search_data)

        # Test messages endpoint
        messages_data = {
            "messages": [
                {"role": "user", "content": "Test message for MCP messages endpoint"}
            ],
            "user_id": self.test_user_id
        }
        self.make_request("POST", "/mcp/messages/", data=messages_data)

    def test_mcp_sse_endpoints(self):
        """Test MCP SSE endpoints"""
        print("\n=== Testing MCP SSE Endpoints ===")

        # Note: SSE endpoints are typically for streaming, so we'll test basic connectivity
        try:
            # Test basic SSE endpoint
            response = self.session.get(f"{self.base_url}/mcp/sse", stream=True, timeout=5)
            if response.status_code == 200:
                self.log_test("GET", "/mcp/sse", "PASS", response.status_code)
            else:
                self.log_test("GET", "/mcp/sse", "FAIL", response.status_code)
            response.close()
        except Exception as e:
            self.log_test("GET", "/mcp/sse", "ERROR", None, None, str(e))

        # Test client-specific SSE endpoint
        try:
            client_sse_endpoint = f"/mcp/test_client/sse/{self.test_user_id}"
            response = self.session.get(f"{self.base_url}{client_sse_endpoint}", stream=True, timeout=5)
            if response.status_code == 200:
                self.log_test("GET", client_sse_endpoint, "PASS", response.status_code)
            else:
                self.log_test("GET", client_sse_endpoint, "FAIL", response.status_code)
            response.close()
        except Exception as e:
            self.log_test("GET", client_sse_endpoint, "ERROR", None, None, str(e))

    def test_api_v1_memories(self):
        """Test API v1 memory endpoints"""
        print("\n=== Testing API v1 Memory Endpoints ===")

        # Create a memory via API v1
        memory_data = {
            "messages": [
                {"role": "user", "content": "This is a test memory for API v1 testing"},
                {"role": "assistant", "content": "I understand this is an API v1 test memory."}
            ],
            "user_id": self.test_user_id,
            "metadata": {"test": True, "endpoint_test": "api_v1_memories"}
        }
        create_result = self.make_request("POST", "/api/v1/memories/", data=memory_data)

        # Store memory ID if successful
        if create_result["success"] and create_result["data"]:
            memories = create_result["data"].get("memories", [])
            if memories and not self.test_memory_id:
                self.test_memory_id = memories[0].get("id")

        # Get all memories
        self.make_request("GET", "/api/v1/memories/", params={"user_id": self.test_user_id})

        # Get memory categories
        self.make_request("GET", "/api/v1/memories/categories")

        # Search memories
        search_data = {
            "query": "test memory",
            "user_id": self.test_user_id
        }
        self.make_request("POST", "/api/v1/memories/search", data=search_data)

        # Filter memories
        filter_data = {
            "user_id": self.test_user_id,
            "filters": {"test": True}
        }
        self.make_request("POST", "/api/v1/memories/filter", data=filter_data)

        # Test individual memory operations if we have a memory ID
        if self.test_memory_id:
            # Get specific memory
            self.make_request("GET", f"/api/v1/memories/{self.test_memory_id}")

            # Update memory
            update_data = {
                "text": "Updated test memory content"
            }
            self.make_request("PUT", f"/api/v1/memories/{self.test_memory_id}", data=update_data)

            # Get memory access log
            self.make_request("GET", f"/api/v1/memories/{self.test_memory_id}/access-log")

            # Get related memories
            self.make_request("GET", f"/api/v1/memories/{self.test_memory_id}/related")

        # Test memory actions
        if self.test_memory_id:
            # Archive memory
            archive_data = {"memory_ids": [self.test_memory_id]}
            self.make_request("POST", "/api/v1/memories/actions/archive", data=archive_data)

            # Pause memory
            pause_data = {"memory_ids": [self.test_memory_id]}
            self.make_request("POST", "/api/v1/memories/actions/pause", data=pause_data)

    def test_api_v1_apps(self):
        """Test API v1 app endpoints"""
        print("\n=== Testing API v1 App Endpoints ===")

        # Get all apps
        apps_result = self.make_request("GET", "/api/v1/apps/")

        # Try to get an app ID from the response
        if apps_result["success"] and apps_result["data"]:
            apps = apps_result["data"].get("apps", [])
            if apps:
                self.test_app_id = apps[0].get("id")

        # If we have an app ID, test app-specific endpoints
        if self.test_app_id:
            # Get specific app
            self.make_request("GET", f"/api/v1/apps/{self.test_app_id}")

            # Update app
            update_data = {
                "name": "Updated Test App",
                "description": "Updated description for testing"
            }
            self.make_request("PUT", f"/api/v1/apps/{self.test_app_id}", data=update_data)

            # Get app memories
            self.make_request("GET", f"/api/v1/apps/{self.test_app_id}/memories")

            # Get app access log
            self.make_request("GET", f"/api/v1/apps/{self.test_app_id}/accessed")
        else:
            print("   No apps found to test app-specific endpoints")

    def test_api_v1_config(self):
        """Test API v1 config endpoints"""
        print("\n=== Testing API v1 Config Endpoints ===")

        # Get general config
        config_result = self.make_request("GET", "/api/v1/config/")

        # Get mem0 LLM config
        self.make_request("GET", "/api/v1/config/mem0/llm")

        # Get mem0 embedder config
        self.make_request("GET", "/api/v1/config/mem0/embedder")

        # Get openmemory config
        self.make_request("GET", "/api/v1/config/openmemory")

        # Test config updates (be careful with actual changes)
        # We'll only test if we can make the request, not necessarily apply changes
        test_config = {"test_mode": True}

        # Test general config update
        self.make_request("PUT", "/api/v1/config/", data=test_config)

        # Test mem0 LLM config update
        self.make_request("PUT", "/api/v1/config/mem0/llm", data=test_config)

        # Test mem0 embedder config update
        self.make_request("PUT", "/api/v1/config/mem0/embedder", data=test_config)

        # Test openmemory config update
        self.make_request("PUT", "/api/v1/config/openmemory", data=test_config)

        # Test config reset
        self.make_request("POST", "/api/v1/config/reset")

    def test_api_v1_stats(self):
        """Test API v1 stats endpoint"""
        print("\n=== Testing API v1 Stats Endpoint ===")

        # Get stats
        self.make_request("GET", "/api/v1/stats/")

    def cleanup_test_data(self):
        """Clean up test data created during testing"""
        print("\n=== Cleaning Up Test Data ===")

        # Delete test memory if created
        if self.test_memory_id:
            self.make_request("DELETE", f"/api/v1/memories/{self.test_memory_id}")

        # Delete memories via MCP endpoint with user_id filter
        delete_data = {"user_id": self.test_user_id}
        self.make_request("DELETE", "/mcp/memories", data=delete_data)

    def generate_report(self):
        """Generate a comprehensive test report"""
        print("\n" + "="*80)
        print("MCP-OPENMEMORY ENDPOINT TEST REPORT")
        print("="*80)

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        error_tests = len([r for r in self.test_results if r["status"] == "ERROR"])

        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Errors: {error_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        print("\nDETAILED RESULTS:")
        print("-" * 80)

        for result in self.test_results:
            status_symbol = "✓" if result["status"] == "PASS" else "✗" if result["status"] == "FAIL" else "!"
            print(f"{status_symbol} {result['method']} {result['endpoint']} [{result['response_code']}]")
            if result["error"]:
                print(f"   Error: {result['error']}")

        # Save detailed report to file
        report_file = f"mcp_endpoint_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "errors": error_tests,
                    "success_rate": (passed_tests/total_tests)*100
                },
                "detailed_results": self.test_results
            }, f, indent=2)

        print(f"\nDetailed report saved to: {report_file}")

        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": error_tests,
            "success_rate": (passed_tests/total_tests)*100
        }

    def run_all_tests(self):
        """Run all endpoint tests"""
        print("Starting MCP-OpenMemory Endpoint Testing...")
        print(f"Base URL: {self.base_url}")
        print(f"Test User ID: {self.test_user_id}")
        print("-" * 80)

        try:
            # Test all endpoint categories
            self.test_health_endpoints()
            self.test_mcp_core_endpoints()
            self.test_mcp_sse_endpoints()
            self.test_api_v1_memories()
            self.test_api_v1_apps()
            self.test_api_v1_config()
            self.test_api_v1_stats()

            # Clean up test data
            self.cleanup_test_data()

            # Generate final report
            summary = self.generate_report()

            # Exit with appropriate code
            if summary["errors"] > 0 or summary["failed"] > 0:
                print(f"\n⚠️  Tests completed with {summary['failed']} failures and {summary['errors']} errors")
                return False
            else:
                print(f"\n✅ All {summary['total']} tests passed successfully!")
                return True

        except KeyboardInterrupt:
            print("\n\n⚠️  Testing interrupted by user")
            self.cleanup_test_data()
            return False
        except Exception as e:
            print(f"\n\n❌ Testing failed with error: {e}")
            self.cleanup_test_data()
            return False

def main():
    """Main function"""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"

    tester = MCPEndpointTester(base_url)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
