-- Fix OpenMemory schema issues by creating views/tables that map to the expected schema

-- First, let's rename the existing memories table to avoid conflicts
ALTER TABLE IF EXISTS memories RENAME TO memories_mem0_backup;

-- Create a new memories table with the schema OpenMemory expects
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    app_id UUID NOT NULL,
    content TEXT NOT NULL,
    vector TEXT,
    metadata JSONB DEFAULT '{}',
    state VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_at TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_app_id ON memories(app_id);
CREATE INDEX IF NOT EXISTS idx_memories_state ON memories(state);
CREATE INDEX IF NOT EXISTS idx_memory_user_state ON memories(user_id, state);
CREATE INDEX IF NOT EXISTS idx_memory_app_state ON memories(app_id, state);
CREATE INDEX IF NOT EXISTS idx_memory_user_app ON memories(user_id, app_id);

-- Ensure we have a default app
DO $$
DECLARE
    default_user_id UUID;
    default_app_id UUID;
BEGIN
    -- Get or create default user
    SELECT id INTO default_user_id FROM users WHERE user_id = 'drj';
    IF default_user_id IS NULL THEN
        INSERT INTO users (id, user_id, name, created_at)
        VALUES (gen_random_uuid(), 'drj', 'Default User', CURRENT_TIMESTAMP)
        RETURNING id INTO default_user_id;
    END IF;

    -- Get or create default app
    SELECT id INTO default_app_id FROM apps WHERE name = 'openmemory' AND owner_id = default_user_id;
    IF default_app_id IS NULL THEN
        INSERT INTO apps (id, owner_id, name, description, is_active, created_at, updated_at)
        VALUES (gen_random_uuid(), default_user_id, 'openmemory', 'Default OpenMemory App', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id INTO default_app_id;
    END IF;

    -- Migrate existing data from mem0_memories to the new memories table
    INSERT INTO memories (id, user_id, app_id, content, vector, metadata, state, created_at)
    SELECT
        m.id,
        default_user_id,
        default_app_id,
        COALESCE(m.payload->>'data', m.payload->>'memory', 'No content'),
        NULL, -- vector stored separately
        m.payload,
        'active',
        COALESCE((m.payload->>'created_at')::timestamp, CURRENT_TIMESTAMP)
    FROM mem0_memories m
    WHERE NOT EXISTS (SELECT 1 FROM memories WHERE id = m.id);

    -- Also migrate from memories_mem0_backup if it exists
    INSERT INTO memories (id, user_id, app_id, content, vector, metadata, state, created_at)
    SELECT
        m.id,
        default_user_id,
        default_app_id,
        COALESCE(m.payload->>'data', m.payload->>'memory', 'No content'),
        NULL, -- vector stored separately
        m.payload,
        'active',
        COALESCE((m.payload->>'created_at')::timestamp, CURRENT_TIMESTAMP)
    FROM memories_mem0_backup m
    WHERE NOT EXISTS (SELECT 1 FROM memories WHERE id = m.id);
END $$;