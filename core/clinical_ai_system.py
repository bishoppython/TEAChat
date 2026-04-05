"""
Módulo de integração principal para sistema de IA de psicologia clínica
Combina recuperação RAG com modelos LoRA e integração OpenAI
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time

from database.db_manager import DatabaseManager
from utils.embedding_generator import CachedEmbeddingGenerator
from .rag_system import ClinicalRAGSystem
from .lora_tuner import ClinicalLoRATuner
from .gemini_interface import ClinicalGeminiInterface
from .openai_interface import ClinicalOpenAIInterface, OpenAIClient
from .model_selector import ModelSelector
from .user_knowledge_base import UserKnowledgeBase
from .local_response_generator import LocalResponseGenerator

# Importar o calculador de métricas
from utils.metrics_calculator import metrics_calculator

# Importar o detector de alertas inteligentes
from .alert_detector import SmartAlertDetector

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClinicalAISystem:
    """
    Sistema principal que integra RAG, ajuste fino LoRA e inferência OpenAI
    """

    def __init__(self,
                 db_manager: DatabaseManager,
                 embedding_generator: CachedEmbeddingGenerator,
                 default_model: str = "gpt-3.5-turbo"):
        """
        Inicializar o sistema de IA clínica

        :param db_manager: Instância do gerenciador de banco de dados
        :param embedding_generator: Instância do gerador de embeddings
        :param default_model: Modelo padrão para inferência
        """
        self.db_manager = db_manager
        self.embedding_generator = embedding_generator
        self.default_model = default_model

        # Inicializar componentes
        self.rag_system = ClinicalRAGSystem(db_manager, embedding_generator)

        # Inicializar Base de Conhecimento do Usuário (similar ao Guru TI)
        self.user_kb = UserKnowledgeBase(db_manager)
        logger.info("Base de Conhecimento do Usuário inicializada")

        # Inicializar interface Gemini
        try:
            self.gemini_interface = ClinicalGeminiInterface()
            logger.info("✅ Interface Gemini inicializada com sucesso")
        except ValueError as e:
            logger.error(f"Falha ao inicializar Gemini: {e}")
            self.gemini_interface = None

        # Inicializar interface OpenAI (se disponível)
        try:
            openai_client = OpenAIClient()
            self.openai_interface = ClinicalOpenAIInterface(openai_client)
            logger.info("✅ Interface OpenAI inicializada com sucesso")
        except ValueError as e:
            logger.warning(f"Interface OpenAI não disponível: {e}")
            self.openai_interface = None

        # Inicializar o seletor de modelos com fallback automático (apenas Gemini/OpenAI)
        self.model_selector = ModelSelector(
            gemini_interface=self.gemini_interface,
            openai_interface=self.openai_interface
        )
        logger.info("✅ Seletor de modelos com fallback automático inicializado (apenas Gemini/OpenAI)")

        # Gerador de Resposta Local DESATIVADO - usando apenas APIs Gemini/OpenAI
        self.local_generator = None
        logger.info("⚠️  Gerador de Resposta Local DESATIVADO - apenas Gemini/OpenAI serão usados")

        # Inicializar detector de alertas inteligentes
        self.alert_detector = SmartAlertDetector()
        logger.info("✅ Detector de Alertas Inteligentes inicializado")

        # Inicializar tuner LoRA (será definido após treinamento)
        self.lora_tuner = None

        # Garantir que as tabelas de histórico existam
        self.db_manager.ensure_history_tables_exist()

    def add_clinical_document(self,
                            owner_id: int,
                            patient_id: int,
                            title: str,
                            text: str,
                            source_type: str = "note",
                            metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Adicionar um documento clínico ao sistema RAG

        :param owner_id: ID do usuário que possui este documento
        :param patient_id: ID do paciente sobre o qual é este documento
        :param title: Título do documento
        :param text: Texto completo do documento
        :param source_type: Tipo de documento
        :param metadata: Metadados adicionais
        :return: Lista de IDs de chunks do documento
        """
        # Anonimizar o conteúdo do texto antes de adicionar
        from anonimizer_functions import process_anonymization
        anonymized_text = process_anonymization("TEXT", text)

        # Primeiro, criar um registro no histórico de documentos
        document_history_id = None
        try:
            document_history_id = self.db_manager.add_document_history(
                action_type='created',
                user_id=owner_id,
                patient_id=patient_id,
                title=title,
                text_content=anonymized_text,  # Usar o texto anonimizado
                source_type=source_type,
                metadata=metadata,
                new_values={'chunks_created': 0}  # Será atualizado após a criação dos chunks
            )
        except Exception as e:
            logger.error(f"Falha ao criar registro de histórico de documento: {e}")
            # Continuar com a criação dos chunks mesmo se o histórico falhar

        # Adicionar os chunks de documento com o ID do histórico
        result = self.rag_system.add_document(
            owner_id=owner_id,
            patient_id=patient_id,
            title=title,
            text=anonymized_text,  # Usar o texto anonimizado
            source_type=source_type,
            metadata=metadata,
            document_history_id=document_history_id
        )

        # Atualizar o registro de histórico com o número de chunks criados
        if document_history_id:
            try:
                # Atualizar o registro de histórico com o número real de chunks
                # Criar um novo registro de histórico para atualização
                self.db_manager.add_document_history(
                    action_type='updated',
                    user_id=owner_id,
                    patient_id=patient_id,
                    title=title,
                    text_content=text,
                    source_type=source_type,
                    metadata=metadata,
                    old_values={'chunks_created': 0},
                    new_values={'chunks_created': len(result)}
                )
            except Exception as e:
                logger.error(f"Falha ao atualizar registro de histórico de documento: {e}")

        # Atualizar índice do usuário após adicionar documento
        try:
            self.user_kb.refresh_user_index(owner_id)
            logger.info(f"Índice do usuário {owner_id} atualizado após adicionar documento")
        except Exception as e:
            logger.warning(f"Erro ao atualizar índice do usuário: {e}")

        return result
    
    def get_user_statistics(self, owner_id: int) -> Dict[str, Any]:
        """
        Obtém estatísticas da base de conhecimento do usuário
        Similar ao endpoint /api/professions/stats do Guru TI
        
        :param owner_id: ID do usuário
        :return: Estatísticas completas
        """
        return self.user_kb.get_statistics(owner_id)
    
    def query_clinical_system(self,
                            query: str,
                            owner_id: int,
                            patient_id: Optional[int] = None,
                            use_openai: bool = True,
                            model: str = None,
                            k: int = 4,
                            min_similarity: float = 0.5,
                            include_user_context: bool = True) -> Dict[str, Any]:
        """
        Consultar o sistema de IA clínica usando RAG e/ou modelo ajustado

        :param query: Consulta do usuário
        :param owner_id: ID do usuário fazendo a solicitação
        :param patient_id: ID opcional do paciente para filtrar resultados
        :param use_openai: Se deve usar OpenAI para geração
        :param model: Modelo a ser usado para geração
        :param k: Número de documentos a recuperar
        :param min_similarity: Limiar mínimo de similaridade
        :param include_user_context: Incluir contexto geral do usuário (similar ao Guru TI)
        :return: Resposta completa com metadados
        """
        start_time = datetime.now()

        # Obter contexto geral do usuário (similar ao Guru TI)
        user_context = ""
        if include_user_context:
            try:
                user_context = self.user_kb.get_user_context(owner_id, patient_id)
                logger.info(f"✅ Contexto do usuário adicionado ({len(user_context)} chars)")
            except Exception as e:
                logger.warning(f"Erro ao obter contexto do usuário: {e}")

        # Executar recuperação RAG
        rag_result = self.rag_system.query(
            query=query,
            owner_id=owner_id,
            patient_id=patient_id,
            k=k,
            min_similarity=min_similarity
        )

        # Adicionar contexto do usuário ao resultado RAG
        if user_context:
            rag_result['user_context'] = user_context
            # Enriquecer o contexto RAG com informações gerais do usuário
            rag_result['context'] = f"{user_context}\n\n{rag_result['context']}"

        # Gerar resposta usando o seletor de modelos com fallback automático (apenas Gemini/OpenAI)
        if use_openai and (self.gemini_interface or self.openai_interface):  # use_openai agora significa "usar IA"
            try:
                response, model_used = self.model_selector.generate_response(rag_result, fallback_enabled=True)
                logger.info(f"✅ Resposta gerada com {model_used}")
            except Exception as e:
                # Fallback local DESATIVADO - lançar erro quando APIs falham
                logger.error(f"❌ Modelos de IA falharam ({str(e)[:100]}...). Fallback local está DESATIVADO.")
                raise RuntimeError(f"Falha ao gerar resposta: APIs Gemini/OpenAI indisponíveis. Fallback local desativado.")
        else:
            # Erro quando modelos de IA não estão disponíveis
            logger.error("❌ Modelos de IA não disponíveis. Fallback local está DESATIVADO.")
            raise RuntimeError("Modelos de IA não disponíveis. Configure Gemini ou OpenAI. Fallback local desativado.")

        # Calcular tempo de resposta
        response_time = (datetime.now() - start_time).total_seconds() * 1000  # em ms

        # Registrar a consulta para fins de auditoria
        patient_info = rag_result.get('patient_info')
        patient_id_for_log = patient_info.get('id') if patient_info else None

        # Primeiro, registrar a consulta para obter o ID
        self.db_manager.log_query_response(
            user_id=owner_id,
            patient_id=patient_id_for_log,
            query=query,
            response=response[:500],  # Registrar apenas os primeiros 500 caracteres para economizar espaço
            model_used=model_used,
            tokens_used=len(response),
            response_time_ms=int(response_time)
        )

        # Obter o ID da consulta recém-registrada para vincular às métricas
        # Isso pode exigir uma consulta para obter o ID mais recente para este usuário e timestamp
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cutoff_time = datetime.now() - timedelta(seconds=5)
                cursor.execute("""
                    SELECT id FROM audit_log
                    WHERE user_id = %s AND created_at >= %s
                    ORDER BY created_at DESC LIMIT 1
                """, (owner_id, cutoff_time))  # Procurar nos últimos 5 segundos
                result = cursor.fetchone()
                query_id = result[0] if result else None

        # Formatar a resposta para melhor apresentação antes de registrar
        from utils.response_formatter import format_markdown_for_display
        formatted_response = format_markdown_for_display(response, "query")

        # Registrar a consulta no histórico de avaliações (adaptando para o tipo genérico de consulta)
        try:
            self.db_manager.add_clinical_assessment(
                user_id=owner_id,
                patient_id=patient_id_for_log or 0,  # Usar 0 temporariamente se paciente não encontrado
                query=query,
                response=formatted_response,
                assessment_type="query",
                confidence_score=0.0,  # Não aplicável para consultas diretas
                processing_time=response_time / 1000,  # Converter para segundos
                model_used=model_used,
                tokens_used=len(formatted_response)
            )
        except Exception as e:
            logger.error(f"Falha ao registrar consulta no histórico de avaliações: {e}")

        # Calcular e armazenar métricas de qualidade
        try:
            # Obter documentos recuperados para cálculo de métricas
            retrieved_docs = rag_result.get('retrieved_documents', [])
            context = rag_result.get('context', '')

            # Calcular métricas abrangentes
            metrics = metrics_calculator.calculate_comprehensive_metrics(
                query=query,
                response=formatted_response,
                retrieved_docs=retrieved_docs,
                context=context,
                embedding_func=self.embedding_generator.generate_single_embedding if self.embedding_generator else None
            )

            # Adicionar métricas de custo (estimativa baseada no tamanho da resposta)
            cost_metrics = metrics_calculator.calculate_cost_metrics(
                input_tokens=len(query.split()) + len(context.split()),
                output_tokens=len(formatted_response.split()),
                model_name=model_used
            )
            metrics['cost_metrics'] = cost_metrics

            # Armazenar métricas no banco de dados se tivermos um query_id
            if query_id:
                self.db_manager.store_query_metrics(query_id, metrics)
                logger.info(f"Métricas de qualidade armazenadas para query_id: {query_id}")
            else:
                logger.warning("Não foi possível obter query_id para armazenar métricas")

        except Exception as e:
            logger.error(f"Falha ao calcular ou armazenar métricas de qualidade: {e}")

        # Detectar e salvar alertas inteligentes baseados na resposta da IA
        try:
            # Detectar alertas na resposta
            alerts = self.alert_detector.detect_alerts(
                query=query,
                response=formatted_response,
                patient_info=patient_info
            )

            # Salvar alertas detectados no banco de dados
            for alert in alerts:
                recommendations = self.alert_detector.generate_recommendations(alert['alert_type'])

                self.db_manager.save_smart_alert(
                    patient_id=patient_id_for_log or 0,
                    owner_id=owner_id,
                    alert_type=alert['alert_type'],
                    severity=alert['severity'],
                    title=f"Alerta Automático: {alert['alert_type'].replace('_', ' ').title()}",
                    description=alert['description'],
                    recommendations=recommendations,
                    metadata={
                        'context': alert['context'],
                        'matched_pattern': alert['matched_pattern'],
                        'timestamp': alert['timestamp']
                    }
                )
                logger.info(f"Alerta inteligente salvo: {alert['alert_type']} para paciente {patient_id_for_log}")
        except Exception as e:
            logger.error(f"Falha ao detectar ou salvar alertas inteligentes: {e}")

        return {
            "query": query,
            "response": formatted_response,
            "rag_result": rag_result,
            "response_time_ms": int(response_time),
            "model_used": model_used,
            "use_gemini": use_openai,  # Renomeado conceitualmente
            "quality_metrics": metrics if 'metrics' in locals() else None
        }

    def setup_lora_model(self,
                        base_model_name: str = "microsoft/DialoGPT-medium",
                        r: int = 16,
                        alpha: int = 32,
                        dropout: float = 0.05) -> None:
        """
        Configurar modelo LoRA para ajuste fino

        :param base_model_name: Modelo base para ajuste fino
        :param r: Ranque LoRA
        :param alpha: Parâmetro alpha LoRA
        :param dropout: Taxa de dropout
        """
        self.lora_tuner = ClinicalLoRATuner(base_model_name=base_model_name)
        self.lora_tuner.prepare_peft_model(r=r, alpha=alpha, dropout=dropout)
        logger.info(f"Modelo LoRA preparado com modelo base: {base_model_name}")

    def train_lora_model(self,
                        train_dataset_path: str,
                        validation_dataset_path: str = None,
                        output_dir: str = "./trained_clinical_model",
                        num_train_epochs: int = 3,
                        per_device_train_batch_size: int = 4) -> str:
        """
        Treinar o modelo LoRA com dados clínicos

        :param train_dataset_path: Caminho para conjunto de dados de treinamento
        :param validation_dataset_path: Caminho para conjunto de dados de validação
        :param output_dir: Diretório de saída para o modelo
        :param num_train_epochs: Número de épocas de treinamento
        :param per_device_train_batch_size: Tamanho do batch
        :return: Caminho para modelo salvo
        """
        if not self.lora_tuner:
            raise ValueError("Tuner LoRA não inicializado. Chame setup_lora_model primeiro.")

        logger.info(f"Iniciando treinamento LoRA com conjunto de dados: {train_dataset_path}")
        
        model_path = self.lora_tuner.train_with_sft(
            train_dataset_path=train_dataset_path,
            validation_dataset_path=validation_dataset_path,
            output_dir=output_dir,
            num_train_epochs=num_train_epochs,
            per_device_train_batch_size=per_device_train_batch_size
        )
        
        logger.info(f"Treinamento LoRA concluído. Modelo salvo em: {model_path}")
        return model_path


    def batch_process_queries(self,
                            queries: List[Dict[str, Any]],
                            owner_id: int) -> List[Dict[str, Any]]:
        """
        Processar múltiplas consultas em lote

        :param queries: Lista de dicionários de consulta com chaves 'query' e 'patient_id'
        :param owner_id: ID do usuário fazendo as solicitações
        :return: Lista de dicionários de resposta
        """
        responses = []

        for query_data in queries:
            query = query_data.get('query', '')
            patient_id = query_data.get('patient_id')
            use_openai = query_data.get('use_openai', True)
            model = query_data.get('model', self.default_model)

            response = self.query_clinical_system(
                query=query,
                owner_id=owner_id,
                patient_id=patient_id,
                use_openai=use_openai,
                model=model
            )
            responses.append(response)

        return responses

    def get_patient_profile(self, owner_id: int, patient_id: int) -> Dict[str, Any]:
        """
        Obter perfil completo do paciente incluindo sensibilidades

        :param owner_id: ID do usuário solicitando o perfil
        :param patient_id: ID do paciente
        :return: Perfil do paciente com todas as informações disponíveis
        """
        patient_info = self.db_manager.get_patient_info(owner_id, patient_id)

        if patient_info:
            # Anonimizar campos sensíveis no perfil do paciente
            from anonimizer_functions import process_anonymization

            if 'first_name' in patient_info:
                patient_info['first_name'] = process_anonymization("TEXT", patient_info['first_name'])
            if 'last_name' in patient_info:
                patient_info['last_name'] = process_anonymization("TEXT", patient_info['last_name'])
            if 'description' in patient_info:
                patient_info['description'] = process_anonymization("TEXT", patient_info['description'])

            # Aplicar formatação de markdown à descrição e diagnóstico
            from utils.response_formatter import format_markdown_for_display

            if 'description' in patient_info and patient_info['description']:
                patient_info['description'] = format_markdown_for_display(patient_info['description'], 'patient_info')

            if 'diagnosis' in patient_info and patient_info['diagnosis']:
                patient_info['diagnosis'] = format_markdown_for_display(patient_info['diagnosis'], 'patient_info')

            # Formatar também o campo neurotype, level e outros campos textuais se necessário
            if 'neurotype' in patient_info and patient_info['neurotype']:
                patient_info['neurotype'] = format_markdown_for_display(patient_info['neurotype'], 'patient_info')

            if 'level' in patient_info and patient_info['level']:
                patient_info['level'] = format_markdown_for_display(patient_info['level'], 'patient_info')

            patient_info['sensitivities'] = self.db_manager.get_patient_sensitivities(
                owner_id, patient_id
            )

        return patient_info or {}

    def add_patient_sensitivity(self, owner_id: int, patient_id: int, sensitivity_type: str,
                               sensitivity_level: str, description: str) -> int:
        """
        Add a patient sensitivity record

        :param owner_id: ID of the user requesting the action
        :param patient_id: ID of the patient
        :param sensitivity_type: Type of sensitivity (e.g., 'noise', 'touch', 'light')
        :param sensitivity_level: Level of sensitivity (e.g., 'low', 'medium', 'high')
        :param description: Detailed description of the sensitivity
        :return: ID of the newly created sensitivity record
        """
        return self.db_manager.add_patient_sensitivity(
            owner_id=owner_id,
            patient_id=patient_id,
            sensitivity_type=sensitivity_type,
            sensitivity_level=sensitivity_level,
            description=description
        )

    def delete_patient_sensitivities(self, owner_id: int, patient_id: int) -> int:
        """
        Delete all sensitivities for a patient

        :param owner_id: ID of the user requesting the action
        :param patient_id: ID of the patient
        :return: Number of deleted sensitivity records
        """
        return self.db_manager.delete_patient_sensitivities(
            owner_id=owner_id,
            patient_id=patient_id
        )
    
    def run_clinical_assessment(self,
                              query: str,
                              owner_id: int,
                              patient_id: int,
                              assessment_type: str = "general") -> Dict[str, Any]:
        """
        Executar uma avaliação clínica estruturada

        :param query: Consulta de avaliação
        :param owner_id: ID do usuário
        :param patient_id: ID do paciente
        :param assessment_type: Tipo de avaliação
        :return: Resultados da avaliação
        """
        start_time = time.time()

        # Obter perfil do paciente
        patient_profile = self.get_patient_profile(owner_id, patient_id)

        # Executar consulta com contexto completo
        result = self.query_clinical_system(
            query=query,
            owner_id=owner_id,
            patient_id=patient_id
        )

        # Formatar a resposta para melhor apresentação
        from utils.response_formatter import format_markdown_for_display
        formatted_response = format_markdown_for_display(result["response"], "assessment")

        # Adicionar processamento específico da avaliação
        assessment_result = {
            "assessment_type": assessment_type,
            "patient_id": patient_id,
            "query": query,
            "response": formatted_response,
            "retrieved_evidence": len(result["rag_result"]["retrieved_documents"]),
            "confidence_score": min(1.0, len(result["rag_result"]["retrieved_documents"]) / 4),  # Heurística simples
            "patient_profile": patient_profile,
            "timestamp": datetime.now().isoformat(),
            "processing_time": time.time() - start_time,
            "model_used": result["model_used"]
        }

        # Registrar a avaliação na tabela de histórico
        try:
            self.db_manager.add_clinical_assessment(
                user_id=owner_id,
                patient_id=patient_id,
                query=query,
                response=formatted_response,
                assessment_type=assessment_type,
                confidence_score=assessment_result["confidence_score"],
                processing_time=assessment_result["processing_time"],
                model_used=result["model_used"],
                tokens_used=len(formatted_response)
            )
        except Exception as e:
            logger.error(f"Falha ao registrar avaliação clínica no histórico: {e}")

        # Calcular e armazenar métricas de qualidade para a avaliação
        try:
            # Obter o ID da avaliação recém-registrada para vincular às métricas
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cutoff_time = datetime.now() - timedelta(seconds=5)
                    cursor.execute("""
                        SELECT id FROM clinical_assessments
                        WHERE user_id = %s AND patient_id = %s AND created_at >= %s
                        ORDER BY created_at DESC LIMIT 1
                    """, (owner_id, patient_id, cutoff_time))  # Procurar nos últimos 5 segundos
                    result = cursor.fetchone()
                    assessment_id = result[0] if result else None

            # Obter documentos recuperados para cálculo de métricas
            # Isso requer ter acesso ao rag_result, então precisamos modificar a chamada
            # Por enquanto, vamos calcular métricas gerais baseadas na resposta e query
            context = assessment_result.get("rag_result", {}).get("context", "") if "rag_result" in assessment_result else ""
            retrieved_docs = assessment_result.get("rag_result", {}).get("retrieved_documents", []) if "rag_result" in assessment_result else []

            # Calcular métricas abrangentes
            metrics = metrics_calculator.calculate_comprehensive_metrics(
                query=query,
                response=formatted_response,
                retrieved_docs=retrieved_docs,
                context=context,
                embedding_func=self.embedding_generator.generate_single_embedding if self.embedding_generator else None
            )

            # Adicionar métricas de custo
            cost_metrics = metrics_calculator.calculate_cost_metrics(
                input_tokens=len(query.split()) + len(context.split()),
                output_tokens=len(formatted_response.split()),
                model_name=result["model_used"]
            )
            metrics['cost_metrics'] = cost_metrics

            # Armazenar métricas no banco de dados se tivermos um assessment_id
            # Para isso, precisamos associar as métricas ao audit_log correspondente
            # Primeiro, vamos registrar na tabela de auditoria para obter um query_id
            self.db_manager.log_query_response(
                user_id=owner_id,
                patient_id=patient_id,
                query=query,
                response=formatted_response[:500],  # Registrar apenas os primeiros 500 caracteres
                model_used=result["model_used"],
                tokens_used=len(formatted_response),
                response_time_ms=int(assessment_result["processing_time"] * 1000)  # Converter para ms
            )

            # Obter o ID da consulta registrada
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cutoff_time = datetime.now() - timedelta(seconds=5)
                    cursor.execute("""
                        SELECT id FROM audit_log
                        WHERE user_id = %s AND patient_id = %s AND created_at >= %s
                        ORDER BY created_at DESC LIMIT 1
                    """, (owner_id, patient_id, cutoff_time))
                    result = cursor.fetchone()
                    query_id = result[0] if result else None

            if query_id:
                self.db_manager.store_query_metrics(query_id, metrics)
                logger.info(f"Métricas de qualidade armazenadas para avaliação com query_id: {query_id}")
            else:
                logger.warning("Não foi possível obter query_id para armazenar métricas da avaliação")

        except Exception as e:
            logger.error(f"Falha ao calcular ou armazenar métricas de qualidade para avaliação: {e}")

        # Atualizar o assessment_result com a resposta formatada
        assessment_result["response"] = formatted_response

        return assessment_result
    
    def generate_clinical_report(self,
                               patient_id: int,
                               owner_id: int,
                               report_type: str = "summary") -> str:
        """
        Gerar um relatório clínico para um paciente com base em informações armazenadas

        :param patient_id: ID do paciente
        :param owner_id: ID do usuário solicitando o relatório
        :param report_type: Tipo de relatório a gerar
        :return: Texto do relatório gerado
        """
        # Recuperar todos os documentos para o paciente
        # Isso seria implementado consultando o banco de dados diretamente
        # Por enquanto, criaremos um relatório modelo simples

        patient_profile = self.get_patient_profile(owner_id, patient_id)

        if not patient_profile:
            return f"Nenhuma informação encontrada para o paciente {patient_id}"

        report = f"""
RELATÓRIO CLÍNICO
================
Paciente: {patient_profile.get('first_name', 'Desconhecido')} {patient_profile.get('last_name', 'Desconhecido')}
ID: {patient_id}
Idade: {patient_profile.get('age', 'Desconhecida')}
Diagnóstico: {patient_profile.get('diagnosis', 'Não especificado')}
Criado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Informações Chave:
- {len(patient_profile.get('sensitivities', []))} registro(s) de sensibilidade identificado(s)
- Notas clínicas disponíveis no sistema

Recomendações:
- Revisar todos os documentos clínicos para compreensão completa
- Considerar os perfis sensorial e comportamental específicos do paciente
- Implementar intervenções baseadas em evidência conforme apropriado
        """.strip()

        return report


# Função de exemplo de uso
def example_usage():
    """
    Exemplo de como usar o ClinicalAISystem
    """
    try:
        # Inicializar componentes do sistema (requer variáveis de ambiente)
        db_manager = DatabaseManager()
        embedder = CachedEmbeddingGenerator()
        
        # Initialize the clinical AI system
        clinical_system = ClinicalAISystem(
            db_manager=db_manager,
            embedding_generator=embedder,
            default_model="gpt-3.5-turbo"
        )

        # Exemplo: Adicionar um documento clínico
        doc_ids = clinical_system.add_clinical_document(
            owner_id=1,
            patient_id=1,
            title="Avaliação Inicial - Lucas Silva",
            text="""
            Relatório de Avaliação: Lucas Silva
            Data: 2023-05-15
            Idade: 8 anos
            Diagnóstico: Dificuldades de aprendizagem, hipersensibilidade auditiva

            Lucas demonstra desafios com compreensão de leitura e apresenta
            hipersensibilidade a sons altos na sala de aula. Quando exposto a
            estímulos auditivos como sirenes de incêndio ou ruídos de construção,
            ele cobre os ouvidos e fica visivelmente desconfortável.

            Recomendação: Fornecer fones de ouvido com cancelamento de ruído
            durante atividades de leitura e implementar uma programação de pausas
            sensoriais a cada 30 minutos.
            """,
            source_type="assessment",
            metadata={"sensory_flags": ["auditory", "noise_sensitive"]}
        )

        print(f"Adicionado documento com {len(doc_ids)} fragmentos")

        # Exemplo de consulta
        result = clinical_system.query_clinical_system(
            query="Quais acomodações devem ser feitas para hipersensibilidade auditiva?",
            owner_id=1,
            patient_id="lucas",
            use_openai=True
        )

        print(f"\nPergunta: {result['query']}")
        print(f"Resposta: {result['response']}")
        print(f"Modelo usado: {result['model_used']}")
        print(f"Tempo de resposta: {result['response_time_ms']}ms")

        # Exemplo de avaliação
        assessment = clinical_system.run_clinical_assessment(
            query="Quais intervenções comportamentais seriam apropriadas?",
            owner_id=1,
            patient_id="lucas",
            assessment_type="behavioral"
        )

        print(f"\nAvaliação concluída em {assessment['processing_time']:.2f}s")
        print(f"Evidência recuperada: {assessment['retrieved_evidence']} documentos")
        print(f"Confiança: {assessment['confidence_score']:.2f}")

    except ValueError as e:
        print(f"Erro: {e}")
        print("Por favor, certifique-se de que todas as variáveis de ambiente necessárias estejam definidas (GOOGLE_API_KEY, OPENAI_API_KEY, DATABASE_URL)")


def test_smart_alerts():
    """
    Função de teste para verificar se o sistema de alertas inteligentes está funcionando
    """
    import os
    from database.db_manager import get_db_manager
    from utils.embedding_generator import CachedEmbeddingGenerator

    # Inicializar componentes necessários
    db_manager = get_db_manager()
    embedding_gen = CachedEmbeddingGenerator()

    # Criar instância do sistema
    ai_system = ClinicalAISystem(db_manager, embedding_gen)

    # Testar a detecção de alertas com exemplos
    test_cases = [
        {
            "query": "Avalie o progresso do paciente nos últimos meses",
            "response": "O paciente apresentou uma regressão significativa nos últimos meses, voltando a apresentar sintomas antigos e demonstrando piora clínica."
        },
        {
            "query": "Como está o estado emocional do paciente?",
            "response": "O paciente está apresentando bons resultados e melhora contínua, com avanços consistentes em todas as áreas avaliadas."
        }
    ]

    print("Testando detecção de alertas inteligentes...")

    for i, test_case in enumerate(test_cases):
        print(f"\nTeste {i+1}:")
        print(f"Consulta: {test_case['query']}")
        print(f"Resposta: {test_case['response']}")

        # Detectar alertas
        alerts = ai_system.alert_detector.detect_alerts(
            query=test_case['query'],
            response=test_case['response']
        )

        print(f"Alertas detectados: {len(alerts)}")
        for alert in alerts:
            print(f"  - Tipo: {alert['alert_type']}, Severidade: {alert['severity']}")
            print(f"    Descrição: {alert['description']}")

            # Gerar recomendações
            recommendations = ai_system.alert_detector.generate_recommendations(alert['alert_type'])
            print(f"    Recomendações: {recommendations}")


if __name__ == "__main__":
    test_smart_alerts()