"""
Gerador de embeddings local usando sentence-transformers
Alternativa quando as APIs do Google Gemini e OpenAI não estão disponíveis
"""
import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)

class LocalEmbeddingGenerator:
    """Gera embeddings localmente usando sentence-transformers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Inicializa o gerador de embeddings local
        
        Args:
            model_name: Nome do modelo sentence-transformers a usar
        """
        self.model = None
        self.model_name = model_name
        self.embedding_dim = 384  # Dimensão padrão do all-MiniLM-L6-v2
        
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Carregando modelo local: {model_name}")
            self.model = SentenceTransformer(model_name)
            
            # Ajustar dimensão baseado no modelo
            test_embedding = self.model.encode("test")
            self.embedding_dim = len(test_embedding)
            
            logger.info(f"✅ Modelo local carregado com sucesso! Dimensão: {self.embedding_dim}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo local: {e}")
            self.model = None
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Gera embedding para um texto
        
        Args:
            text: Texto para gerar embedding
            
        Returns:
            Lista de floats representando o embedding
        """
        if not self.model:
            raise ValueError("Modelo local não está disponível")
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Normalizar para ter dimensão 1536 (compatível com OpenAI)
            if len(embedding) != 1536:
                # Pad com zeros ou truncar
                if len(embedding) < 1536:
                    embedding = np.pad(embedding, (0, 1536 - len(embedding)), mode='constant')
                else:
                    embedding = embedding[:1536]
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Erro ao gerar embedding local: {e}")
            raise
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos
        
        Args:
            texts: Lista de textos
            
        Returns:
            Lista de embeddings
        """
        if not self.model:
            raise ValueError("Modelo local não está disponível")
        
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            
            # Normalizar dimensões
            normalized_embeddings = []
            for embedding in embeddings:
                if len(embedding) != 1536:
                    if len(embedding) < 1536:
                        embedding = np.pad(embedding, (0, 1536 - len(embedding)), mode='constant')
                    else:
                        embedding = embedding[:1536]
                normalized_embeddings.append(embedding.tolist())
            
            return normalized_embeddings
            
        except Exception as e:
            logger.error(f"Erro ao gerar embeddings em batch: {e}")
            raise
    
    def is_available(self) -> bool:
        """Verifica se o modelo local está disponível"""
        return self.model is not None
