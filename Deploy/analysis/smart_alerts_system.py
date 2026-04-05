"""
Módulo de sistema de alertas inteligentes para o sistema de psicologia
Gera alertas baseados na análise de evolução do paciente
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

from database.db_manager import DatabaseManager
from analysis.clinical_evolution_analyzer import EvolutionAnalysisResult, EvolutionPattern

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Níveis de severidade dos alertas"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Tipos de alertas"""
    STAGNATION = "stagnation"  # Estagnação terapêutica
    REGRESSION = "regression"  # Regressão clínica
    TREATMENT_CHANGE_NEEDED = "treatment_change_needed"  # Necessidade de mudança de tratamento
    INSUFFICIENT_DATA = "insufficient_data"  # Dados insuficientes para análise
    POSITIVE_TREND = "positive_trend"  # Tendência positiva identificada


class SmartAlert:
    """Representa um alerta inteligente"""
    
    def __init__(self, 
                 patient_id: int,
                 owner_id: int,
                 alert_type: AlertType,
                 severity: AlertSeverity,
                 title: str,
                 description: str,
                 recommendations: Optional[List[str]] = None,
                 metadata: Optional[Dict] = None):
        self.id = None  # Será atribuído quando salvo no banco
        self.patient_id = patient_id
        self.owner_id = owner_id
        self.alert_type = alert_type
        self.severity = severity
        self.title = title
        self.description = description
        self.recommendations = recommendations or []
        self.is_resolved = False
        self.generated_at = datetime.now()
        self.resolved_at = None
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        """Converter alerta para dicionário"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'owner_id': self.owner_id,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'recommendations': self.recommendations,
            'is_resolved': self.is_resolved,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'metadata': self.metadata
        }


class SmartAlertsSystem:
    """
    Sistema de alertas inteligentes baseado na evolução do paciente
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Inicializar o sistema de alertas inteligentes

        :param db_manager: Instância do gerenciador de banco de dados
        """
        self.db_manager = db_manager

    def check_patient_evolution_alerts(self, patient_id: int, owner_id: int) -> List[SmartAlert]:
        """
        Verifica se há alertas necessários para o paciente com base na análise de evolução

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário (terapeuta)
        :return: Lista de alertas inteligentes
        """
        logger.info(f"Verificando alertas para paciente {patient_id} e owner {owner_id}")
        
        # Esta função seria chamada após a análise de evolução
        # Por enquanto, retornamos uma lista vazia - a integração completa será feita posteriormente
        return []

    def generate_alerts_from_analysis(self, analysis_result: EvolutionAnalysisResult) -> List[SmartAlert]:
        """
        Gera alertas com base no resultado da análise de evolução

        :param analysis_result: Resultado da análise de evolução
        :return: Lista de alertas gerados
        """
        alerts = []
        
        # Verificar se há alertas necessários na análise
        for alert_desc in analysis_result.alerts_needed:
            alert = self._create_alert_from_description(
                analysis_result.patient_id,
                analysis_result.owner_id,
                alert_desc
            )
            if alert:
                alerts.append(alert)
        
        # Adicionalmente, gerar alertas com base no padrão de evolução
        pattern_alerts = self._generate_pattern_based_alerts(analysis_result)
        alerts.extend(pattern_alerts)
        
        logger.info(f"Gerados {len(alerts)} alertas para o paciente {analysis_result.patient_id}")
        return alerts

    def _create_alert_from_description(self, patient_id: int, owner_id: int, description: str) -> Optional[SmartAlert]:
        """
        Cria um alerta com base em uma descrição textual

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário
        :param description: Descrição do alerta
        :return: Alerta criado ou None
        """
        # Determinar tipo e severidade com base na descrição
        alert_type, severity = self._classify_alert(description)
        
        if not alert_type or not severity:
            return None
        
        # Gerar título apropriado
        title = self._generate_alert_title(alert_type, description)
        
        # Criar alerta
        alert = SmartAlert(
            patient_id=patient_id,
            owner_id=owner_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            recommendations=[]  # Será populado separadamente
        )
        
        return alert

    def _classify_alert(self, description: str) -> tuple[Optional[AlertType], Optional[AlertSeverity]]:
        """
        Classifica o tipo e severidade do alerta com base na descrição

        :param description: Descrição do alerta
        :return: Tupla com (tipo_alerta, severidade) ou (None, None)
        """
        description_lower = description.lower()
        
        # Classificar tipo de alerta
        if 'estagnação' in description_lower or 'sem evolução' in description_lower:
            alert_type = AlertType.STAGNATION
        elif 'regressão' in description_lower or 'piora' in description_lower:
            alert_type = AlertType.REGRESSION
        elif 'mudança' in description_lower or 'alteração' in description_lower:
            alert_type = AlertType.TREATMENT_CHANGE_NEEDED
        elif 'dados insuficientes' in description_lower:
            alert_type = AlertType.INSUFFICIENT_DATA
        else:
            alert_type = AlertType.STAGNATION  # Tipo padrão
        
        # Classificar severidade
        if 'imediatamente' in description_lower or 'urgente' in description_lower or 'crítica' in description_lower:
            severity = AlertSeverity.CRITICAL
        elif 'recomendada' in description_lower or 'considerar' in description_lower:
            severity = AlertSeverity.MEDIUM
        elif 'identificada' in description_lower:
            severity = AlertSeverity.LOW
        else:
            # Determinar severidade com base no tipo
            if alert_type in [AlertType.REGRESSION, AlertType.TREATMENT_CHANGE_NEEDED]:
                severity = AlertSeverity.HIGH
            elif alert_type == AlertType.STAGNATION:
                severity = AlertSeverity.MEDIUM
            else:
                severity = AlertSeverity.LOW
        
        return alert_type, severity

    def _generate_alert_title(self, alert_type: AlertType, description: str) -> str:
        """
        Gera um título apropriado para o alerta

        :param alert_type: Tipo do alerta
        :param description: Descrição do alerta
        :return: Título do alerta
        """
        titles = {
            AlertType.STAGNATION: "Possível estagnação terapêutica identificada",
            AlertType.REGRESSION: "Regressão clínica identificada",
            AlertType.TREATMENT_CHANGE_NEEDED: "Necessidade de alteração no tratamento",
            AlertType.INSUFFICIENT_DATA: "Dados insuficientes para análise completa",
            AlertType.POSITIVE_TREND: "Tendência positiva identificada"
        }
        
        return titles.get(alert_type, "Alerta clínico identificado")

    def _generate_pattern_based_alerts(self, analysis_result: EvolutionAnalysisResult) -> List[SmartAlert]:
        """
        Gera alertas baseados no padrão de evolução identificado

        :param analysis_result: Resultado da análise de evolução
        :return: Lista de alertas baseados em padrões
        """
        alerts = []
        
        # Alerta baseado no padrão de evolução
        if analysis_result.evolution_pattern == EvolutionPattern.STAGNANT:
            if analysis_result.sessions_analyzed >= 4:
                alert = SmartAlert(
                    patient_id=analysis_result.patient_id,
                    owner_id=analysis_result.owner_id,
                    alert_type=AlertType.STAGNATION,
                    severity=AlertSeverity.MEDIUM,
                    title="Estagnação terapêutica após 4 sessões",
                    description=f"O paciente não demonstrou evolução significativa após {analysis_result.sessions_analyzed} sessões consecutivas.",
                    recommendations=[
                        "Considerar revisão do plano terapêutico atual",
                        "Avaliar necessidade de abordagem terapêutica alternativa",
                        "Explorar novas técnicas ou intervenções baseadas em evidências"
                    ]
                )
                alerts.append(alert)
        
        elif analysis_result.evolution_pattern == EvolutionPattern.NEGATIVE:
            alert = SmartAlert(
                patient_id=analysis_result.patient_id,
                owner_id=analysis_result.owner_id,
                alert_type=AlertType.REGRESSION,
                severity=AlertSeverity.HIGH,
                title="Regressão clínica identificada",
                description=f"O paciente demonstrou sinais de regressão clínica com base na análise de {analysis_result.sessions_analyzed} sessão(ões).",
                recommendations=[
                    "Reavaliar imediatamente o plano terapêutico",
                    "Considerar intensificação da intervenção",
                    "Avaliar necessidade de encaminhamento especializado"
                ]
            )
            alerts.append(alert)
        
        elif analysis_result.evolution_pattern == EvolutionPattern.POSITIVE:
            # Alerta positivo para reconhecer progresso
            alert = SmartAlert(
                patient_id=analysis_result.patient_id,
                owner_id=analysis_result.owner_id,
                alert_type=AlertType.POSITIVE_TREND,
                severity=AlertSeverity.LOW,
                title="Tendência positiva identificada",
                description=f"O paciente demonstrou evolução positiva com base na análise de {analysis_result.sessions_analyzed} sessão(ões).",
                recommendations=[
                    "Continuar abordagem atual com monitoramento regular",
                    "Considerar aumento gradual da complexidade das intervenções",
                    "Documentar estratégias que estão sendo eficazes"
                ]
            )
            alerts.append(alert)
        
        return alerts

    def save_alerts_to_database(self, alerts: List[SmartAlert]) -> List[int]:
        """
        Salva os alertas no banco de dados

        :param alerts: Lista de alertas para salvar
        :return: Lista de IDs dos alertas salvos
        """
        saved_alert_ids = []
        
        for alert in alerts:
            alert_id = self._save_single_alert(alert)
            if alert_id:
                saved_alert_ids.append(alert_id)
        
        logger.info(f"Salvos {len(saved_alert_ids)} alertas no banco de dados")
        return saved_alert_ids

    def _save_single_alert(self, alert: SmartAlert) -> Optional[int]:
        """
        Salva um único alerta no banco de dados

        :param alert: Alerta para salvar
        :return: ID do alerta salvo ou None em caso de erro
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Converter o array de recomendações para o formato adequado do PostgreSQL
                    recommendations_array = "{" + ",".join([f'"{rec}"' for rec in alert.recommendations]) + "}" if alert.recommendations else "{}"

                    cursor.execute("""
                        INSERT INTO smart_alerts (
                            patient_id, owner_id, alert_type, severity, title, description,
                            recommendations, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s::TEXT[], %s)
                        RETURNING id
                    """, (
                        alert.patient_id, alert.owner_id, alert.alert_type.value,
                        alert.severity.value, alert.title, alert.description,
                        recommendations_array, str(alert.metadata)
                    ))
                    
                    alert_id = cursor.fetchone()[0]
                    conn.commit()
                    
                    alert.id = alert_id
                    return alert_id
                    
        except Exception as e:
            logger.error(f"Erro ao salvar alerta no banco de dados: {e}")
            return None

    def get_active_alerts_for_patient(self, patient_id: int, owner_id: int) -> List[SmartAlert]:
        """
        Obtém alertas ativos para um paciente específico

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário
        :return: Lista de alertas ativos
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, alert_type, severity, title, description, 
                               recommendations, generated_at, is_resolved, resolved_at, metadata
                        FROM smart_alerts
                        WHERE patient_id = %s AND owner_id = %s AND is_resolved = FALSE
                        ORDER BY generated_at DESC
                    """, (patient_id, owner_id))
                    
                    rows = cursor.fetchall()
                    
                    alerts = []
                    for row in rows:
                        import ast
                        alert = SmartAlert(
                            patient_id=patient_id,
                            owner_id=owner_id,
                            alert_type=AlertType(row[1]),
                            severity=AlertSeverity(row[2]),
                            title=row[3],
                            description=row[4],
                            recommendations=row[5] if row[5] else [],  # Agora é um array PostgreSQL, não precisa converter
                            metadata=ast.literal_eval(row[9]) if row[9] else {}  # Converte string de volta para dict com segurança
                        )
                        alert.id = row[0]
                        alert.generated_at = datetime.fromisoformat(row[6]) if row[6] else None
                        alert.is_resolved = row[7]
                        alert.resolved_at = datetime.fromisoformat(row[8]) if row[8] else None
                        
                        alerts.append(alert)
                    
                    return alerts
                    
        except Exception as e:
            logger.error(f"Erro ao buscar alertas para paciente {patient_id}: {e}")
            return []

    def resolve_alert(self, alert_id: int, owner_id: int) -> bool:
        """
        Marca um alerta como resolvido

        :param alert_id: ID do alerta
        :param owner_id: ID do proprietário (para verificação de permissão)
        :return: True se resolvido com sucesso, False caso contrário
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE smart_alerts
                        SET is_resolved = TRUE, resolved_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND owner_id = %s AND is_resolved = FALSE
                        RETURNING id
                    """, (alert_id, owner_id))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        logger.info(f"Alerta {alert_id} marcado como resolvido")
                        return True
                    else:
                        logger.warning(f"Alerta {alert_id} não encontrado ou já resolvido")
                        return False
                        
        except Exception as e:
            logger.error(f"Erro ao resolver alerta {alert_id}: {e}")
            return False

    def generate_stagnation_alert(self, patient_id: int, owner_id: int, session_count: int = 4) -> SmartAlert:
        """
        Gera um alerta específico de estagnação

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário
        :param session_count: Número de sessões sem evolução
        :return: Alerta de estagnação
        """
        return SmartAlert(
            patient_id=patient_id,
            owner_id=owner_id,
            alert_type=AlertType.STAGNATION,
            severity=AlertSeverity.MEDIUM,
            title=f"Estagnação após {session_count} sessões",
            description=f"O paciente não demonstrou evolução significativa após {session_count} sessões consecutivas.",
            recommendations=[
                "Reavaliar plano terapêutico atual",
                "Considerar abordagem alternativa baseada em evidências",
                "Consultar agente de recomendação para opções de tratamento"
            ]
        )

    def generate_regression_alert(self, patient_id: int, owner_id: int) -> SmartAlert:
        """
        Gera um alerta específico de regressão

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário
        :return: Alerta de regressão
        """
        return SmartAlert(
            patient_id=patient_id,
            owner_id=owner_id,
            alert_type=AlertType.REGRESSION,
            severity=AlertSeverity.HIGH,
            title="Regressão clínica identificada",
            description="Foram identificados sinais de piora clínica no paciente.",
            recommendations=[
                "Intervenção imediata recomendada",
                "Reavaliação completa do caso",
                "Considerar encaminhamento especializado"
            ]
        )


# Função auxiliar para uso externo
def create_smart_alerts_system(db_manager: DatabaseManager) -> SmartAlertsSystem:
    """
    Criar instância do sistema de alertas inteligentes
    
    :param db_manager: Gerenciador de banco de dados
    :return: Instância do sistema de alertas
    """
    return SmartAlertsSystem(db_manager)