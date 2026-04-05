#!/usr/bin/env python3
"""
Test script to verify that the system can handle the problematic scenario
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from utils.embedding_generator import MultiModelEmbeddingGenerator

def test_problematic_scenario():
    """Test the scenario that was causing the error"""
    print("Testing the problematic scenario...")
    
    # Initialize components
    db_manager = DatabaseManager()
    embedder = MultiModelEmbeddingGenerator()
    
    # Add a document with 1536-dimension embedding (typical OpenAI)
    doc_text_1536 = "This is a test document with 1536 dimensions from OpenAI."
    embedding_1536 = embedder.generate_single_embedding(doc_text_1536, "RETRIEVAL_DOCUMENT")
    print(f"Generated first embedding with {len(embedding_1536)} dimensions")
    
    try:
        doc_id_1 = db_manager.add_document_chunk(
            owner_id=8,
            patient_id=14,
            title="Test Document 1536 dims",
            text=doc_text_1536,
            embedding=embedding_1536
        )
        print(f"✅ Successfully added document with {len(embedding_1536)} dimensions")
    except Exception as e:
        print(f"❌ Failed to add first document: {e}")
        return False
    
    # Now try to add a document with potentially different dimensions
    # This simulates the scenario that was causing the error
    doc_text_3072 = "This is another test document that might have 3072 dimensions."
    embedding_3072 = embedder.generate_single_embedding(doc_text_3072, "RETRIEVAL_DOCUMENT")
    print(f"Generated second embedding with {len(embedding_3072)} dimensions")
    
    try:
        doc_id_2 = db_manager.add_document_chunk(
            owner_id=8,
            patient_id=14,
            title="Test Document 3072 dims",
            text=doc_text_3072,
            embedding=embedding_3072
        )
        print(f"✅ Successfully added document with {len(embedding_3072)} dimensions")
    except Exception as e:
        print(f"❌ Failed to add second document: {e}")
        return False
    
    # Test retrieval with query
    query_text = "Find test documents"
    query_embedding = embedder.generate_single_embedding(query_text, "RETRIEVAL_QUERY")
    print(f"Generated query embedding with {len(query_embedding)} dimensions")
    
    try:
        results = db_manager.retrieve_similar_documents(
            owner_id=8,
            query=query_text,
            patient_id=14,
            k=5
        )
        print(f"✅ Successfully retrieved {len(results)} documents")
        for result in results:
            print(f"  - Doc ID: {result['id']}, Similarity: {result['similarity']:.4f}")
        return True
    except Exception as e:
        print(f"❌ Failed to retrieve documents: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_problematic_scenario()
    if success:
        print("\n🎉 The system can now handle the problematic scenario!")
        print("The 'different vector dimensions' error should be resolved!")
    else:
        print("\n❌ The test failed.")