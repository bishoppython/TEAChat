#!/usr/bin/env python3
"""
Script to investigate the exact error and vector dimension issue
"""
import os
import sys
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from utils.embedding_generator import MultiModelEmbeddingGenerator

def investigate_vector_issue():
    """Investigate the exact vector dimension issue"""
    print("Investigating vector dimension issue...")
    
    # Initialize components
    db_manager = DatabaseManager()
    embedder = MultiModelEmbeddingGenerator()
    
    # Test generating an embedding
    test_text = "Test document for investigation"
    embedding = embedder.generate_single_embedding(test_text, "RETRIEVAL_DOCUMENT")
    print(f"Generated embedding with {len(embedding)} dimensions")
    print(f"First 5 values: {embedding[:5]}")
    
    # Check the exact format being sent to database
    embedding_str = "[" + ",".join([str(float(x)) for x in embedding]) + "]"
    print(f"Embedding string length: {len(embedding_str)}")
    print(f"Embedding string preview: {embedding_str[:100]}...")
    
    # Check database table structure more thoroughly
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            # Get detailed information about the embedding column
            cursor.execute("""
                SELECT 
                    a.attname AS column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                    a.atttypmod,
                    t.typname
                FROM pg_catalog.pg_attribute a
                JOIN pg_catalog.pg_type t ON t.oid = a.atttypid
                WHERE a.attrelid = 'documents'::regclass
                AND a.attname = 'embedding'
                AND a.attnum > 0
            """)
            result = cursor.fetchone()
            
            if result:
                column_name, full_type, atttypmod, typname = result
                print(f"\nDetailed column info:")
                print(f"  - Column: {column_name}")
                print(f"  - Full type: {full_type}")
                print(f"  - Type modifier: {atttypmod}")
                print(f"  - Type name: {typname}")
                
                # The atttypmod for vector type can indicate dimension constraints
                if atttypmod != -1:  # -1 means no constraint
                    print(f"  - Type modifier {atttypmod} may indicate dimension constraint")
                else:
                    print(f"  - No dimension constraint (atttypmod = -1)")
    
    # Try to create a test user and patient if they don't exist
    try:
        # Try to get existing user or create one
        user_id = None
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users LIMIT 1")
                result = cursor.fetchone()
                if result:
                    user_id = result[0]
                    print(f"Using existing user ID: {user_id}")
                else:
                    user_id = db_manager.create_user("test_user", "Test User", "test@example.com")
                    print(f"Created test user ID: {user_id}")
        
        # Create a test patient if needed
        patient_id = None
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM patients LIMIT 1")
                result = cursor.fetchone()
                if result:
                    patient_id = result[0]
                    print(f"Using existing patient ID: {patient_id}")
                else:
                    patient_id = db_manager.create_patient(
                        patient_id="test_patient", 
                        owner_id=user_id,
                        first_name="Test", 
                        last_name="Patient",
                        age=30,
                        diagnosis="Test diagnosis"
                    )
                    print(f"Created test patient ID: {patient_id}")
        
        # Now try to add a document with the embedding
        print(f"\nAttempting to add document with {len(embedding)}-dimension embedding...")
        try:
            doc_id = db_manager.add_document_chunk(
                owner_id=user_id,
                patient_id=patient_id,
                title="Test Document",
                text=test_text,
                embedding=embedding
            )
            print(f"✅ Successfully added document with ID: {doc_id}")
        except Exception as e:
            print(f"❌ Failed to add document: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"Error setting up test data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    investigate_vector_issue()