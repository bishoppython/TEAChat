"""
Módulo de embeddings para sistema RAG de psicologia clínica
Lida com geração e gerenciamento de embeddings usando Google Gemini com OpenAI como fallback,
e embeddings locais como fallback final
"""
import os
import logging
from typing import List, Dict, Any, Union, Tuple
import google.genai as genai
import numpy as np
from scipy.spatial.distance import cosine
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import openai
from openai import OpenAI

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tentar importar embeddings locais
try:
    from .local_embeddings import LocalEmbeddingGenerator
    LOCAL_EMBEDDINGS_AVAILABLE = True
except ImportError:
    LOCAL_EMBEDDINGS_AVAILABLE = False
    logger.warning("Embeddings locais não disponíveis")


class MultiModelEmbeddingGenerator:
    """
    Classe para lidar com geração de embeddings usando API Google Gemini com OpenAI como fallback
    """

    def __init__(self, google_api_key: str = None, openai_api_key: str = None,
                 google_model_name: str = "models/embedding-001",
                 openai_model_name: str = "text-embedding-3-large"):
        """
        Inicializar o gerador de embeddings

        :param google_api_key: Chave da API Google (se não fornecida, usará variável de ambiente GOOGLE_API_KEY)
        :param openai_api_key: Chave da API OpenAI (se não fornecida, usará variável de ambiente OPENAI_API_KEY)
        :param google_model_name: Nome do modelo de embedding Google a usar
        :param openai_model_name: Nome do modelo de embedding OpenAI a usar
        """
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        # Inicializar Google Gemini se chave estiver disponível
        self.use_google = False
        if self.google_api_key:
            try:
                # For the new google-genai library, we might need to create a client
                from google.genai import GenerativeModel, embedding
                self.google_client = embedding
                self.google_model_name = google_model_name
                self.use_google = True
                logger.info("Google GenAI API configured successfully")
            except ImportError:
                try:
                    # Fallback to the old configuration method if the new API is different
                    genai.configure(api_key=self.google_api_key)
                    self.google_model_name = google_model_name
                    self.use_google = True
                    logger.info("Google GenAI API configured successfully")
                except Exception as e:
                    logger.warning(f"Could not configure Google GenAI API: {e}")
            except Exception as e:
                logger.warning(f"Could not configure Google GenAI API: {e}")

        # Inicializar OpenAI se chave estiver disponível
        self.use_openai = False
        if self.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                self.openai_model_name = openai_model_name
                self.use_openai = True
                logger.info("API OpenAI configurada com sucesso")
            except Exception as e:
                logger.warning(f"Não foi possível configurar API OpenAI: {e}")


        # Inicializar embeddings locais como fallback final
        self.local_generator = None
        self.use_local = False
        if LOCAL_EMBEDDINGS_AVAILABLE:
            try:
                self.local_generator = LocalEmbeddingGenerator()
                if self.local_generator.is_available():
                    self.use_local = True
                    logger.info("✅ Embeddings locais configurados como fallback")
            except Exception as e:
                logger.warning(f"Não foi possível configurar embeddings locais: {e}")

        if not self.use_google and not self.use_openai and not self.use_local:
            logger.warning("⚠️  Nenhum serviço de embedding disponível! O sistema usará busca de texto como fallback.")

        # Configurar pool de threads para geração concorrente de embeddings
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Adicionar cache para dimensões detectadas automaticamente
        self.detected_dimensions = {}
        self.provider_info = {}

    def generate_single_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """
        Generate embedding for a single text using OpenAI as primary, with Google and local as fallbacks

        :param text: Input text to embed
        :param task_type: Type of task (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, etc.)
        :return: Embedding as a list of floats
        """
        # Try OpenAI first
        if self.use_openai:
            try:
                response = self.openai_client.embeddings.create(
                    input=text,
                    model=self.openai_model_name
                )
                embedding = response.data[0].embedding
                logger.info(f"Embedding generated successfully with OpenAI. Dimensions: {len(embedding)}")

                # Cache the dimensions and provider info
                self.detected_dimensions['openai'] = len(embedding)
                self.provider_info['openai'] = {'model': self.openai_model_name, 'dimensions': len(embedding)}

                return embedding
            except Exception as e:
                logger.warning(f"OpenAI failed to generate embedding: {str(e)}")

        # If OpenAI failed or is not configured, try Google
        if self.use_google:
            try:
                # Try the new google-genai API first
                if hasattr(self, 'google_client'):
                    # Use the new API
                    result = self.google_client.embed_content(
                        model=self.google_model_name,
                        content=[text],
                        task_type=task_type.lower().replace("_", "")
                    )
                    embedding = result['embedding'][0] if isinstance(result, dict) else result.embeddings[0]
                else:
                    # Fallback to the old API
                    # Convert task type to Gemini format
                    gemini_task_type = task_type.lower().replace("_", "")
                    result = genai.embed_content(
                        model=self.google_model_name,
                        content=[text],
                        task_type=gemini_task_type
                    )
                    embedding = result['embedding'][0]  # Assuming single embedding returned
                
                logger.info(f"Embedding generated successfully with Google GenAI. Dimensions: {len(embedding)}")

                # Cache the dimensions and provider info
                self.detected_dimensions['google'] = len(embedding)
                self.provider_info['google'] = {'model': self.google_model_name, 'dimensions': len(embedding)}

                return embedding
            except Exception as e:
                logger.error(f"Google GenAI failed to generate embedding: {str(e)}")

        # If all primary options failed, try local embeddings as final fallback
        if self.use_local:
            try:
                logger.info("🔄 Trying local embeddings as fallback...")
                local_embedding = self.local_generator.generate_embedding(text)
                if local_embedding is not None:
                    logger.info(f"Embedding generated successfully with local model. Dimensions: {len(local_embedding)}")

                    # Cache the dimensions and provider info
                    self.detected_dimensions['local'] = len(local_embedding)
                    self.provider_info['local'] = {'dimensions': len(local_embedding)}

                    return local_embedding
            except Exception as e:
                logger.error(f"Local embeddings failed: {str(e)}")

        # If all options failed, return a default embedding vector
        logger.error("All embedding providers failed")
        return self._get_default_embedding_vector()

    def _get_default_embedding_vector(self) -> List[float]:
        """
        Get a default embedding vector based on the most commonly detected dimensions.
        If no dimensions have been detected yet, use 768 (Google Gemini default).
        """
        # If we have detected dimensions from any provider, use the most common one
        if self.detected_dimensions:
            # Find the most common dimension size
            from collections import Counter
            dimension_counts = Counter(self.detected_dimensions.values())
            most_common_dim = dimension_counts.most_common(1)[0][0]
            logger.info(f"Using most common dimension size: {most_common_dim}")
            return [0.0] * most_common_dim
        else:
            # Default to 768 dimensions (Google Gemini) if no dimensions have been detected yet
            logger.info("Using default dimension size: 768")
            return [0.0] * 768

    def get_current_provider_info(self) -> Dict[str, Any]:
        """
        Get information about the current embedding provider and dimensions
        """
        return self.provider_info

    def get_detected_dimensions(self) -> Dict[str, int]:
        """
        Get the dimensions detected for each provider
        """
        return self.detected_dimensions

    async def generate_embedding_async(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """
        Async version of embedding generation
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self.generate_single_embedding, text, task_type
        )

    def generate_embeddings_batch(self, texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
        """
        Generate embeddings for a batch of texts

        :param texts: List of input texts to embed
        :param task_type: Type of task (RETRIEVAL_DOCUMENT, RETRIEVAL_QUERY, etc.)
        :return: List of embeddings (each embedding is a list of floats)
        """
        embeddings = []
        for text in texts:
            embedding = self.generate_single_embedding(text, task_type)
            embeddings.append(embedding)
        return embeddings

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings

        :param embedding1: First embedding
        :param embedding2: Second embedding
        :return: Cosine similarity score between -1 and 1
        """
        try:
            # Convert to numpy arrays for computation
            emb1 = np.array(embedding1)
            emb2 = np.array(embedding2)

            # Compute cosine similarity
            similarity = 1 - cosine(emb1, emb2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0

    def rank_documents_by_similarity(self, query_embedding: List[float],
                                   document_embeddings: List[List[float]],
                                   document_ids: List[Any],
                                   threshold: float = 0.3) -> List[Tuple[Any, float]]:
        """
        Rank documents by similarity to query embedding

        :param query_embedding: Embedding of the query
        :param document_embeddings: List of document embeddings
        :param document_ids: List of document identifiers corresponding to embeddings
        :param threshold: Minimum similarity threshold
        :return: List of tuples (document_id, similarity_score) sorted by similarity
        """
        similarities = []

        for doc_id, doc_emb in zip(document_ids, document_embeddings):
            sim = self.compute_similarity(query_embedding, doc_emb)
            if sim >= threshold:
                similarities.append((doc_id, sim))

        # Sort by similarity in descending order
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities

class CachedEmbeddingGenerator(MultiModelEmbeddingGenerator):
    """
    Extension of MultiModelEmbeddingGenerator with caching functionality
    """

    def __init__(self, google_api_key: str = None, openai_api_key: str = None,
                 google_model_name: str = "models/embedding-001",
                 #openai_model_name: str = "text-embedding-3-small", # <- Leve e Rápido
                 openai_model_name: str = "text-embedding-3-large", # <-- Robusto e +preciso text-embedding-3-large
                 cache_size: int = 10000):
        super().__init__(google_api_key, openai_api_key, google_model_name, openai_model_name)
        self.cache = {}
        self.cache_order = []  # To track order for LRU
        self.cache_size = cache_size

    def generate_single_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """
        Generate embedding with caching
        """
        cache_key = f"{text[:100]}_{task_type}"  # Create a cache key (truncated text + task type)

        # Check if result is in cache
        if cache_key in self.cache:
            # Move to end (most recently used)
            self.cache_order.remove(cache_key)
            self.cache_order.append(cache_key)
            logger.debug(f"Cache hit for text: {text[:50]}...")
            return self.cache[cache_key]

        # Generate embedding using parent method
        result = super().generate_single_embedding(text, task_type)

        # Add to cache
        self.cache[cache_key] = result
        self.cache_order.append(cache_key)

        # Maintain cache size
        if len(self.cache) > self.cache_size:
            oldest_key = self.cache_order.pop(0)
            del self.cache[oldest_key]

        logger.debug(f"Generated and cached embedding for text: {text[:50]}...")
        return result

def example_usage():
    """
    Example of how to use the MultiModelEmbeddingGenerator
    """
    try:
        # Initialize the generator (keys will be loaded from environment variables)
        embedder = MultiModelEmbeddingGenerator()

        # Generate embedding for a sample text
        text = "Patient demonstrates hypersensitivity to auditory stimuli"
        embedding = embedder.generate_single_embedding(text, "RETRIEVAL_DOCUMENT")

        print(f"Generated embedding with {len(embedding)} dimensions")
        print(f"Sample embedding values: {embedding[:5]}...")

        # Generate embedding for query
        query = "What accommodations should be made for auditory hypersensitivity?"
        query_embedding = embedder.generate_single_embedding(query, "RETRIEVAL_QUERY")

        print(f"Query embedding with {len(query_embedding)} dimensions")

        # Compute similarity
        similarity = embedder.compute_similarity(embedding, query_embedding)
        print(f"Similarity between text and query: {similarity}")

    except ValueError as e:
        print(f"Error: {e}")
        print("Please ensure you have set either GOOGLE_API_KEY or OPENAI_API_KEY environment variables")

if __name__ == "__main__":
    example_usage()