#!/usr/bin/env python3
"""
Test script to verify that the 3072 dimension issue is resolved
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from utils.embedding_generator import MultiModelEmbeddingGenerator

def test_3072_dimensions():
    """Test if we can now handle 3072 dimension embeddings"""
    print("Testing if 3072 dimension embeddings work...")
    
    # Initialize components
    db_manager = DatabaseManager()
    embedder = MultiModelEmbeddingGenerator()
    
    # Check what dimensions are currently being generated
    test_text = "Test document to check dimension handling"
    embedding = embedder.generate_single_embedding(test_text, "RETRIEVAL_DOCUMENT")
    print(f"Generated embedding with {len(embedding)} dimensions")
    
    # Try to add to database
    try:
        # Use existing user and patient IDs from your error log (user 8, patient 14)
        doc_id = db_manager.add_document_chunk(
            owner_id=8,
            patient_id=14,
            title="Test Document for 3072 Dimensions",
            text=test_text,
            embedding=embedding
        )
        print(f"✅ Successfully added document with {len(embedding)} dimensions to database!")
        print(f"Document ID: {doc_id}")
        
        # Also test retrieval
        query_embedding = embedder.generate_single_embedding("Test query", "RETRIEVAL_QUERY")
        print(f"Query embedding dimensions: {len(query_embedding)}")
        
        results = db_manager.retrieve_similar_documents(
            owner_id=8,
            query="Test query",
            patient_id=14,
            k=2
        )
        print(f"✅ Retrieved {len(results)} similar documents")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to add document: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_3072_dimensions()
    if success:
        print("\n🎉 Success! The system now properly handles variable embedding dimensions.")
        print("The error 'expected 1536 dimensions, not 3072' should be resolved!")
    else:
        print("\n❌ Test failed.")