"""
Módulo de análise de evolução clínica para o sistema de psicologia
Detecta padrões de evolução, estagnação ou regressão após 4 sessões
"""
import logging
from typing import List, Dict, Optional, Tuple
from enum import Enum

from database.db_manager import DatabaseManager
from utils.embedding_generator import CachedEmbeddingGenerator
from analysis.evolution_metrics_calculator import EvolutionMetricsCalculator
from analysis.data_classes import SessionData, EvolutionAnalysisResult, EvolutionPattern

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EvolutionPattern(Enum):
    """Padrões de evolução clínica"""
    POSITIVE = "positive"
    STAGNANT = "stagnant"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"




class ClinicalEvolutionAnalyzer:
    """
    Analisador de evolução clínica do paciente ao longo de múltiplas sessões
    """

    def __init__(self, db_manager: DatabaseManager, embedding_generator: CachedEmbeddingGenerator):
        """
        Inicializar o analisador de evolução clínica

        :param db_manager: Instância do gerenciador de banco de dados
        :param embedding_generator: Instância do gerador de embeddings
        """
        self.db_manager = db_manager
        self.embedding_generator = embedding_generator
        self.metrics_calculator = EvolutionMetricsCalculator()

    def analyze_patient_evolution(self, patient_id: int, owner_id: int, session_count: int = 4) -> EvolutionAnalysisResult:
        """
        Analisa a evolução do paciente com base nas últimas N sessões

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário (terapeuta)
        :param session_count: Número de sessões para análise (padrão: 4)
        :return: Resultado da análise de evolução
        """
        logger.info(f"Analisando evolução do paciente {patient_id} para owner {owner_id} com {session_count} sessões")

        # Obter as últimas sessões do paciente
        sessions = self._get_recent_sessions(patient_id, owner_id, session_count)
        
        if len(sessions) < 2:
            logger.warning(f"Não há sessões suficientes para análise. Encontradas: {len(sessions)}")
            return self._create_insufficient_data_result(patient_id, owner_id, len(sessions))

        # Calcular métricas de evolução
        evolution_metrics = self.metrics_calculator.calculate_progress_metrics(sessions)
        
        # Determinar padrão de evolução
        evolution_pattern = self._determine_evolution_pattern(evolution_metrics)
        
        # Calcular score de evolução
        evolution_score = self._calculate_evolution_score(evolution_metrics)
        
        # Gerar notas clínicas
        clinical_notes = self._generate_clinical_notes(sessions, evolution_metrics)
        
        # Gerar recomendações
        recommendations = self._generate_recommendations(sessions, evolution_pattern)
        
        # Identificar alertas necessários
        alerts_needed = self._identify_alerts_needed(evolution_pattern, evolution_score, sessions)
        
        # Comparação entre sessões
        session_comparison = self._compare_sessions(sessions)

        result = EvolutionAnalysisResult(
            patient_id=patient_id,
            owner_id=owner_id,
            sessions_analyzed=len(sessions),
            evolution_pattern=evolution_pattern,
            evolution_score=evolution_score,
            clinical_notes=clinical_notes,
            recommendations=recommendations,
            alerts_needed=alerts_needed,
            session_comparison=session_comparison
        )

        logger.info(f"Análise concluída - Padrão: {evolution_pattern.value}, Score: {evolution_score:.2f}")
        return result

    def _get_recent_sessions(self, patient_id: int, owner_id: int, count: int) -> List[SessionData]:
        """
        Obter as sessões mais recentes do paciente

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário
        :param count: Número de sessões para retornar
        :return: Lista de dados de sessão ordenada da mais antiga para a mais recente
        """
        logger.info(f"Obtendo {count} sessões mais recentes para paciente {patient_id}")

        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Obter documentos clínicos recentes (sessões) para o paciente
                cursor.execute("""
                    SELECT id, text, created_at
                    FROM documents
                    WHERE patient_id = %s AND owner_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (patient_id, owner_id, count))
                
                rows = cursor.fetchall()
                
                sessions = []
                for row in reversed(rows):  # Inverter para ordem cronológica (mais antigo primeiro)
                    session_data = SessionData(
                        id=row[0],
                        patient_id=patient_id,
                        owner_id=owner_id,
                        date=row[2],
                        content=row[1][:1000]  # Limitar conteúdo para processamento eficiente
                    )
                    sessions.append(session_data)
                
                logger.info(f"Encontradas {len(sessions)} sessões")
                return sessions

    def _determine_evolution_pattern(self, metrics: Dict) -> EvolutionPattern:
        """
        Determinar o padrão de evolução com base nas métricas
        
        :param metrics: Métricas de evolução calculadas
        :return: Padrão de evolução determinado
        """
        # Usar o score de evolução para determinar o padrão
        evolution_score = metrics.get('evolution_score', 0.5)
        
        if evolution_score >= 0.7:
            return EvolutionPattern.POSITIVE
        elif evolution_score <= 0.3:
            return EvolutionPattern.NEGATIVE
        else:
            # Para o caso intermediário, verificar outras métricas
            improvement_indicators = metrics.get('improvement_indicators', 0)
            decline_indicators = metrics.get('decline_indicators', 0)
            
            if improvement_indicators > decline_indicators:
                return EvolutionPattern.POSITIVE
            elif decline_indicators > improvement_indicators:
                return EvolutionPattern.NEGATIVE
            else:
                return EvolutionPattern.STAGNANT

    def _calculate_evolution_score(self, metrics: Dict) -> float:
        """
        Calcular score de evolução baseado em múltiplas métricas
        
        :param metrics: Métricas de evolução calculadas
        :return: Score de evolução (0.0 a 1.0)
        """
        # Ponderar diferentes métricas para obter um score geral
        positive_indicators = metrics.get('positive_changes', 0)
        negative_indicators = metrics.get('negative_changes', 0)
        stability_indicators = metrics.get('stability_indicators', 0)
        
        total_indicators = positive_indicators + negative_indicators + stability_indicators
        
        if total_indicators == 0:
            return 0.5  # Neutro se não houver indicadores claros
        
        # Calcular score ponderado
        score = (positive_indicators * 1.0 + stability_indicators * 0.5) / total_indicators
        return min(max(score, 0.0), 1.0)  # Garantir que esteja entre 0 e 1

    def _generate_clinical_notes(self, sessions: List[SessionData], metrics: Dict) -> str:
        """
        Gerar notas clínicas com base na análise das sessões
        
        :param sessions: Lista de sessões analisadas
        :param metrics: Métricas de evolução
        :return: Notas clínicas descritivas
        """
        if not sessions:
            return "Não há dados suficientes para gerar notas clínicas."
        
        first_session = sessions[0]
        last_session = sessions[-1]
        
        notes = f"""
Análise de Evolução Clínica
==========================

Período analisado: {first_session.date.strftime('%d/%m/%Y')} a {last_session.date.strftime('%d/%m/%Y')}
Número de sessões: {len(sessions)}

Indicadores:
- Mudanças positivas identificadas: {metrics.get('positive_changes', 0)}
- Mudanças negativas identificadas: {metrics.get('negative_changes', 0)}
- Indicadores de estabilidade: {metrics.get('stability_indicators', 0)}
- Palavras-chave comuns: {', '.join(metrics.get('common_keywords', [])[:5]) if metrics.get('common_keywords') else 'Nenhuma'}

Resumo: {metrics.get('summary', 'Análise preliminar.')}
        """.strip()
        
        return notes

    def _generate_recommendations(self, sessions: List[SessionData], pattern: EvolutionPattern) -> List[str]:
        """
        Gerar recomendações com base no padrão de evolução
        
        :param sessions: Lista de sessões analisadas
        :param pattern: Padrão de evolução identificado
        :return: Lista de recomendações
        """
        recommendations = []
        
        if pattern == EvolutionPattern.STAGNANT:
            recommendations.extend([
                "Considerar revisão do plano terapêutico atual",
                "Avaliar necessidade de abordagem terapêutica alternativa",
                "Explorar novas técnicas ou intervenções baseadas em evidências",
                "Considerar avaliação multidisciplinar se aplicável"
            ])
        elif pattern == EvolutionPattern.NEGATIVE:
            recommendations.extend([
                "Reavaliar imediatamente o plano terapêutico",
                "Considerar intensificação da intervenção",
                "Avaliar necessidade de encaminhamento especializado",
                "Revisar fatores ambientais ou contextuais que possam estar interferindo"
            ])
        elif pattern == EvolutionPattern.POSITIVE:
            recommendations.extend([
                "Continuar abordagem atual com monitoramento regular",
                "Considerar aumento gradual da complexidade das intervenções",
                "Documentar estratégias que estão sendo eficazes"
            ])
        
        return recommendations

    def _identify_alerts_needed(self, pattern: EvolutionPattern, score: float, sessions: List[SessionData]) -> List[str]:
        """
        Identificar quais alertas são necessários com base na análise
        
        :param pattern: Padrão de evolução identificado
        :param score: Score de evolução
        :param sessions: Lista de sessões analisadas
        :return: Lista de alertas necessários
        """
        alerts = []
        
        # Alerta de estagnação: quando não há evolução após 4 sessões
        if pattern == EvolutionPattern.STAGNANT and len(sessions) >= 4:
            alerts.append("Estagnação terapêutica identificada após 4 sessões")
        
        # Alerta de regressão: quando há piora clínica
        if pattern == EvolutionPattern.NEGATIVE:
            alerts.append("Regressão clínica identificada - ação imediata recomendada")
        
        # Alerta de baixa evolução: quando o score é muito baixo
        if score < 0.3 and len(sessions) >= 3:
            alerts.append(f"Baixa evolução detectada (score: {score:.2f}) - considerar mudanças no tratamento")
        
        return alerts

    def _compare_sessions(self, sessions: List[SessionData]) -> Dict[str, any]:
        """
        Comparar as sessões para identificar mudanças e padrões
        
        :param sessions: Lista de sessões para comparação
        :return: Dicionário com comparação detalhada
        """
        if len(sessions) < 2:
            return {"comparison_available": False, "message": "Não há sessões suficientes para comparação"}
        
        comparison = {
            "comparison_available": True,
            "session_count": len(sessions),
            "time_span_days": (sessions[-1].date - sessions[0].date).days if len(sessions) > 1 else 0,
            "first_session_date": sessions[0].date.isoformat(),
            "last_session_date": sessions[-1].date.isoformat(),
            "session_dates": [s.date.isoformat() for s in sessions]
        }
        
        # Se tivermos embeddings, podemos fazer comparações semânticas
        try:
            # Gerar embeddings para comparação semântica
            embeddings = []
            for session in sessions:
                emb = self.embedding_generator.generate_single_embedding(session.content, "RETRIEVAL_DOCUMENT")
                embeddings.append(emb)
            
            # Calcular similaridade entre sessões consecutivas
            similarities = []
            for i in range(len(embeddings) - 1):
                # Calcular similaridade de cosseno entre embeddings
                import numpy as np
                emb1 = np.array(embeddings[i])
                emb2 = np.array(embeddings[i + 1])
                similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                similarities.append(float(similarity))
            
            comparison["semantic_similarities"] = similarities
            comparison["average_similarity"] = sum(similarities) / len(similarities) if similarities else 0
            
        except Exception as e:
            logger.warning(f"Não foi possível calcular similaridades semânticas: {e}")
            comparison["semantic_analysis"] = "Não disponível"
        
        return comparison

    def _create_insufficient_data_result(self, patient_id: int, owner_id: int, session_count: int) -> EvolutionAnalysisResult:
        """
        Criar resultado para quando não há dados suficientes
        
        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário
        :param session_count: Número de sessões encontradas
        :return: Resultado com dados insuficientes
        """
        return EvolutionAnalysisResult(
            patient_id=patient_id,
            owner_id=owner_id,
            sessions_analyzed=session_count,
            evolution_pattern=EvolutionPattern.UNKNOWN,
            evolution_score=0.0,
            clinical_notes=f"Dados insuficientes para análise. Apenas {session_count} sessão(ões) disponível(is). Mínimo necessário: 2 sessões.",
            recommendations=["Coletar mais dados clínicos em sessões futuras para análise de evolução"],
            alerts_needed=["Dados insuficientes para análise de evolução - aguardar mais sessões"],
            session_comparison={"comparison_available": False, "message": "Dados insuficientes para comparação"}
        )


# Função auxiliar para uso externo
def create_clinical_evolution_analyzer(db_manager: DatabaseManager, embedding_generator: CachedEmbeddingGenerator) -> ClinicalEvolutionAnalyzer:
    """
    Criar instância do analisador de evolução clínica
    
    :param db_manager: Gerenciador de banco de dados
    :param embedding_generator: Gerador de embeddings
    :return: Instância do analisador
    """
    return ClinicalEvolutionAnalyzer(db_manager, embedding_generator)