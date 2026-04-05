"""
Gerador de Respostas Local (Fallback)
Quando APIs do Gemini/OpenAI falham, gera resposta baseada apenas no contexto RAG
"""
import logging
from typing import Dict, Any, List

# Importar a função de formatação
from utils.response_formatter import format_markdown_for_display

logger = logging.getLogger(__name__)

class LocalResponseGenerator:
    """
    Gera respostas estruturadas baseadas apenas no contexto RAG
    Não usa LLM - apenas formatação inteligente do contexto
    """
    
    def __init__(self):
        logger.info("✅ Local Response Generator inicializado (fallback para APIs)")
    
    def generate_response_from_rag(self, rag_result: Dict[str, Any]) -> str:
        """
        Gera resposta estruturada baseada no resultado RAG
        
        Args:
            rag_result: Resultado do sistema RAG
            
        Returns:
            Resposta formatada em texto
        """
        query = rag_result.get('query', '')
        context = rag_result.get('context', '')
        documents = rag_result.get('retrieved_documents', [])
        patient_info = rag_result.get('patient_info', {})
        
        # Construir resposta estruturada
        response_parts = []
        
        # Cabeçalho
        response_parts.append("📋 **Análise Baseada nos Documentos:**\n")
        
        # Informações do paciente (se disponível)
        if patient_info:
            patient_name = f"{patient_info.get('first_name', '')} {patient_info.get('last_name', '')}".strip()
            if patient_name:
                response_parts.append(f"**Paciente:** {patient_name}")
            
            if patient_info.get('diagnosis'):
                response_parts.append(f"**Diagnóstico:** {patient_info['diagnosis']}")
            
            if patient_info.get('age'):
                response_parts.append(f"**Idade:** {patient_info['age']} anos")
            
            response_parts.append("")
            response_parts.append("⚠️ **Nota:** Esta análise contém APENAS informações deste paciente específico.")
            response_parts.append("")
        
        # Resumo dos documentos encontrados
        if documents:
            response_parts.append(f"**Documentos Relevantes Encontrados:** {len(documents)}\n")
            
            # Extrair informações-chave dos documentos
            key_points = self._extract_key_points(documents, query)
            
            if key_points:
                response_parts.append("**Informações Relevantes:**")
                for i, point in enumerate(key_points[:5], 1):  # Limitar a 5 pontos
                    response_parts.append(f"{i}. {point}")
                response_parts.append("")
            
            # Adicionar trechos dos documentos
            response_parts.append("**Contexto dos Documentos:**")
            for i, doc in enumerate(documents[:3], 1):  # Mostrar até 3 documentos
                title = doc.get('title', 'Documento sem título')
                text = doc.get('text', '')[:200]  # Primeiros 200 chars
                similarity = doc.get('similarity', 0)
                
                response_parts.append(f"\n📄 **{i}. {title}** (Relevância: {similarity:.0%})")
                response_parts.append(f"   {text}...")
            
            response_parts.append("")
        else:
            response_parts.append("⚠️ **Nenhum documento relevante encontrado na base de dados.**\n")
            response_parts.append("Sugestões:")
            response_parts.append("- Verifique se há documentos cadastrados para este paciente")
            response_parts.append("- Tente reformular a pergunta")
            response_parts.append("- Adicione mais documentos à base de conhecimento\n")
        
        # Rodapé
        response_parts.append("---")
        response_parts.append("💡 **Nota:** Esta resposta foi gerada localmente baseada nos documentos disponíveis.")
        response_parts.append("Para análises mais detalhadas, aguarde a disponibilidade da API de IA.")
        
        # Formatar a resposta para melhor apresentação
        raw_response = "\n".join(response_parts)
        formatted_response = format_markdown_for_display(raw_response, "general")
        return formatted_response

    def _extract_key_points(self, documents: List[Dict], query: str) -> List[str]:
        """
        Extrai pontos-chave dos documentos relevantes à query
        
        Args:
            documents: Lista de documentos
            query: Query do usuário
            
        Returns:
            Lista de pontos-chave
        """
        key_points = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        for doc in documents:
            text = doc.get('text', '')
            
            # Dividir em sentenças
            sentences = text.split('.')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                sentence_lower = sentence.lower()
                
                # Verificar se a sentença contém palavras da query
                sentence_words = set(sentence_lower.split())
                overlap = query_words.intersection(sentence_words)
                
                # Se houver overlap significativo, adicionar como ponto-chave
                if len(overlap) >= 1 and len(sentence) > 20:
                    # Limpar e formatar
                    clean_sentence = sentence[:150]  # Limitar tamanho
                    if clean_sentence not in key_points:
                        key_points.append(clean_sentence)
                
                # Limitar a 10 pontos-chave
                if len(key_points) >= 10:
                    break
            
            if len(key_points) >= 10:
                break
        
        return key_points
    
    def generate_summary_response(self, 
                                  total_docs: int, 
                                  context_preview: str,
                                  patient_info: Dict[str, Any] = None) -> str:
        """
        Gera resposta de resumo quando não há documentos específicos
        
        Args:
            total_docs: Total de documentos na base
            context_preview: Preview do contexto
            patient_info: Informações do paciente
            
        Returns:
            Resposta formatada
        """
        response_parts = []
        
        response_parts.append("📊 **Resumo da Base de Conhecimento:**\n")
        
        if patient_info:
            patient_name = f"{patient_info.get('first_name', '')} {patient_info.get('last_name', '')}".strip()
            if patient_name:
                response_parts.append(f"**Paciente:** {patient_name}")
            
            if patient_info.get('diagnosis'):
                response_parts.append(f"**Diagnóstico:** {patient_info['diagnosis']}")
            
            response_parts.append("")
        
        response_parts.append(f"**Total de documentos disponíveis:** {total_docs}")
        response_parts.append("")
        
        if context_preview:
            response_parts.append("**Preview do Contexto:**")
            response_parts.append(context_preview[:300] + "...")
            response_parts.append("")
        
        response_parts.append("💡 **Dica:** Faça perguntas específicas sobre o paciente para obter informações mais relevantes.")
        
        return "\n".join(response_parts)


# Instância global
local_generator = LocalResponseGenerator()


def generate_local_response(rag_result: Dict[str, Any]) -> str:
    """
    Função helper para gerar resposta local
    
    Args:
        rag_result: Resultado do RAG
        
    Returns:
        Resposta formatada
    """
    return local_generator.generate_response_from_rag(rag_result)
