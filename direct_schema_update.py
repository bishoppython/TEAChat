#!/usr/bin/env python3
"""
Direct script to update the database schema to multi-column embeddings
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager

def direct_schema_update():
    """Directly update the database schema to multi-column embeddings"""
    print("Directly updating database schema to multi-column embeddings...")
    
    db_manager = DatabaseManager()
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # Check current columns
                cursor.execute("""
                    SELECT column_name, data_type, udt_name
                    FROM information_schema.columns 
                    WHERE table_name = 'documents' 
                    AND column_name LIKE 'embedding%'
                    ORDER BY column_name
                """)
                current_cols = cursor.fetchall()
                
                print("Current embedding columns:")
                for col in current_cols:
                    print(f"  - {col[0]}: {col[1]} ({col[2]})")
                
                # Add new columns if they don't exist
                new_columns = ['embedding_768', 'embedding_1536', 'embedding_3072']
                for col_name in new_columns:
                    try:
                        cursor.execute(f"ALTER TABLE documents ADD COLUMN {col_name} vector")
                        print(f"Added {col_name} column")
                    except Exception as e:
                        print(f"Column {col_name} may already exist: {e}")
                
                # Update the columns to have the correct dimensions
                try:
                    cursor.execute("ALTER TABLE documents ALTER COLUMN embedding_768 TYPE vector(768)")
                    print("Updated embedding_768 to 768 dimensions")
                except Exception as e:
                    print(f"Could not update embedding_768: {e}")
                
                try:
                    cursor.execute("ALTER TABLE documents ALTER COLUMN embedding_1536 TYPE vector(1536)")
                    print("Updated embedding_1536 to 1536 dimensions")
                except Exception as e:
                    print(f"Could not update embedding_1536: {e}")
                
                try:
                    cursor.execute("ALTER TABLE documents ALTER COLUMN embedding_3072 TYPE vector(3072)")
                    print("Updated embedding_3072 to 3072 dimensions")
                except Exception as e:
                    print(f"Could not update embedding_3072: {e}")
                
                # Check if old embedding column exists and drop it
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns 
                    WHERE table_name = 'documents' 
                    AND column_name = 'embedding'
                """)
                old_col = cursor.fetchone()
                
                if old_col:
                    # First, migrate data if needed
                    print("Migrating data from old embedding column...")
                    try:
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
                    cursor.execute("ALTER TABLE documents DROP COLUMN embedding")
                    print("Dropped old embedding column")
                
                # Create indexes
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_embedding_768 ON documents USING ivfflat (embedding_768 vector_cosine_ops) WITH (lists = 100)")
                    print("Created index for 768-dim embeddings")
                except Exception as e:
                    print(f"Could not create index for 768-dim: {e}")
                
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_embedding_1536 ON documents USING ivfflat (embedding_1536 vector_cosine_ops) WITH (lists = 100)")
                    print("Created index for 1536-dim embeddings")
                except Exception as e:
                    print(f"Could not create index for 1536-dim: {e}")
                
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_embedding_3072 ON documents USING ivfflat (embedding_3072 vector_cosine_ops) WITH (lists = 100)")
                    print("Created index for 3072-dim embeddings")
                except Exception as e:
                    print(f"Could not create index for 3072-dim: {e}")
                
                conn.commit()
                print("✅ Direct schema update completed!")
                
                # Verify the update
                cursor.execute("""
                    SELECT column_name, data_type, udt_name
                    FROM information_schema.columns 
                    WHERE table_name = 'documents' 
                    AND column_name LIKE 'embedding%'
                    ORDER BY column_name
                """)
                final_cols = cursor.fetchall()
                
                print("\nFinal embedding columns:")
                for col in final_cols:
                    print(f"  - {col[0]}: {col[1]} ({col[2]})")
                
                return True
                
            except Exception as e:
                print(f"❌ Error in direct schema update: {e}")
                import traceback
                traceback.print_exc()
                conn.rollback()
                return False

if __name__ == "__main__":
    success = direct_schema_update()
    if success:
        print("\n🎉 Direct schema update successful!")
    else:
        print("\n❌ Direct schema update failed.")