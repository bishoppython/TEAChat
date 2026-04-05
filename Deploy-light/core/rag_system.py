"""
Sistema RAG (Retrieval-Augmented Generation) para psicologia clínica
Lida com recuperação de documentos baseada em consultas de usuários usando similaridade vetorial
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from database.db_manager import DatabaseManager
from utils.embedding_generator import CachedEmbeddingGenerator
from utils.text_processor import ClinicalDataProcessor

# Importar o calculador de métricas
from utils.metrics_calculator import metrics_calculator

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClinicalRAGSystem:
    """
    Sistema RAG especificamente projetado para aplicações de psicologia clínica
    com isolamento de usuário e manipulação de dados médicos
    """

    def __init__(self, db_manager: DatabaseManager, embedding_generator: CachedEmbeddingGenerator):
        """
        Inicializar o sistema RAG

        :param db_manager: Instância do gerenciador de banco de dados
        :param embedding_generator: Instância do gerador de embeddings
        """
        self.db_manager = db_manager
        self.embedding_generator = embedding_generator
        self.text_processor = ClinicalDataProcessor()
    
    def add_document(self,
                    owner_id: int,
                    patient_id: int,
                    title: str,
                    text: str,
                    source_type: str = "note",
                    metadata: Optional[Dict[str, Any]] = None,
                    chunk_size: int = 500,
                    chunk_overlap: int = 50,
                    document_history_id: Optional[int] = None) -> List[str]:
        """
        Adicionar um documento clínico ao sistema RAG

        :param owner_id: ID do usuário que possui este documento
        :param patient_id: ID do paciente sobre o qual é este documento
        :param title: Título do documento
        :param text: Texto completo do documento
        :param source_type: Tipo de documento (nota, avaliação, etc.)
        :param metadata: Metadados adicionais sobre o documento
        :param chunk_size: Tamanho dos chunks de texto para processamento
        :param chunk_overlap: Sobreposição entre chunks
        :param document_history_id: ID do histórico de documento (opcional)
        :return: Lista de IDs de chunks de documento adicionados
        """
        # Processar o documento em chunks
        processor = ClinicalDataProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = processor.chunk_text(text, chunk_id_prefix=title.replace(" ", "_"))

        doc_chunk_ids = []

        for i, chunk in enumerate(chunks):
            # Gerar embedding para o chunk
            embedding = self.embedding_generator.generate_single_embedding(
                chunk['text'],
                task_type="RETRIEVAL_DOCUMENT"
            )

            # Adicionar o chunk ao banco de dados
            chunk_id = self.db_manager.add_document_chunk(
                owner_id=owner_id,
                patient_id=patient_id,
                title=f"{title} - Chunk {i+1}",
                text=chunk['text'],
                source_type=source_type,
                chunk_order=i+1,
                chunk_id=f"{title.replace(' ', '_')}_chunk_{i+1}",
                metadata={**(metadata or {}), **chunk['metadata']},
                embedding=embedding,
                document_history_id=document_history_id
            )

            doc_chunk_ids.append(chunk_id)

        logger.info(f"Documento '{title}' adicionado com {len(doc_chunk_ids)} chunks para paciente {patient_id}")
        return doc_chunk_ids

    def retrieve_similar_documents(self,
                                 query: str,
                                 owner_id: int,
                                 patient_id: Optional[int] = None,
                                 k: int = 4,
                                 min_similarity: float = 0.5) -> List[Dict[str, Any]]:
        """
        Recuperar documentos similares à consulta

        :param query: Consulta do usuário para encontrar documentos similares
        :param owner_id: ID do usuário fazendo a solicitação (para controle de acesso)
        :param patient_id: ID opcional do paciente para filtrar resultados
        :param k: Número de documentos principais a recuperar
        :param min_similarity: Limiar mínimo de similaridade
        :return: Lista de documentos similares com metadados
        """
        # Gerar embedding para a consulta
        query_embedding = self.embedding_generator.generate_single_embedding(
            query,
            task_type="RETRIEVAL_QUERY"
        )

        # Recuperar documentos similares do banco de dados
        # O gerenciador de banco de dados lida com isolamento de usuário (owner_id)
        similar_docs = self.db_manager.retrieve_similar_documents(
            owner_id=owner_id,
            query=query,
            patient_id=patient_id,
            k=k,
            min_similarity=min_similarity
        )
        
        return similar_docs
    
    def build_context_from_documents(self,
                                   documents: List[Dict[str, Any]],
                                   max_tokens: int = 2048) -> str:
        """
        Construir string de contexto a partir de documentos recuperados

        :param documents: Lista de documentos recuperados do sistema RAG
        :param max_tokens: Número máximo de tokens para incluir no contexto
        :return: String de contexto contendo textos dos documentos
        """
        from anonimizer_functions import process_anonymization
        context_parts = []
        total_tokens = 0

        # Ordenar documentos por pontuação de similaridade (maior primeiro)
        sorted_docs = sorted(documents, key=lambda x: x['similarity'], reverse=True)

        for doc in sorted_docs:
            # Anonimizar o conteúdo do documento antes de adicionar ao contexto
            anonymized_text = process_anonymization("TEXT", doc['text'])

            # Estimativa simples de token (1 token ~ 4 caracteres para texto em inglês)
            estimated_tokens = len(anonymized_text) // 4

            if total_tokens + estimated_tokens > max_tokens:
                logger.info(f"Alcançado máximo de tokens de contexto ({max_tokens})")
                break

            # Adicionar documento ao contexto
            doc_context = f"Documento: {doc['title']}\n"
            doc_context += f"Similaridade: {doc['similarity']:.3f}\n"
            doc_context += f"Conteúdo: {anonymized_text}\n\n"

            context_parts.append(doc_context)
            total_tokens += estimated_tokens

        return "".join(context_parts)

    def build_prompt(self,
                    system_prompt: str,
                    context: str,
                    user_query: str,
                    patient_info: Optional[Dict[str, Any]] = None) -> str:
        """
        Construir uma prompt completa com instruções do sistema, contexto e consulta do usuário

        :param system_prompt: Instruções do sistema para o modelo
        :param context: Contexto recuperado do RAG
        :param user_query: Consulta original do usuário
        :param patient_info: Informações opcionais do paciente para incluir
        :return: String completa de prompt
        """
        from anonimizer_functions import process_anonymization
        prompt_parts = []

        # Adicionar prompt do sistema
        prompt_parts.append(f"<|system|>\n{system_prompt}\n")

        # Adicionar informações do paciente se disponível
        if patient_info:
            # Anonimizar nome do paciente
            first_name = patient_info.get('first_name', 'Desconhecido')
            last_name = patient_info.get('last_name', '')
            anonymized_first_name = process_anonymization("TEXT", first_name)
            anonymized_last_name = process_anonymization("TEXT", last_name)

            patient_details = (
                f"Informações do Paciente:\n"
                f"- Nome: {anonymized_first_name} {anonymized_last_name}\n"
                f"- Idade: {patient_info.get('age', 'Desconhecida')}\n"
                f"- Diagnóstico: {patient_info.get('diagnosis', 'Não especificado')}\n\n"
            )
            prompt_parts.append(patient_details)

        # Adicionar contexto se disponível
        if context.strip():
            prompt_parts.append(f"<|context|>\n{context}\n")

        # Adicionar consulta do usuário
        prompt_parts.append(f"<|user|>\n{user_query}\n")

        # Adicionar marcador de resposta
        prompt_parts.append("<|assistant|>\n")

        return "".join(prompt_parts)

    def query(self,
             query: str,
             owner_id: int,
             patient_id: Optional[str] = None,
             k: int = 4,
             min_similarity: float = 0.5,
             max_context_tokens: int = 2048,
             system_prompt: str = None) -> Dict[str, Any]:
        """
        Processo completo de consulta: recuperar, construir contexto e preparar resposta

        :param query: Consulta do usuário
        :param owner_id: ID do usuário fazendo a solicitação
        :param patient_id: ID opcional do paciente para filtrar resultados
        :param k: Número de documentos a recuperar
        :param min_similarity: Limiar mínimo de similaridade
        :param max_context_tokens: Comprimento máximo do contexto
        :param system_prompt: Prompt personalizado do sistema (se None, usa padrão)
        :return: Dicionário com resultados da consulta e metadados
        """
        start_time = datetime.now()

        # Recuperar documentos similares
        similar_docs = self.retrieve_similar_documents(
            query=query,
            owner_id=owner_id,
            patient_id=patient_id,
            k=k,
            min_similarity=min_similarity
        )
        
        # Construir contexto a partir dos documentos recuperados
        context = self.build_context_from_documents(similar_docs, max_context_tokens)

        # Obter informações do paciente se especificado
        patient_info = None
        if patient_id:
            patient_info = self.db_manager.get_patient_info(owner_id, patient_id)

        # Usar prompt padrão do sistema se nenhum for fornecido
        if system_prompt is None:
            system_prompt = (
                "Você é um assistente clínico especialista para um psicopedagogo. "
                "Use APENAS as informações fornecidas na seção de contexto para responder perguntas. "
                "Se o contexto não contiver informações relevantes, afirme isso claramente. "
                "Mantenha sempre um tom profissional e empático. "
                "Não faça diagnósticos, mas sugira intervenções baseadas em evidências com base no perfil do paciente."
            )

        # Construir o prompt completo
        full_prompt = self.build_prompt(
            system_prompt=system_prompt,
            context=context,
            user_query=query,
            patient_info=patient_info
        )

        # Registrar a consulta para fins de auditoria
        response_time = (datetime.now() - start_time).total_seconds() * 1000  # em ms
        self.db_manager.log_query_response(
            user_id=owner_id,
            patient_id=patient_info['id'] if patient_info else None,
            query=query,
            model_used="RAG-retrieval",
            tokens_used=len(full_prompt),
            response_time_ms=int(response_time)
        )

        # Calcular métricas de retrieval se possível
        retrieval_metrics = None
        try:
            # Para calcular métricas de retrieval precisamos de documentos relevantes conhecidos
            # Isso geralmente é feito com dados de benchmark ou avaliação humana
            # Por enquanto, vamos calcular métricas básicas baseadas nos documentos recuperados
            retrieval_metrics = {
                "num_documents_retrieved": len(similar_docs),
                "avg_similarity_score": sum(doc.get('similarity', 0) for doc in similar_docs) / len(similar_docs) if similar_docs else 0,
                "max_similarity_score": max(doc.get('similarity', 0) for doc in similar_docs) if similar_docs else 0,
                "min_similarity_score": min(doc.get('similarity', 0) for doc in similar_docs) if similar_docs else 0
            }
        except Exception as e:
            logger.warning(f"Falha ao calcular métricas de retrieval: {e}")

        return {
            "query": query,
            "retrieved_documents": similar_docs,
            "context": context,
            "full_prompt": full_prompt,
            "patient_info": patient_info,
            "query_time_ms": int(response_time),
            "num_documents_retrieved": len(similar_docs),
            "retrieval_metrics": retrieval_metrics
        }

    def batch_add_documents(self,
                           documents: List[Dict[str, Any]],
                           owner_id: int) -> Dict[str, Any]:
        """
        Adicionar múltiplos documentos em lote

        :param documents: Lista de dicionários de documentos com chaves:
                         'patient_id', 'title', 'text', 'source_type', 'metadata'
        :param owner_id: ID do usuário adicionando os documentos
        :return: Resumo da operação em lote
        """
        results = {
            'successful': 0,
            'failed': 0,
            'errors': [],
            'document_ids': []
        }

        for doc_data in documents:
            try:
                doc_ids = self.add_document(
                    owner_id=owner_id,
                    patient_id=doc_data['patient_id'],
                    title=doc_data['title'],
                    text=doc_data['text'],
                    source_type=doc_data.get('source_type', 'note'),
                    metadata=doc_data.get('metadata', {})
                )
                results['document_ids'].extend(doc_ids)
                results['successful'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'document': doc_data.get('title', 'Desconhecido'),
                    'error': str(e)
                })
                logger.error(f"Falha ao adicionar documento: {e}")

        logger.info(f"Adição em lote concluída: {results['successful']} bem-sucedidas, {results['failed']} falharam")
        return results


# Função de exemplo de uso
def example_usage():
    """
    Exemplo de como usar o ClinicalRAGSystem
    """
    try:
        # Inicializar componentes (requer variáveis de ambiente definidas)
        db_manager = DatabaseManager()
        embedder = CachedEmbeddingGenerator()
        rag_system = ClinicalRAGSystem(db_manager, embedder)

        # Exemplo: Adicionar um documento de exemplo
        sample_doc = """
        Relatório de Avaliação: Lucas Silva
        Data: 2023-05-15
        Idade: 8 anos
        Diagnóstico: Dificuldades de aprendizagem, Hipersensibilidade auditiva

        Lucas demonstra desafios com compreensão de leitura e apresenta
        hipersensibilidade a sons altos na sala de aula. Quando exposto a
        estímulos auditivos como sirenes de incêndio ou ruídos de construção,
        ele cobre os ouvidos e fica visivelmente desconfortável.

        Recomendação: Fornecer fones de ouvido com cancelamento de ruído
        durante atividades de leitura e implementar uma programação de pausas
        sensoriais a cada 30 minutos.
        """

        # Obter IDs de proprietário e paciente (assumindo que existam no banco de dados)
        # Este é apenas um placeholder - na prática, você recuperaria do banco de dados
        owner_id = 1  # Exemplo de ID de proprietário
        patient_id = 1  # Exemplo de ID de paciente

        # Adicionar o documento ao sistema RAG
        doc_chunk_ids = rag_system.add_document(
            owner_id=owner_id,
            patient_id=patient_id,
            title="Avaliação Inicial - Lucas Silva",
            text=sample_doc,
            source_type="assessment"
        )

        print(f"Documento adicionado com {len(doc_chunk_ids)} chunks")

        # Exemplo de consulta
        query = "Quais acomodações devem ser feitas para hipersensibilidade auditiva?"

        # Executar consulta RAG
        result = rag_system.query(
            query=query,
            owner_id=owner_id,
            patient_id="lucas"  # string de patient_id conforme armazenada no banco de dados
        )

        print(f"\nConsulta: {result['query']}")
        print(f"Documentos recuperados: {result['num_documents_retrieved']}")
        print(f"Comprimento do contexto: {len(result['context'])} caracteres")

        print(f"\nPrompt completo:\n{result['full_prompt']}")

    except ValueError as e:
        print(f"Erro: {e}")
        print("Por favor, certifique-se de que todas as variáveis de ambiente necessárias estejam definidas")


if __name__ == "__main__":
    example_usage()