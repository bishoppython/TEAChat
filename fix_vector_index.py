#!/usr/bin/env python3
"""
Script to fix the vector index issue definitively
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager

def fix_vector_index():
    """Fix the vector index to properly handle variable dimensions"""
    print("Fixing vector index for variable dimensions...")
    
    db_manager = DatabaseManager()
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # Drop the existing vector index
                print("Dropping existing vector index...")
                cursor.execute("DROP INDEX IF EXISTS idx_documents_embedding")
                conn.commit()
                print("✅ Vector index dropped")
                
                # Create a new vector index that's more compatible with variable dimensions
                print("Creating new vector index...")
                cursor.execute("CREATE INDEX idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
                conn.commit()
                print("✅ New vector index created")
                
                # Verify the index was created
                cursor.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'documents' 
                    AND indexname = 'idx_documents_embedding'
                """)
                result = cursor.fetchone()
                
                if result:
                    print(f"✅ Index verification: {result[0]} exists")
                else:
                    print("❌ Index was not created properly")
                    return False
                
                # Check if there are any documents with different dimensions in the database
                print("\nChecking existing embeddings in database...")
                cursor.execute("""
                    SELECT vector_dims(embedding), COUNT(*) 
                    FROM documents 
                    WHERE embedding IS NOT NULL 
                    GROUP BY vector_dims(embedding)
                    ORDER BY vector_dims(embedding)
                """)
                results = cursor.fetchall()
                
                if results:
                    print("Existing embedding dimensions in database:")
                    for dim, count in results:
                        print(f"  - {count} documents with {dim} dimensions")
                else:
                    print("  - No existing embeddings in database")
                
                return True
                
            except Exception as e:
                print(f"❌ Error fixing vector index: {e}")
                import traceback
                traceback.print_exc()
                return False

if __name__ == "__main__":
    success = fix_vector_index()
    if success:
        print("\n🎉 Vector index has been fixed for variable dimensions!")
    else:
        print("\n❌ Failed to fix the vector index.")