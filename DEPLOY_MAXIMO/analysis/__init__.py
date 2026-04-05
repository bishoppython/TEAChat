"""
Módulo principal de análise de evolução clínica e alertas inteligentes
Integra todos os componentes do sistema de alertas e recomendações
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime

from database.db_manager import DatabaseManager
from utils.embedding_generator import CachedEmbeddingGenerator
from core.openai_interface import ClinicalOpenAIInterface, OpenAIClient
from core.gemini_interface import ClinicalGeminiInterface

from analysis.data_classes import EvolutionAnalysisResult
from analysis.clinical_evolution_analyzer import ClinicalEvolutionAnalyzer
from analysis.smart_alerts_system import SmartAlertsSystem, SmartAlert
from analysis.therapy_recommendation_agent import TherapyRecommendationAgent
from analysis.evolution_metrics_calculator import EvolutionMetricsCalculator

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClinicalIntelligenceSystem:
    """
    Sistema integrado de inteligência clínica para análise de evolução e geração de alertas
    """

    def __init__(self, 
                 db_manager: DatabaseManager, 
                 embedding_generator: CachedEmbeddingGenerator,
                 openai_interface: Optional[ClinicalOpenAIInterface] = None,
                 gemini_interface: Optional[ClinicalGeminiInterface] = None):
        """
        Inicializar o sistema de inteligência clínica

        :param db_manager: Instância do gerenciador de banco de dados
        :param embedding_generator: Instância do gerador de embeddings
        :param openai_interface: Interface OpenAI para assistência (opcional)
        :param gemini_interface: Interface Gemini para assistência (opcional)
        """
        self.db_manager = db_manager
        self.embedding_generator = embedding_generator
        self.openai_interface = openai_interface
        self.gemini_interface = gemini_interface
        
        # Inicializar componentes
        self.evolution_analyzer = ClinicalEvolutionAnalyzer(db_manager, embedding_generator)
        self.alerts_system = SmartAlertsSystem(db_manager)
        self.recommendation_agent = TherapyRecommendationAgent(
            db_manager, openai_interface, gemini_interface
        )
        self.metrics_calculator = EvolutionMetricsCalculator()

    def analyze_patient_evolution_and_alert(self, 
                                         patient_id: int, 
                                         owner_id: int, 
                                         session_count: int = 4) -> Dict:
        """
        Analisa a evolução do paciente e gera alertas e recomendações

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário (terapeuta)
        :param session_count: Número de sessões para análise (padrão: 4)
        :return: Dicionário com resultados da análise, alertas e recomendações
        """
        logger.info(f"Iniciando análise de evolução para paciente {patient_id}")
        
        # 1. Analisar evolução do paciente
        analysis_result = self.evolution_analyzer.analyze_patient_evolution(
            patient_id, owner_id, session_count
        )
        
        # 2. Gerar alertas com base na análise
        alerts = self.alerts_system.generate_alerts_from_analysis(analysis_result)
        
        # 3. Salvar alertas no banco de dados
        alert_ids = self.alerts_system.save_alerts_to_database(alerts)
        
        # 4. Gerar recomendações terapêuticas
        recommendations = self.recommendation_agent.recommend_alternative_therapy(analysis_result)
        
        # 5. Obter as principais recomendações
        top_recommendations = self.recommendation_agent.get_top_recommendations(
            analysis_result, count=3
        )
        
        # 6. Preparar resultado final
        result = {
            "patient_id": patient_id,
            "owner_id": owner_id,
            "analysis_result": {
                "sessions_analyzed": analysis_result.sessions_analyzed,
                "evolution_pattern": analysis_result.evolution_pattern.value,
                "evolution_score": analysis_result.evolution_score,
                "clinical_notes": analysis_result.clinical_notes,
                "session_comparison": analysis_result.session_comparison
            },
            "alerts_generated": [alert.to_dict() for alert in alerts],
            "alert_ids_saved": alert_ids,
            "recommendations": [
                {
                    "treatment_name": rec.treatment_option.name,
                    "relevance_score": rec.relevance_score,
                    "confidence_level": rec.confidence_level,
                    "description": rec.treatment_option.description,
                    "personalization_notes": rec.personalization_notes,
                    "implementation_notes": rec.implementation_notes
                } for rec in top_recommendations
            ],
            "all_recommendations_count": len(recommendations),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Análise concluída para paciente {patient_id}. "
                   f"Alertas gerados: {len(alerts)}, Recomendações: {len(top_recommendations)}")
        
        return result

    def get_patient_alerts(self, patient_id: int, owner_id: int) -> List[Dict]:
        """
        Obter alertas ativos para um paciente específico

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário
        :return: Lista de alertas ativos
        """
        return self.alerts_system.get_active_alerts_for_patient(patient_id, owner_id)

    def resolve_alert(self, alert_id: int, owner_id: int) -> bool:
        """
        Marcar um alerta como resolvido

        :param alert_id: ID do alerta
        :param owner_id: ID do proprietário
        :return: True se resolvido com sucesso, False caso contrário
        """
        return self.alerts_system.resolve_alert(alert_id, owner_id)

    def get_patient_evolution_summary(self, patient_id: int, owner_id: int) -> Dict:
        """
        Obter um sumário da evolução do paciente

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário
        :return: Sumário da evolução
        """
        # Obter as últimas sessões
        sessions = self.evolution_analyzer._get_recent_sessions(patient_id, owner_id, 10)
        
        if not sessions:
            return {
                "patient_id": patient_id,
                "has_data": False,
                "message": "Nenhuma sessão registrada para este paciente"
            }
        
        # Calcular métricas de evolução
        metrics = self.metrics_calculator.calculate_progress_metrics(sessions)
        
        # Determinar padrão de evolução
        pattern = self.evolution_analyzer._determine_evolution_pattern(metrics)
        score = self.evolution_analyzer._calculate_evolution_score(metrics)
        
        # Gerar notas clínicas
        clinical_notes = self.evolution_analyzer._generate_clinical_notes(sessions, metrics)
        
        return {
            "patient_id": patient_id,
            "has_data": True,
            "session_count": len(sessions),
            "latest_session_date": sessions[-1].date.isoformat() if sessions else None,
            "evolution_pattern": pattern.value,
            "evolution_score": score,
            "clinical_summary": clinical_notes,
            "time_span_days": metrics.get('time_span_days', 0),
            "positive_indicators": metrics.get('positive_changes', 0),
            "negative_indicators": metrics.get('negative_changes', 0),
            "stability_indicators": metrics.get('stability_indicators', 0)
        }

    def run_complete_clinical_assessment(self, patient_id: int, owner_id: int) -> Dict:
        """
        Executar uma avaliação clínica completa com análise de evolução, alertas e recomendações

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário
        :return: Avaliação clínica completa
        """
        logger.info(f"Executando avaliação clínica completa para paciente {patient_id}")
        
        # 1. Obter sumário de evolução
        evolution_summary = self.get_patient_evolution_summary(patient_id, owner_id)
        
        # 2. Analisar evolução detalhadamente (se houver dados suficientes)
        detailed_analysis = None
        if evolution_summary["has_data"] and evolution_summary["session_count"] >= 2:
            analysis_result = self.evolution_analyzer.analyze_patient_evolution(
                patient_id, owner_id, session_count=min(evolution_summary["session_count"], 6)
            )
            
            # 3. Gerar alertas
            alerts = self.alerts_system.generate_alerts_from_analysis(analysis_result)
            alert_ids = self.alerts_system.save_alerts_to_database(alerts)
            
            # 4. Gerar recomendações
            recommendations = self.recommendation_agent.get_top_recommendations(
                analysis_result, count=5
            )
            
            detailed_analysis = {
                "analysis_result": {
                    "sessions_analyzed": analysis_result.sessions_analyzed,
                    "evolution_pattern": analysis_result.evolution_pattern.value,
                    "evolution_score": analysis_result.evolution_score,
                    "clinical_notes": analysis_result.clinical_notes
                },
                "alerts_generated": len(alerts),
                "alert_ids_saved": alert_ids,
                "top_recommendations": [
                    {
                        "name": rec.treatment_option.name,
                        "relevance_score": rec.relevance_score,
                        "confidence": rec.confidence_level,
                        "description": rec.treatment_option.description
                    } for rec in recommendations
                ]
            }
        
        # 5. Obter alertas ativos
        active_alerts = self.get_patient_alerts(patient_id, owner_id)
        
        # 6. Preparar resultado completo
        complete_assessment = {
            "patient_id": patient_id,
            "owner_id": owner_id,
            "evolution_summary": evolution_summary,
            "detailed_analysis": detailed_analysis,
            "active_alerts": [alert.to_dict() for alert in active_alerts],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Avaliação clínica completa concluída para paciente {patient_id}")
        return complete_assessment


# Função auxiliar para criação do sistema
def create_clinical_intelligence_system(
    db_manager: DatabaseManager,
    embedding_generator: CachedEmbeddingGenerator,
    openai_interface: Optional[ClinicalOpenAIInterface] = None,
    gemini_interface: Optional[ClinicalGeminiInterface] = None
) -> ClinicalIntelligenceSystem:
    """
    Criar instância do sistema de inteligência clínica
    
    :param db_manager: Gerenciador de banco de dados
    :param embedding_generator: Gerador de embeddings
    :param openai_interface: Interface OpenAI (opcional)
    :param gemini_interface: Interface Gemini (opcional)
    :return: Instância do sistema de inteligência clínica
    """
    return ClinicalIntelligenceSystem(
        db_manager, embedding_generator, openai_interface, gemini_interface
    )