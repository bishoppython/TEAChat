#!/usr/bin/env python3
"""
Script to update the database schema to support multi-column embeddings
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager

def update_database_schema():
    """Update the database schema to support multi-column embeddings"""
    print("Updating database schema to support multi-column embeddings...")
    
    db_manager = DatabaseManager()
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # Check if the old embedding column exists
                print("Checking current table structure...")
                cursor.execute("""
                    SELECT column_name, data_type, udt_name
                    FROM information_schema.columns 
                    WHERE table_name = 'documents' 
                    AND column_name = 'embedding'
                """)
                old_column = cursor.fetchone()
                
                if old_column:
                    print(f"Found old embedding column: {old_column}")
                    
                    # Check if new columns already exist
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns 
                        WHERE table_name = 'documents' 
                        AND column_name IN ('embedding_768', 'embedding_1536', 'embedding_3072')
                    """)
                    new_columns = cursor.fetchall()
                    
                    if new_columns:
                        print(f"New columns already exist: {[col[0] for col in new_columns]}")
                        print("Skipping schema update...")
                        return True
                    
                    print("Adding new embedding columns...")
                    
                    # Add the new embedding columns
                    cursor.execute("ALTER TABLE documents ADD COLUMN embedding_768 vector(768)")
                    print("Added embedding_768 column")
                    
                    cursor.execute("ALTER TABLE documents ADD COLUMN embedding_1536 vector(1536)")
                    print("Added embedding_1536 column")
                    
                    cursor.execute("ALTER TABLE documents ADD COLUMN embedding_3072 vector(3072)")
                    print("Added embedding_3072 column")
                    
                    # Migrate existing embeddings to the appropriate new column
                    # This assumes the old column had variable dimensions
                    print("Migrating existing embeddings...")
                    cursor.execute("""
                        UPDATE documents 
                        SET embedding_1536 = embedding::vector(1536)
                        WHERE embedding IS NOT NULL 
                        AND vector_dims(embedding) = 1536
                    """)
                    migrated_1536 = cursor.rowcount
                    print(f"Migrated {migrated_1536} embeddings to 1536-dim column")
                    
                    cursor.execute("""
                        UPDATE documents 
                        SET embedding_768 = embedding::vector(768)
                        WHERE embedding IS NOT NULL 
                        AND vector_dims(embedding) = 768
                    """)
                    migrated_768 = cursor.rowcount
                    print(f"Migrated {migrated_768} embeddings to 768-dim column")
                    
                    cursor.execute("""
                        UPDATE documents 
                        SET embedding_3072 = embedding::vector(3072)
                        WHERE embedding IS NOT NULL 
                        AND vector_dims(embedding) = 3072
                    """)
                    migrated_3072 = cursor.rowcount
                    print(f"Migrated {migrated_3072} embeddings to 3072-dim column")
                    
                    # Drop the old embedding column
                    cursor.execute("ALTER TABLE documents DROP COLUMN embedding")
                    print("Dropped old embedding column")
                    
                    # Create the new indexes
                    print("Creating new vector indexes...")
                    try:
                        cursor.execute("CREATE INDEX idx_documents_embedding_768 ON documents USING ivfflat (embedding_768 vector_cosine_ops) WITH (lists = 100)")
                        print("Created index for 768-dim embeddings")
                    except Exception as e:
                        print(f"Could not create index for 768-dim: {e}")
                    
                    try:
                        cursor.execute("CREATE INDEX idx_documents_embedding_1536 ON documents USING ivfflat (embedding_1536 vector_cosine_ops) WITH (lists = 100)")
                        print("Created index for 1536-dim embeddings")
                    except Exception as e:
                        print(f"Could not create index for 1536-dim: {e}")
                        
                    try:
                        cursor.execute("CREATE INDEX idx_documents_embedding_3072 ON documents USING ivfflat (embedding_3072 vector_cosine_ops) WITH (lists = 100)")
                        print("Created index for 3072-dim embeddings")
                    except Exception as e:
                        print(f"Could not create index for 3072-dim: {e}")
                    
                    conn.commit()
                    print("✅ Database schema updated successfully!")
                    return True
                else:
                    # Check if new columns already exist
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns 
                        WHERE table_name = 'documents' 
                        AND column_name IN ('embedding_768', 'embedding_1536', 'embedding_3072')
                    """)
                    new_columns = cursor.fetchall()
                    
                    if new_columns:
                        print(f"New columns already exist: {[col[0] for col in new_columns]}")
                        print("Database schema is already updated.")
                        return True
                    else:
                        print("ERROR: Neither old nor new embedding columns found!")
                        return False
                        
            except Exception as e:
                print(f"❌ Error updating database schema: {e}")
                import traceback
                traceback.print_exc()
                conn.rollback()
                return False

if __name__ == "__main__":
    success = update_database_schema()
    if success:
        print("\n🎉 Database schema has been successfully updated for multi-column embeddings!")
    else:
        print("\n❌ Failed to update database schema.")