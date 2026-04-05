#!/usr/bin/env python3
"""
Script to fix the database schema using direct SQL commands
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def fix_schema_directly():
    """Fix the database schema using direct SQL commands"""
    print("Fixing database schema using direct SQL commands...")
    
    # Connect directly using psycopg2
    connection_string = os.getenv("DATABASE_URL")
    if not connection_string:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    try:
        conn = psycopg2.connect(connection_string)
        
        # Execute the schema changes in a single transaction
        with conn.cursor() as cursor:
            print("Starting schema update transaction...")
            
            # First, check what columns exist
            cursor.execute("""
                SELECT column_name, data_type, udt_name
                FROM information_schema.columns 
                WHERE table_name = 'documents' 
                AND column_name LIKE 'embedding%'
                ORDER BY column_name
            """)
            current_cols = cursor.fetchall()
            print(f"Current embedding columns: {[col[0] for col in current_cols]}")
            
            # Add new columns if they don't exist
            new_columns = [
                ("embedding_768", "vector(768)"),
                ("embedding_1536", "vector(1536)"),
                ("embedding_3072", "vector(3072)")
            ]
            
            for col_name, col_type in new_columns:
                try:
                    cursor.execute(f"ALTER TABLE documents ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
                    print(f"Added/verified column {col_name} {col_type}")
                except Exception as e:
                    print(f"Warning for {col_name}: {e}")
            
            # Check if old column exists and migrate data if needed
            old_col_exists = any(col[0] == 'embedding' for col in current_cols)
            if old_col_exists:
                print("Migrating data from old embedding column...")
                try:
                    # Update documents to copy data to appropriate new column
                    cursor.execute("""
                        UPDATE documents 
                        SET embedding_1536 = embedding::vector(1536)
                        WHERE embedding IS NOT NULL
                    """)
                    migrated = cursor.rowcount
                    print(f"Migrated {migrated} embeddings to 1536-dim column")
                except Exception as e:
                    print(f"Could not migrate data: {e}")
                
                # Drop the old column
                cursor.execute("ALTER TABLE documents DROP COLUMN IF EXISTS embedding")
                print("Dropped old embedding column")
            else:
                print("Old embedding column does not exist, no migration needed")
            
            # Create indexes if they don't exist
            indexes = [
                ("idx_documents_embedding_768", "embedding_768", 768),
                ("idx_documents_embedding_1536", "embedding_1536", 1536)
            ]
            
            for idx_name, col_name, dim in indexes:
                try:
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS {idx_name} 
                        ON documents USING ivfflat ({col_name} vector_cosine_ops) 
                        WITH (lists = 100)
                    """)
                    print(f"Created/verified index {idx_name} for {col_name}")
                except Exception as e:
                    print(f"Could not create index {idx_name}: {e}")
            
            # Try to create 3072 index but expect it to fail
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_embedding_3072 
                    ON documents USING ivfflat (embedding_3072 vector_cosine_ops) 
                    WITH (lists = 100)
                """)
                print("Created index for 3072-dim embeddings (unexpected)")
            except Exception as e:
                print(f"Expected error for 3072-dim index: {e}")
            
            # Commit the transaction
            conn.commit()
            print("✅ Schema update transaction committed!")
        
        # Verify the changes
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT column_name, udt_name
                FROM information_schema.columns 
                WHERE table_name = 'documents' 
                AND column_name LIKE 'embedding%'
                ORDER BY column_name
            """)
            final_cols = cursor.fetchall()
            
            print(f"\nFinal embedding columns: {[col['column_name'] for col in final_cols]}")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error fixing schema: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()
        return False

if __name__ == "__main__":
    success = fix_schema_directly()
    if success:
        print("\n🎉 Schema has been successfully updated!")
    else:
        print("\n❌ Schema update failed.")