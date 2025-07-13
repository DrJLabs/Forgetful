#!/bin/bash

# Run Alembic migrations for OpenMemory API

echo "Running OpenMemory database migrations..."

# First, backup the current database
echo "Creating backup of current database..."
docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" postgres-mem0 pg_dump -U drj -d mem0 > backup_before_migration_$(date +%Y%m%d_%H%M%S).sql

# Run migrations inside the openmemory-mcp container
echo "Running Alembic migrations..."
docker exec openmemory-mcp bash -c "cd /app && alembic upgrade head"

echo "Migration complete!"

# Check if migration was successful
echo "Checking migration status..."
docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" postgres-mem0 psql -U drj -d mem0 -c "SELECT version_num FROM alembic_version;"

# List tables to verify schema
echo "Current database tables:"
docker exec -e PGPASSWORD="${DATABASE_PASSWORD:-testpass}" postgres-mem0 psql -U drj -d mem0 -c "\dt"
