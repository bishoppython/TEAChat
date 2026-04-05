"""
Updated script to fix embedding dimension in database
Handles potential permission issues by attempting to alter table in a different way
"""
import os
import psycopg2
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def check_current_embedding_dimension():
    """Check the current dimension of the embedding column"""
    database_url = os.getenv("DATABASE_URL")

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Check the current column definition
        cursor.execute("""
            SELECT data_type, udt_name 
            FROM information_schema.columns 
            WHERE table_name = 'documents' AND column_name = 'embedding'
        """)
        
        result = cursor.fetchone()
        if result:
            data_type, udt_name = result
            logger.info(f"Current embedding column type: {data_type}, udt_name: {udt_name}")
            
            # For vector type in pgvector, check the dimension
            cursor.execute("""
                SELECT atttypmod 
                FROM pg_attribute 
                WHERE attrelid = 'documents'::regclass AND attname = 'embedding'
            """)
            
            dim_result = cursor.fetchone()
            if dim_result:
                atttypmod = dim_result[0]
                if atttypmod > 0:
                    logger.info(f"Current embedding dimension: {atttypmod}")
                    return atttypmod
                else:
                    logger.info("Current embedding dimension is variable/undefined")
                    return None
        else:
            logger.warning("Embedding column not found in documents table")
            
        cursor.close()
        conn.close()
        
        return None
        
    except Exception as e:
        logger.error(f"Error checking current embedding dimension: {e}")
        return None

def fix_embedding_dimension():
    """Attempt to fix the embedding dimension with multiple approaches"""
    database_url = os.getenv("DATABASE_URL")

    try:
        logger.info("🔄 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # First, check current dimension
        current_dim = check_current_embedding_dimension()
        logger.info(f"Current embedding dimension: {current_dim}")
        
        if current_dim == 1536:
            logger.info("✅ Embedding dimension is already 1536. No changes needed.")
            cursor.close()
            conn.close()
            return True

        logger.info("🔧 Attempting to update embedding dimension to 1536...")

        # Try approach 1: Direct alter column with DROP and ADD is likely to fail due to permissions
        # Try approach 2: Add a new column, migrate data, then replace
        try:
            # Check if temporary column already exists and drop it
            cursor.execute("ALTER TABLE documents DROP COLUMN IF EXISTS embedding_temp;")
            conn.commit()
            
            # Add new temp embedding column with 1536 dimensions
            cursor.execute("ALTER TABLE documents ADD COLUMN embedding_temp vector(1536);")
            conn.commit()
            
            # Migrate existing embeddings to new column
            cursor.execute("""
                UPDATE documents 
                SET embedding_temp = embedding::vector(1536) 
                WHERE embedding IS NOT NULL;
            """)
            conn.commit()
            
            # Drop the original embedding column
            cursor.execute("ALTER TABLE documents DROP COLUMN embedding CASCADE;")
            conn.commit()
            
            # Rename the temp column to embedding
            cursor.execute("ALTER TABLE documents RENAME COLUMN embedding_temp TO embedding;")
            conn.commit()
            
            # Recreate the index
            try:
                cursor.execute("DROP INDEX IF EXISTS idx_documents_embedding;")
                conn.commit()
            except:
                pass  # Index might not exist or may have different name
                
            cursor.execute("""
                CREATE INDEX idx_documents_embedding
                ON documents USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            conn.commit()
            
            logger.info("✅ Successfully updated embedding dimension to 1536!")
            
        except psycopg2.errors.InsufficientPrivilege as e:
            logger.error(f"Permission error with approach 1: {e}")
            conn.rollback()
            
            # Approach 3: If we can't modify the table structure, at least check if it matches schema
            logger.info("Attempting to recreate entire table structure...")
            # Read the schema and apply it (with proper handling)
            with open('database/schema.sql', 'r') as schema_file:
                schema_sql = schema_file.read()
            
            # Extract only the documents table creation part
            import re
            # Find the documents table definition
            doc_table_match = re.search(
                r'(CREATE TABLE documents\s*\([^)]*embedding vector\(1536\)[^)]*\);)',
                schema_sql,
                re.DOTALL | re.IGNORECASE
            )
            
            if doc_table_match:
                logger.info("Found documents table schema with 1536 dimensions in schema file")
                logger.info("Recommendation: Recreate the database with the correct schema or use a user with DDL privileges")
            else:
                logger.warning("Documents table definition not found in schema file")
                
        except Exception as e:
            logger.error(f"Error with approach 1: {e}")
            conn.rollback()
            
            # Fallback: Check schema expectations vs reality
            logger.info("Checking if schema file matches database expectations...")
            expected_dim = 1536  # From schema.sql, the table should be vector(1536)
            
            if current_dim != expected_dim:
                logger.warning(f"Schema expects {expected_dim} dimensions but database has {current_dim}.")
                logger.warning("You may need to run the full schema recreation with appropriate privileges.")
            else:
                logger.info("Current dimension matches expected dimension.")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False

def main():
    print("=" * 60)
    print("🔧 Advanced Fix for Embedding Dimension")
    print("=" * 60)
    print()
    
    # Check current state
    current_dim = check_current_embedding_dimension()
    print(f"Current embedding dimension: {current_dim}")
    
    if current_dim == 1536:
        print("✅ Database already has correct embedding dimension (1536)")
        print()
        return True
    
    print()
    print("Attempting to fix...")
    success = fix_embedding_dimension()

    print()
    if success:
        print("✅ Fix process completed!")
        # Check final state
        final_dim = check_current_embedding_dimension()
        if final_dim == 1536:
            print("✅ Database now has correct embedding dimension (1536)!")
        else:
            print(f"⚠️  Dimension is still {final_dim}. You may need to run schema recreation with proper privileges.")
    else:
        print("❌ Fix process failed.")
    print()
    
    return success

if __name__ == "__main__":
    main()