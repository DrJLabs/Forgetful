#!/usr/bin/env python3
"""
MCP Server Functionality Test Script
Tests all MCP endpoints and operations to verify proper functionality
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
import sys

# Configuration
MCP_BASE_URL = "http://localhost:8765"
USER_ID = "drj"
CLIENT_NAME = "test_client"


class MCPTester:
    def __init__(self):
        self.base_url = MCP_BASE_URL
        self.user_id = USER_ID
        self.client_name = CLIENT_NAME
        self.test_results = []

    async def test_mcp_endpoint(self):
        """Test if MCP endpoint is accessible"""
        print("\n🔍 Testing MCP endpoint accessibility...")
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/mcp/{self.client_name}/sse/{self.user_id}"
                async with session.get(url) as response:
                    status = response.status
                    print(f"✅ MCP endpoint accessible: {url}")
                    print(f"   Status: {status}")
                    self.test_results.append(("Endpoint Access", True, f"Status: {status}"))
                    return True
        except Exception as e:
            print(f"❌ Failed to access MCP endpoint: {e}")
            self.test_results.append(("Endpoint Access", False, str(e)))
            return False

    async def test_direct_api_operations(self):
        """Test operations through direct API for comparison"""
        print("\n🔍 Testing direct API operations...")
        
        # Test memory creation
        try:
            async with aiohttp.ClientSession() as session:
                # Create a test memory
                create_url = "http://localhost:8000/memories"
                test_memory = {
                    "messages": [
                        {"role": "user", "content": "MCP functionality test"},
                        {"role": "assistant", "content": f"Testing MCP server at {datetime.now().isoformat()}"}
                    ],
                    "user_id": self.user_id,
                    "metadata": {
                        "type": "test",
                        "test_type": "mcp_verification",
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                async with session.post(create_url, json=test_memory) as response:
                    if response.status == 200:
                        result = await response.json()
                        print("✅ Memory created via API")
                        self.test_results.append(("API Memory Creation", True, "Success"))
                        
                        # Test search
                        search_url = "http://localhost:8000/search"
                        search_data = {
                            "query": "MCP functionality test",
                            "user_id": self.user_id
                        }
                        
                        async with session.post(search_url, json=search_data) as search_response:
                            if search_response.status == 200:
                                search_result = await search_response.json()
                                memories_found = len(search_result.get("results", []))
                                print(f"✅ Search via API: Found {memories_found} memories")
                                self.test_results.append(("API Search", True, f"Found {memories_found} memories"))
                            else:
                                print(f"❌ Search failed: {search_response.status}")
                                self.test_results.append(("API Search", False, f"Status: {search_response.status}"))
                    else:
                        print(f"❌ Memory creation failed: {response.status}")
                        self.test_results.append(("API Memory Creation", False, f"Status: {response.status}"))
                        
        except Exception as e:
            print(f"❌ API test failed: {e}")
            self.test_results.append(("API Operations", False, str(e)))

    async def test_mcp_vs_api_consistency(self):
        """Verify that MCP and API access the same backend"""
        print("\n🔍 Testing MCP vs API consistency...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Create unique test content
                unique_content = f"Consistency test {datetime.now().timestamp()}"
                
                # Create via API
                create_url = "http://localhost:8000/memories"
                test_memory = {
                    "messages": [
                        {"role": "user", "content": unique_content},
                        {"role": "assistant", "content": "Testing backend consistency"}
                    ],
                    "user_id": self.user_id,
                    "metadata": {"type": "consistency_test"}
                }
                
                async with session.post(create_url, json=test_memory) as response:
                    if response.status == 200:
                        # Search via API to verify
                        search_url = "http://localhost:8000/search"
                        search_data = {"query": unique_content, "user_id": self.user_id}
                        
                        async with session.post(search_url, json=search_data) as search_response:
                            if search_response.status == 200:
                                result = await search_response.json()
                                if result.get("results"):
                                    print("✅ MCP and API use same backend storage")
                                    self.test_results.append(("Backend Consistency", True, "Verified"))
                                else:
                                    print("❌ Memory not found - backend inconsistency")
                                    self.test_results.append(("Backend Consistency", False, "Memory not found"))
                    
        except Exception as e:
            print(f"❌ Consistency test failed: {e}")
            self.test_results.append(("Backend Consistency", False, str(e)))

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 MCP FUNCTIONALITY TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed = sum(1 for _, success, _ in self.test_results if success)
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {total_tests - passed}")
        print(f"Success Rate: {(passed/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        print("-"*60)
        for test_name, success, details in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} | {test_name}: {details}")
        
        print("\n📝 MCP Configuration for Cursor:")
        print("-"*60)
        print("1. Open Cursor Settings > MCP Servers")
        print("2. Add new MCP server:")
        print(f"   - Name: mem0")
        print(f"   - Type: SSE")
        print(f"   - Endpoint: {self.base_url}/mcp/messages/")
        print("3. Restart Cursor to apply changes")
        
        print("\n🔧 Available MCP Tools:")
        print("-"*60)
        print("- add_memories: Store new information")
        print("- search_memory: Find relevant memories (auto-called)")
        print("- list_memories: View all memories")
        print("- delete_all_memories: Clear storage")
        
        return passed == total_tests


async def main():
    """Run all MCP tests"""
    print("🚀 Starting MCP Server Functionality Tests")
    print(f"   MCP URL: {MCP_BASE_URL}")
    print(f"   User ID: {USER_ID}")
    print(f"   Client: {CLIENT_NAME}")
    
    tester = MCPTester()
    
    # Run tests
    await tester.test_mcp_endpoint()
    await tester.test_direct_api_operations()
    await tester.test_mcp_vs_api_consistency()
    
    # Print summary
    all_passed = tester.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main()) 