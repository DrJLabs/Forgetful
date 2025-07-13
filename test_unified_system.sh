#!/bin/bash
echo "=== Testing Unified Memories System ==="

echo -e "\n1. Health checks:"
echo -n "mem0 API: "
curl -s http://localhost:8000/health | jq -r .status 2>/dev/null || echo "FAILED"

echo -e "\n2. Database status:"
docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" postgres-mem0 psql -U drj -d mem0 -t -c "SELECT 'memories table:', COUNT(*) FROM memories;"

echo -e "\n3. Testing mem0 API:"
curl -s "http://localhost:8000/memories?user_id=drj" | jq -c '{total: (.results // [] | length), first_memory: ((.results // [])[0].memory // "none")}' 2>/dev/null || echo "Error accessing mem0 API"

echo -e "\n4. Testing OpenMemory API:"
echo -n "Apps with memory count: "
curl -s "http://localhost:8765/api/v1/apps/" | jq -r '.apps[0].total_memories_created' 2>/dev/null || echo "0"

echo -n "Memories via filter: "
curl -s -X POST "http://localhost:8765/api/v1/memories/filter" -H "Content-Type: application/json" -d '{"user_id": "drj"}' | jq -r '.total' 2>/dev/null || echo "0"

echo -e "\n5. Checking remaining tables:"
docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" postgres-mem0 psql -U drj -d mem0 -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE '%memor%';" | grep -v tablename | grep -v "^-" | sort
