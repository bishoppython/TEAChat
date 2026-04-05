#!/usr/bin/env python3
"""
Test script to verify that the embedding dimension detection works correctly
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.embedding_generator import MultiModelEmbeddingGenerator

def test_embedding_dimension_detection():
    """Test that embedding dimensions are detected and cached correctly"""
    print("Testing embedding dimension detection...")
    
    # Initialize the embedding generator
    embedder = MultiModelEmbeddingGenerator()
    
    # Test generating an embedding
    test_text = "This is a test document for embedding dimension detection."
    embedding = embedder.generate_single_embedding(test_text, "RETRIEVAL_DOCUMENT")
    
    print(f"Generated embedding with {len(embedding)} dimensions")
    print(f"First 5 values: {embedding[:5]}")
    
    # Check detected dimensions
    detected_dims = embedder.get_detected_dimensions()
    print(f"Detected dimensions: {detected_dims}")
    
    # Check provider info
    provider_info = embedder.get_current_provider_info()
    print(f"Provider info: {provider_info}")
    
    # Generate another embedding to test consistency
    embedding2 = embedder.generate_single_embedding("Another test document", "RETRIEVAL_DOCUMENT")
    print(f"Second embedding dimensions: {len(embedding2)}")
    
    # Verify dimensions are consistent
    if len(embedding) == len(embedding2):
        print("✅ Embedding dimensions are consistent")
    else:
        print("❌ Embedding dimensions are inconsistent")
        return False
    
    print("✅ Test passed!")
    return True

if __name__ == "__main__":
    test_embedding_dimension_detection()