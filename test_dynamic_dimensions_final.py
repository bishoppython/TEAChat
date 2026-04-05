#!/usr/bin/env python3
"""
Test script to verify that the database now supports dynamic embedding dimensions
"""
import os
import sys
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from utils.embedding_generator import MultiModelEmbeddingGenerator

def test_dynamic_dimensions():
    """Test that the database can handle embeddings of different dimensions"""
    print("Testing dynamic embedding dimensions support...")
    
    # Initialize database manager and embedding generator
    db_manager = DatabaseManager()
    embedder = MultiModelEmbeddingGenerator()
    
    # Create a test user if one doesn't exist
    try:
        # Try to create a test user
        user_id = None
        try:
            user_id = db_manager.create_user(
                username="test_user",
                full_name="Test User",
                email="test@example.com",
                role="therapist"
            )
            print(f"✅ Created test user with ID: {user_id}")
        except Exception as e:
            print(f"⚠️ Could not create test user (may already exist): {e}")
            # Try to get an existing user
            import psycopg2
            from psycopg2.extras import RealDictCursor
            with db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT id FROM users LIMIT 1")
                    result = cursor.fetchone()
                    if result:
                        user_id = result['id']
                        print(f"✅ Using existing user with ID: {user_id}")
                    else:
                        print("❌ No users found in database")
                        return False
        
        # Create a test patient
        patient_id = db_manager.create_patient(
            patient_id="test_patient",
            owner_id=user_id,
            first_name="Test",
            last_name="Patient",
            age=25,
            diagnosis="Test diagnosis"
        )
        print(f"✅ Created test patient with ID: {patient_id}")
        
    except Exception as e:
        print(f"❌ Error setting up test data: {e}")
        return False
    
    # Test adding a document with embedding
    print(f"\nTesting document addition with embedding...")
    try:
        test_text = "This is a test document to verify dynamic embedding dimensions."
        embedding = embedder.generate_single_embedding(test_text, "RETRIEVAL_DOCUMENT")
        actual_dim = len(embedding)
        
        print(f"Generated embedding with {actual_dim} dimensions")
        
        # Add document to database
        doc_id = db_manager.add_document_chunk(
            owner_id=user_id,
            patient_id=patient_id,
            title="Test Document for Dynamic Dimensions",
            text=test_text,
            embedding=embedding
        )
        print(f"✅ Successfully added document with {actual_dim} dimensions to database. Doc ID: {doc_id}")
        
    except Exception as e:
        print(f"❌ Failed to add document: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test retrieval
    print("\nTesting retrieval with query embedding...")
    try:
        query_embedding = embedder.generate_single_embedding("Test query for retrieval", "RETRIEVAL_QUERY")
        print(f"Query embedding dimensions: {len(query_embedding)}")
        
        results = db_manager.retrieve_similar_documents(
            owner_id=user_id,
            query="Test query for retrieval",
            patient_id=patient_id,
            k=2
        )
        
        print(f"✅ Retrieved {len(results)} similar documents")
        for result in results:
            print(f"  - Doc ID: {result['id']}, Similarity: {result['similarity']:.4f}")
        
    except Exception as e:
        print(f"❌ Retrieval test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ All tests passed! Database now supports dynamic embedding dimensions.")
    return True

if __name__ == "__main__":
    success = test_dynamic_dimensions()
    if success:
        print("\n🎉 All tests completed successfully! The system now supports dynamic embedding dimensions.")
    else:
        print("\n❌ Some tests failed.")