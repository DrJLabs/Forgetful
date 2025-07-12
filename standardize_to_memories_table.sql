-- Standardize all components to use the memories table

-- First, ensure the memories table has the columns mem0 expects
-- Check if 'vector' column exists, if not add it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'memories' AND column_name = 'vector'
    ) THEN
        ALTER TABLE memories ADD COLUMN vector vector(1536);
    END IF;
END $$;

-- Check if 'payload' column exists, if not add it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'memories' AND column_name = 'payload'
    ) THEN
        ALTER TABLE memories ADD COLUMN payload JSONB DEFAULT '{}';
    END IF;
END $$;

-- Update the payload column with existing metadata
UPDATE memories
SET payload = COALESCE(metadata, '{}')
WHERE payload IS NULL OR payload = '{}';

-- Drop the trigger we created earlier
DROP TRIGGER IF EXISTS sync_mem0_memories ON mem0_memories;
DROP FUNCTION IF EXISTS sync_mem0_to_openmemory();

-- Drop the mem0_memories table
DROP TABLE IF EXISTS mem0_memories CASCADE;

-- Drop the memories_original table if it exists
DROP TABLE IF EXISTS memories_original CASCADE;

-- Drop the backup table
DROP TABLE IF EXISTS memories_mem0_backup CASCADE;

-- Create indexes that mem0 expects
CREATE INDEX IF NOT EXISTS memories_vector_idx ON memories USING ivfflat (vector vector_l2_ops);

-- Verify the final state
SELECT
    'Table: memories' as info,
    COUNT(*) as record_count,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT app_id) as unique_apps
FROM memories;

-- Show column information
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name = 'memories'
ORDER BY ordinal_position;
