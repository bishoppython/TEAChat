ALTER TABLE documents ADD COLUMN IF NOT EXISTS embedding_768 vector(768);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS embedding_1536 vector(1536);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS embedding_3072 vector(3072);

-- Migrate data from old column if it exists
UPDATE documents 
SET embedding_1536 = embedding::vector(1536)
WHERE embedding IS NOT NULL;

-- Drop the old column
ALTER TABLE documents DROP COLUMN IF EXISTS embedding;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_documents_embedding_768 ON documents USING ivfflat (embedding_768 vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_documents_embedding_1536 ON documents USING ivfflat (embedding_1536 vector_cosine_ops) WITH (lists = 100);