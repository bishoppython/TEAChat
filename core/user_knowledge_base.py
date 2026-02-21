"""
Sistema de Base de Conhecimento por Usuário
Similar ao Guru TI, mas com isolamento por owner_id
Mantém contexto sempre disponível para cada usuário
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class UserKnowledgeBase:
    """
    Gerencia base de conhecimento específica de cada usuário
    Mantém índice em memória para acesso rápido (similar ao Guru TI)
    """
    
    def __init__(self, db_manager):
        """
        Inicializa a base de conhecimento do usuário
        
        Args:
            db_manager: Instância do DatabaseManager
        """
        self.db_manager = db_manager
        self.user_indexes = {}  # Cache de índices por owner_id
        self.last_refresh = {}  # Timestamp da última atualização
        
    def build_user_index(self, owner_id: int, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Constrói índice de documentos do usuário para acesso rápido
        
        Args:
            owner_id: ID do usuário
            force_refresh: Forçar reconstrução do índice
            
        Returns:
            Dicionário com estatísticas e índices
        """
        # Verificar se precisa atualizar (cache de 5 minutos)
        if not force_refresh and owner_id in self.user_indexes:
            last_update = self.last_refresh.get(owner_id)
            if last_update and (datetime.now() - last_update).seconds < 300:
                return self.user_indexes[owner_id]
        
        logger.info(f"Construindo índice para owner_id: {owner_id}")
        
        # Buscar todos os documentos do usuário
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Buscar documentos
                cursor.execute("""
                    SELECT id, patient_id, title, text, source_type, metadata, chunk_order
                    FROM documents
                    WHERE owner_id = %s
                    ORDER BY created_at DESC
                """, (owner_id,))

                documents = cursor.fetchall()
                
                # Buscar pacientes
                cursor.execute("""
                    SELECT id, first_name, last_name, diagnosis, age
                    FROM patients
                    WHERE owner_id = %s
                """, (owner_id,))

                patients = cursor.fetchall()
        
        # Construir índices
        index = {
            'owner_id': owner_id,
            'total_documents': len(documents),
            'total_patients': len(patients),
            'documents_by_patient': {},
            'documents_by_type': {},
            'patients_index': {},
            'recent_documents': [],
            'full_context': ""
        }
        
        # Indexar pacientes
        for patient in patients:
            patient_data = {
                'id': patient[0],
                'patient_id': patient[0],  # Use the id as patient_id since patient_id column no longer exists
                'name': f"{patient[1]} {patient[2]}".strip(),
                'diagnosis': patient[3],
                'age': patient[4]
            }
            index['patients_index'][patient[0]] = patient_data
        
        # Indexar documentos
        for doc in documents:
            doc_id, patient_id, title, text, source_type, metadata, chunk_order = doc
            
            # Por paciente
            if patient_id not in index['documents_by_patient']:
                index['documents_by_patient'][patient_id] = []
            
            index['documents_by_patient'][patient_id].append({
                'id': doc_id,
                'title': title,
                'text': text[:200] + '...' if len(text) > 200 else text,
                'source_type': source_type,
                'chunk_order': chunk_order
            })
            
            # Por tipo
            if source_type not in index['documents_by_type']:
                index['documents_by_type'][source_type] = 0
            index['documents_by_type'][source_type] += 1
            
            # Documentos recentes (últimos 10)
            if len(index['recent_documents']) < 10:
                index['recent_documents'].append({
                    'title': title,
                    'patient_id': patient_id,
                    'text_preview': text[:100] + '...' if len(text) > 100 else text
                })
        
        # Construir contexto geral (resumo da base do usuário)
        # NOTA: Este contexto é usado apenas quando NÃO há patient_id específico
        context_parts = [
            f"📊 Base de Conhecimento do Usuário (ID: {owner_id})",
            f"Total de documentos: {index['total_documents']}",
            f"Total de pacientes: {index['total_patients']}",
            ""
        ]
        
        if index['patients_index']:
            context_parts.append("👥 Pacientes cadastrados:")
            for pid, patient_data in list(index['patients_index'].items())[:5]:
                context_parts.append(
                    f"  • {patient_data['name']} (ID: {pid}) - "
                    f"{patient_data['diagnosis'] or 'Sem diagnóstico'}"
                )
            context_parts.append("")
            context_parts.append("⚠️ Para consultas específicas, selecione um paciente.")
            context_parts.append("")
        
        if index['documents_by_type']:
            context_parts.append("📁 Tipos de documentos:")
            for doc_type, count in index['documents_by_type'].items():
                context_parts.append(f"  • {doc_type}: {count} documento(s)")
            context_parts.append("")
        
        index['full_context'] = "\n".join(context_parts)
        
        # Salvar no cache
        self.user_indexes[owner_id] = index
        self.last_refresh[owner_id] = datetime.now()
        
        logger.info(f"✅ Índice construído: {index['total_documents']} docs, {index['total_patients']} pacientes")
        
        return index
    
    def get_user_context(self, owner_id: int, patient_id: Optional[int] = None) -> str:
        """
        Obtém contexto completo do usuário (similar ao Guru TI)
        
        Args:
            owner_id: ID do usuário
            patient_id: ID do paciente (opcional, para filtrar)
            
        Returns:
            String com contexto formatado
        """
        index = self.build_user_index(owner_id)
        
        if patient_id:
            # IMPORTANTE: Contexto APENAS do paciente específico
            patient_docs = index['documents_by_patient'].get(patient_id, [])
            patient_info = index['patients_index'].get(patient_id, {})
            
            if not patient_info:
                # Paciente não encontrado
                return f"⚠️ Paciente ID {patient_id} não encontrado na base do usuário {owner_id}"
            
            context = [
                f"📋 **CONTEXTO RESTRITO AO PACIENTE:**",
                f"Nome: {patient_info.get('name', 'Desconhecido')}",
                f"ID: {patient_id}",
                f"Diagnóstico: {patient_info.get('diagnosis', 'Não especificado')}",
                f"Idade: {patient_info.get('age', 'N/A')} anos",
                f"Total de documentos deste paciente: {len(patient_docs)}",
                "",
                "⚠️ **IMPORTANTE:** Responda APENAS com informações deste paciente específico.",
                "NÃO mencione outros pacientes ou documentos de outros pacientes.",
                ""
            ]
            
            # Adicionar resumo dos documentos APENAS deste paciente
            if patient_docs:
                context.append("📄 Documentos disponíveis para este paciente:")
                for doc in patient_docs[:5]:  # Limitar a 5 para não sobrecarregar
                    context.append(f"  • {doc['title']}: {doc['text']}")
                
                if len(patient_docs) > 5:
                    context.append(f"  ... e mais {len(patient_docs) - 5} documento(s) deste paciente")
            else:
                context.append("⚠️ Nenhum documento encontrado para este paciente específico.")
            
            return "\n".join(context)
        else:
            # Contexto geral do usuário (quando não especifica paciente)
            return index['full_context']
    
    def get_statistics(self, owner_id: int) -> Dict[str, Any]:
        """
        Obtém estatísticas da base do usuário

        Args:
            owner_id: ID do usuário

        Returns:
            Dicionário com estatísticas
        """
        index = self.build_user_index(owner_id)

        # Obter contagem de avaliações clínicas com resposta
        total_assessments = 0
        try:
            assessments = self.db_manager.get_clinical_assessments(owner_id, None, limit=10000, offset=0)
            # Contar apenas avaliações que têm resposta (campo 'response' não vazio)
            total_assessments = len([a for a in assessments if a.get('response', '').strip() != ''])
        except Exception as e:
            logger.error(f"Erro ao obter contagem de avaliações clínicas: {e}")

        # Obter contagem de consultas (baseado em auditoria)
        total_queries = 0
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) FROM audit_log
                        WHERE user_id = %s
                    """, (owner_id,))
                    total_queries = cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Erro ao obter contagem de consultas: {e}")

        # Obter contagem de uploads de documentos
        total_uploads = 0
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) FROM file_uploads
                        WHERE user_id = %s
                    """, (owner_id,))
                    total_uploads = cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Erro ao obter contagem de uploads: {e}")

        return {
            'total_documents': index['total_documents'],
            'total_patients': index['total_patients'],
            'total_assessments': total_assessments,
            'total_queries': total_queries,
            'total_uploads': total_uploads,
            'documents_by_type': index['documents_by_type'],
            'patients': list(index['patients_index'].values()),
            'recent_documents': index['recent_documents']
        }
    
    def search_in_user_base(self, owner_id: int, query: str, patient_id: Optional[int] = None) -> List[Dict]:
        """
        Busca textual simples na base do usuário (fallback quando embeddings falham)
        
        Args:
            owner_id: ID do usuário
            query: Texto de busca
            patient_id: ID do paciente (opcional)
            
        Returns:
            Lista de documentos encontrados
        """
        index = self.build_user_index(owner_id)
        query_lower = query.lower()
        results = []
        
        # Determinar onde buscar
        if patient_id and patient_id in index['documents_by_patient']:
            search_docs = index['documents_by_patient'][patient_id]
        else:
            # Buscar em todos os documentos do usuário
            search_docs = []
            for patient_docs in index['documents_by_patient'].values():
                search_docs.extend(patient_docs)
        
        # Busca simples por palavra-chave
        for doc in search_docs:
            if query_lower in doc['title'].lower() or query_lower in doc['text'].lower():
                results.append(doc)
        
        return results
    
    def refresh_user_index(self, owner_id: int):
        """
        Força atualização do índice do usuário
        
        Args:
            owner_id: ID do usuário
        """
        self.build_user_index(owner_id, force_refresh=True)
        logger.info(f"Índice do usuário {owner_id} atualizado")
    
    def clear_cache(self, owner_id: Optional[int] = None):
        """
        Limpa cache de índices
        
        Args:
            owner_id: ID do usuário (None para limpar todos)
        """
        if owner_id:
            if owner_id in self.user_indexes:
                del self.user_indexes[owner_id]
                del self.last_refresh[owner_id]
                logger.info(f"Cache do usuário {owner_id} limpo")
        else:
            self.user_indexes.clear()
            self.last_refresh.clear()
            logger.info("Cache de todos os usuários limpo")
