#!/usr/bin/env python3
"""
Test client for the secure MCP server
"""

import asyncio
import json
import os
import sys

import aiohttp


async def test_mcp_server(base_url, api_key):
    """Test the secure MCP server endpoints"""

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        # 1. Test health endpoint (no auth required)
        print("🔍 Testing health endpoint...")
        async with session.get(f"{base_url}/health") as response:
            if response.status == 200:
                health_data = await response.json()
                print(f"✅ Health check: {health_data['status']}")
            else:
                print(f"❌ Health check failed: {response.status}")
                return False

        # 2. Test authenticated endpoints
        print("\n🔐 Testing authenticated endpoints...")

        # Test add_memories
        print("Testing add_memories...")
        add_payload = {
            "name": "add_memories",
            "arguments": {
                "text": "Test memory from secure MCP client - external API access working"
            },
        }

        async with session.post(
            f"{base_url}/tools/call", json=add_payload, headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ add_memories: {result['success']}")
                print(f"   Added {len(result['result']['results'])} memories")
            else:
                print(f"❌ add_memories failed: {response.status}")
                return False

        # Test search_memory
        print("Testing search_memory...")
        search_payload = {
            "name": "search_memory",
            "arguments": {"query": "secure MCP client external API"},
        }

        async with session.post(
            f"{base_url}/tools/call", json=search_payload, headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ search_memory: {result['success']}")
                print(f"   Found {len(result['result']['results'])} memories")
            else:
                print(f"❌ search_memory failed: {response.status}")
                return False

        # Test list_memories
        print("Testing list_memories...")
        list_payload = {"name": "list_memories", "arguments": {}}

        async with session.post(
            f"{base_url}/tools/call", json=list_payload, headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ list_memories: {result['success']}")
                print(f"   Total memories: {len(result['result']['results'])}")
            else:
                print(f"❌ list_memories failed: {response.status}")
                return False

        # Test SSE endpoint (just connection, not full stream)
        print("Testing SSE endpoint...")
        async with session.get(
            f"{base_url}/sse",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "text/event-stream",
            },
        ) as response:
            if response.status == 200:
                print("✅ SSE endpoint: Connected successfully")
                # Read first few events
                async for line in response.content:
                    if line.startswith(b"data: "):
                        event_data = json.loads(line[6:].decode())
                        print(f"   Event: {event_data.get('type', 'unknown')}")
                        if event_data.get("type") == "tools":
                            print(
                                f"   Available tools: {len(event_data.get('tools', []))}"
                            )
                            break
            else:
                print(f"❌ SSE endpoint failed: {response.status}")
                return False

        print("\n🎉 All tests passed! MCP server is working correctly.")
        return True


async def test_without_auth(base_url):
    """Test that protected endpoints require authentication"""
    print("\n🔒 Testing authentication requirement...")

    async with aiohttp.ClientSession() as session:
        # Try to access protected endpoint without auth
        test_payload = {"name": "list_memories", "arguments": {}}

        async with session.post(
            f"{base_url}/tools/call", json=test_payload
        ) as response:
            if response.status == 401:
                print(
                    "✅ Authentication required: Properly rejected unauthorized request"
                )
                return True
            else:
                print(f"❌ Authentication bypass: Expected 401, got {response.status}")
                return False


if __name__ == "__main__":
    # Configuration
    BASE_URL = "http://localhost:8081"

    # Try to read API key from environment or .env.mcp file
    api_key = os.getenv("API_KEY")
    if not api_key:
        try:
            with open(".env.mcp", "r") as f:
                for line in f:
                    if line.startswith("API_KEYS="):
                        api_key = line.split("=", 1)[1].strip()
                        break
        except FileNotFoundError:
            pass

    if not api_key:
        print(
            "❌ API key not found. Please provide it as API_KEY environment variable or in .env.mcp file"
        )
        sys.exit(1)

    print(f"🚀 Testing MCP server at {BASE_URL}")
    print(f"Using API key: {api_key[:8]}...")

    # Run tests
    async def run_tests():
        # Test with authentication
        success = await test_mcp_server(BASE_URL, api_key)
        if not success:
            return False

        # Test authentication requirement
        success = await test_without_auth(BASE_URL)
        return success

    # Run the tests
    success = asyncio.run(run_tests())

    if success:
        print("\n✅ All tests completed successfully!")
        print("Your secure MCP server is ready for external access!")
    else:
        print("\n❌ Some tests failed. Please check the server logs.")
        sys.exit(1)
