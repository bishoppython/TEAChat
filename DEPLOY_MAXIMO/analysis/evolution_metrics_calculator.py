"""
Módulo de cálculo de métricas de evolução clínica
Calcula métricas específicas para análise de progresso terapêutico
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
import re
from collections import Counter

from analysis.data_classes import SessionData

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EvolutionMetricsCalculator:
    """
    Calculadora de métricas de evolução clínica
    """

    def __init__(self):
        # Palavras-chave positivas e negativas para análise de sentimento clínico
        self.positive_keywords = {
            'melhora', 'progresso', 'avanço', 'resposta', 'ajuda', 'benefício', 'sucesso',
            'positivo', 'bem-estar', 'calma', 'controle', 'confiança', 'autoestima',
            'socialização', 'comunicação', 'expressão', 'participação', 'interação'
        }
        
        self.negative_keywords = {
            'dificuldade', 'problema', 'crise', 'ansiedade', 'tristeza', 'raiva', 'medo',
            'retirada', 'agressividade', 'choro', 'recusa', 'bloqueio', 'fragilidade',
            'instabilidade', 'impulsividade', 'hiperatividade', 'distração', 'frustração'
        }

    def calculate_progress_metrics(self, sessions: List[SessionData]) -> Dict:
        """
        Calcula métricas de progresso entre sessões clínicas
        
        :param sessions: Lista de sessões para análise
        :return: Dicionário com métricas de evolução
        """
        if not sessions:
            return self._get_empty_metrics()
        
        # Extrair conteúdo de todas as sessões
        contents = [session.content for session in sessions]
        
        # Calcular métricas básicas
        metrics = {
            'session_count': len(sessions),
            'total_content_length': sum(len(content) for content in contents),
            'average_content_length': sum(len(content) for content in contents) / len(contents) if contents else 0,
            'time_span_days': (sessions[-1].date - sessions[0].date).days if len(sessions) > 1 else 0
        }
        
        # Analisar palavras-chave em cada sessão
        session_keywords = []
        for session in sessions:
            keywords = self._extract_keywords(session.content)
            session_keywords.append(keywords)
        
        # Calcular métricas de palavras-chave
        all_keywords = [kw for keywords in session_keywords for kw in keywords]
        keyword_counts = Counter(all_keywords)
        
        # Identificar mudanças entre sessões
        changes = self._analyze_session_changes(sessions)
        
        # Calcular indicadores de evolução
        positive_changes = sum(1 for change in changes if change['type'] == 'positive')
        negative_changes = sum(1 for change in changes if change['type'] == 'negative')
        stability_indicators = sum(1 for change in changes if change['type'] == 'stable')
        
        # Calcular score de evolução
        evolution_score = self._calculate_evolution_score(
            positive_changes, negative_changes, stability_indicators
        )

        # Extrair palavras-chave comuns
        common_keywords = [kw for kw, count in keyword_counts.most_common(10)]

        # Combinar todas as métricas ANTES de gerar o sumário
        metrics.update({
            'positive_changes': positive_changes,
            'negative_changes': negative_changes,
            'stability_indicators': stability_indicators,
            'evolution_score': evolution_score,
            'common_keywords': common_keywords,
            'session_changes': changes,
            'keyword_counts': dict(keyword_counts),
            'improvement_indicators': positive_changes + stability_indicators * 0.3,
            'decline_indicators': negative_changes
        })

        # Gerar sumário com todas as métricas já disponíveis
        summary = self._generate_summary(metrics, changes, keyword_counts)

        # Atualizar o sumário nas métricas
        metrics['summary'] = summary
        
        return metrics

    def _get_empty_metrics(self) -> Dict:
        """Retorna métricas vazias"""
        return {
            'session_count': 0,
            'total_content_length': 0,
            'average_content_length': 0,
            'time_span_days': 0,
            'positive_changes': 0,
            'negative_changes': 0,
            'stability_indicators': 0,
            'evolution_score': 0.0,
            'common_keywords': [],
            'session_changes': [],
            'keyword_counts': {},
            'summary': 'Não há dados suficientes para análise.',
            'improvement_indicators': 0,
            'decline_indicators': 0
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extrai palavras-chave relevantes do texto da sessão
        
        :param text: Texto da sessão
        :return: Lista de palavras-chave identificadas
        """
        # Converter para minúsculas e remover pontuação
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean_text.split()
        
        # Filtrar palavras relevantes (remover stopwords comuns e manter termos clínicos)
        clinical_keywords = []
        for word in words:
            if len(word) > 3 and word in (self.positive_keywords | self.negative_keywords):
                clinical_keywords.append(word)
        
        return clinical_keywords

    def _analyze_session_changes(self, sessions: List[SessionData]) -> List[Dict]:
        """
        Analisa mudanças entre sessões consecutivas
        
        :param sessions: Lista de sessões
        :return: Lista de mudanças identificadas
        """
        if len(sessions) < 2:
            return []
        
        changes = []
        
        for i in range(len(sessions) - 1):
            prev_session = sessions[i]
            curr_session = sessions[i + 1]
            
            # Extrair palavras-chave de ambas as sessões
            prev_keywords = set(self._extract_keywords(prev_session.content))
            curr_keywords = set(self._extract_keywords(curr_session.content))
            
            # Identificar mudanças
            new_keywords = curr_keywords - prev_keywords
            lost_keywords = prev_keywords - curr_keywords
            maintained_keywords = prev_keywords & curr_keywords
            
            # Determinar tipo de mudança
            change_type = self._determine_change_type(new_keywords, lost_keywords, maintained_keywords)
            
            change = {
                'session_pair': (prev_session.id, curr_session.id),
                'previous_date': prev_session.date.isoformat(),
                'current_date': curr_session.date.isoformat(),
                'new_keywords': list(new_keywords),
                'lost_keywords': list(lost_keywords),
                'maintained_keywords': list(maintained_keywords),
                'type': change_type,
                'significance': self._calculate_change_significance(new_keywords, lost_keywords)
            }
            
            changes.append(change)
        
        return changes

    def _determine_change_type(self, new_keywords: set, lost_keywords: set, maintained_keywords: set) -> str:
        """
        Determina o tipo de mudança entre sessões
        
        :param new_keywords: Palavras-chave novas
        :param lost_keywords: Palavras-chave perdidas
        :param maintained_keywords: Palavras-chave mantidas
        :return: Tipo de mudança ('positive', 'negative', 'stable')
        """
        # Contar palavras-chave positivas e negativas nas mudanças
        new_positive = len(new_keywords & self.positive_keywords)
        new_negative = len(new_keywords & self.negative_keywords)
        
        lost_positive = len(lost_keywords & self.positive_keywords)
        lost_negative = len(lost_keywords & self.negative_keywords)
        
        # Determinar tipo com base nas mudanças
        if new_positive > new_negative and lost_negative >= lost_positive:
            return 'positive'
        elif new_negative > new_positive and lost_positive >= lost_negative:
            return 'negative'
        elif abs(new_positive - new_negative) <= 1 and abs(lost_positive - lost_negative) <= 1:
            return 'stable'
        elif new_positive > new_negative:
            return 'positive'
        elif new_negative > new_positive:
            return 'negative'
        else:
            return 'stable'

    def _calculate_change_significance(self, new_keywords: set, lost_keywords: set) -> float:
        """
        Calcula a significância da mudança (0.0 a 1.0)
        
        :param new_keywords: Palavras-chave novas
        :param lost_keywords: Palavras-chave perdidas
        :return: Significância da mudança
        """
        total_changed = len(new_keywords) + len(lost_keywords)
        if total_changed == 0:
            return 0.0
        
        # A significância aumenta com a quantidade de mudanças
        # Mas é normalizada pelo tamanho do vocabulário esperado
        significance = min(total_changed / 10.0, 1.0)  # Assumindo ~10 palavras-chave como baseline
        return significance

    def _calculate_evolution_score(self, positive_changes: int, negative_changes: int, stability_indicators: int) -> float:
        """
        Calcula o score geral de evolução
        
        :param positive_changes: Número de mudanças positivas
        :param negative_changes: Número de mudanças negativas
        :param stability_indicators: Número de indicadores de estabilidade
        :return: Score de evolução (0.0 a 1.0)
        """
        total_changes = positive_changes + negative_changes + stability_indicators
        
        if total_changes == 0:
            return 0.5  # Valor neutro se não houver mudanças
        
        # Calcular score ponderado
        # Mudanças positivas têm peso maior, mudanças negativas reduzem o score
        weighted_score = (positive_changes * 1.0 + stability_indicators * 0.5 - negative_changes * 0.8) / total_changes
        
        # Garantir que o score esteja entre 0 e 1
        return max(0.0, min(1.0, weighted_score + 0.5))  # Adiciona 0.5 para centralizar em 0.5

    def _generate_summary(self, metrics: Dict, changes: List[Dict], keyword_counts: Counter) -> str:
        """
        Gera um sumário textual das métricas
        
        :param metrics: Métricas calculadas
        :param changes: Mudanças identificadas
        :param keyword_counts: Contagem de palavras-chave
        :return: Sumário textual
        """
        if not changes:
            return "Não há dados suficientes para análise. Apenas uma sessão disponível."
        
        positive_changes = sum(1 for change in changes if change['type'] == 'positive')
        negative_changes = sum(1 for change in changes if change['type'] == 'negative')
        stable_changes = sum(1 for change in changes if change['type'] == 'stable')
        
        most_common = keyword_counts.most_common(5)
        common_words = [f"{word}({count})" for word, count in most_common]
        
        summary = f"""
Análise Preliminar:
- Total de sessões analisadas: {metrics['session_count']}
- Mudanças positivas identificadas: {positive_changes}
- Mudanças negativas identificadas: {negative_changes}
- Indicadores de estabilidade: {stable_changes}
- Palavras-chave mais comuns: {', '.join(common_words)}
- Score de evolução: {metrics['evolution_score']:.2f}
        """.strip()
        
        return summary

    def detect_stagnation_patterns(self, metrics: List[Dict]) -> bool:
        """
        Detecta padrões de estagnação no tratamento
        
        :param metrics: Lista de métricas de diferentes períodos
        :return: True se padrão de estagnação for detectado
        """
        if len(metrics) < 2:
            return False
        
        # Verificar se os scores de evolução são consistentemente baixos
        evolution_scores = [m.get('evolution_score', 0.5) for m in metrics]
        avg_score = sum(evolution_scores) / len(evolution_scores)
        
        # Verificar se há poucas mudanças positivas
        avg_positive_changes = sum(m.get('positive_changes', 0) for m in metrics) / len(metrics)
        
        # Critérios para estagnação:
        # 1. Score médio de evolução abaixo de 0.4
        # 2. Média de mudanças positivas inferior a 1 por período
        # 3. Mais de 50% das mudanças são estáveis ou negativas
        stagnation_criteria_met = 0
        
        if avg_score < 0.4:
            stagnation_criteria_met += 1
        
        if avg_positive_changes < 1.0:
            stagnation_criteria_met += 1
            
        # Calcular proporção de mudanças não-positivas
        total_changes = sum(m.get('positive_changes', 0) + m.get('negative_changes', 0) + m.get('stability_indicators', 0) for m in metrics)
        non_positive_changes = sum(m.get('negative_changes', 0) + m.get('stability_indicators', 0) for m in metrics)
        
        if total_changes > 0 and (non_positive_changes / total_changes) > 0.5:
            stagnation_criteria_met += 1
        
        # Considerar estagnação se pelo menos 2 dos 3 critérios forem atendidos
        return stagnation_criteria_met >= 2

    def assess_clinical_improvement(self, patient_history: List[Dict]) -> Dict:
        """
        Avalia objetivamente a melhora clínica
        
        :param patient_history: Histórico clínico do paciente
        :return: Avaliação de melhora clínica
        """
        # Esta função pode ser expandida para incluir mais critérios de avaliação
        # baseados em protocolos clínicos específicos
        
        assessment = {
            'has_improved': False,
            'improvement_level': 'unknown',  # 'significant', 'moderate', 'minimal', 'none', 'decline'
            'confidence': 0.0,
            'key_indicators': [],
            'recommendations': []
        }
        
        if not patient_history:
            return assessment
        
        # Implementar lógica de avaliação baseada em múltiplos critérios
        # Esta é uma implementação inicial que pode ser expandida
        
        # Exemplo básico de avaliação
        recent_metrics = patient_history[-1] if patient_history else {}
        evolution_score = recent_metrics.get('evolution_score', 0.5)
        
        if evolution_score >= 0.7:
            assessment['has_improved'] = True
            assessment['improvement_level'] = 'significant'
            assessment['confidence'] = 0.8
        elif evolution_score >= 0.5:
            assessment['has_improved'] = True
            assessment['improvement_level'] = 'moderate'
            assessment['confidence'] = 0.6
        elif evolution_score >= 0.3:
            assessment['has_improved'] = False
            assessment['improvement_level'] = 'minimal'
            assessment['confidence'] = 0.5
        else:
            assessment['has_improved'] = False
            assessment['improvement_level'] = 'decline'
            assessment['confidence'] = 0.7
        
        return assessment


# Função auxiliar para uso externo
def create_evolution_metrics_calculator() -> EvolutionMetricsCalculator:
    """
    Criar instância da calculadora de métricas de evolução
    
    :return: Instância da calculadora
    """
    return EvolutionMetricsCalculator()