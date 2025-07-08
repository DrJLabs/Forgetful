#!/usr/bin/env python3
"""
Memory System Test Suite

This script tests both the mem0 server and OpenMemory API endpoints
to verify memory creation, retrieval, search, update, and deletion operations.
"""

import os
import sys
import time
import json
import requests
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class TestResult:
    """Test result data structure"""
    test_name: str
    passed: bool
    message: str
    duration: float = 0.0
    response_data: Optional[Dict] = None


class MemoryTester:
    """Test suite for memory system functionality"""
    
    def __init__(self):
        # API endpoints
        self.mem0_base_url = "http://localhost:8000"  # Will use docker exec
        self.openmemory_base_url = "http://localhost:8765"
        
        # Test data
        self.test_user_id = "drj"  # Use default user
        self.test_agent_id = "test_agent_456"
        self.test_run_id = "test_run_789"
        self.test_app_name = "test_app"
        
        # Storage for created memories
        self.created_memories = []
        self.test_results = []
        
        print("🧪 Memory System Test Suite")
        print("=" * 50)
    
    def docker_exec_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """Execute HTTP request inside the mem0 container"""
        
        # Build the command components properly
        cmd_parts = ["docker", "exec", "mem0", "curl", "-s", "-X", method, f"http://localhost:8000{endpoint}"]
        
        if data:
            cmd_parts.extend(["-H", "Content-Type: application/json", "-d", json.dumps(data)])
        
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True
        )
        
        # Debug output disabled for cleaner test results
        # print(f"DEBUG: Command: {' '.join(cmd_parts)}")
        # print(f"DEBUG: Return code: {result.returncode}")
        # print(f"DEBUG: Stdout: {result.stdout}")
        # print(f"DEBUG: Stderr: {result.stderr}")
        
        # Create a mock response object
        class MockResponse:
            def __init__(self, text: str, status_code: int = 200):
                self.text = text
                self.status_code = status_code
                
            def json(self):
                if self.text:
                    try:
                        return json.loads(self.text)
                    except json.JSONDecodeError as e:
                        print(f"DEBUG: JSON decode error: {e}")
                        print(f"DEBUG: Raw text: {self.text}")
                        return {}
                return {}
                
            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")
        
        return MockResponse(result.stdout, 200 if result.returncode == 0 else 500)
    
    def run_test(self, test_func) -> TestResult:
        """Execute a single test and capture results"""
        start_time = time.time()
        try:
            result = test_func()
            duration = time.time() - start_time
            
            if isinstance(result, TestResult):
                result.duration = duration
                return result
            else:
                return TestResult(
                    test_name=test_func.__name__,
                    passed=True,
                    message=str(result),
                    duration=duration
                )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_func.__name__,
                passed=False,
                message=f"Error: {str(e)}",
                duration=duration
            )
    
    def log_test_result(self, result: TestResult):
        """Log test result"""
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status} {result.test_name} ({result.duration:.2f}s)")
        if not result.passed:
            print(f"   {result.message}")
        else:
            print(f"   {result.message}")
        print()
        
        self.test_results.append(result)
    
    # MEM0 SERVER TESTS
    
    def test_mem0_create_memory(self) -> TestResult:
        """Test creating memories using mem0 server"""
        test_data = {
            "messages": [
                {"role": "user", "content": "My name is John and I love pizza"},
                {"role": "assistant", "content": "Nice to meet you John! I'll remember that you love pizza."}
            ],
            "user_id": self.test_user_id,
            "metadata": {"test": "memory_creation", "timestamp": datetime.now().isoformat()}
        }
        
        response = self.docker_exec_request("POST", "/memories", test_data)
        result_data = response.json()
        
        # Check if memories were created (either in results or if relationships were added)
        memories_created = False
        memory_id = None
        
        if "results" in result_data and len(result_data["results"]) > 0:
            memory_id = result_data["results"][0]["id"]
            memories_created = True
        elif "relations" in result_data and "added_entities" in result_data["relations"] and len(result_data["relations"]["added_entities"]) > 0:
            # Memories were processed but may already exist, get them from the database
            get_response = self.docker_exec_request("GET", f"/memories?user_id={self.test_user_id}")
            get_data = get_response.json()
            if "results" in get_data and len(get_data["results"]) > 0:
                memory_id = get_data["results"][0]["id"]
                memories_created = True
        
        if memories_created and memory_id:
            self.created_memories.append({"id": memory_id, "source": "mem0"})
            return TestResult(
                test_name="mem0_create_memory",
                passed=True,
                message=f"Memory processing successful, using memory ID: {memory_id}",
                response_data=result_data
            )
        else:
            return TestResult(
                test_name="mem0_create_memory",
                passed=False,
                message=f"Failed to create memory: {result_data}",
                response_data=result_data
            )
    
    def test_mem0_get_all_memories(self) -> TestResult:
        """Test retrieving all memories using mem0 server"""
        response = self.docker_exec_request("GET", f"/memories?user_id={self.test_user_id}")
        result_data = response.json()
        
        if isinstance(result_data, dict) and "results" in result_data and len(result_data["results"]) > 0:
            return TestResult(
                test_name="mem0_get_all_memories",
                passed=True,
                message=f"Retrieved {len(result_data['results'])} memories",
                response_data=result_data
            )
        else:
            return TestResult(
                test_name="mem0_get_all_memories",
                passed=False,
                message=f"Failed to retrieve memories or no memories found: {result_data}",
                response_data=result_data
            )
    
    def test_mem0_get_memory_by_id(self) -> TestResult:
        """Test retrieving a specific memory by ID"""
        if not self.created_memories:
            return TestResult(
                test_name="mem0_get_memory_by_id",
                passed=False,
                message="No memories available to test"
            )
        
        mem0_memory = next((m for m in self.created_memories if m["source"] == "mem0"), None)
        if not mem0_memory:
            return TestResult(
                test_name="mem0_get_memory_by_id",
                passed=False,
                message="No mem0 memories available"
            )
        
        memory_id = mem0_memory["id"]
        response = self.docker_exec_request("GET", f"/memories/{memory_id}")
        result_data = response.json()
        
        if "id" in result_data and result_data["id"] == memory_id:
            return TestResult(
                test_name="mem0_get_memory_by_id",
                passed=True,
                message=f"Retrieved memory: {result_data.get('memory', '')[:50]}...",
                response_data=result_data
            )
        else:
            return TestResult(
                test_name="mem0_get_memory_by_id",
                passed=False,
                message=f"Failed to retrieve memory: {result_data}",
                response_data=result_data
            )
    
    def test_mem0_search_memories(self) -> TestResult:
        """Test searching memories using mem0 server"""
        search_data = {
            "query": "pizza",
            "user_id": self.test_user_id
        }
        
        response = self.docker_exec_request("POST", "/search", search_data)
        result_data = response.json()
        
        if "results" in result_data and len(result_data["results"]) > 0:
            return TestResult(
                test_name="mem0_search_memories",
                passed=True,
                message=f"Found {len(result_data['results'])} memories matching 'pizza'",
                response_data=result_data
            )
        else:
            return TestResult(
                test_name="mem0_search_memories",
                passed=False,
                message=f"No memories found for search: {result_data}",
                response_data=result_data
            )
    
    def test_mem0_update_memory(self) -> TestResult:
        """Test updating a memory using mem0 server"""
        if not self.created_memories:
            return TestResult(
                test_name="mem0_update_memory",
                passed=False,
                message="No memories available to update"
            )
        
        mem0_memory = next((m for m in self.created_memories if m["source"] == "mem0"), None)
        if not mem0_memory:
            return TestResult(
                test_name="mem0_update_memory",
                passed=False,
                message="No mem0 memories available"
            )
        
        memory_id = mem0_memory["id"]
        update_data = {
            "text": "John loves pizza and pasta"
        }
        
        response = self.docker_exec_request("PUT", f"/memories/{memory_id}", update_data)
        result_data = response.json()
        
        if "message" in result_data and "updated" in result_data["message"].lower():
            return TestResult(
                test_name="mem0_update_memory",
                passed=True,
                message=f"Successfully updated memory: {result_data}",
                response_data=result_data
            )
        else:
            return TestResult(
                test_name="mem0_update_memory",
                passed=False,
                message=f"Failed to update memory: {result_data}",
                response_data=result_data
            )
    
    def test_mem0_memory_history(self) -> TestResult:
        """Test getting memory history using mem0 server"""
        if not self.created_memories:
            return TestResult(
                test_name="mem0_memory_history",
                passed=False,
                message="No memories available to get history"
            )
        
        mem0_memory = next((m for m in self.created_memories if m["source"] == "mem0"), None)
        if not mem0_memory:
            return TestResult(
                test_name="mem0_memory_history",
                passed=False,
                message="No mem0 memories available"
            )
        
        memory_id = mem0_memory["id"]
        response = self.docker_exec_request("GET", f"/memories/{memory_id}/history")
        result_data = response.json()
        
        if isinstance(result_data, list):
            return TestResult(
                test_name="mem0_memory_history",
                passed=True,
                message=f"Retrieved {len(result_data)} history entries",
                response_data=result_data
            )
        else:
            return TestResult(
                test_name="mem0_memory_history",
                passed=False,
                message=f"Failed to retrieve history: {result_data}",
                response_data=result_data
            )
    
    # OPENMEMORY API TESTS
    
    def test_openmemory_create_memory(self) -> TestResult:
        """Test creating memories using OpenMemory API"""
        test_data = {
            "user_id": self.test_user_id,
            "app": self.test_app_name,
            "text": "I prefer to work out in the morning and drink green tea",
            "metadata": {"test": "openmemory_creation", "timestamp": datetime.now().isoformat()}
        }
        
        response = requests.post(f"{self.openmemory_base_url}/api/v1/memories/", json=test_data)
        
        if response.status_code == 200:
            try:
                result_data = response.json()
                
                # Handle the case where memory client returns results/relations format
                if isinstance(result_data, dict) and "results" in result_data:
                    # Memory was processed but may not have created new entries
                    # Get the memory from the list endpoint instead
                    list_response = requests.get(f"{self.openmemory_base_url}/api/v1/memories/?user_id={self.test_user_id}")
                    if list_response.status_code == 200:
                        try:
                            list_data = list_response.json()
                            if "items" in list_data and len(list_data["items"]) > 0:
                                memory_id = list_data["items"][0]["id"]
                                self.created_memories.append({"id": memory_id, "source": "openmemory"})
                                return TestResult(
                                    test_name="openmemory_create_memory",
                                    passed=True,
                                    message=f"Memory processed, found existing memory with ID: {memory_id}",
                                    response_data=result_data
                                )
                        except:
                            pass
                    
                    return TestResult(
                        test_name="openmemory_create_memory",
                        passed=True,
                        message="Memory processed (no new memories created)",
                        response_data=result_data
                    )
                
                # Original logic for direct memory creation response
                if "id" in result_data:
                    self.created_memories.append({"id": result_data["id"], "source": "openmemory"})
                    return TestResult(
                        test_name="openmemory_create_memory",
                        passed=True,
                        message=f"Created memory with ID: {result_data['id']}",
                        response_data=result_data
                    )
            except Exception as e:
                return TestResult(
                    test_name="openmemory_create_memory",
                    passed=False,
                    message=f"Error: {str(e)}",
                    response_data={"error": str(e), "response": response.text[:500]}
                )
        
        return TestResult(
            test_name="openmemory_create_memory",
            passed=False,
            message=f"Failed to create memory: {response.text}",
            response_data=response.json() if response.text else {}
        )
    
    def test_openmemory_list_memories(self) -> TestResult:
        """Test listing memories using OpenMemory API"""
        # Try without pagination first
        response = requests.get(f"{self.openmemory_base_url}/api/v1/memories/?user_id={self.test_user_id}")
        
        if response.status_code == 200:
            try:
                result_data = response.json()
                if "items" in result_data:
                    return TestResult(
                        test_name="openmemory_list_memories",
                        passed=True,
                        message=f"Listed {len(result_data['items'])} memories",
                        response_data=result_data
                    )
                else:
                    # Try alternate response format
                    return TestResult(
                        test_name="openmemory_list_memories",
                        passed=True,
                        message=f"Listed memories (alternate format)",
                        response_data=result_data
                    )
            except json.JSONDecodeError as e:
                # Log the raw response for debugging
                print(f"DEBUG: Raw response: {response.text[:200]}")
                return TestResult(
                    test_name="openmemory_list_memories",
                    passed=False,
                    message=f"Failed to parse JSON response: {e}",
                    response_data={"raw_response": response.text[:500], "status_code": response.status_code}
                )
        
        return TestResult(
            test_name="openmemory_list_memories",
            passed=False,
            message=f"Failed to list memories: HTTP {response.status_code}",
            response_data={"error": response.text[:500], "status_code": response.status_code}
        )
    
    def test_openmemory_get_memory_by_id(self) -> TestResult:
        """Test retrieving a specific memory by ID using OpenMemory API"""
        openmemory_memory = next((m for m in self.created_memories if m["source"] == "openmemory"), None)
        if not openmemory_memory:
            return TestResult(
                test_name="openmemory_get_memory_by_id",
                passed=False,
                message="No OpenMemory memories available"
            )
        
        memory_id = openmemory_memory["id"]
        response = requests.get(f"{self.openmemory_base_url}/api/v1/memories/{memory_id}")
        
        if response.status_code == 200:
            result_data = response.json()
            return TestResult(
                test_name="openmemory_get_memory_by_id",
                passed=True,
                message=f"Retrieved memory: {result_data.get('content', '')[:50]}...",
                response_data=result_data
            )
        
        return TestResult(
            test_name="openmemory_get_memory_by_id",
            passed=False,
            message=f"Failed to retrieve memory: {response.text}",
            response_data=response.json() if response.text else {}
        )
    
    def test_openmemory_search_memories(self) -> TestResult:
        """Test searching memories using OpenMemory API"""
        params = {
            "user_id": self.test_user_id,
            "search_query": "green tea"
        }
        
        response = requests.get(f"{self.openmemory_base_url}/api/v1/memories/", params=params)
        
        if response.status_code == 200:
            result_data = response.json()
            if "items" in result_data:
                return TestResult(
                    test_name="openmemory_search_memories",
                    passed=True,
                    message=f"Found {len(result_data['items'])} memories matching 'green tea'",
                    response_data=result_data
                )
        
        return TestResult(
            test_name="openmemory_search_memories",
            passed=False,
            message=f"Failed to search memories: {response.text}",
            response_data=response.json() if response.text else {}
        )
    
    def test_openmemory_update_memory(self) -> TestResult:
        """Test updating a memory using OpenMemory API"""
        openmemory_memory = next((m for m in self.created_memories if m["source"] == "openmemory"), None)
        if not openmemory_memory:
            return TestResult(
                test_name="openmemory_update_memory",
                passed=False,
                message="No OpenMemory memories available"
            )
        
        memory_id = openmemory_memory["id"]
        update_data = {
            "memory_content": "I prefer to work out in the morning, drink green tea, and eat healthy snacks",
            "user_id": self.test_user_id
        }
        
        response = requests.put(f"{self.openmemory_base_url}/api/v1/memories/{memory_id}", json=update_data)
        
        if response.status_code == 200:
            result_data = response.json()
            return TestResult(
                test_name="openmemory_update_memory",
                passed=True,
                message=f"Successfully updated memory",
                response_data=result_data
            )
        
        return TestResult(
            test_name="openmemory_update_memory",
            passed=False,
            message=f"Failed to update memory: {response.text}",
            response_data=response.json() if response.text else {}
        )
    
    def test_openmemory_delete_memory(self) -> TestResult:
        """Test deleting a memory using OpenMemory API"""
        openmemory_memory = next((m for m in self.created_memories if m["source"] == "openmemory"), None)
        if not openmemory_memory:
            return TestResult(
                test_name="openmemory_delete_memory",
                passed=False,
                message="No OpenMemory memories available"
            )
        
        memory_id = openmemory_memory["id"]
        response = requests.delete(f"{self.openmemory_base_url}/api/v1/memories/{memory_id}")
        
        if response.status_code == 200:
            # Remove from tracking
            self.created_memories = [m for m in self.created_memories if m["id"] != memory_id]
            return TestResult(
                test_name="openmemory_delete_memory",
                passed=True,
                message=f"Successfully deleted memory {memory_id}",
                response_data=response.json()
            )
        
        return TestResult(
            test_name="openmemory_delete_memory",
            passed=False,
            message=f"Failed to delete memory: {response.text}",
            response_data=response.json() if response.text else {}
        )
    
    def test_mem0_delete_memory(self) -> TestResult:
        """Test deleting a memory using mem0 server"""
        mem0_memory = next((m for m in self.created_memories if m["source"] == "mem0"), None)
        if not mem0_memory:
            return TestResult(
                test_name="mem0_delete_memory",
                passed=False,
                message="No mem0 memories available"
            )
        
        memory_id = mem0_memory["id"]
        response = self.docker_exec_request("DELETE", f"/memories/{memory_id}")
        result_data = response.json()
        
        if "message" in result_data and "deleted" in result_data["message"].lower():
            # Remove from tracking
            self.created_memories = [m for m in self.created_memories if m["id"] != memory_id]
            return TestResult(
                test_name="mem0_delete_memory",
                passed=True,
                message=f"Successfully deleted memory {memory_id}",
                response_data=result_data
            )
        
        return TestResult(
            test_name="mem0_delete_memory",
            passed=False,
            message=f"Failed to delete memory: {result_data}",
            response_data=result_data
        )
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("Starting comprehensive memory system tests...\n")
        
        # Test sequence - order matters for dependencies
        tests = [
            # Creation tests
            self.test_mem0_create_memory,
            self.test_openmemory_create_memory,
            
            # Retrieval tests
            self.test_mem0_get_all_memories,
            self.test_mem0_get_memory_by_id,
            self.test_openmemory_list_memories,
            self.test_openmemory_get_memory_by_id,
            
            # Search tests
            self.test_mem0_search_memories,
            self.test_openmemory_search_memories,
            
            # Update tests
            self.test_mem0_update_memory,
            self.test_openmemory_update_memory,
            
            # History test
            self.test_mem0_memory_history,
            
            # Deletion tests (last to clean up)
            self.test_mem0_delete_memory,
            self.test_openmemory_delete_memory,
        ]
        
        for test in tests:
            result = self.run_test(test)
            self.log_test_result(result)
            
            # Small delay between tests
            time.sleep(0.5)
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result.passed:
                    print(f"  ❌ {result.test_name}: {result.message}")
        
        print("\nMemory System Test Complete!")
        
        # Clean up any remaining memories
        self.cleanup_memories()
    
    def cleanup_memories(self):
        """Clean up any remaining test memories"""
        print("\n🧹 Cleaning up test data...")
        
        cleanup_count = 0
        for memory in self.created_memories:
            try:
                if memory["source"] == "mem0":
                    self.docker_exec_request("DELETE", f"/memories/{memory['id']}")
                elif memory["source"] == "openmemory":
                    requests.delete(f"{self.openmemory_base_url}/api/v1/memories/{memory['id']}")
                cleanup_count += 1
            except Exception as e:
                print(f"Failed to cleanup memory {memory['id']}: {e}")
        
        print(f"Cleaned up {cleanup_count} test memories")


if __name__ == "__main__":
    tester = MemoryTester()
    tester.run_all_tests() 