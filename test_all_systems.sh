#!/bin/bash
echo "=== Testing All Systems ==="

echo -e "\n1. Health checks:"
echo -n "mem0 API: "
curl -s http://localhost:8000/health | jq -r .status || echo "FAILED"
echo -n "OpenMemory UI: "
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q 200 && echo "UP" || echo "DOWN"

echo -e "\n2. Testing mem0 API:"
curl -s "http://localhost:8000/memories?user_id=drj" | jq -c '{total: .results | length, first_memory: .results[0].memory}' 2>/dev/null || echo "No memories found"

echo -e "\n3. Testing OpenMemory API:"
echo -n "Apps: "
curl -s "http://localhost:8765/api/v1/apps/" | jq -r '.apps[0].total_memories_created' 2>/dev/null || echo "0"
echo -n "Memories via filter: "
curl -s -X POST "http://localhost:8765/api/v1/memories/filter" -H "Content-Type: application/json" -d '{"user_id": "drj"}' | jq -r '.total' 2>/dev/null || echo "0"

echo -e "\n4. Database status:"
docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" postgres-mem0 psql -U drj -d mem0 -t -c "SELECT 'mem0_memories:', COUNT(*) FROM mem0_memories UNION ALL SELECT 'memories:', COUNT(*) FROM memories;"

echo -e "\n5. Running db monitor:"
./scripts/db_monitor.sh health | grep "Application health"
