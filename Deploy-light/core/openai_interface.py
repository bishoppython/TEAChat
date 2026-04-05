"""
OpenAI integration module for clinical psychology RAG system
Handles interaction with OpenAI API for clinical response generation
"""
import os
import logging
from typing import List, Dict, Any, Optional
import openai
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIClient:
    """
    Client for interacting with OpenAI API
    """
    
    def __init__(self, api_key: Optional[str] = None, organization: Optional[str] = None):
        """
        Initialize OpenAI client
        
        :param api_key: OpenAI API key (if not provided, will use OPENAI_API_KEY environment variable)
        :param organization: OpenAI organization ID (optional)
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.api_key = api_key
        self.organization = organization or os.getenv("OPENAI_ORGANIZATION")
        
        # Configure OpenAI client
        openai.api_key = self.api_key
        if self.organization:
            openai.organization = self.organization
        
        # Test connection
        try:
            # Use new OpenAI client format
            client = openai.OpenAI(api_key=self.api_key, organization=self.organization)
            # Try a simple model listing to test connection
            client.models.list()
            logger.info("Successfully connected to OpenAI API")
            self.client = client
        except Exception as e:
            logger.error(f"Could not connect to OpenAI API: {e}")
            # Don't raise exception, just log the error and set client to None
            self.client = None
            # The system can work with only Google Gemini if OpenAI is not available
    
    def generate(self, 
                model: str = "gpt-3.5-turbo", 
                messages: List[Dict[str, str]] = None,
                system_prompt: str = None,
                user_prompt: str = None,
                temperature: float = 0.7,
                max_tokens: int = 500,
                top_p: float = 1.0,
                frequency_penalty: float = 0.0,
                presence_penalty: float = 0.0) -> str:
        """
        Generate text using OpenAI API
        
        :param model: Model name to use (gpt-3.5-turbo, gpt-4, etc.)
        :param messages: List of messages in the conversation format
        :param system_prompt: System prompt (will be converted to message format)
        :param user_prompt: User prompt (will be converted to message format if messages not provided)
        :param temperature: Sampling temperature
        :param max_tokens: Maximum tokens in response
        :param top_p: Top-p sampling
        :param frequency_penalty: Frequency penalty
        :param presence_penalty: Presence penalty
        :return: Generated text
        """
        # Check if client is available
        if self.client is None:
            return "OpenAI client not available. API connection failed during initialization."

        # Prepare messages if not provided
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if user_prompt:
                messages.append({"role": "user", "content": user_prompt})

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating with OpenAI: {e}")
            return f"Error generating response: {str(e)}"


class ClinicalOpenAIInterface:
    """
    Interface for using OpenAI models in clinical psychology applications
    """
    
    def __init__(self, openai_client: OpenAIClient, default_model: str = "gpt-3.5-turbo"):
        """
        Initialize the clinical OpenAI interface
        
        :param openai_client: OpenAI client instance
        :param default_model: Default model to use
        """
        self.openai = openai_client
        self.default_model = default_model
    
    def generate_clinical_response(self, 
                                 context: str, 
                                 query: str, 
                                 patient_info: Dict[str, Any] = None,
                                 model: str = None,
                                 temperature: float = 0.3) -> str:
        """
        Generate a clinical response using OpenAI with context and patient info
        
        :param context: Retrieved context from RAG system
        :param query: User query
        :param patient_info: Patient information
        :param model: Model to use (defaults to instance default)
        :param temperature: Generation temperature
        :return: Generated response
        """
        model = model or self.default_model
        
        # Build system prompt
        system_prompt = "Você é um assistente clínico especializado para psicopedagogos. "
        system_prompt += "Use APENAS as informações fornecidas na seção de contexto para responder às perguntas. "
        system_prompt += "Se o contexto não contiver informações relevantes, afirme isso claramente. "
        system_prompt += "Mantenha sempre um tom profissional e empático. "
        system_prompt += "Não faça diagnósticos definitivos, mas sugira intervenções baseadas em evidências com base no perfil do paciente."
        
        # Add patient-specific information to system prompt if available
        if patient_info:
            patient_details = (
                f"Informações do Paciente:\n"
                f"- Nome: {patient_info.get('first_name', 'Desconhecido')} {patient_info.get('last_name', '')}\n"
                f"- Idade: {patient_info.get('age', 'Desconhecida')}\n"
                f"- Diagnóstico: {patient_info.get('diagnosis', 'Não especificado')}\n\n"
            )
            system_prompt += patient_details
        
        # Build user prompt with context
        user_prompt = f"Contexto:\n{context}\n\nPergunta: {query}"
        
        # Generate response using OpenAI
        response = self.openai.generate(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=500
        )
        
        return response
    
    def generate_with_rag_context(self, 
                                rag_result: Dict[str, Any], 
                                model: str = None,
                                temperature: float = 0.3) -> str:
        """
        Generate response using the full RAG result
        
        :param rag_result: Full result from RAG system query
        :param model: Model to use (defaults to instance default)
        :param temperature: Generation temperature
        :return: Generated response
        """
        context = rag_result.get('context', '')
        query = rag_result.get('query', '')
        patient_info = rag_result.get('patient_info', None)
        
        return self.generate_clinical_response(
            context=context,
            query=query,
            patient_info=patient_info,
            model=model,
            temperature=temperature
        )
    
    def batch_generate(self, 
                      queries: List[Dict[str, Any]], 
                      model: str = None) -> List[str]:
        """
        Generate responses for multiple queries (sequentially since OpenAI doesn't support true batch)
        
        :param queries: List of dictionaries with 'context', 'query', 'patient_info'
        :param model: Model to use (defaults to instance default)
        :return: List of generated responses
        """
        responses = []
        
        for query_data in queries:
            context = query_data.get('context', '')
            query = query_data.get('query', '')
            patient_info = query_data.get('patient_info', None)
            
            response = self.generate_clinical_response(
                context=context,
                query=query,
                patient_info=patient_info,
                model=model
            )
            responses.append(response)
        
        return responses
    
    def evaluate_model_response(self, 
                              query: str, 
                              response: str, 
                              reference: str = None) -> Dict[str, float]:
        """
        Basic evaluation of model response quality
        In a real implementation, you would use more sophisticated metrics
        
        :param query: Original query
        :param response: Model response
        :param reference: Reference response (if available)
        :return: Evaluation metrics
        """
        metrics = {
            "response_length": len(response),
            "contains_query_terms": any(term.lower() in response.lower() for term in query.split()[:5]) if query else False,
            "has_clinical_keywords": any(
                word in response.lower() for word in 
                ["intervenção", "acomodação", "comportamento", "recomendação", "estratégia", "apoio", "avaliação", "terapia"]
            )
        }
        
        # If reference is provided, calculate basic similarity (very basic)
        if reference:
            # Simple overlap-based similarity
            response_words = set(response.lower().split())
            reference_words = set(reference.lower().split())
            overlap = len(response_words.intersection(reference_words))
            total = len(response_words.union(reference_words))
            metrics["similarity_to_reference"] = overlap / total if total > 0 else 0
        
        return metrics


# Example usage function
def example_usage():
    """
    Example of how to use the ClinicalOpenAIInterface
    """
    try:
        # Initialize OpenAI client and interface
        openai_client = OpenAIClient()  # Assumes OPENAI_API_KEY is set in environment
        
        interface = ClinicalOpenAIInterface(openai_client, default_model="gpt-3.5-turbo")
        
        # Example RAG result (simulated)
        rag_result = {
            "query": "Quais acomodações devem ser feitas para hipersensibilidade auditiva?",
            "context": "Paciente demonstra hipersensibilidade a estímulos auditivos, particularmente sons altos que causam desconforto.",
            "patient_info": {
                "first_name": "Lucas",
                "last_name": "Silva",
                "age": 8,
                "diagnosis": "Dificuldades de aprendizagem, hipersensibilidade auditiva"
            }
        }
        
        print("Gerando resposta clínica com OpenAI...")
        response = interface.generate_with_rag_context(rag_result)
        
        print(f"Pergunta: {rag_result['query']}")
        print(f"Resposta: {response}")
        
        # Evaluate the response
        evaluation = interface.evaluate_model_response(
            query=rag_result['query'],
            response=response
        )
        
        print("\nAvaliação da resposta:")
        for metric, value in evaluation.items():
            print(f"  {metric}: {value}")
    
    except ValueError as e:
        print(f"Erro: {e}")
        print("Por favor, certifique-se de que a variável OPENAI_API_KEY está definida.")


if __name__ == "__main__":
    example_usage()