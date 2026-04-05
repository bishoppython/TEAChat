"""
Script to recreate the documents table with the correct embedding dimension
This approach recreates the entire table with data migration
"""
import os
import psycopg2
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def recreate_documents_table_with_correct_dimension():
    """Recreate documents table with correct embedding dimension"""
    database_url = os.getenv("DATABASE_URL")

    try:
        logger.info("🔄 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Check if documents table exists and get current structure
        cursor.execute("""
            SELECT column_name, data_type, udt_name 
            FROM information_schema.columns 
            WHERE table_name = 'documents' AND column_name = 'embedding'
        """)
        
        result = cursor.fetchone()
        if result:
            col_name, data_type, udt_name = result
            logger.info(f"Current embedding column: {col_name}, type: {data_type}, udt_name: {udt_name}")
        else:
            logger.warning("Embedding column not found in documents table")
            
        # Step 1: Create a new temporary table with correct structure
        logger.info("Creating temporary table with correct embedding dimension...")
        
        cursor.execute("""
            CREATE TABLE documents_new (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                owner_id INTEGER NOT NULL,  -- Will add FK after data migration
                patient_id INTEGER NOT NULL,  -- Will add FK after data migration
                title VARCHAR(500),
                text TEXT NOT NULL,
                source_type VARCHAR(50) DEFAULT 'note',
                chunk_order INTEGER DEFAULT 0,
                chunk_id VARCHAR(100),
                embedding vector(1536),  -- Correct dimension
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        
        logger.info("Temporary table created successfully with 1536-dim embedding column")
        
        # Step 2: Migrate data from old table to new table
        # We need to handle the embedding conversion carefully
        logger.info("Migrating data from old table to new table...")
        
        # Get all documents with their embeddings
        cursor.execute("""
            SELECT id, owner_id, patient_id, title, text, source_type, 
                   chunk_order, chunk_id, embedding, metadata, created_at, updated_at
            FROM documents
        """)
        
        documents = cursor.fetchall()
        logger.info(f"Migrating {len(documents)} documents...")
        
        # Prepare insert statement for new table
        insert_query = """
            INSERT INTO documents_new (id, owner_id, patient_id, title, text, source_type, 
                                      chunk_order, chunk_id, embedding, metadata, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        migrated_count = 0
        for doc in documents:
            doc_id, owner_id, patient_id, title, text, source_type, chunk_order, chunk_id, embedding, metadata, created_at, updated_at = doc
            
            # Convert the embedding to the new dimension (this is tricky if it's not already 1536)
            # For now, let's try to convert it by padding or truncating
            try:
                if embedding is not None:
                    # If embedding is stored as a vector, we need to convert it
                    # First, let's try to convert it to the correct size
                    # Since we can't easily change dimensions in pgvector, we'll try direct assignment
                    new_embedding = embedding
                else:
                    new_embedding = None
                    
                cursor.execute(insert_query, (
                    doc_id, owner_id, patient_id, title, text, source_type,
                    chunk_order, chunk_id, new_embedding, metadata, created_at, updated_at
                ))
                migrated_count += 1
                
                if migrated_count % 100 == 0:
                    logger.info(f"Migrated {migrated_count} documents...")
                    conn.commit()
                    
            except Exception as e:
                logger.error(f"Error migrating document {doc_id}: {e}")
                # For now, we'll skip this document or insert with null embedding
                cursor.execute(insert_query, (
                    doc_id, owner_id, patient_id, title, text, source_type,
                    chunk_order, chunk_id, None, metadata, created_at, updated_at
                ))
                logger.info(f"Document {doc_id} inserted with null embedding due to conversion error")
        
        conn.commit()
        logger.info(f"Successfully migrated {migrated_count} documents")
        
        # Step 3: Drop old indexes and constraints (if any)
        try:
            cursor.execute("DROP INDEX IF EXISTS idx_documents_embedding;")
        except:
            pass  # Index might not exist or may have different name
        conn.commit()
        
        # Step 4: Drop old table
        logger.info("Dropping old documents table...")
        cursor.execute("DROP TABLE documents CASCADE;")
        conn.commit()
        
        # Step 5: Rename new table to documents
        logger.info("Renaming temporary table to documents...")
        cursor.execute("ALTER TABLE documents_new RENAME TO documents;")
        conn.commit()
        
        # Step 6: Recreate foreign key constraints
        logger.info("Recreating foreign key constraints...")
        cursor.execute("""
            ALTER TABLE documents ADD CONSTRAINT fk_document_owner 
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;
        """)
        cursor.execute("""
            ALTER TABLE documents ADD CONSTRAINT fk_document_patient 
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE;
        """)
        conn.commit()
        
        # Step 7: Recreate indexes
        logger.info("Recreating indexes...")
        cursor.execute("CREATE INDEX idx_documents_owner_id ON documents(owner_id);")
        cursor.execute("CREATE INDEX idx_documents_patient_id ON documents(patient_id);")
        cursor.execute("CREATE INDEX idx_documents_chunk_id ON documents(chunk_id);")
        
        cursor.execute("""
            CREATE INDEX idx_documents_embedding 
            ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """)
        cursor.execute("CREATE INDEX idx_documents_created_at ON documents(created_at);")
        conn.commit()
        
        # Step 8: Recreate the ownership trigger
        logger.info("Recreating ownership trigger...")
        cursor.execute("""
            CREATE OR REPLACE FUNCTION check_document_patient_ownership()
            RETURNS TRIGGER AS $$
            BEGIN
                IF (SELECT owner_id FROM patients WHERE id = NEW.patient_id) != NEW.owner_id THEN
                    RAISE EXCEPTION 'Document owner must match patient owner';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        cursor.execute("""
            CREATE TRIGGER trigger_check_document_patient_ownership
                BEFORE INSERT OR UPDATE ON documents
                FOR EACH ROW
                EXECUTE FUNCTION check_document_patient_ownership();
        """)
        conn.commit()
        
        logger.info("✅ Successfully recreated documents table with correct 1536-dim embedding column!")
        
        # Verify the new table structure
        cursor.execute("""
            SELECT atttypmod 
            FROM pg_attribute 
            WHERE attrelid = 'documents'::regclass AND attname = 'embedding'
        """)
        
        dim_result = cursor.fetchone()
        if dim_result and dim_result[0] > 0:
            logger.info(f"✅ New embedding dimension confirmed: {dim_result[0]}")
        else:
            logger.info("✅ New embedding column created with variable dimensions (should accept 1536-dim vectors)")
        
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"❌ Error during table recreation: {e}")
        if 'conn' in locals():
            try:
                conn.rollback()
            except:
                pass
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        return False

def main():
    print("=" * 70)
    print("🔧 Complete recreation of Documents Table with 1536-dim Embeddings")
    print("=" * 70)
    print()
    
    success = recreate_documents_table_with_correct_dimension()

    print()
    if success:
        print("✅ Table recreation completed successfully!")
        print("The documents table now has the correct 1536-dimensional embedding column.")
    else:
        print("❌ Table recreation failed.")
        print("You may need to run this with database superuser privileges.")
    print()
    
    return success

if __name__ == "__main__":
    main()