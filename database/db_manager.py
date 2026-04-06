"""
Database module for the clinical psychology RAG system
Handles PostgreSQL connection with pgvector support
"""
import os
import logging
import json
from typing import Optional, List, Dict, Any
from uuid import UUID
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import register_adapter
import numpy as np
from contextlib import contextmanager
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
import json

# Import the multi-model embedding generator
from utils.embedding_generator import MultiModelEmbeddingGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, connection_string: Optional[str] = None, embedding_generator: Optional[MultiModelEmbeddingGenerator] = None):
        """
        Initialize database manager with connection string
        If not provided, will try to get from environment variable DATABASE_URL
        """
        self.connection_string = connection_string or os.getenv("DATABASE_URL")
        if not self.connection_string:
            raise ValueError("DATABASE_URL environment variable is required")

        # Use provided embedding generator or create a new one
        if embedding_generator:
            self.embedding_generator = embedding_generator
        else:
            # Initialize with multi-tier fallback (Google -> OpenAI -> Local)
            self.embedding_generator = MultiModelEmbeddingGenerator()

        # Ensure the embedding column supports variable dimensions
        try:
            self.update_embedding_column_type()
        except Exception as e:
            logger.warning(f"Could not update embedding column type: {e}")

        # Ensure the vector index exists
        try:
            self.ensure_vector_index_exists()
        except Exception as e:
            logger.warning(f"Could not ensure vector index exists: {e}")

        # Check for dimension inconsistencies
        try:
            self.rebuild_vector_index_if_needed()
        except Exception as e:
            logger.warning(f"Could not check embedding dimensions: {e}")

        logger.info("✅ DatabaseManager initialized with multi-tier embedding fallback")

    def _safe_json_dumps(self, obj):
        """
        Método seguro para converter objetos em JSON para evitar erros de sintaxe
        """
        import json
        try:
            return json.dumps(obj, default=str, ensure_ascii=False)
        except TypeError:
            # Se houver erro de tipo, converter para string
            return json.dumps(str(obj), ensure_ascii=False)

    def store_query_metrics(self, query_id: int, metrics: Dict[str, Any]):
        """
        Armazena métricas de qualidade para uma consulta específica
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Preparar os dados para inserção
                    cursor.execute("""
                        INSERT INTO query_quality_metrics (
                            query_id,
                            latency_seconds, response_time_ms,
                            model_name, input_tokens, output_tokens, total_tokens,
                            input_cost_usd, output_cost_usd, total_cost_usd, cost_per_thousand_tokens,
                            retrieval_precision, retrieval_recall, retrieval_f1,
                            retrieval_true_positives, retrieval_false_positives, retrieval_false_negatives,
                            retrieval_retrieved_count, retrieval_relevant_count,
                            faithfulness_score, faithfulness_statements_count,
                            faithfulness_supported_statements, faithfulness_unsupported_statements,
                            answer_relevance_score, answer_semantic_similarity, answer_keyword_overlap,
                            context_relevance_score, context_semantic_similarity, context_keyword_overlap,
                            ndcg_score, ndcg_dcg, ndcg_idcg, ndcg_k, ndcg_retrieved_count, ndcg_relevant_in_top_k,
                            flesch_reading_ease, flesch_kincaid_grade, smog_index, coleman_liau_index,
                            automated_readability_index, avg_sentence_length, avg_word_length, complex_words_ratio,
                            readability_level, overall_quality_score, faithfulness_details, metric_details
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s
                        )
                    """, (
                        # Basic info
                        query_id,

                        # Latency metrics
                        metrics.get('latency_metrics', {}).get('latency_seconds'),
                        metrics.get('latency_metrics', {}).get('latency_milliseconds'),

                        # Cost metrics
                        metrics.get('cost_metrics', {}).get('model_name'),
                        metrics.get('cost_metrics', {}).get('input_tokens'),
                        metrics.get('cost_metrics', {}).get('output_tokens'),
                        metrics.get('cost_metrics', {}).get('total_tokens'),
                        metrics.get('cost_metrics', {}).get('input_cost_usd'),
                        metrics.get('cost_metrics', {}).get('output_cost_usd'),
                        metrics.get('cost_metrics', {}).get('total_cost_usd'),
                        metrics.get('cost_metrics', {}).get('cost_per_thousand_tokens'),

                        # Retrieval metrics
                        metrics.get('retrieval_metrics', {}).get('precision'),
                        metrics.get('retrieval_metrics', {}).get('recall'),
                        metrics.get('retrieval_metrics', {}).get('f1'),
                        metrics.get('retrieval_metrics', {}).get('true_positives'),
                        metrics.get('retrieval_metrics', {}).get('false_positives'),
                        metrics.get('retrieval_metrics', {}).get('false_negatives'),
                        metrics.get('retrieval_metrics', {}).get('retrieved_count'),
                        metrics.get('retrieval_metrics', {}).get('relevant_count'),

                        # Faithfulness metrics
                        metrics.get('faithfulness', {}).get('faithfulness_score'),
                        metrics.get('faithfulness', {}).get('statements_count'),
                        metrics.get('faithfulness', {}).get('supported_statements'),
                        metrics.get('faithfulness', {}).get('unsupported_statements'),

                        # Answer relevance metrics
                        metrics.get('answer_relevance', {}).get('relevance_score'),
                        metrics.get('answer_relevance', {}).get('semantic_similarity'),
                        metrics.get('answer_relevance', {}).get('keyword_overlap'),

                        # Context relevance metrics
                        metrics.get('context_relevance', {}).get('relevance_score'),
                        metrics.get('context_relevance', {}).get('semantic_similarity'),
                        metrics.get('context_relevance', {}).get('keyword_overlap'),

                        # NDCG metrics
                        metrics.get('ndcg_at_k', {}).get('ndcg_score'),
                        metrics.get('ndcg_at_k', {}).get('dcg'),
                        metrics.get('ndcg_at_k', {}).get('idcg'),
                        metrics.get('ndcg_at_k', {}).get('k'),
                        metrics.get('ndcg_at_k', {}).get('retrieved_count'),
                        metrics.get('ndcg_at_k', {}).get('relevant_in_top_k'),

                        # Readability metrics
                        metrics.get('readability', {}).get('flesch_reading_ease'),
                        metrics.get('readability', {}).get('flesch_kincaid_grade'),
                        metrics.get('readability', {}).get('smog_index'),
                        metrics.get('readability', {}).get('coleman_liau_index'),
                        metrics.get('readability', {}).get('automated_readability_index'),
                        metrics.get('readability', {}).get('avg_sentence_length'),
                        metrics.get('readability', {}).get('avg_word_length'),
                        metrics.get('readability', {}).get('complex_words_ratio'),
                        metrics.get('readability', {}).get('readability_level'),

                        # Overall quality score
                        metrics.get('overall_quality_score'),

                        # Detailed faithfulness info
                        self._safe_json_dumps(metrics.get('faithfulness', {}).get('details', [])),

                        # Additional metric details
                        self._safe_json_dumps(metrics) if metrics else None
                    ))

                    conn.commit()
                    logger.info(f"Métricas armazenadas para query_id: {query_id}")
        except psycopg2.errors.UndefinedTable:
            logger.warning("Tabela query_quality_metrics não existe, pulando armazenamento de métricas detalhadas")
        except Exception as e:
            logger.error(f"Falha ao armazenar métricas de qualidade: {e}")
            raise

    def store_binary_acceptance_rating(self, query_id: int, rating: bool, rater_id: int = None, notes: str = None):
        """
        Armazena avaliação binária de aceitação (útil/não útil) para uma consulta
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO binary_acceptance_ratings (query_id, rating, rater_id, notes)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (query_id, rater_id) DO UPDATE
                    SET rating = EXCLUDED.rating, rating_timestamp = CURRENT_TIMESTAMP, notes = EXCLUDED.notes
                """, (query_id, rating, rater_id, notes))

                conn.commit()
                logger.info(f"Avaliação binária armazenada para query_id: {query_id}, rating: {rating}")

    def store_qualitative_error_analysis(self, query_id: int, error_category: str, severity_level: str,
                                      description: str, suggested_fix: str = None, analyzed_by: int = None):
        """
        Armazena análise qualitativa de erros para uma consulta
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO qualitative_error_analysis (
                        query_id, error_category, severity_level, description, suggested_fix, analyzed_by
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (query_id, error_category, severity_level, description, suggested_fix, analyzed_by))

                conn.commit()
                logger.info(f"Análise qualitativa de erro armazenada para query_id: {query_id}")

    def get_aggregated_metrics(self, start_date: str = None, end_date: str = None, model_name: str = None):
        """
        Retorna métricas agregadas para um período específico
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT
                        COUNT(*) as total_queries,
                        AVG(overall_quality_score) as avg_quality_score,
                        AVG(latency_seconds) as avg_latency,
                        AVG(retrieval_f1) as avg_f1_score,
                        AVG(faithfulness_score) as avg_faithfulness,
                        AVG(answer_relevance_score) as avg_answer_relevance,
                        AVG(context_relevance_score) as avg_context_relevance,
                        AVG(ndcg_score) as avg_ndcg,
                        SUM(total_cost_usd) as total_cost
                    FROM query_quality_metrics qqm
                    JOIN audit_log al ON qqm.query_id = al.id
                """

                conditions = []
                params = []

                if start_date:
                    conditions.append("al.created_at >= %s")
                    params.append(start_date)

                if end_date:
                    conditions.append("al.created_at <= %s")
                    params.append(end_date)

                if model_name:
                    conditions.append("qqm.model_name = %s")
                    params.append(model_name)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                cursor.execute(query, params)
                result = cursor.fetchone()

                return {
                    "total_queries": result[0],
                    "avg_quality_score": float(result[1]) if result[1] is not None else 0.0,
                    "avg_latency": float(result[2]) if result[2] is not None else 0.0,
                    "avg_f1_score": float(result[3]) if result[3] is not None else 0.0,
                    "avg_faithfulness": float(result[4]) if result[4] is not None else 0.0,
                    "avg_answer_relevance": float(result[5]) if result[5] is not None else 0.0,
                    "avg_context_relevance": float(result[6]) if result[6] is not None else 0.0,
                    "avg_ndcg": float(result[7]) if result[7] is not None else 0.0,
                    "total_cost": float(result[8]) if result[8] is not None else 0.0
                }

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def create_tables(self):
        """Execute the schema SQL to create tables"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Read and execute schema file
                with open('database/schema.sql', 'r') as schema_file:
                    schema_sql = schema_file.read()

                # Only execute the schema creation part, not the sample data
                # Split by the sample inserts and take only the schema part
                schema_parts = schema_sql.split('-- Sample insertions for initial setup')
                schema_only = schema_parts[0]

                cursor.execute(schema_only)
                conn.commit()
                logger.info("Tables created successfully")

    def update_embedding_column_type(self):
        """Update the embedding column to support variable dimensions"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check if the column exists and needs to be updated
                cursor.execute("""
                    SELECT data_type, udt_name
                    FROM information_schema.columns
                    WHERE table_name = 'documents'
                    AND column_name = 'embedding'
                """)
                result = cursor.fetchone()

                if result:
                    data_type, udt_name = result
                    if udt_name != 'vector':  # If it's not already a variable vector
                        logger.info("Updating embedding column to support variable dimensions...")
                        cursor.execute("ALTER TABLE documents ALTER COLUMN embedding TYPE vector USING embedding::vector")
                        conn.commit()
                        logger.info("Embedding column updated to support variable dimensions")
                    else:
                        logger.info("Embedding column already supports variable dimensions")
                else:
                    logger.warning("Embedding column not found in documents table")

    def ensure_vector_index_exists(self):
        """Ensure the vector indexes exist and are properly configured for each dimension"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # Check if the vector indexes exist for each dimension
                    indexes_to_check = [
                        'idx_documents_embedding_768',
                        'idx_documents_embedding_1536',
                        'idx_documents_embedding_3072'
                    ]

                    for index_name in indexes_to_check:
                        cursor.execute("""
                            SELECT indexname
                            FROM pg_indexes
                            WHERE tablename = 'documents'
                            AND indexname = %s
                        """, (index_name,))
                        index_exists = cursor.fetchone()

                        if not index_exists:
                            logger.info(f"Vector index {index_name} does not exist, it should be created via schema.sql")
                        else:
                            logger.info(f"Vector index {index_name} already exists")

                except Exception as e:
                    logger.warning(f"Could not check vector indexes: {e}")
                    # Continue without the index if it fails, as it's not critical for functionality

    def rebuild_vector_index_if_needed(self):
        """Check embedding distribution across different dimension columns"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    # Check how many documents exist in each embedding dimension column
                    cursor.execute("""
                        SELECT
                            COUNT(CASE WHEN embedding_768 IS NOT NULL THEN 1 END) as count_768,
                            COUNT(CASE WHEN embedding_1536 IS NOT NULL THEN 1 END) as count_1536,
                            COUNT(CASE WHEN embedding_3072 IS NOT NULL THEN 1 END) as count_3072
                        FROM documents
                    """)
                    results = cursor.fetchone()

                    if results:
                        count_768, count_1536, count_3072 = results
                        logger.info(f"Embedding distribution - 768d: {count_768}, 1536d: {count_1536}, 3072d: {count_3072}")
                    else:
                        logger.info("No embeddings found in database")

                except Exception as e:
                    logger.warning(f"Could not check embedding distribution: {e}")

    def create_user(self, username: str, full_name: str, email: str, role: str = 'therapist') -> int:
        """Create a new user and return the user ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (username, full_name, email, role)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (username, full_name, email, role))

                user_id = cursor.fetchone()[0]
                conn.commit()
                return user_id

    # def create_patient(self, patient_id: Optional[str], owner_id: int, first_name: str, last_name: str = "",
    #                   date_of_birth: str = None, diagnosis: str = "", age: int = None,
    #                   neurotype: str = "", level: str = "", description: str = "") -> int:
    #     """Create a new patient and return the patient ID"""
    #     with self.get_connection() as conn:
    #         with conn.cursor() as cursor:
    #             # Verificar se a coluna patient_id existe na tabela
    #             cursor.execute("""
    #                 SELECT column_name
    #                 FROM information_schema.columns
    #                 WHERE table_name = 'patients' AND column_name = 'patient_id'
    #             """)
    #             col_exists = cursor.fetchone()

    #             if col_exists:
    #                 # Coluna patient_id existe, usar a versão completa
    #                 cursor.execute("""
    #                     INSERT INTO patients (patient_id, owner_id, first_name, last_name, date_of_birth, diagnosis, age, neurotype, level, description)
    #                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    #                     RETURNING id
    #                 """, (patient_id, owner_id, first_name, last_name, date_of_birth, diagnosis, age, neurotype, level, description))
    #             else:
    #                 # Coluna patient_id não existe, usar versão compatível com tabelas antigas
    #                 cursor.execute("""
    #                     INSERT INTO patients (owner_id, first_name, last_name, date_of_birth, diagnosis, age, neurotype, level, description)
    #                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    #                     RETURNING id
    #                 """, (owner_id, first_name, last_name, date_of_birth, diagnosis, age, neurotype, level, description))

    #             patient_db_id = cursor.fetchone()[0]
    #             conn.commit()
    #             return patient_db_id

    def create_patient(self, patient_id: Optional[str], owner_id: int, first_name: str, last_name: str = "",
                      date_of_birth: str = None, diagnosis: str = "", age: int = None,
                      neurotype: str = "", level: str = "", description: str = "") -> int:
        """Create a new patient and return the patient ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Verificar se a coluna patient_id existe na tabela
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'patients' AND column_name = 'patient_id'
                """)
                col_exists = cursor.fetchone()

                if col_exists:
                    # Coluna patient_id existe, usar a versão completa
                    cursor.execute("""
                        INSERT INTO patients (id, owner_id, first_name, last_name, date_of_birth, diagnosis, age, neurotype, level, description)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) # Editei aqui 18.12 - 11:33
                        RETURNING id
                    """, (patient_id, owner_id, first_name, last_name, date_of_birth, diagnosis, age, neurotype, level, description))
                else:
                    # Coluna patient_id não existe, usar versão compatível com tabelas antigas
                    # Nesse caso, não passamos o patient_id nos valores
                    cursor.execute("""
                        INSERT INTO patients (owner_id, first_name, last_name, date_of_birth, diagnosis, age, neurotype, level, description)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (owner_id, first_name, last_name, date_of_birth, diagnosis, age, neurotype, level, description))

                patient_db_id = cursor.fetchone()[0]
                conn.commit()
                return patient_db_id

    def add_document_chunk(self, owner_id: int, patient_id: int, title: str, text: str,
                          source_type: str = "note", chunk_order: int = 0, chunk_id: str = None,
                          metadata: Dict[str, Any] = None, embedding: List[float] = None,
                          document_history_id: Optional[int] = None) -> str:
        """
        Add a document chunk to the database with optional embedding
        """
        logger.info(f"Adicionando chunk de documento: título='{title[:50]}...', owner_id={owner_id}, patient_id={patient_id}")

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Generate embedding if not provided
                if embedding is None:
                    logger.info("Gerando embedding para o chunk de documento...")
                    try:
                        # Use multi-tier embedding generator (Google -> OpenAI -> Local)
                        embedding = self.embedding_generator.generate_single_embedding(text, "RETRIEVAL_DOCUMENT")
                        logger.info(f"✅ Embedding gerado com sucesso. Tamanho: {len(embedding)}")
                    except Exception as e:
                        logger.error(f"Failed to generate embedding: {e}")
                        logger.warning("Continuando sem embedding - o documento ainda será armazenado, mas não será recuperável via busca semântica")

                # Determine which embedding column to use based on dimension
                embedding_768 = None
                embedding_1536 = None
                embedding_3072 = None
                embedding_str = None

                if embedding:
                    embedding_dimension = len(embedding)
                    embedding_str = "[" + ",".join([str(float(x)) for x in embedding]) + "]"
                    logger.debug(f"Embedding convertido para string: {embedding_str[:50]}...")

                    # Assign to appropriate column based on dimension
                    if embedding_dimension == 768:
                        embedding_768 = embedding_str
                    elif embedding_dimension == 1536:
                        embedding_1536 = embedding_str
                    elif embedding_dimension == 3072:
                        embedding_3072 = embedding_str
                    else:
                        # For other dimensions, use the closest available column or default to 1536
                        logger.warning(f"Embedding dimension {embedding_dimension} not supported by dedicated column, using 1536 column")
                        embedding_1536 = embedding_str

                # Default metadata if none provided
                if metadata is None:
                    metadata = {}

                # Add embedding dimension to metadata for tracking
                if embedding:
                    if metadata is None:
                        metadata = {}
                    metadata['embedding_dimension'] = len(embedding)

                logger.debug(f"Executando query de inserção com parâmetros: owner_id={owner_id}, patient_id={patient_id}")
                cursor.execute("""
                    INSERT INTO documents (owner_id, patient_id, title, text, source_type, chunk_order, chunk_id,
                                          embedding_768, embedding_1536, embedding_3072, metadata, document_history_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (owner_id, patient_id, title, text, source_type, chunk_order, chunk_id,
                      embedding_768, embedding_1536, embedding_3072, json.dumps(metadata), document_history_id))

                doc_id = cursor.fetchone()[0]
                conn.commit()

                logger.info(f"Chunk de documento adicionado com sucesso. ID: {doc_id}")
                return str(doc_id)

    def add_knowledge_base_entry(self, owner_id: int, patient_id: int = None, text: str = "",
                                 metadata: Dict[str, Any] = None, embedding: List[float] = None) -> str:
        """
        Add a knowledge base entry to the database with optional embedding.
        This is a more generic entry point for vectorized data.
        """
        logger.info(f"Adding knowledge base entry for owner_id={owner_id}, patient_id={patient_id}")

        # Anonimizar o conteúdo do texto antes de adicionar
        from anonimizer_functions import process_anonymization
        anonymized_text = process_anonymization("TEXT", text)

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Generate embedding if not provided
                if embedding is None:
                    logger.info("Generating embedding for knowledge base entry...")
                    try:
                        embedding = self.embedding_generator.generate_single_embedding(anonymized_text, "RETRIEVAL_DOCUMENT")
                        logger.info(f"✅ Embedding generated successfully. Size: {len(embedding)}")
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for knowledge base entry: {e}")
                        logger.warning("Continuing without embedding - entry will be stored, but not retrievable via semantic search")

                # Determine which embedding column to use based on dimension
                embedding_768 = None
                embedding_1536 = None
                embedding_3072 = None
                embedding_str = None

                if embedding:
                    embedding_dimension = len(embedding)
                    embedding_str = "[" + ",".join([str(float(x)) for x in embedding]) + "]"
                    logger.debug(f"Embedding converted to string: {embedding_str[:50]}...")

                    # Assign to appropriate column based on dimension
                    if embedding_dimension == 768:
                        embedding_768 = embedding_str
                    elif embedding_dimension == 1536:
                        embedding_1536 = embedding_str
                    elif embedding_dimension == 3072:
                        embedding_3072 = embedding_str
                    else:
                        # For other dimensions, use the closest available column or default to 1536
                        logger.warning(f"Embedding dimension {embedding_dimension} not supported by dedicated column, using 1536 column")
                        embedding_1536 = embedding_str

                # Default metadata if none provided
                if metadata is None:
                    metadata = {}

                logger.debug(f"Executing knowledge base insertion query with parameters: owner_id={owner_id}, patient_id={patient_id}")
                cursor.execute("""
                    INSERT INTO knowledge_base (owner_id, patient_id, content, embedding_768, embedding_1536, embedding_3072, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (owner_id, patient_id, anonymized_text, embedding_768, embedding_1536, embedding_3072, json.dumps(metadata)))

                entry_id = cursor.fetchone()[0]
                conn.commit()

                logger.info(f"Knowledge base entry added successfully. ID: {entry_id}")
                return str(entry_id)

    def retrieve_similar_documents(self, owner_id: int, query: str, patient_id: int = None,
                                  k: int = 4, min_similarity: float = 0.5) -> List[Dict]:
        """
        Retrieve top-k similar documents for a given query using vector similarity
        Optionally filter by patient
        """
        logger.info(f"Buscando documentos similares para query: '{query[:50]}...' com owner_id: {owner_id}, patient_id: {patient_id}")

        # Generate embedding for query using multi-tier fallback
        try:
            query_embedding = self.embedding_generator.generate_single_embedding(query, "RETRIEVAL_QUERY")
            logger.info(f"✅ Embedding da query gerado com sucesso. Tamanho: {len(query_embedding)}")

            # Determine which embedding column to use based on query embedding dimension
            query_embedding_str = "[" + ",".join([str(float(x)) for x in query_embedding]) + "]"
            query_dimension = len(query_embedding)

            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Build query based on the dimension of the query embedding
                    if query_dimension == 768:
                        embedding_column = "embedding_768"
                    elif query_dimension == 1536:
                        embedding_column = "embedding_1536"
                    elif query_dimension == 3072:
                        embedding_column = "embedding_3072"
                    else:
                        # For other dimensions, default to 1536 or use a more sophisticated approach
                        logger.warning(f"Query embedding dimension {query_dimension} not supported by dedicated column, using 1536 column")
                        embedding_column = "embedding_1536"
                        query_dimension = 1536  # Update to match the column we'll use

                    # Build query with optional patient filter
                    base_query = f"""
                        SELECT d.id, d.title, d.text, d.chunk_order, d.metadata,
                               (1 - (d.{embedding_column} <=> %s::vector)) AS similarity
                        FROM documents d
                        WHERE d.owner_id = %s
                        AND d.{embedding_column} IS NOT NULL  -- Only match documents with embeddings of this dimension
                        AND (1 - (d.{embedding_column} <=> %s::vector)) > %s
                    """
                    params = [query_embedding_str, owner_id, query_embedding_str, min_similarity]

                    if patient_id is not None:
                        # Verificar se a coluna patient_id existe no esquema do banco de dados
                        cursor.execute("""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_name = 'documents' AND column_name = 'patient_id'
                        """)
                        col_exists = cursor.fetchone()

                        if col_exists:
                            base_query += " AND d.patient_id = %s"
                            params.append(patient_id)
                            logger.info(f"Filtrando por patient_id: {patient_id}")
                        else:
                            logger.warning(f"Coluna patient_id não encontrada na tabela documents. Filtro ignorado para patient_id {patient_id}")
                    else:
                        logger.info("Sem filtro por patient_id")

                    base_query += f" ORDER BY d.{embedding_column} <=> %s::vector LIMIT %s"
                    params.extend([query_embedding_str, k])

                    logger.info(f"Executando query SQL com parâmetros owner_id: {owner_id}, min_similarity: {min_similarity}, k: {k}")
                    cursor.execute(base_query, params)
                    results = cursor.fetchall()

                    logger.info(f"Recuperados {len(results)} documentos do banco de dados")

                    # Convert to proper format
                    documents = []
                    for row in results:
                        logger.debug(f"Documento encontrado: ID={row['id']}, título='{row['title']}', similaridade={row['similarity']}")
                        documents.append({
                            'id': row['id'],
                            'title': row['title'],
                            'text': row['text'],
                            'chunk_order': row['chunk_order'],
                            'metadata': row['metadata'],
                            'similarity': float(row['similarity'])
                        })

                    logger.info(f"Total de {len(documents)} documentos retornados após processamento")

                    # If no documents were found, try text-based search as fallback (instead of dimension fallback)
                    if len(documents) == 0:
                        logger.info("Nenhum documento encontrado com similaridade vetorial. Tentando busca textual como fallback...")
                        return self._retrieve_similar_documents_text_fallback(owner_id, query, patient_id, k)

                    return documents
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            logger.info("Tentando busca por palavras-chave como fallback...")

            # Fallback: busca por palavras-chave
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Build query with text search as fallback
                    base_query = """
                        SELECT d.id, d.title, d.text, d.chunk_order, d.metadata,
                               0.0 AS similarity  -- Default similarity when no embedding
                        FROM documents d
                        WHERE d.owner_id = %s
                        AND (d.text ILIKE %s OR d.title ILIKE %s)
                    """
                    search_param = f"%{query}%"
                    params = [owner_id, search_param, search_param]

                    if patient_id is not None:
                        # Verificar se a coluna patient_id existe no esquema do banco de dados (fallback)
                        cursor.execute("""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_name = 'documents' AND column_name = 'patient_id'
                        """)
                        col_exists = cursor.fetchone()

                        if col_exists:
                            base_query += " AND d.patient_id = %s"
                            params.append(patient_id)
                            logger.info(f"Filtrando por patient_id (fallback): {patient_id}")
                        else:
                            logger.warning(f"Coluna patient_id não encontrada na tabela documents. Filtro ignorado para patient_id {patient_id}")
                    else:
                        logger.info("Sem filtro por patient_id")

                    base_query += " LIMIT %s"
                    params.append(k)

                    logger.info(f"Executando query SQL de fallback com parâmetros owner_id: {owner_id}, k: {k}")
                    cursor.execute(base_query, params)
                    results = cursor.fetchall()

                    logger.info(f"Recuperados {len(results)} documentos do banco de dados via busca textual")

                    # Convert to proper format
                    documents = []
                    for row in results:
                        logger.debug(f"Documento encontrado (fallback): ID={row['id']}, título='{row['title']}'")
                        documents.append({
                            'id': row['id'],
                            'title': row['title'],
                            'text': row['text'],
                            'chunk_order': row['chunk_order'],
                            'metadata': row['metadata'],
                            'similarity': float(row['similarity'])
                        })

                    logger.info(f"Total de {len(documents)} documentos retornados via fallback")
                    return documents

    def _retrieve_similar_documents_fallback_dimensionless(self, owner_id: int, query: str, patient_id: int = None,
                                                          k: int = 4, min_similarity: float = 0.5) -> List[Dict]:
        """
        Fallback method to retrieve similar documents without dimension filtering
        This is used when no documents with matching dimensions are found
        """
        logger.info("Executando busca sem filtro de dimensão como fallback...")

        # Generate embedding for query using multi-tier fallback
        query_embedding = self.embedding_generator.generate_single_embedding(query, "RETRIEVAL_QUERY")
        embedding_str = "[" + ",".join([str(float(x)) for x in query_embedding]) + "]"

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Build query with dimension filter to avoid vector dimension mismatch
                base_query = """
                    SELECT d.id, d.title, d.text, d.chunk_order, d.metadata,
                           (1 - (d.embedding <=> %s::vector)) AS similarity
                    FROM documents d
                    WHERE d.owner_id = %s
                    AND vector_dims(d.embedding) = %s  -- Match only embeddings with same dimension
                    AND (1 - (d.embedding <=> %s::vector)) > %s
                """
                params = [embedding_str, owner_id, len(query_embedding), embedding_str, min_similarity]

                if patient_id is not None:
                    # Verificar se a coluna patient_id existe no esquema do banco de dados
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'documents' AND column_name = 'patient_id'
                    """)
                    col_exists = cursor.fetchone()

                    if col_exists:
                        base_query += " AND d.patient_id = %s"
                        params.append(patient_id)
                        logger.info(f"Filtrando por patient_id: {patient_id}")
                    else:
                        logger.warning(f"Coluna patient_id não encontrada na tabela documents. Filtro ignorado para patient_id {patient_id}")
                else:
                    logger.info("Sem filtro por patient_id")

                base_query += " ORDER BY d.embedding <=> %s::vector LIMIT %s"
                params.extend([embedding_str, k])

                logger.info(f"Executando query SQL de fallback com filtro de dimensão com parâmetros owner_id: {owner_id}, min_similarity: {min_similarity}, k: {k}")
                cursor.execute(base_query, params)
                results = cursor.fetchall()

                logger.info(f"Recuperados {len(results)} documentos do banco de dados via fallback com filtro de dimensão")

                # Convert to proper format
                documents = []
                for row in results:
                    logger.debug(f"Documento encontrado (fallback com dimensão): ID={row['id']}, título='{row['title']}', similaridade={row['similarity']}")
                    documents.append({
                        'id': row['id'],
                        'title': row['title'],
                        'text': row['text'],
                        'chunk_order': row['chunk_order'],
                        'metadata': row['metadata'],
                        'similarity': float(row['similarity'])
                    })

                logger.info(f"Total de {len(documents)} documentos retornados via fallback com filtro de dimensão")

                # If still no results, try the text-based fallback
                if len(documents) == 0:
                    logger.info("Nenhum documento encontrado mesmo com filtro de dimensão. Tentando busca textual...")
                    return self._retrieve_similar_documents_text_fallback(owner_id, query, patient_id, k)

                return documents

    # Método de fallback por dimensão removido conforme nova arquitetura
    # O sistema agora usa um único modelo de embedding consistente (OpenAI text-embedding-3-large)
    # e busca textual como fallback quando não há correspondência vetorial

    def _retrieve_similar_documents_text_fallback(self, owner_id: int, query: str, patient_id: int = None,
                                                 k: int = 4) -> List[Dict]:
        """
        Text-based fallback method when vector similarity fails
        """
        logger.info("Executando busca textual como fallback...")

        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Build query with text search as fallback
                base_query = """
                    SELECT d.id, d.title, d.text, d.chunk_order, d.metadata,
                           0.0 AS similarity  -- Default similarity when no embedding
                    FROM documents d
                    WHERE d.owner_id = %s
                    AND (d.text ILIKE %s OR d.title ILIKE %s)
                """
                search_param = f"%{query}%"
                params = [owner_id, search_param, search_param]

                if patient_id is not None:
                    # Verificar se a coluna patient_id existe no esquema do banco de dados (fallback)
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'documents' AND column_name = 'patient_id'
                    """)
                    col_exists = cursor.fetchone()

                    if col_exists:
                        base_query += " AND d.patient_id = %s"
                        params.append(patient_id)
                        logger.info(f"Filtrando por patient_id (fallback textual): {patient_id}")
                    else:
                        logger.warning(f"Coluna patient_id não encontrada na tabela documents. Filtro ignorado para patient_id {patient_id}")
                else:
                    logger.info("Sem filtro por patient_id")

                base_query += " LIMIT %s"
                params.append(k)

                logger.info(f"Executando query SQL de fallback textual com parâmetros owner_id: {owner_id}, k: {k}")
                cursor.execute(base_query, params)
                results = cursor.fetchall()

                logger.info(f"Recuperados {len(results)} documentos do banco de dados via busca textual")

                # Convert to proper format
                documents = []
                for row in results:
                    logger.debug(f"Documento encontrado (fallback textual): ID={row['id']}, título='{row['title']}'")
                    documents.append({
                        'id': row['id'],
                        'title': row['title'],
                        'text': row['text'],
                        'chunk_order': row['chunk_order'],
                        'metadata': row['metadata'],
                        'similarity': float(row['similarity'])
                    })

                logger.info(f"Total de {len(documents)} documentos retornados via fallback textual")
                return documents

    def get_patient_info(self, owner_id: int, patient_id: int) -> Optional[Dict]:
        """Get patient information by patient_id (which refers to patients.id) for the specified owner"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM patients
                    WHERE id = %s AND owner_id = %s
                """, (patient_id, owner_id))

                result = cursor.fetchone()
                if result:
                    return dict(result)
                return None

    def get_patient_sensitivities(self, owner_id: int, patient_id: int) -> List[Dict]:
        """Get patient sensitivities by patient_id (which refers to patients.id) for the specified owner"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT ps.* FROM patient_sensitivities ps
                    JOIN patients p ON ps.patient_id = p.id
                    WHERE ps.patient_id = %s AND p.owner_id = %s
                """, (patient_id, owner_id))

                results = cursor.fetchall()
                return [dict(row) for row in results]

    def add_patient_sensitivity(self, owner_id: int, patient_id: int, sensitivity_type: str,
                                sensitivity_level: str, description: str) -> int:
        """Add a patient sensitivity record"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Verify that the patient belongs to the owner
                cursor.execute("""
                    SELECT id FROM patients
                    WHERE id = %s AND owner_id = %s
                """, (patient_id, owner_id))

                patient = cursor.fetchone()
                if not patient:
                    raise ValueError("Patient does not belong to the specified owner")

                # Insert the sensitivity record
                cursor.execute("""
                    INSERT INTO patient_sensitivities (patient_id, sensitivity_type, sensitivity_level, description)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (patient_id, sensitivity_type, sensitivity_level, description))

                sensitivity_id = cursor.fetchone()[0]
                conn.commit()

                return sensitivity_id

    def delete_patient_sensitivities(self, owner_id: int, patient_id: int) -> int:
        """Delete all sensitivities for a patient"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Verify that the patient belongs to the owner
                cursor.execute("""
                    SELECT id FROM patients
                    WHERE id = %s AND owner_id = %s
                """, (patient_id, owner_id))

                patient = cursor.fetchone()
                if not patient:
                    raise ValueError("Patient does not belong to the specified owner")

                # Delete all sensitivity records for this patient
                cursor.execute("""
                    DELETE FROM patient_sensitivities
                    WHERE patient_id = %s
                """, (patient_id,))

                deleted_count = cursor.rowcount
                conn.commit()

                return deleted_count

    def log_query_response(self, user_id: int, patient_id: int, query: str, response: str = None,
                          model_used: str = "gemini", tokens_used: int = 0, response_time_ms: int = 0):
        """Log a query and response for audit purposes"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO audit_log (user_id, patient_id, query, response, model_used, tokens_used, response_time_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (user_id, patient_id, query, response, model_used, tokens_used, response_time_ms))

                conn.commit()


    def document_exists(self, text: str, owner_id: int, patient_id: int) -> bool:
        """Check if a document with similar content already exists"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM documents
                    WHERE text = %s AND owner_id = %s AND patient_id = %s
                """, (text, owner_id, patient_id))

                count = cursor.fetchone()[0]
                return count > 0

    def update_user_password(self, user_id: int, password_hash: str):
        """Update user's password hash"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE users 
                    SET password_hash = %s 
                    WHERE id = %s
                """, (password_hash, user_id))
                conn.commit()

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user information by username"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, username, full_name, email, role, password_hash, created_at
                    FROM users
                    WHERE username = %s
                """, (username,))
                result = cursor.fetchone()
                if result:
                    return dict(result)
                return None

    def update_last_login(self, user_id: int):
        """Update the last login timestamp for a user"""
        # Esta é uma funcionalidade adicional que pode ser útil para controle de acesso
        pass

    def add_clinical_assessment(self, user_id: int, patient_id: int, query: str, response: str,
                                assessment_type: str = "clinical", confidence_score: float = 0.0,
                                processing_time: float = 0.0, model_used: str = "", tokens_used: int = 0) -> int:
        """Add a clinical assessment to the history"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO clinical_assessments
                    (user_id, patient_id, query, response, assessment_type, confidence_score,
                     processing_time, model_used, tokens_used)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, patient_id, query, response, assessment_type, confidence_score,
                      processing_time, model_used, tokens_used))

                assessment_id = cursor.fetchone()[0]
                conn.commit()
                return assessment_id

    def get_clinical_assessments(self, user_id: int, patient_id: Optional[int] = None,
                                 limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get clinical assessments for a user (excluding queries), optionally filtered by patient"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verify if clinical_assessments table exists
                cursor.execute("""
                    SELECT EXISTS (
                       SELECT FROM information_schema.tables
                       WHERE table_schema = 'public'
                       AND table_name = 'clinical_assessments'
                   );
                """)
                result = cursor.fetchone()
                table_exists = result['exists'] if result else False

                if not table_exists:
                    logger.warning("Table clinical_assessments does not exist")
                    return []

                query = """
                    SELECT ca.id, ca.user_id, ca.patient_id, ca.query, ca.response,
                           ca.assessment_type, ca.confidence_score, ca.processing_time,
                           ca.model_used, ca.tokens_used, ca.created_at
                    FROM clinical_assessments ca
                    WHERE ca.user_id = %s AND ca.assessment_type != 'query'
                """
                params = [user_id]

                if patient_id is not None:
                    query += " AND ca.patient_id = %s"
                    params.append(patient_id)

                query += " ORDER BY ca.created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cursor.execute(query, params)
                results = cursor.fetchall()

                # Garantir que campos None sejam convertidos para valores padrão
                processed_results = []
                for row in results:
                    processed_row = dict(row)
                    # Converter valores None para valores padrão
                    if processed_row['query'] is None:
                        processed_row['query'] = ''
                    if processed_row['response'] is None:
                        processed_row['response'] = ''
                    if processed_row['assessment_type'] is None:
                        processed_row['assessment_type'] = 'clinical'
                    if processed_row['model_used'] is None:
                        processed_row['model_used'] = 'N/A'
                    processed_results.append(processed_row)

                return processed_results

    def add_file_upload(self, user_id: int, patient_id: int, title: str, original_filename: str,
                        file_path: str = None, file_size: int = 0, file_type: str = "",
                        metadata: Dict = None, status: str = "active") -> int:
        """Add a file upload record to the history"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO file_uploads
                    (user_id, patient_id, title, original_filename, file_path, file_size, file_type, status, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, patient_id, title, original_filename, file_path, file_size,
                      file_type, status, json.dumps(metadata or {})))

                upload_id = cursor.fetchone()[0]
                conn.commit()
                return upload_id

    def get_file_uploads(self, user_id: int, patient_id: Optional[int] = None,
                         status: str = "active", limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get file uploads for a user, optionally filtered by patient and status"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verify if file_uploads table exists
                cursor.execute("""
                    SELECT EXISTS (
                       SELECT FROM information_schema.tables
                       WHERE table_schema = 'public'
                       AND table_name = 'file_uploads'
                   );
                """)
                result = cursor.fetchone()
                table_exists = result['exists'] if result else False

                if not table_exists:
                    logger.warning("Table file_uploads does not exist")
                    return []

                query = """
                    SELECT id, user_id, patient_id, title, original_filename, file_path,
                           file_size, file_type, upload_date, status, metadata
                    FROM file_uploads
                    WHERE user_id = %s
                """
                params = [user_id]

                if patient_id is not None:
                    query += " AND patient_id = %s"
                    params.append(patient_id)

                if status:
                    query += " AND status = %s"
                    params.append(status)

                query += " ORDER BY upload_date DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cursor.execute(query, params)
                results = cursor.fetchall()

                # Garantir que campos None sejam convertidos para valores padrão
                processed_results = []
                for row in results:
                    processed_row = dict(row)
                    # Converter valores None para valores padrão
                    if processed_row['title'] is None:
                        processed_row['title'] = ''
                    if processed_row['original_filename'] is None:
                        processed_row['original_filename'] = ''
                    if processed_row['file_path'] is None:
                        processed_row['file_path'] = ''
                    if processed_row['file_type'] is None:
                        processed_row['file_type'] = ''
                    processed_results.append(processed_row)

                return processed_results

    def update_file_upload(self, upload_id: int, user_id: int, title: str = None,
                          file_path: str = None, file_size: int = None,
                          file_type: str = None, status: str = None) -> bool:
        """Update a file upload record"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Build dynamic update query
                update_fields = []
                params = []

                if title is not None:
                    update_fields.append("title = %s")
                    params.append(title)
                if file_path is not None:
                    update_fields.append("file_path = %s")
                    params.append(file_path)
                if file_size is not None:
                    update_fields.append("file_size = %s")
                    params.append(file_size)
                if file_type is not None:
                    update_fields.append("file_type = %s")
                    params.append(file_type)
                if status is not None:
                    update_fields.append("status = %s")
                    params.append(status)

                if not update_fields:
                    return False  # Nothing to update

                query = f"""
                    UPDATE file_uploads
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                """
                params.extend([upload_id, user_id])

                cursor.execute(query, params)
                result = cursor.fetchone()
                conn.commit()

                return result is not None

    def delete_file_upload(self, upload_id: int, user_id: int) -> bool:
        """Mark a file upload as deleted (soft delete) and delete associated documents"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Primeiro, obter o nome do arquivo original para identificar os documentos associados
                cursor.execute("""
                    SELECT original_filename, patient_id FROM file_uploads
                    WHERE id = %s AND user_id = %s
                """, (upload_id, user_id))
                result = cursor.fetchone()

                if not result:
                    return False  # Upload não encontrado ou sem permissão

                original_filename, patient_id = result

                # Obter os documentos que serão excluídos para registrar no histórico
                cursor.execute("""
                    SELECT id, title, text, source_type, metadata FROM documents
                    WHERE owner_id = %s AND metadata->>'original_filename' = %s
                """, (user_id, original_filename))
                documents_to_delete = cursor.fetchall()

                # Registrar a exclusão de cada documento no histórico
                for doc in documents_to_delete:
                    doc_id, title, text_content, source_type, metadata = doc
                    # Adicionar entrada no histórico de documentos com action_type 'deleted'
                    cursor.execute("""
                        INSERT INTO document_history
                        (action_type, user_id, patient_id, title, text_content, source_type, metadata, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, ('deleted', user_id, patient_id, title, text_content, source_type,
                          json.dumps(metadata), 'active'))

                # Excluir documentos associados ao upload
                cursor.execute("""
                    DELETE FROM documents
                    WHERE owner_id = %s AND metadata->>'original_filename' = %s
                """, (user_id, original_filename))

                # Marcar o upload como excluído
                cursor.execute("""
                    UPDATE file_uploads
                    SET status = 'deleted'
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                """, (upload_id, user_id))

                result = cursor.fetchone()
                conn.commit()

                return result is not None

    def delete_documents_by_upload_filename(self, user_id: int, original_filename: str) -> int:
        """Delete all documents associated with a specific uploaded file, returning the number of deleted documents"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM documents
                    WHERE owner_id = %s AND metadata->>'original_filename' = %s
                """, (user_id, original_filename))

                deleted_count = cursor.rowcount
                conn.commit()

                return deleted_count

    def add_document_history(self, action_type: str,
                             user_id: int, patient_id: int, title: str = "",
                             text_content: str = "", source_type: str = "note",
                             metadata: Dict = None, old_values: Dict = None,
                             new_values: Dict = None, status: str = "active") -> int:
        """Add a document history record"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO document_history
                    (action_type, user_id, patient_id, title, text_content,
                     source_type, metadata, old_values, new_values, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (action_type, user_id, patient_id, title, text_content,
                      source_type, json.dumps(metadata or {}), json.dumps(old_values or {}),
                      json.dumps(new_values or {}), status))

                history_id = cursor.fetchone()[0]
                conn.commit()
                return history_id

    def update_document_history(self, history_id: int, user_id: int, title: str = None,
                               text_content: str = None, source_type: str = None,
                               metadata: Dict = None, status: str = None) -> bool:
        """Update a document history record"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Build dynamic update query
                update_fields = []
                params = []

                if title is not None:
                    update_fields.append("title = %s")
                    params.append(title)
                if text_content is not None:
                    update_fields.append("text_content = %s")
                    params.append(text_content)
                if source_type is not None:
                    update_fields.append("source_type = %s")
                    params.append(source_type)
                if metadata is not None:
                    update_fields.append("metadata = %s")
                    params.append(json.dumps(metadata))
                if status is not None:
                    update_fields.append("status = %s")
                    params.append(status)

                # Always update the updated_at timestamp
                update_fields.append("updated_at = CURRENT_TIMESTAMP")

                if not update_fields:
                    return False  # Nothing to update

                query = f"""
                    UPDATE document_history
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                """
                params.extend([history_id, user_id])

                cursor.execute(query, params)
                result = cursor.fetchone()
                conn.commit()

                return result is not None

    def delete_document_history(self, history_id: int, user_id: int) -> bool:
        """Delete a document history record"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM document_history
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                """, (history_id, user_id))

                result = cursor.fetchone()
                conn.commit()

                return result is not None

    def get_document_history(self, user_id: int, patient_id: Optional[int] = None,
                             action_type: Optional[str] = None, limit: int = 50,
                             offset: int = 0) -> List[Dict]:
        """Get document history for a user, optionally filtered by patient and action type"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verify if document_history table exists
                cursor.execute("""
                    SELECT EXISTS (
                       SELECT FROM information_schema.tables
                       WHERE table_schema = 'public'
                       AND table_name = 'document_history'
                   );
                """)
                result = cursor.fetchone()
                table_exists = result['exists'] if result else False

                if not table_exists:
                    logger.warning("Table document_history does not exist")
                    return []

                query = """
                    SELECT dh.id, dh.action_type, dh.user_id, dh.patient_id,
                           dh.title, dh.text_content, dh.source_type, dh.metadata,
                           dh.action_date, dh.status, dh.old_values, dh.new_values,
                           dh.action_performed_by
                    FROM document_history dh
                    WHERE dh.user_id = %s
                """
                params = [user_id]

                if patient_id is not None:
                    query += " AND dh.patient_id = %s"
                    params.append(patient_id)

                if action_type is not None:
                    query += " AND dh.action_type = %s"
                    params.append(action_type)

                query += " ORDER BY dh.action_date DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cursor.execute(query, params)
                results = cursor.fetchall()

                # Garantir que campos None sejam convertidos para valores padrão
                processed_results = []
                for row in results:
                    processed_row = dict(row)
                    # Converter valores None para valores padrão
                    if processed_row['title'] is None:
                        processed_row['title'] = ''
                    if processed_row['text_content'] is None:
                        processed_row['text_content'] = ''
                    if processed_row['source_type'] is None:
                        processed_row['source_type'] = 'note'
                    if processed_row['action_type'] is None:
                        processed_row['action_type'] = 'unknown'
                    if processed_row['status'] is None:
                        processed_row['status'] = 'active'
                    processed_results.append(processed_row)

                return processed_results

    def get_query_history(self, user_id: int, patient_id: Optional[int] = None,
                          limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get query history for a user, optionally filtered by patient (queries are stored as assessments with type 'query')"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Verify if clinical_assessments table exists
                cursor.execute("""
                    SELECT EXISTS (
                       SELECT FROM information_schema.tables
                       WHERE table_schema = 'public'
                       AND table_name = 'clinical_assessments'
                   );
                """)
                result = cursor.fetchone()
                table_exists = result['exists'] if result else False

                if not table_exists:
                    logger.warning("Table clinical_assessments does not exist")
                    return []

                query = """
                    SELECT ca.id, ca.user_id, ca.patient_id, ca.query, ca.response,
                           ca.assessment_type, ca.confidence_score, ca.processing_time,
                           ca.model_used, ca.tokens_used, ca.created_at
                    FROM clinical_assessments ca
                    WHERE ca.user_id = %s AND ca.assessment_type = 'query'
                """
                params = [user_id]

                if patient_id is not None:
                    query += " AND ca.patient_id = %s"
                    params.append(patient_id)

                query += " ORDER BY ca.created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cursor.execute(query, params)
                results = cursor.fetchall()

                # Garantir que campos None sejam convertidos para valores padrão
                processed_results = []
                for row in results:
                    processed_row = dict(row)
                    # Converter valores None para valores padrão
                    if processed_row['query'] is None:
                        processed_row['query'] = ''
                    if processed_row['response'] is None:
                        processed_row['response'] = ''
                    if processed_row['assessment_type'] is None:
                        processed_row['assessment_type'] = 'query'
                    if processed_row['model_used'] is None:
                        processed_row['model_used'] = 'N/A'
                    processed_results.append(processed_row)

                return processed_results

    def update_query_history(self, query_id: int, user_id: int, query_text: str = None,
                             response: str = None, assessment_type: str = None) -> bool:
        """Update a query history record"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Build dynamic update query
                update_fields = []
                params = []

                if query_text is not None:
                    update_fields.append("query = %s")
                    params.append(query_text)
                if response is not None:
                    update_fields.append("response = %s")
                    params.append(response)
                if assessment_type is not None:
                    update_fields.append("assessment_type = %s")
                    params.append(assessment_type)

                # Always update the updated_at timestamp
                update_fields.append("updated_at = CURRENT_TIMESTAMP")

                if not update_fields:
                    return False  # Nothing to update

                query = f"""
                    UPDATE clinical_assessments
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND user_id = %s AND assessment_type = 'query'
                    RETURNING id
                """
                params.extend([query_id, user_id])

                cursor.execute(query, params)
                result = cursor.fetchone()
                conn.commit()

                return result is not None

    def delete_query_history(self, query_id: int, user_id: int) -> bool:
        """Delete a query history record"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM clinical_assessments
                    WHERE id = %s AND user_id = %s AND assessment_type = 'query'
                    RETURNING id
                """, (query_id, user_id))

                result = cursor.fetchone()
                conn.commit()

                return result is not None

    def ensure_history_tables_exist(self):
        """Create history tables if they don't exist"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Create clinical_assessments table if not exists
                    # Note: We avoid direct REFERENCES to ensure tables are created even without foreign key constraints
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS clinical_assessments (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL,
                            patient_id INTEGER NOT NULL,
                            query TEXT NOT NULL,
                            response TEXT NOT NULL,
                            assessment_type VARCHAR(100) DEFAULT 'clinical',
                            confidence_score FLOAT DEFAULT 0.0,
                            processing_time FLOAT,
                            model_used VARCHAR(100),
                            tokens_used INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Create indexes for clinical_assessments if not exist
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_clinical_assessments_user_id ON clinical_assessments(user_id);
                        CREATE INDEX IF NOT EXISTS idx_clinical_assessments_patient_id ON clinical_assessments(patient_id);
                        CREATE INDEX IF NOT EXISTS idx_clinical_assessments_created_at ON clinical_assessments(created_at);
                    """)

                    # Create file_uploads table if not exists
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS file_uploads (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL,
                            patient_id INTEGER NOT NULL,
                            title VARCHAR(500),
                            original_filename VARCHAR(255) NOT NULL,
                            file_path VARCHAR(500),
                            file_size BIGINT,
                            file_type VARCHAR(100),
                            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            status VARCHAR(50) DEFAULT 'active',
                            metadata JSONB DEFAULT '{}',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Create indexes for file_uploads if not exist
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_file_uploads_user_id ON file_uploads(user_id);
                        CREATE INDEX IF NOT EXISTS idx_file_uploads_patient_id ON file_uploads(patient_id);
                        CREATE INDEX IF NOT EXISTS idx_file_uploads_upload_date ON file_uploads(upload_date);
                        CREATE INDEX IF NOT EXISTS idx_file_uploads_status ON file_uploads(status);
                    """)

                    # Create document_history table if not exists
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS document_history (
                            id SERIAL PRIMARY KEY,
                            action_type VARCHAR(50) NOT NULL,
                            user_id INTEGER NOT NULL,
                            patient_id INTEGER NOT NULL,
                            title VARCHAR(500),
                            text_content TEXT,
                            source_type VARCHAR(50) DEFAULT 'note',
                            metadata JSONB DEFAULT '{}',
                            action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            action_performed_by INTEGER,
                            old_values JSONB,
                            new_values JSONB,
                            status VARCHAR(50) DEFAULT 'active'
                        )
                    """)

                    # Create indexes for document_history if not exist
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_document_history_user_id ON document_history(user_id);
                        CREATE INDEX IF NOT EXISTS idx_document_history_patient_id ON document_history(patient_id);
                        CREATE INDEX IF NOT EXISTS idx_document_history_action_type ON document_history(action_type);
                        CREATE INDEX IF NOT EXISTS idx_document_history_action_date ON document_history(action_date);
                    """)

                    # Criar tabela de análise de evolução do paciente
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS patient_evolution_analysis (
                            id SERIAL PRIMARY KEY,
                            patient_id INTEGER NOT NULL,
                            owner_id INTEGER NOT NULL,
                            analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            evolution_score DECIMAL(5, 4),
                            evolution_pattern VARCHAR(50), -- 'positive', 'stagnant', 'negative', 'unknown'
                            session_count INTEGER,
                            clinical_notes TEXT,
                            recommendations JSONB,
                            alerts_generated JSONB,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)

                    # Criar índices para análise de evolução
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_patient_evolution_patient_id ON patient_evolution_analysis(patient_id);
                        CREATE INDEX IF NOT EXISTS idx_patient_evolution_owner_id ON patient_evolution_analysis(owner_id);
                        CREATE INDEX IF NOT EXISTS idx_patient_evolution_analysis_date ON patient_evolution_analysis(analysis_date);
                    """)

                    # Criar tabela de alertas inteligentes
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS smart_alerts (
                            id SERIAL PRIMARY KEY,
                            patient_id INTEGER NOT NULL,
                            owner_id INTEGER NOT NULL,
                            alert_type VARCHAR(50), -- 'stagnation', 'regression', 'treatment_change_needed', 'insufficient_data', 'positive_trend'
                            severity VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
                            title VARCHAR(200),
                            description TEXT,
                            recommendations TEXT[], -- Array de recomendações
                            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            resolved_at TIMESTAMP,
                            is_resolved BOOLEAN DEFAULT FALSE,
                            metadata JSONB
                        )
                    """)

                    # Criar índices para alertas inteligentes
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_smart_alerts_patient_id ON smart_alerts(patient_id);
                        CREATE INDEX IF NOT EXISTS idx_smart_alerts_owner_id ON smart_alerts(owner_id);
                        CREATE INDEX IF NOT EXISTS idx_smart_alerts_alert_type ON smart_alerts(alert_type);
                        CREATE INDEX IF NOT EXISTS idx_smart_alerts_severity ON smart_alerts(severity);
                        CREATE INDEX IF NOT EXISTS idx_smart_alerts_is_resolved ON smart_alerts(is_resolved);
                        CREATE INDEX IF NOT EXISTS idx_smart_alerts_generated_at ON smart_alerts(generated_at);
                    """)

                    conn.commit()
                    logger.info("History tables ensured to exist")

                    # Agora podemos tentar adicionar as restrições de chave estrangeira
                    try:
                        cursor.execute("""ALTER TABLE clinical_assessments
                                       ADD CONSTRAINT fk_clinical_assessments_user
                                       FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;""")
                    except:
                        pass  # Chave estrangeira já pode existir ou tabela pode não estar pronta

                    try:
                        cursor.execute("""ALTER TABLE clinical_assessments
                                       ADD CONSTRAINT fk_clinical_assessments_patient
                                       FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE;""")
                    except:
                        pass

                    try:
                        cursor.execute("""ALTER TABLE file_uploads
                                       ADD CONSTRAINT fk_file_uploads_user
                                       FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;""")
                    except:
                        pass

                    try:
                        cursor.execute("""ALTER TABLE file_uploads
                                       ADD CONSTRAINT fk_file_uploads_patient
                                       FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE;""")
                    except:
                        pass

                    # Removido: não há mais coluna document_id na tabela document_history

                    try:
                        cursor.execute("""ALTER TABLE document_history
                                       ADD CONSTRAINT fk_document_history_user
                                       FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;""")
                    except:
                        pass

                    try:
                        cursor.execute("""ALTER TABLE document_history
                                       ADD CONSTRAINT fk_document_history_patient
                                       FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE;""")
                    except:
                        pass

                    # Adicionar chave estrangeira para análise de evolução
                    try:
                        cursor.execute("""ALTER TABLE patient_evolution_analysis
                                       ADD CONSTRAINT fk_patient_evolution_analysis_patient
                                       FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE;""")
                    except:
                        pass  # Chave estrangeira já pode existir

                    try:
                        cursor.execute("""ALTER TABLE patient_evolution_analysis
                                       ADD CONSTRAINT fk_patient_evolution_analysis_owner
                                       FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;""")
                    except:
                        pass  # Chave estrangeira já pode existir

                    # Adicionar chave estrangeira para alertas inteligentes
                    try:
                        cursor.execute("""ALTER TABLE smart_alerts
                                       ADD CONSTRAINT fk_smart_alerts_patient
                                       FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE;""")
                    except:
                        pass  # Chave estrangeira já pode existir

                    try:
                        cursor.execute("""ALTER TABLE smart_alerts
                                       ADD CONSTRAINT fk_smart_alerts_owner
                                       FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;""")
                    except:
                        pass  # Chave estrangeira já pode existir

                    conn.commit()

                    # Verificar se a coluna document_history_id existe na tabela documents
                    # Esta operação precisa ser feita em uma transação separada
                    try:
                        with conn.cursor() as check_cursor:
                            check_cursor.execute("""
                                SELECT column_name
                                FROM information_schema.columns
                                WHERE table_name = 'documents' AND column_name = 'document_history_id'
                            """)
                            col_exists = check_cursor.fetchone()

                        if not col_exists:
                            # Adicionar a coluna document_history_id à tabela documents
                            # Esta operação precisa ser feita em uma transação separada
                            with conn.cursor() as alter_cursor:
                                alter_cursor.execute("""
                                    ALTER TABLE documents
                                    ADD COLUMN document_history_id INTEGER
                                """)
                                conn.commit()
                                logger.info("Coluna document_history_id adicionada à tabela documents")
                        else:
                            logger.info("Coluna document_history_id já existe na tabela documents")
                    except Exception as e:
                        logger.error(f"Erro ao verificar/adicionar coluna document_history_id: {e}")
                        # Fazer rollback da transação atual e continuar
                        try:
                            conn.rollback()
                        except:
                            pass  # Ignorar erro de rollback

        except Exception as e:
            logger.error(f"Erro ao garantir existência das tabelas de histórico: {e}")
            # Não lança exceção para não interromper a aplicação, apenas loga o erro


    def get_queries_count(self, user_id: int, patient_id: Optional[int] = None) -> int:
        """Get count of queries for a user, optionally filtered by patient"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT COUNT(*)
                    FROM clinical_assessments
                    WHERE user_id = %s AND assessment_type = 'query'
                """
                params = [user_id]

                if patient_id is not None:
                    query += " AND patient_id = %s"
                    params.append(patient_id)

                cursor.execute(query, params)
                count = cursor.fetchone()[0]
                return count

    def get_assessments_count(self, user_id: int, patient_id: Optional[int] = None) -> int:
        """Get count of clinical assessments for a user, optionally filtered by patient"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT COUNT(*)
                    FROM clinical_assessments
                    WHERE user_id = %s AND assessment_type != 'query'
                """
                params = [user_id]

                if patient_id is not None:
                    query += " AND patient_id = %s"
                    params.append(patient_id)

                cursor.execute(query, params)
                count = cursor.fetchone()[0]
                return count

    def get_uploads_count(self, user_id: int, patient_id: Optional[int] = None, status: str = "active") -> int:
        """Get count of file uploads for a user, optionally filtered by patient and status"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT COUNT(*)
                    FROM file_uploads
                    WHERE user_id = %s
                """
                params = [user_id]

                if patient_id is not None:
                    query += " AND patient_id = %s"
                    params.append(patient_id)

                if status:
                    query += " AND status = %s"
                    params.append(status)

                cursor.execute(query, params)
                count = cursor.fetchone()[0]
                return count

    def get_documents_count(self, user_id: int, patient_id: Optional[int] = None) -> int:
        """Get count of document history records for a user, optionally filtered by patient"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Verify if document_history table exists
                cursor.execute("""
                    SELECT EXISTS (
                       SELECT FROM information_schema.tables
                       WHERE table_schema = 'public'
                       AND table_name = 'document_history'
                   );
                """)
                table_exists = cursor.fetchone()[0]

                if not table_exists:
                    logger.warning("Table document_history does not exist")
                    return 0

                query = """
                    SELECT COUNT(*)
                    FROM document_history
                    WHERE user_id = %s
                """
                params = [user_id]

                if patient_id is not None:
                    query += " AND patient_id = %s"
                    params.append(patient_id)

                cursor.execute(query, params)
                count = cursor.fetchone()[0]
                return count

    def update_clinical_assessment(self, assessment_id: int, user_id: int, query: str = None,
                                   response: str = None, assessment_type: str = None) -> bool:
        """Update a clinical assessment record"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Build dynamic update query
                update_fields = []
                params = []

                if query is not None:
                    update_fields.append("query = %s")
                    params.append(query)
                if response is not None:
                    update_fields.append("response = %s")
                    params.append(response)
                if assessment_type is not None:
                    update_fields.append("assessment_type = %s")
                    params.append(assessment_type)

                # Always update the updated_at timestamp
                update_fields.append("updated_at = CURRENT_TIMESTAMP")

                if not update_fields:
                    return False  # Nothing to update

                query = f"""
                    UPDATE clinical_assessments
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                """
                params.extend([assessment_id, user_id])

                cursor.execute(query, params)
                result = cursor.fetchone()
                conn.commit()

                return result is not None

    def delete_clinical_assessment(self, assessment_id: int, user_id: int) -> bool:
        """Delete a clinical assessment record"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM clinical_assessments
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                """, (assessment_id, user_id))

                result = cursor.fetchone()
                conn.commit()

                return result is not None

    def get_history_statistics(self, user_id: int, patient_id: Optional[int] = None) -> Dict[str, int]:
        """Get comprehensive history statistics for a user"""
        return {
            'queries_count': self.get_queries_count(user_id, patient_id),
            'assessments_count': self.get_assessments_count(user_id, patient_id),
            'uploads_count': self.get_uploads_count(user_id, patient_id),
            'documents_count': self.get_documents_count(user_id, patient_id)
        }

    def save_smart_alert(self, patient_id: int, owner_id: int, alert_type: str, severity: str,
                         title: str, description: str, recommendations: list = None, metadata: dict = None):
        """
        Salva um alerta inteligente no banco de dados
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Converter lista de recomendações para array PostgreSQL se necessário
                recommendations_array = recommendations if recommendations else []

                # Converter metadados para JSON se necessário
                import json
                metadata_json = json.dumps(metadata) if metadata else '{}'

                cursor.execute("""
                    INSERT INTO smart_alerts (
                        patient_id, owner_id, alert_type, severity,
                        title, description, recommendations, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    patient_id, owner_id, alert_type, severity,
                    title, description, recommendations_array, metadata_json
                ))

                conn.commit()
                logger.info(f"Alerta inteligente salvo para paciente {patient_id}, tipo: {alert_type}")

    def get_smart_alerts_for_patient(self, patient_id: int, owner_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna alertas inteligentes para um paciente específico
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM smart_alerts
                    WHERE patient_id = %s AND owner_id = %s
                    ORDER BY generated_at DESC
                    LIMIT %s
                """, (patient_id, owner_id, limit))

                return [dict(row) for row in cursor.fetchall()]

    def get_unresolved_smart_alerts(self, owner_id: int) -> List[Dict[str, Any]]:
        """
        Retorna alertas inteligentes não resolvidos para um usuário
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM smart_alerts
                    WHERE owner_id = %s AND is_resolved = FALSE
                    ORDER BY generated_at DESC
                """, (owner_id,))

                return [dict(row) for row in cursor.fetchall()]


def get_db_manager() -> DatabaseManager:
    """Get a configured database manager instance"""
    return DatabaseManager()
