#!/bin/bash
# Wrapper script to run the MCP server inside the Docker container

# Pass all environment variables and run the Python script inside the container
docker exec -i \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e POSTGRES_HOST="postgres-mem0" \
  -e POSTGRES_PORT="5432" \
  -e POSTGRES_DB="mem0" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e NEO4J_URL="neo4j://neo4j-mem0:7687" \
  -e NEO4J_AUTH="$NEO4J_AUTH" \
  -e USER_ID="$USER_ID" \
  -e CLIENT_NAME="$CLIENT_NAME" \
  openmemory-mcp \
  python /usr/src/openmemory/mcp_standalone.py
