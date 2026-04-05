#!/usr/bin/env python3
"""
Script to properly handle the vector index for variable dimensions
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager

def update_vector_index_handling():
    """Update vector index handling to support variable dimensions"""
    print("Updating vector index handling for variable dimensions...")
    
    db_manager = DatabaseManager()
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            try:
                # Drop the existing vector index that doesn't support variable dimensions
                print("Checking for existing vector index...")
                cursor.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'documents' 
                    AND indexname = 'idx_documents_embedding'
                """)
                index_exists = cursor.fetchone()
                
                if index_exists:
                    print("Dropping problematic vector index...")
                    cursor.execute("DROP INDEX idx_documents_embedding")
                    conn.commit()
                    print("✅ Problematic vector index dropped")
                else:
                    print("✅ No problematic vector index found")
                
                # Check existing embeddings
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
                
                print("\n✅ Vector index handling updated successfully!")
                print("The system will now support variable embedding dimensions.")
                print("Note: Without the IVFFlat index, similarity search performance may be reduced,")
                print("but the 'different vector dimensions' error should be resolved.")
                
                return True
                
            except Exception as e:
                print(f"❌ Error updating vector index handling: {e}")
                import traceback
                traceback.print_exc()
                return False

if __name__ == "__main__":
    success = update_vector_index_handling()
    if success:
        print("\n🎉 Vector index handling has been updated for variable dimensions!")
        print("The system should now properly handle embeddings of different dimensions.")
    else:
        print("\n❌ Failed to update vector index handling.")