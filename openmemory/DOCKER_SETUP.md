# OpenMemory Docker Setup

## Overview

OpenMemory has been migrated from the `archive/openmemory/` directory to the main project structure. The services are now integrated into the main `docker-compose.yml` file in the project root.

## Services

The OpenMemory stack consists of two services:

1. **openmemory-mcp** - The MCP (Model Context Protocol) API server
   - Port: 8765
   - Provides memory storage and retrieval API
   - Connects to postgres-mem0 and neo4j-mem0

2. **openmemory-ui** - The React-based web interface
   - Port: 3000
   - Provides a developer dashboard for managing memories
   - Available at http://localhost:3000

## Migration History

- **Previous Location**: `archive/openmemory/`
- **Current Location**: `openmemory/`
- **Docker Compose**: Integrated into main `docker-compose.yml`
- **Migration Date**: January 9, 2025

## Usage

To start OpenMemory services:

```bash
# From project root
docker-compose up -d openmemory-mcp openmemory-ui

# Or start all services
docker-compose up -d
```

To stop OpenMemory services:

```bash
docker-compose stop openmemory-mcp openmemory-ui
```

## Configuration

The services use environment variables from:
- Main `.env` file in project root
- `openmemory/api/.env` for API-specific settings
- `openmemory/ui/.env` for UI-specific settings

## Dependencies

OpenMemory depends on:
- postgres-mem0 (PostgreSQL with pgvector)
- neo4j-mem0 (Neo4j graph database)

These are automatically started when you run the OpenMemory services.

## API Endpoints

- Base URL: http://localhost:8765
- Memories: http://localhost:8765/api/v1/memories/
- Search: http://localhost:8765/api/v1/search/

## Notes

- The old `docker-compose.yml` in this directory has been renamed to `docker-compose.yml.old`
- All services now use the main project's docker network (traefik)
- Container names are simplified (no more project prefix) 