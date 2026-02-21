"""
Módulo de cálculo de métricas para o sistema de IA clínica
Implementa métricas de qualidade para avaliação de respostas RAG
"""
import numpy as np
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import cosine
import nltk
from nltk.tokenize import sent_tokenize
from collections import Counter
import math

# Tente importar bibliotecas opcionais
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Transformers não disponível. Algumas métricas avançadas não estarão disponíveis.")

try:
    import evaluate
    EVALUATE_AVAILABLE = True
except ImportError:
    EVALUATE_AVAILABLE = False
    print("Evaluate não disponível. Algumas métricas não estarão disponíveis.")


class MetricsCalculator:
    """
    Classe para cálculo de métricas de qualidade para o sistema RAG clínico
    """
    
    def __init__(self):
        self.tokenizer = None
        self.qa_pipeline = None
        
        # Inicializar recursos do NLTK se disponíveis
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        
        try:
            nltk.data.find('tokenizers/punkt_tab')
        except LookupError:
            nltk.download('punkt_tab')
    
    def calculate_latency_metrics(self, start_time: float, end_time: float) -> Dict[str, float]:
        """
        Calcula métricas de latência
        """
        latency = end_time - start_time
        return {
            "latency_seconds": latency,
            "latency_milliseconds": latency * 1000
        }
    
    def calculate_cost_metrics(self, input_tokens: int, output_tokens: int, model_name: str) -> Dict[str, float]:
        """
        Calcula métricas de custo baseado em tokens usados
        """
        # Preços por 1M de tokens (em dólares)
        # Fonte: preços aproximados de 2024
        pricing = {
            # Modelos OpenAI
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            "gpt-3.5-turbo-0125": {"input": 0.50, "output": 1.50},
            "gpt-4": {"input": 30.00, "output": 60.00},
            "gpt-4-0613": {"input": 30.00, "output": 60.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-4o": {"input": 5.00, "output": 15.00},

            # Modelos Gemini
            "gemini-pro": {"input": 0.50, "output": 1.50},
            "gemini-2.5-flash-lite": {"input": 0.075, "output": 0.30},
            "gemini-2.5-pro": {"input": 1.00, "output": 2.00},

            # Modelos de embeddings
            "text-embedding-004": {"input": 0.025, "output": 0.025},  # Embeddings
            "text-embedding-3-large": {"input": 0.13, "output": 0.13},
            "text-embedding-3-small": {"input": 0.02, "output": 0.02},

            # Modelos alternativos
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
            "claude-3-sonnet": {"input": 3.00, "output": 15.00},
            "claude-3-opus": {"input": 15.00, "output": 75.00}
        }

        model_pricing = pricing.get(model_name, {"input": 0.50, "output": 1.50})

        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
        total_cost = input_cost + output_cost

        return {
            "model_name": model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(total_cost, 6),
            "cost_per_thousand_tokens": round((total_cost / (input_tokens + output_tokens)) * 1000, 8) if (input_tokens + output_tokens) > 0 else 0.0
        }
    
    def calculate_semantic_similarity(self, text1: str, text2: str, embedding_func=None) -> float:
        """
        Calcula similaridade semântica entre dois textos usando embeddings
        """
        if embedding_func is None:
            # Placeholder - usar embeddings reais no sistema
            # Por enquanto, retorna uma similaridade básica baseada em overlap
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 and not words2:
                return 1.0
            if not words1 or not words2:
                return 0.0
                
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            jaccard_similarity = len(intersection) / len(union)
            return jaccard_similarity
        else:
            # Usar embeddings reais
            emb1 = embedding_func(text1)
            emb2 = embedding_func(text2)
            
            if isinstance(emb1, list):
                emb1 = np.array(emb1).reshape(1, -1)
            if isinstance(emb2, list):
                emb2 = np.array(emb2).reshape(1, -1)
                
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)
    
    def calculate_precision_recall_f1(self, retrieved_docs: List[Dict], relevant_docs: List[str],
                                    threshold: float = 0.5) -> Dict[str, float]:
        """
        Calcula precision, recall e F1 para documentos recuperados
        """
        if not relevant_docs:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "true_positives": 0, "false_positives": 0, "false_negatives": 0}

        # Supondo que relevant_docs contenha IDs ou títulos dos documentos relevantes
        retrieved_ids = {doc.get('id') or doc.get('title') for doc in retrieved_docs if doc.get('id') or doc.get('title')}
        relevant_ids = set(relevant_docs)

        # Calcular verdadeiros positivos
        tp = len(retrieved_ids.intersection(relevant_ids))
        fp = len(retrieved_ids) - tp
        fn = len(relevant_ids) - tp

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "retrieved_count": len(retrieved_ids),
            "relevant_count": len(relevant_ids)
        }
    
    def calculate_faithfulness(self, response: str, context: str, embedding_func=None) -> Dict[str, Any]:
        """
        Calcula a fidelidade da resposta ao contexto fornecido
        """
        # Dividir a resposta em sentenças
        sentences = sent_tokenize(response)

        if not sentences:
            return {
                "faithfulness_score": 0.0,
                "statements_count": 0,
                "supported_statements": 0,
                "unsupported_statements": 0,
                "details": []
            }

        supported_statements = 0
        total_statements = len(sentences)
        details = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Verificar se a sentença está apoiada pelo contexto
            if embedding_func:
                # Usar similaridade semântica
                similarity = self.calculate_semantic_similarity(sentence, context, embedding_func)
                is_supported = similarity > 0.3  # Threshold para considerar como apoiado
                support_score = similarity
            else:
                # Usar overlap de palavras como fallback
                sentence_words = set(re.sub(r'[^\w\s]', '', sentence.lower()).split())
                context_words = set(re.sub(r'[^\w\s]', '', context.lower()).split())

                if sentence_words and context_words:
                    overlap = len(sentence_words.intersection(context_words))
                    total_unique = len(sentence_words.union(context_words))
                    support_score = overlap / total_unique if total_unique > 0 else 0.0
                    is_supported = support_score > 0.1  # Threshold mais baixo para overlap
                else:
                    support_score = 0.0
                    is_supported = False

            if is_supported:
                supported_statements += 1

            details.append({
                "sentence": sentence[:100] + "..." if len(sentence) > 100 else sentence,
                "support_score": round(support_score, 3),
                "is_supported": is_supported
            })

        faithfulness_score = supported_statements / total_statements if total_statements > 0 else 0.0

        return {
            "faithfulness_score": faithfulness_score,
            "statements_count": total_statements,
            "supported_statements": supported_statements,
            "unsupported_statements": total_statements - supported_statements,
            "details": details
        }
    
    def calculate_answer_relevance(self, question: str, answer: str, embedding_func=None) -> Dict[str, float]:
        """
        Calcula a relevância da resposta para a pergunta
        """
        if not question or not answer:
            return {
                "relevance_score": 0.0,
                "semantic_similarity": 0.0,
                "keyword_overlap": 0.0
            }

        # Calcular similaridade semântica
        semantic_similarity = self.calculate_semantic_similarity(question, answer, embedding_func)

        # Calcular overlap de palavras-chave
        question_words = set(re.sub(r'[^\w\s]', '', question.lower()).split())
        answer_words = set(re.sub(r'[^\w\s]', '', answer.lower()).split())

        if question_words and answer_words:
            intersection = question_words.intersection(answer_words)
            union = question_words.union(answer_words)
            keyword_overlap = len(intersection) / len(union)
        else:
            keyword_overlap = 0.0

        # Combinar métricas para uma pontuação geral de relevância
        combined_relevance = (semantic_similarity * 0.7 + keyword_overlap * 0.3)

        return {
            "relevance_score": round(combined_relevance, 3),
            "semantic_similarity": round(semantic_similarity, 3),
            "keyword_overlap": round(keyword_overlap, 3)
        }

    def calculate_context_relevance(self, question: str, context: str, embedding_func=None) -> Dict[str, float]:
        """
        Calcula a relevância do contexto para a pergunta
        """
        if not question or not context:
            return {
                "relevance_score": 0.0,
                "semantic_similarity": 0.0,
                "keyword_overlap": 0.0
            }

        # Calcular similaridade semântica
        semantic_similarity = self.calculate_semantic_similarity(question, context, embedding_func)

        # Calcular overlap de palavras-chave
        question_words = set(re.sub(r'[^\w\s]', '', question.lower()).split())
        context_words = set(re.sub(r'[^\w\s]', '', context.lower()).split())

        if question_words and context_words:
            intersection = question_words.intersection(context_words)
            union = question_words.union(context_words)
            keyword_overlap = len(intersection) / len(union)
        else:
            keyword_overlap = 0.0

        # Combinar métricas para uma pontuação geral de relevância
        combined_relevance = (semantic_similarity * 0.7 + keyword_overlap * 0.3)

        return {
            "relevance_score": round(combined_relevance, 3),
            "semantic_similarity": round(semantic_similarity, 3),
            "keyword_overlap": round(keyword_overlap, 3)
        }
    
    def calculate_ndcg_at_k(self, ranked_results: List[Dict], relevant_items: List[str], k: int = 10) -> Dict[str, float]:
        """
        Calcula NDCG@k (Normalized Discounted Cumulative Gain)
        ranked_results: lista de documentos rankeados [{'id': ..., 'relevance_score': ...}]
        relevant_items: lista de IDs de itens relevantes
        """
        if not ranked_results or not relevant_items:
            return {
                "ndcg_score": 0.0,
                "dcg": 0.0,
                "idcg": 0.0,
                "k": k
            }

        # Limitar ao top-k
        ranked_results = ranked_results[:k]

        # Calcular DCG (Discounted Cumulative Gain)
        dcg = 0.0
        for i, item in enumerate(ranked_results):
            rank = i + 1
            item_id = item.get('id')
            relevance = 1 if item_id in relevant_items else 0
            dcg += relevance / math.log2(rank + 1) if rank > 1 else relevance

        # Calcular IDCG (Ideal DCG)
        # Ideal ranking: todos os itens relevantes no início
        ideal_relevance_scores = []
        for i in range(min(len(relevant_items), k)):
            ideal_relevance_scores.append(1)  # Supondo relevância binária

        idcg = 0.0
        for i, relevance in enumerate(ideal_relevance_scores):
            rank = i + 1
            idcg += relevance / math.log2(rank + 1) if rank > 1 else relevance

        # Calcular NDCG
        ndcg = dcg / idcg if idcg > 0 else 0.0

        return {
            "ndcg_score": round(ndcg, 3),
            "dcg": round(dcg, 3),
            "idcg": round(idcg, 3),
            "k": k,
            "retrieved_count": len(ranked_results),
            "relevant_in_top_k": sum(1 for item in ranked_results if item.get('id') in relevant_items)
        }
    
    def calculate_readability_metrics(self, text: str) -> Dict[str, float]:
        """
        Calcula métricas de legibilidade automática
        """
        if not text:
            return {
                "flesch_reading_ease": 0.0,
                "flesch_kincaid_grade": 0.0,
                "smog_index": 0.0,
                "coleman_liau_index": 0.0,
                "automated_readability_index": 0.0,
                "avg_sentence_length": 0.0,
                "avg_word_length": 0.0,
                "complex_words_ratio": 0.0,
                "readability_level": "Muito Difícil"
            }

        sentences = sent_tokenize(text)
        words = re.findall(r'\b\w+\b', text.lower())
        characters = len(re.sub(r'\s', '', text))  # Contar caracteres excluindo espaços

        if not sentences or not words:
            return {
                "flesch_reading_ease": 0.0,
                "flesch_kincaid_grade": 0.0,
                "smog_index": 0.0,
                "coleman_liau_index": 0.0,
                "automated_readability_index": 0.0,
                "avg_sentence_length": 0.0,
                "avg_word_length": 0.0,
                "complex_words_ratio": 0.0,
                "readability_level": "Muito Difícil"
            }

        # Calcular estatísticas básicas
        num_sentences = len(sentences)
        num_words = len(words)
        num_syllables = sum(self._count_syllables(word) for word in words)

        avg_sentence_length = num_words / num_sentences if num_sentences > 0 else 0
        avg_word_length = sum(len(word) for word in words) / num_words if num_words > 0 else 0

        # Palavras complexas (> 3 sílabas)
        complex_words = [word for word in words if self._count_syllables(word) > 3]
        complex_words_ratio = len(complex_words) / num_words if num_words > 0 else 0

        # Flesch Reading Ease
        # Formula: 206.835 - (1.015 × ASL) - (84.6 × ASW)
        # ASL = Average Sentence Length (words per sentence)
        # ASW = Average Syllables per Word
        avg_syllables_per_word = num_syllables / num_words if num_words > 0 else 0
        flesch_reading_ease = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)

        # Flesch-Kincaid Grade Level
        # Formula: (0.39 × ASL) + (11.8 × ASW) - 15.59
        flesch_kincaid_grade = (0.39 * avg_sentence_length) + (11.8 * avg_syllables_per_word) - 15.59

        # SMOG Index
        # Formula: 1.0430 * √(polysyllables * 30/sentences) + 3.1291
        # Polysyllables = palavras com 3+ sílabas
        if num_sentences > 0:
            smog_poly = len([word for word in words if self._count_syllables(word) >= 3])
            smog_index = 1.043 * math.sqrt(smog_poly * (30 / num_sentences)) + 3.1291
        else:
            smog_index = 0.0

        # Coleman-Liau Index
        # Formula: (0.0588 * L) - (0.296 * S) - 15.8
        # L = letras por 100 palavras, S = sentenças por 100 palavras
        if num_words > 0:
            letters_per_100_words = (characters / num_words) * 100
            sentences_per_100_words = (num_sentences / num_words) * 100
            coleman_liau_index = (0.0588 * letters_per_100_words) - (0.296 * sentences_per_100_words) - 15.8
        else:
            coleman_liau_index = 0.0

        # Automated Readability Index
        # Formula: (4.71 * (characters/words)) + (0.5 * (words/sentences)) - 21.43
        if num_words > 0 and num_sentences > 0:
            automated_readability_index = (4.71 * (characters / num_words)) + (0.5 * (num_words / num_sentences)) - 21.43
        else:
            automated_readability_index = 0.0

        # Determinar nível de legibilidade
        if flesch_reading_ease >= 90:
            readability_level = "Muito Fácil"
        elif flesch_reading_ease >= 80:
            readability_level = "Fácil"
        elif flesch_reading_ease >= 70:
            readability_level = "Razoavelmente Fácil"
        elif flesch_reading_ease >= 60:
            readability_level = "Standard"
        elif flesch_reading_ease >= 50:
            readability_level = "Um Pouco Difícil"
        elif flesch_reading_ease >= 30:
            readability_level = "Difícil"
        else:
            readability_level = "Muito Difícil"

        return {
            "flesch_reading_ease": round(flesch_reading_ease, 2),
            "flesch_kincaid_grade": round(flesch_kincaid_grade, 2),
            "smog_index": round(smog_index, 2),
            "coleman_liau_index": round(coleman_liau_index, 2),
            "automated_readability_index": round(automated_readability_index, 2),
            "avg_sentence_length": round(avg_sentence_length, 2),
            "avg_word_length": round(avg_word_length, 2),
            "complex_words_ratio": round(complex_words_ratio, 3),
            "readability_level": readability_level
        }
    
    def _count_syllables(self, word: str) -> int:
        """
        Conta o número aproximado de sílabas em uma palavra
        """
        vowels = "aeiouy"
        word = word.lower()
        syllable_count = 0
        prev_was_vowel = False
        
        for i, char in enumerate(word):
            is_vowel = char in vowels
            
            # Contar mudança de vogal para consoante como final de sílaba
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            
            prev_was_vowel = is_vowel
        
        # Palavras terminadas em 'e' geralmente têm uma sílaba a menos
        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1
        
        # Cada palavra tem pelo menos uma sílaba
        return max(1, syllable_count)
    
    def calculate_binary_acceptance_rate(self, responses: List[Dict[str, Any]], 
                                       evaluator_func=None) -> Dict[str, float]:
        """
        Calcula taxa de aceitação binária (útil/não útil) de respostas
        """
        if not responses:
            return {"acceptance_rate": 0.0, "total_responses": 0, "accepted_responses": 0}
        
        accepted_count = 0
        total_count = len(responses)
        
        for response in responses:
            if evaluator_func:
                is_accepted = evaluator_func(response)
            else:
                # Critério padrão: respostas com mais de 20 caracteres e menos de 80% de stop words
                answer = response.get('response', '')
                question = response.get('query', '')
                
                is_accepted = self._default_acceptance_criterion(answer, question)
            
            if is_accepted:
                accepted_count += 1
        
        acceptance_rate = accepted_count / total_count if total_count > 0 else 0.0
        
        return {
            "acceptance_rate": acceptance_rate,
            "total_responses": total_count,
            "accepted_responses": accepted_count,
            "rejected_responses": total_count - accepted_count
        }
    
    def _default_acceptance_criterion(self, answer: str, question: str) -> bool:
        """
        Critério padrão para aceitação de resposta
        """
        if len(answer) < 20:
            return False
        
        # Verificar se a resposta não é apenas repetição da pergunta
        if question.lower() in answer.lower():
            return False
        
        # Verificar se tem conteúdo substancial
        words = answer.split()
        unique_words = set(word.lower() for word in words)
        
        # Se a maioria das palavras são stopwords ou muito curtas, pode ser uma resposta ruim
        meaningful_words = [word for word in unique_words if len(word) > 3]
        if len(meaningful_words) / len(unique_words) < 0.5:
            return False
        
        return True
    
    def calculate_comprehensive_metrics(self, query: str, response: str, retrieved_docs: List[Dict], 
                                     context: str, embedding_func=None, relevant_docs: List[str] = None) -> Dict[str, Any]:
        """
        Calcula um conjunto abrangente de métricas
        """
        start_time = time.time()
        
        # Calcular métricas individuais
        answer_relevance = self.calculate_answer_relevance(query, response, embedding_func)
        context_relevance = self.calculate_context_relevance(query, context, embedding_func)
        faithfulness = self.calculate_faithfulness(response, context, embedding_func)
        readability = self.calculate_readability_metrics(response)
        
        # Calcular métricas de retrieval se documentos relevantes forem fornecidos
        retrieval_metrics = {}
        if relevant_docs:
            retrieval_metrics = self.calculate_precision_recall_f1(retrieved_docs, relevant_docs)
        
        # Calcular NDCG se rankings estiverem disponíveis
        ndcg_score = 0.0
        if retrieved_docs and relevant_docs:
            ndcg_score = self.calculate_ndcg_at_k(retrieved_docs, relevant_docs, k=5)
        
        end_time = time.time()
        latency_metrics = self.calculate_latency_metrics(start_time, end_time)
        
        # Calcular uma pontuação geral de qualidade (média ponderada)
        weights = {
            "answer_relevance": 0.2,
            "faithfulness": 0.2,
            "context_relevance": 0.15,
            "readability": 0.1,  # Normalizado para contribuir proporcionalmente
            "retrieval_f1": 0.2 if retrieval_metrics else 0.0,
            "ndcg": 0.15
        }

        # Obter os valores das métricas (agora que são dicionários)
        answer_relevance_score = answer_relevance.get("relevance_score", 0.0) if isinstance(answer_relevance, dict) else answer_relevance
        context_relevance_score = context_relevance.get("relevance_score", 0.0) if isinstance(context_relevance, dict) else context_relevance

        # Normalizar pontuação de legibilidade (converter Flesch Reading Ease para escala 0-1)
        normalized_readability = max(0, min(1, (readability["flesch_reading_ease"] + 15) / 121.835))

        overall_quality_score = (
            weights["answer_relevance"] * answer_relevance_score +
            weights["faithfulness"] * faithfulness["faithfulness_score"] +
            weights["context_relevance"] * context_relevance_score +
            weights["readability"] * normalized_readability +
            weights["retrieval_f1"] * retrieval_metrics.get("f1", 0) +
            weights["ndcg"] * ndcg_score
        )
        
        return {
            "overall_quality_score": round(overall_quality_score, 3),
            "answer_relevance": answer_relevance,  # Já é um dicionário
            "context_relevance": context_relevance,  # Já é um dicionário
            "faithfulness": faithfulness,
            "readability": readability,
            "retrieval_metrics": retrieval_metrics,
            "ndcg_at_k": {"ndcg_score": round(ndcg_score, 3)},  # Corrigido para retornar dicionário
            "latency_metrics": latency_metrics,
            "timestamp": time.time()
        }


# Instância global para uso no sistema
metrics_calculator = MetricsCalculator()