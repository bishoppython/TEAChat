"""
Interface para Google Gemini API
Similar ao Guru TI, mas adaptado para contexto clínico
"""
import os
import logging
import requests
from typing import Dict, Any, Optional

# Importar a função de formatação
from utils.response_formatter import format_markdown_for_display

logger = logging.getLogger(__name__)

class GeminiInterface:
    """Interface para comunicação com Google Gemini API"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash-lite"):
        """
        Inicializa interface Gemini
        
        Args:
            api_key: Chave da API (usa GOOGLE_API_KEY do .env se não fornecida)
            model: Modelo Gemini a usar (padrão: gemini-2.5-flash-lite)
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY não configurada")
        
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
        logger.info(f"✅ Gemini Interface inicializada com modelo: {model}")
    
    def generate_response(self, 
                         prompt: str, 
                         temperature: float = 0.7,
                         max_tokens: int = 1024) -> str:
        """
        Gera resposta usando Gemini API
        
        Args:
            prompt: Prompt completo (system + context + query)
            temperature: Controla criatividade (0.0-1.0)
            max_tokens: Máximo de tokens na resposta
            
        Returns:
            Texto da resposta gerada
            
        Raises:
            Exception: Quando a API falha (quota, timeout, etc)
        """
        url = f"{self.base_url}/{self.model}:generateContent"
        
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': self.api_key
        }
        
        payload = {
            'contents': [{
                'parts': [{
                    'text': prompt
                }]
            }],
            'generationConfig': {
                'temperature': temperature,
                'topK': 40,
                'topP': 0.95,
                'maxOutputTokens': max_tokens
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()

                if 'candidates' in result and len(result['candidates']) > 0:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    logger.info(f"✅ Resposta Gemini gerada ({len(text)} chars)")

                    # Formatar a resposta para melhor apresentação
                    formatted_text = format_markdown_for_display(text, "general")
                    return formatted_text
                else:
                    logger.error("Resposta Gemini sem candidates")
                    raise Exception("Resposta inválida da API Gemini")
            elif response.status_code == 429:
                # Quota excedida - lançar exceção para fallback
                logger.error(f"Gemini quota excedida (429)")
                raise Exception("Gemini API quota exceeded (429)")
            else:
                logger.error(f"Erro Gemini API: {response.status_code}")
                raise Exception(f"Gemini API error: {response.status_code}")

        except requests.exceptions.Timeout:
            logger.error("Timeout na requisição Gemini")
            raise Exception("Timeout na comunicação com Gemini")
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de rede ao chamar Gemini: {e}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            # Re-raise para que o fallback seja ativado
            if "quota" in str(e).lower() or "429" in str(e):
                raise Exception("Gemini quota exceeded")
            raise
    
    def generate_with_rag_context(self, 
                                  rag_result: Dict[str, Any],
                                  system_prompt: Optional[str] = None) -> str:
        """
        Gera resposta usando contexto RAG
        
        Args:
            rag_result: Resultado do sistema RAG com contexto e documentos
            system_prompt: Prompt do sistema (opcional)
            
        Returns:
            Resposta gerada
        """
        # Prompt padrão para contexto clínico
        if not system_prompt:
            system_prompt = """Você é um assistente especializado em psicopedagogia clínica.

**DIRETRIZES:**
- Seja objetivo e técnico
- Use informações dos documentos fornecidos
- Cite evidências quando relevante
- Forneça recomendações práticas
- Mantenha confidencialidade e ética profissional

**FORMATO:**
1. Resposta direta à pergunta
2. Evidências dos documentos
3. Recomendações práticas (se aplicável)
"""
        
        # Extrair informações do RAG
        query = rag_result.get('query', '')
        context = rag_result.get('context', '')
        patient_info = rag_result.get('patient_info', {})
        num_docs = len(rag_result.get('retrieved_documents', []))
        
        # Construir prompt completo
        prompt_parts = [system_prompt]
        
        # Adicionar informações do paciente se disponível
        if patient_info:
            prompt_parts.append(f"\n**PACIENTE:**")
            prompt_parts.append(f"Nome: {patient_info.get('first_name', 'N/A')} {patient_info.get('last_name', '')}")
            if patient_info.get('diagnosis'):
                prompt_parts.append(f"Diagnóstico: {patient_info['diagnosis']}")
            if patient_info.get('age'):
                prompt_parts.append(f"Idade: {patient_info['age']} anos")
        
        # Adicionar contexto dos documentos
        if context:
            prompt_parts.append(f"\n**CONTEXTO DOS DOCUMENTOS ({num_docs} documento(s)):**")
            prompt_parts.append(context)
        else:
            prompt_parts.append("\n**AVISO:** Nenhum documento relevante encontrado na base.")
        
        # Adicionar pergunta do usuário
        prompt_parts.append(f"\n**PERGUNTA DO USUÁRIO:**")
        prompt_parts.append(query)
        
        prompt_parts.append("\n**SUA RESPOSTA:**")
        
        full_prompt = "\n".join(prompt_parts)
        
        # Gerar resposta
        return self.generate_response(full_prompt, temperature=0.7, max_tokens=1024)


class ClinicalGeminiInterface(GeminiInterface):
    """
    Interface Gemini especializada para contexto clínico
    Adiciona funcionalidades específicas para psicopedagogia
    """
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key, model="gemini-2.5-flash-lite")
        
        self.clinical_system_prompt = """Você é um assistente de IA especializado em psicopedagogia clínica.

**SOBRE VOCÊ:**
Você auxilia profissionais de psicopedagogia com análise de documentos clínicos, 
recomendações de intervenções e orientações baseadas em evidências.

**DIRETRIZES CLÍNICAS:**
- Mantenha confidencialidade absoluta
- Base suas respostas APENAS em evidências dos documentos fornecidos
- Seja objetivo e técnico
- Forneça recomendações práticas e aplicáveis
- Cite fontes quando relevante
- Nunca faça diagnósticos - apenas analise informações existentes

**⚠️ REGRA CRÍTICA DE PRIVACIDADE:**
- Se o contexto mencionar um paciente específico, responda APENAS sobre esse paciente
- NUNCA mencione informações de outros pacientes
- NUNCA misture dados de pacientes diferentes
- Se não houver informações suficientes sobre o paciente específico, diga claramente

**FORMATO DE RESPOSTA:**
1. **Análise:** Resposta direta baseada nos documentos DO PACIENTE ESPECÍFICO
2. **Evidências:** Citações relevantes dos documentos DESTE PACIENTE
3. **Recomendações:** Sugestões práticas (se aplicável)

Seja conciso mas completo. Máximo 3-4 parágrafos.
"""
    
    def generate_clinical_response(self, rag_result: Dict[str, Any]) -> str:
        """
        Gera resposta clínica usando o prompt especializado
        
        Args:
            rag_result: Resultado do RAG com contexto
            
        Returns:
            Resposta clínica formatada
        """
        return self.generate_with_rag_context(
            rag_result, 
            system_prompt=self.clinical_system_prompt
        )
    
    def generate_assessment_report(self, 
                                   patient_info: Dict[str, Any],
                                   documents_summary: str) -> str:
        """
        Gera relatório de avaliação
        
        Args:
            patient_info: Informações do paciente
            documents_summary: Resumo dos documentos
            
        Returns:
            Relatório formatado
        """
        prompt = f"""{self.clinical_system_prompt}

**TAREFA:** Gerar relatório de avaliação clínica

**PACIENTE:**
Nome: {patient_info.get('first_name', 'N/A')} {patient_info.get('last_name', '')}
Idade: {patient_info.get('age', 'N/A')} anos
Diagnóstico: {patient_info.get('diagnosis', 'Não especificado')}

**DOCUMENTOS DISPONÍVEIS:**
{documents_summary}

**GERE UM RELATÓRIO ESTRUTURADO COM:**
1. Resumo do perfil do paciente
2. Principais achados dos documentos
3. Áreas de atenção
4. Recomendações de intervenção

Seja objetivo e profissional.
"""
        
        return self.generate_response(prompt, temperature=0.5, max_tokens=1500)


# Função helper para uso fácil
def create_gemini_interface() -> ClinicalGeminiInterface:
    """
    Cria instância da interface Gemini
    
    Returns:
        Interface Gemini configurada
    """
    try:
        return ClinicalGeminiInterface()
    except ValueError as e:
        logger.error(f"Erro ao criar interface Gemini: {e}")
        raise
