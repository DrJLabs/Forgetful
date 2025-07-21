#!/bin/bash
set -e

echo "🐳 Starting background services with DinD support..."

# Start Docker daemon if not running (for self-hosted runners)
sudo systemctl start docker || true

# Create extended docker-compose for background testing
cat > docker-compose.background.yml << 'EOF'
version: '3.8'
services:
  postgres-background:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: background_test_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: testpass
      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"
    ports:
      - "5433:5432"
    volumes:
      - postgres_background_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d background_test_db"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  neo4j-background:
    image: neo4j:5.15
    environment:
      NEO4J_AUTH: neo4j/testpass
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_memory_heap_max__size: 2G
      NEO4J_dbms_memory_pagecache_size: 1G
    ports:
      - "7688:7687"
      - "7475:7474"
    volumes:
      - neo4j_background_data:/data
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p testpass 'RETURN 1'"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

  redis-background:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  postgres_background_data:
  neo4j_background_data:
EOF

# Start background services
docker-compose -f docker-compose.background.yml up -d

# Wait for services to be healthy
echo "Waiting for background services to be healthy..."
timeout 300 bash -c '
  until docker-compose -f docker-compose.background.yml ps | grep -q "healthy"; do
    echo "Waiting for services to become healthy..."
    sleep 10
  done
'

docker-compose -f docker-compose.background.yml ps
