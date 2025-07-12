-- Fix to support both mem0 and OpenMemory schemas

-- First, ensure mem0's original table exists
CREATE TABLE IF NOT EXISTS memories_original (
    id UUID PRIMARY KEY,
    vector vector(1536),
    payload JSONB
);

-- Copy data from backup if exists
INSERT INTO memories_original (id, vector, payload)
SELECT id, vector, payload FROM memories_mem0_backup
ON CONFLICT (id) DO NOTHING;

-- Recreate the indexes mem0 expects
CREATE INDEX IF NOT EXISTS memories_original_pkey ON memories_original(id);

-- Now create a trigger to sync data between the schemas
-- When mem0 inserts into mem0_memories, also insert into memories table
CREATE OR REPLACE FUNCTION sync_mem0_to_openmemory()
RETURNS TRIGGER AS $$
DECLARE
    default_user_id UUID;
    default_app_id UUID;
BEGIN
    -- Get default user and app
    SELECT id INTO default_user_id FROM users WHERE user_id = COALESCE(NEW.payload->>'user_id', 'drj');
    SELECT id INTO default_app_id FROM apps WHERE name = 'openmemory' AND owner_id = default_user_id;

    -- Insert into memories table
    INSERT INTO memories (id, user_id, app_id, content, metadata, state, created_at)
    VALUES (
        NEW.id,
        default_user_id,
        default_app_id,
        COALESCE(NEW.payload->>'memory', NEW.payload->>'data', 'No content'),
        NEW.payload,
        'active',
        COALESCE((NEW.payload->>'created_at')::timestamp, CURRENT_TIMESTAMP)
    )
    ON CONFLICT (id) DO UPDATE SET
        content = EXCLUDED.content,
        metadata = EXCLUDED.metadata,
        updated_at = CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on mem0_memories table
DROP TRIGGER IF EXISTS sync_mem0_memories ON mem0_memories;
CREATE TRIGGER sync_mem0_memories
AFTER INSERT OR UPDATE ON mem0_memories
FOR EACH ROW
EXECUTE FUNCTION sync_mem0_to_openmemory();

-- Ensure all existing mem0_memories are synced
INSERT INTO memories (id, user_id, app_id, content, metadata, state, created_at)
SELECT
    m.id,
    u.id,
    a.id,
    COALESCE(m.payload->>'memory', m.payload->>'data', 'No content'),
    m.payload,
    'active',
    COALESCE((m.payload->>'created_at')::timestamp, CURRENT_TIMESTAMP)
FROM mem0_memories m
JOIN users u ON u.user_id = COALESCE(m.payload->>'user_id', 'drj')
JOIN apps a ON a.name = 'openmemory' AND a.owner_id = u.id
ON CONFLICT (id) DO NOTHING;