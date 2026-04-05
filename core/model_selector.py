"""
Módulo para seleção inteligente de modelos com fallback automático entre Gemini e OpenAI.
Fallback para modelos locais está DESATIVADO.
"""
import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .gemini_interface import ClinicalGeminiInterface
from .openai_interface import ClinicalOpenAIInterface, OpenAIClient

# Configurar logger antes dos imports condicionais
logger = logging.getLogger(__name__)


class ModelSelector:
    """
    Selecionador inteligente de modelos com fallback automático entre Gemini e OpenAI.
    Modelos locais estão DESATIVADOS.
    """

    def __init__(self, gemini_interface: ClinicalGeminiInterface, openai_interface: ClinicalOpenAIInterface = None):
        """
        Inicializa o selecionador de modelos

        :param gemini_interface: Interface do Gemini
        :param openai_interface: Interface do OpenAI (opcional)
        """
        self.gemini_interface = gemini_interface
        self.openai_interface = openai_interface


        # Métricas de desempenho para cada modelo
        self.model_performance = {
            'gemini': {
                'success_count': 0,
                'failure_count': 0,
                'avg_response_time': 0.0,
                'last_used': None
            },
            'openai': {
                'success_count': 0,
                'failure_count': 0,
                'avg_response_time': 0.0,
                'last_used': None
            }
        }

        # Histórico de inferências para aprendizado
        self.inference_history = []

        logger.info("✅ ModelSelector inicializado com interfaces de Gemini e OpenAI")
    
    def _calculate_model_score(self, model_name: str) -> float:
        """
        Calcula pontuação para um modelo baseado em métricas de desempenho

        :param model_name: Nome do modelo ('gemini', 'openai')
        :return: Pontuação do modelo (quanto maior, melhor)
        """
        metrics = self.model_performance[model_name]

        # Evitar divisão por zero
        total_requests = metrics['success_count'] + metrics['failure_count']
        if total_requests == 0:
            # Se o modelo nunca foi usado, dar uma pontuação base
            if model_name == 'openai':
                return 0.8  # OpenAI tem prioridade inicial
            else:
                return 0.7  # Gemini tem pontuação inicial um pouco menor que OpenAI

        # Taxa de sucesso
        success_rate = metrics['success_count'] / total_requests if total_requests > 0 else 0

        # Incentivar uso balanceado dos modelos
        time_since_last_use = 0
        if metrics['last_used']:
            time_since_last_use = (datetime.now() - metrics['last_used']).total_seconds()

        # Calcular pontuação combinando taxa de sucesso e tempo desde último uso
        score = success_rate * 0.7 + (time_since_last_use / 3600) * 0.3  # Incentivar uso balanceado

        return score
    
    def _update_metrics(self, model_name: str, success: bool, response_time: float):
        """
        Atualiza as métricas de desempenho para um modelo
        
        :param model_name: Nome do modelo ('gemini' ou 'openai')
        :param success: Se a requisição foi bem-sucedida
        :param response_time: Tempo de resposta em segundos
        """
        metrics = self.model_performance[model_name]
        
        if success:
            metrics['success_count'] += 1
            # Atualizar média de tempo de resposta
            total_requests = metrics['success_count'] + metrics['failure_count']
            metrics['avg_response_time'] = (
                (metrics['avg_response_time'] * (total_requests - 1) + response_time) / total_requests
            )
        else:
            metrics['failure_count'] += 1
        
        metrics['last_used'] = datetime.now()
    
    def _select_best_model(self) -> Tuple[str, Any]:
        """
        Seleciona o melhor modelo com base nas métricas de desempenho

        :return: Tupla com nome do modelo e interface correspondente
        """
        gemini_score = self._calculate_model_score('gemini')
        openai_score = self._calculate_model_score('openai') if self.openai_interface else 0

        logger.info(f"Pontuações dos modelos - Gemini: {gemini_score:.3f}, OpenAI: {openai_score:.3f}")

        # Priorizar OpenAI consistentemente, mesmo com pontuações semelhantes
        # Criar uma lista de modelos com suas pontuações e prioridades
        models_scores = []

        if self.openai_interface:
            models_scores.append(('openai', openai_score, self.openai_interface))
        models_scores.append(('gemini', gemini_score, self.gemini_interface))

        # Ordenar por pontuação (decrescente) e por prioridade (OpenAI primeiro quando empate)
        # Atribuir prioridade numérica: OpenAI=1, Gemini=2 (menor número tem maior prioridade)
        def get_priority(model_name):
            if model_name == 'openai':
                return 1
            else:  # gemini
                return 2

        # Ordenar primeiro por pontuação (decrescente), depois por prioridade (crescente)
        models_scores.sort(key=lambda x: (-x[1], get_priority(x[0])))

        best_model, best_score, best_interface = models_scores[0]

        return best_model, best_interface
    
    def generate_response(self, 
                         rag_result: Dict[str, Any], 
                         fallback_enabled: bool = True) -> Tuple[str, str]:
        """
        Gera resposta usando o melhor modelo disponível
        
        :param rag_result: Resultado do sistema RAG
        :param fallback_enabled: Se deve usar fallback para o outro modelo em caso de falha
        :return: Tupla com resposta gerada e nome do modelo usado
        """
        # Selecionar o melhor modelo inicial
        primary_model, primary_interface = self._select_best_model()
        
        logger.info(f"Tentando gerar resposta com modelo primário: {primary_model}")
        
        # Tentar com o modelo primário
        start_time = time.time()
        try:
            if primary_model == 'gemini':
                response = primary_interface.generate_clinical_response(rag_result)
            elif primary_model == 'openai':
                response = primary_interface.generate_with_rag_context(rag_result)
            else:  # caso não seja gemini nem openai
                # Serviço não disponível, vamos retornar uma mensagem indicando isso
                response = "Serviço não está mais disponível."
                primary_model = "service_unavailable"

            response_time = time.time() - start_time

            # Atualizar métricas com sucesso
            self._update_metrics(primary_model, True, response_time)

            # Registrar inferência no histórico
            self._log_inference(primary_model, rag_result.get('query', ''), len(response), response_time, True)

            logger.info(f"✅ Resposta gerada com sucesso usando {primary_model}")
            return response, primary_model

        except Exception as e:
            response_time = time.time() - start_time
            logger.warning(f"Falha ao gerar resposta com {primary_model}: {str(e)[:100]}...")

            # Atualizar métricas com falha
            self._update_metrics(primary_model, False, response_time)

            # Registrar inferência com falha
            self._log_inference(primary_model, rag_result.get('query', ''), 0, response_time, False, str(e))

            # Se fallback estiver habilitado e tivermos outro modelo disponível
            if fallback_enabled:
                # Tentar com os outros modelos
                available_models = []

                if primary_model != 'gemini' and self.gemini_interface:
                    available_models.append(('gemini', self.gemini_interface))
                if primary_model != 'openai' and self.openai_interface:
                    available_models.append(('openai', self.openai_interface))

                for fallback_model, fallback_interface in available_models:
                    logger.info(f"Tentando fallback para modelo: {fallback_model}")

                    start_time = time.time()
                    try:
                        if fallback_model == 'gemini':
                            response = fallback_interface.generate_clinical_response(rag_result)
                        elif fallback_model == 'openai':
                            response = fallback_interface.generate_with_rag_context(rag_result)

                        response_time = time.time() - start_time

                        # Atualizar métricas do fallback com sucesso
                        self._update_metrics(fallback_model, True, response_time)

                        # Registrar inferência no histórico
                        self._log_inference(fallback_model, rag_result.get('query', ''), len(response), response_time, True)

                        logger.info(f"✅ Resposta gerada com sucesso usando fallback {fallback_model}")
                        return response, fallback_model

                    except Exception as fallback_error:
                        response_time = time.time() - start_time
                        logger.error(f"Falha no fallback para {fallback_model}: {str(fallback_error)[:100]}...")

                        # Atualizar métricas do fallback com falha
                        self._update_metrics(fallback_model, False, response_time)

                        # Registrar inferência com falha
                        self._log_inference(fallback_model, rag_result.get('query', ''), 0, response_time, False, str(fallback_error))

            # Se todos os modelos falharem (Gemini e OpenAI), retornar mensagem de erro
            error_msg = f"Falha ao gerar resposta com {primary_model}."
            if fallback_enabled:
                error_msg += f" Fallback (Gemini/OpenAI) também falhou."
            
            # Fallback local está DESATIVADO
            error_msg += " Modelos locais estão DESATIVADOS."
            
            logger.error(f"❌ {error_msg}")
            raise RuntimeError(f"{error_msg} Configure Gemini ou OpenAI.")
    
    def _log_inference(self, model_name: str, query: str, response_length: int, 
                      response_time: float, success: bool, error: str = None):
        """
        Registra uma inferência no histórico para aprendizado
        
        :param model_name: Nome do modelo usado
        :param query: Consulta do usuário
        :param response_length: Tamanho da resposta gerada
        :param response_time: Tempo de resposta
        :param success: Se a inferência foi bem-sucedida
        :param error: Mensagem de erro (se houver)
        """
        inference_record = {
            'timestamp': datetime.now(),
            'model': model_name,
            'query_preview': query[:100] if query else '',
            'response_length': response_length,
            'response_time': response_time,
            'success': success,
            'error': error
        }
        
        self.inference_history.append(inference_record)
        
        # Manter apenas as últimas 1000 inferências para evitar consumo excessivo de memória
        if len(self.inference_history) > 1000:
            self.inference_history = self.inference_history[-1000:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de desempenho dos modelos

        :return: Dicionário com estatísticas de desempenho
        """
        stats = {}

        for model_name in ['gemini', 'openai']:
            # Pular modelos que não estão disponíveis
            if model_name == 'openai' and not self.openai_interface:
                continue

            metrics = self.model_performance[model_name]
            total_requests = metrics['success_count'] + metrics['failure_count']

            stats[model_name] = {
                'total_requests': total_requests,
                'success_count': metrics['success_count'],
                'failure_count': metrics['failure_count'],
                'success_rate': metrics['success_count'] / total_requests if total_requests > 0 else 0,
                'avg_response_time': metrics['avg_response_time'],
                'last_used': metrics['last_used'].isoformat() if metrics['last_used'] else None,
                'current_score': self._calculate_model_score(model_name)
            }

        return stats
    
    def get_model_recommendation(self, query: str = None) -> str:
        """
        Retorna a recomendação atual de modelo com base nas métricas

        :param query: Consulta (opcional, pode ser usada para lógica mais avançada no futuro)
        :return: Nome do modelo recomendado
        """
        gemini_score = self._calculate_model_score('gemini')
        openai_score = self._calculate_model_score('openai') if self.openai_interface else 0

        # Encontrar o modelo com a maior pontuação
        best_model = 'gemini'
        best_score = gemini_score

        if self.openai_interface and openai_score > best_score:
            best_model = 'openai'
            best_score = openai_score

        return best_model