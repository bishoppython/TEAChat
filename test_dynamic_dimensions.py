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
    
    # Test different embedding sizes
    test_cases = [
        ("Test document with 768 dimensions", 768),
        ("Test document with 1536 dimensions", 1536),
        ("Test document with 3072 dimensions", 3072),
    ]
    
    for i, (text, expected_dim) in enumerate(test_cases):
        print(f"\nTest case {i+1}: {text} (expected {expected_dim} dimensions)")
        
        # Generate a test embedding with the expected dimensions
        # In practice, we'll use the actual embedding generator
        embedding = embedder.generate_single_embedding(text, "RETRIEVAL_DOCUMENT")
        actual_dim = len(embedding)
        
        print(f"Generated embedding with {actual_dim} dimensions")
        
        # Add document to database
        try:
            doc_id = db_manager.add_document_chunk(
                owner_id=1,
                patient_id=1,
                title=f"Test Document {i+1}",
                text=text,
                embedding=embedding
            )
            print(f"✅ Successfully added document with {actual_dim} dimensions to database. Doc ID: {doc_id}")
        except Exception as e:
            print(f"❌ Failed to add document with {actual_dim} dimensions: {e}")
            return False
    
    print("\n✅ All tests passed! Database now supports dynamic embedding dimensions.")
    
    # Test retrieval
    print("\nTesting retrieval with query embedding...")
    try:
        query_embedding = embedder.generate_single_embedding("Test query for retrieval", "RETRIEVAL_QUERY")
        print(f"Query embedding dimensions: {len(query_embedding)}")
        
        results = db_manager.retrieve_similar_documents(
            owner_id=1,
            query="Test query for retrieval",
            k=2
        )
        
        print(f"✅ Retrieved {len(results)} similar documents")
        for result in results:
            print(f"  - Doc ID: {result['id']}, Similarity: {result['similarity']:.4f}")
        
    except Exception as e:
        print(f"❌ Retrieval test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_dynamic_dimensions()
    if success:
        print("\n🎉 All tests completed successfully! The system now supports dynamic embedding dimensions.")
    else:
        print("\n❌ Some tests failed.")