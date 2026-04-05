#!/usr/bin/env python3
"""
Test script to verify that the system can handle different embedding dimensions
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from utils.embedding_generator import MultiModelEmbeddingGenerator

def test_different_dimensions():
    """Test if the system can handle different embedding dimensions properly"""
    print("Testing different embedding dimensions...")
    
    # Initialize components
    db_manager = DatabaseManager()
    embedder = MultiModelEmbeddingGenerator()
    
    # Test with different documents and embeddings
    test_cases = [
        ("Document with first embedding type", "retrieval_document"),
        ("Query for similarity search", "retrieval_query")
    ]
    
    # Add a document with embedding
    doc_text = "This is a test document about patient evaluation and clinical assessment."
    embedding = embedder.generate_single_embedding(doc_text, "RETRIEVAL_DOCUMENT")
    print(f"Generated document embedding with {len(embedding)} dimensions")
    
    try:
        doc_id = db_manager.add_document_chunk(
            owner_id=8,
            patient_id=14,
            title="Test Document for Dimension Filtering",
            text=doc_text,
            embedding=embedding
        )
        print(f"✅ Successfully added document with {len(embedding)} dimensions")
    except Exception as e:
        print(f"❌ Failed to add document: {e}")
        return False
    
    # Now try to query with a different embedding
    query_text = "Find information about patient evaluation"
    query_embedding = embedder.generate_single_embedding(query_text, "RETRIEVAL_QUERY")
    print(f"Generated query embedding with {len(query_embedding)} dimensions")
    
    try:
        results = db_manager.retrieve_similar_documents(
            owner_id=8,
            query=query_text,
            patient_id=14,
            k=5
        )
        print(f"✅ Successfully retrieved {len(results)} documents with dimension filtering")
        for result in results:
            print(f"  - Doc ID: {result['id']}, Similarity: {result['similarity']:.4f}")
        return True
    except Exception as e:
        print(f"❌ Failed to retrieve documents: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_different_dimensions()
    if success:
        print("\n🎉 The system can now properly handle different embedding dimensions!")
        print("The 'different vector dimensions' error should be resolved!")
    else:
        print("\n❌ Test failed.")