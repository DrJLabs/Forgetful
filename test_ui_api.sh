#!/bin/bash
echo "Testing OpenMemory UI API endpoints..."

# Test stats endpoint
echo -e "\n1. Testing stats endpoint:"
curl -s "http://localhost:8765/api/v1/stats?user_id=drj" | jq .

# Test memories filter endpoint (used by UI)
echo -e "\n2. Testing memories filter endpoint:"
curl -s -X POST "http://localhost:8765/api/v1/memories/filter" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "drj", "page": 1, "size": 50}' | jq .

# Test apps endpoint
echo -e "\n3. Testing apps endpoint:"
curl -s "http://localhost:8765/api/v1/apps/" | jq .

# Test direct memories list
echo -e "\n4. Testing direct memories list:"
curl -s "http://localhost:8765/api/v1/memories/?user_id=drj&page=1&size=50" | jq .
