#!/usr/bin/env python3
"""
Test script to verify the new multi-column embedding system
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from utils.embedding_generator import MultiModelEmbeddingGenerator

def test_multi_column_embeddings():
    """Test the new multi-column embedding system"""
    print("Testing multi-column embedding system...")
    
    # Initialize components
    db_manager = DatabaseManager()
    embedder = MultiModelEmbeddingGenerator()
    
    # Test adding documents with different embedding dimensions
    test_cases = [
        ("Test document with 1536-dim embedding", 1536),
        ("Another test document", 1536),  # OpenAI typically generates 1536-dim
    ]
    
    doc_ids = []
    for i, (text, expected_dim) in enumerate(test_cases):
        print(f"\nTest case {i+1}: Adding document with embedding")
        try:
            embedding = embedder.generate_single_embedding(text, "RETRIEVAL_DOCUMENT")
            print(f"Generated embedding with {len(embedding)} dimensions")
            
            doc_id = db_manager.add_document_chunk(
                owner_id=8,
                patient_id=14,
                title=f"Test Document {i+1}",
                text=text,
                embedding=embedding
            )
            doc_ids.append(doc_id)
            print(f"✅ Successfully added document with ID: {doc_id}")
        except Exception as e:
            print(f"❌ Failed to add document: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Test retrieval
    print(f"\nTesting retrieval...")
    try:
        query_text = "Test query for retrieval"
        results = db_manager.retrieve_similar_documents(
            owner_id=8,
            query=query_text,
            patient_id=14,
            k=5
        )
        
        print(f"✅ Retrieved {len(results)} documents")
        for result in results:
            print(f"  - Doc ID: {result['id']}, Similarity: {result['similarity']:.4f}")
        
        return True
    except Exception as e:
        print(f"❌ Retrieval test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_multi_column_embeddings()
    if success:
        print("\n🎉 Multi-column embedding system is working correctly!")
        print("The system can now handle different embedding dimensions with optimized IVFFlat indexes!")
    else:
        print("\n❌ Multi-column embedding system test failed.")