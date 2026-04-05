"""
Módulo de agente de recomendação terapêutica para o sistema de psicologia
Sugere terapias alternativas baseadas na falta de evolução do paciente
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import random
from datetime import datetime

from database.db_manager import DatabaseManager
from analysis.clinical_evolution_analyzer import EvolutionAnalysisResult, EvolutionPattern
from core.openai_interface import ClinicalOpenAIInterface, OpenAIClient
from core.gemini_interface import ClinicalGeminiInterface

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EvidenceBasedTreatment:
    """Tratamento baseado em evidências"""
    name: str
    description: str
    evidence_level: str  # A, B, C, D (A sendo a mais alta qualidade)
    target_conditions: List[str]
    age_group: str  # "child", "adult", "elderly", "all"
    intervention_type: str  # "cognitive", "behavioral", "combined", etc.
    estimated_duration: str  # "short_term", "medium_term", "long_term"
    effectiveness_percentage: float  # 0.0 to 1.0


@dataclass
class PersonalizedRecommendation:
    """Recomendação personalizada para um paciente específico"""
    treatment_option: EvidenceBasedTreatment
    relevance_score: float  # 0.0 to 1.0
    personalization_notes: str
    confidence_level: str  # "high", "medium", "low"
    implementation_notes: List[str]


class TherapyRecommendationAgent:
    """
    Agente inteligente que sugere novas terapias baseadas na falta de evolução
    """

    def __init__(self, 
                 db_manager: DatabaseManager, 
                 openai_interface: Optional[ClinicalOpenAIInterface] = None,
                 gemini_interface: Optional[ClinicalGeminiInterface] = None):
        """
        Inicializar o agente de recomendação terapêutica

        :param db_manager: Instância do gerenciador de banco de dados
        :param openai_interface: Interface OpenAI para assistência (opcional)
        :param gemini_interface: Interface Gemini para assistência (opcional)
        """
        self.db_manager = db_manager
        self.openai_interface = openai_interface
        self.gemini_interface = gemini_interface
        
        # Base de conhecimento de tratamentos baseados em evidências
        self.evidence_based_treatments = self._initialize_evidence_base()

    def recommend_alternative_therapy(self, analysis_result: EvolutionAnalysisResult) -> List[PersonalizedRecommendation]:
        """
        Recomenda terapias alternativas baseadas na análise de evolução

        :param analysis_result: Resultado da análise de evolução do paciente
        :return: Lista de recomendações personalizadas
        """
        logger.info(f"Gerando recomendações para paciente {analysis_result.patient_id}")
        
        # Obter perfil do paciente
        patient_profile = self._get_patient_profile(analysis_result.patient_id, analysis_result.owner_id)
        
        # Selecionar tratamentos relevantes com base no padrão de evolução
        relevant_treatments = self._select_relevant_treatments(analysis_result, patient_profile)
        
        # Personalizar recomendações
        personalized_recommendations = self._personalize_recommendations(
            relevant_treatments, 
            patient_profile, 
            analysis_result
        )
        
        # Ordenar por score de relevância
        personalized_recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"Geradas {len(personalized_recommendations)} recomendações para o paciente")
        return personalized_recommendations

    def _initialize_evidence_base(self) -> List[EvidenceBasedTreatment]:
        """
        Inicializa a base de conhecimento com tratamentos baseados em evidências
        Esta é uma base inicial que pode ser expandida com dados reais
        """
        treatments = [
            # Terapias cognitivo-comportamentais
            EvidenceBasedTreatment(
                name="Terapia Cognitivo-Comportamental (TCC)",
                description="Abordagem baseada em evidências para diversos transtornos psicológicos, focando na relação entre pensamentos, sentimentos e comportamentos.",
                evidence_level="A",
                target_conditions=["ansiedade", "depressão", "TDAH", "TEA", "transtornos de conduta"],
                age_group="all",
                intervention_type="cognitive_behavioral",
                estimated_duration="medium_term",
                effectiveness_percentage=0.75
            ),
            EvidenceBasedTreatment(
                name="TCC Adaptada para TEA",
                description="Versão modificada da TCC para atender as necessidades específicas de pessoas com Transtorno do Espectro Autista.",
                evidence_level="B",
                target_conditions=["TEA", "ansiedade_em_TEA", "depressão_em_TEA"],
                age_group="all",
                intervention_type="cognitive_behavioral",
                estimated_duration="medium_term",
                effectiveness_percentage=0.68
            ),
            EvidenceBasedTreatment(
                name="Terapia Comportamental Aplicada (ABA)",
                description="Abordagem baseada em princípios de aprendizagem para desenvolver habilidades sociais, comunicativas e comportamentais.",
                evidence_level="A",
                target_conditions=["TEA", "desenvolvimento_atípico"],
                age_group="child",
                intervention_type="behavioral",
                estimated_duration="long_term",
                effectiveness_percentage=0.82
            ),
            EvidenceBasedTreatment(
                name="Terapia Dialética-Comportamental (DBT)",
                description="Terapia que combina TCC com técnicas de mindfulness e regulacão emocional.",
                evidence_level="A",
                target_conditions=["disregulacao_emocional", "TDAH", "borderline"],
                age_group="adult",
                intervention_type="combined",
                estimated_duration="long_term",
                effectiveness_percentage=0.73
            ),
            EvidenceBasedTreatment(
                name="EMDR (Eye Movement Desensitization and Reprocessing)",
                description="Terapia eficaz para traumas e distúrbios relacionados a memórias perturbadoras.",
                evidence_level="A",
                target_conditions=["trauma", "PTSD", "ansiedade_trauma_relacionada"],
                age_group="all",
                intervention_type="cognitive",
                estimated_duration="short_term",
                effectiveness_percentage=0.78
            ),
            EvidenceBasedTreatment(
                name="Terapia de Aceitação e Compromisso (ACT)",
                description="Terapia baseada em mindfulness que ajuda a aceitar pensamentos difíceis e comprometer-se com ações valiosas.",
                evidence_level="B",
                target_conditions=["ansiedade", "depressão", "dor_crônica", "TDAH"],
                age_group="all",
                intervention_type="cognitive",
                estimated_duration="medium_term",
                effectiveness_percentage=0.69
            ),
            EvidenceBasedTreatment(
                name="Terapia Centrada no Jogo",
                description="Abordagem terapêutica para crianças que utiliza o jogo como meio de comunicação e cura.",
                evidence_level="B",
                target_conditions=["problemas_emocionais_infantis", "trauma_infantil", "dificuldades_sociais"],
                age_group="child",
                intervention_type="play_based",
                estimated_duration="medium_term",
                effectiveness_percentage=0.71
            ),
            EvidenceBasedTreatment(
                name="Musicoterapia",
                description="Uso sistemático de elementos musicais para facilitar e promover a comunicação, relacionamento, aprendizagem e expressão.",
                evidence_level="B",
                target_conditions=["TEA", "demencia", "ansiedade", "depressão"],
                age_group="all",
                intervention_type="expressive",
                estimated_duration="medium_term",
                effectiveness_percentage=0.65
            ),
            EvidenceBasedTreatment(
                name="Arteterapia",
                description="Forma de terapia que utiliza o processo criativo artístico para melhorar o bem-estar físico, mental e emocional.",
                evidence_level="B",
                target_conditions=["trauma", "ansiedade", "depressão", "expressao_dificultada"],
                age_group="all",
                intervention_type="expressive",
                estimated_duration="medium_term",
                effectiveness_percentage=0.67
            ),
            EvidenceBasedTreatment(
                name="Terapia Familiar Sistêmica",
                description="Abordagem que considera o sistema familiar como unidade de tratamento, explorando padrões de interação.",
                evidence_level="A",
                target_conditions=["problemas_familiares", "comportamentos_desafiadores", "transicoes_dificeis"],
                age_group="all",
                intervention_type="family_systemic",
                estimated_duration="long_term",
                effectiveness_percentage=0.74
            )
        ]
        
        return treatments

    def _get_patient_profile(self, patient_id: int, owner_id: int) -> Dict:
        """
        Obtém o perfil do paciente do banco de dados

        :param patient_id: ID do paciente
        :param owner_id: ID do proprietário
        :return: Dicionário com o perfil do paciente
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT first_name, last_name, age, diagnosis, neurotype, level, description
                        FROM patients
                        WHERE id = %s AND owner_id = %s
                    """, (patient_id, owner_id))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        return {
                            'id': patient_id,
                            'first_name': result[0],
                            'last_name': result[1],
                            'age': result[2],
                            'diagnosis': result[3],
                            'neurotype': result[4],
                            'level': result[5],
                            'description': result[6]
                        }
                    else:
                        logger.warning(f"Perfil do paciente {patient_id} não encontrado")
                        return {}
                        
        except Exception as e:
            logger.error(f"Erro ao obter perfil do paciente {patient_id}: {e}")
            return {}

    def _select_relevant_treatments(self, analysis_result: EvolutionAnalysisResult, patient_profile: Dict) -> List[EvidenceBasedTreatment]:
        """
        Seleciona tratamentos relevantes com base na análise de evolução e perfil do paciente

        :param analysis_result: Resultado da análise de evolução
        :param patient_profile: Perfil do paciente
        :return: Lista de tratamentos relevantes
        """
        relevant_treatments = []
        
        # Determinar condições-alvo com base na análise e no perfil
        target_conditions = self._determine_target_conditions(analysis_result, patient_profile)
        
        # Filtrar tratamentos com base nas condições-alvo
        for treatment in self.evidence_based_treatments:
            # Verificar se o tratamento é apropriado para as condições identificadas
            if any(condition in target_conditions for condition in treatment.target_conditions):
                # Verificar se o grupo etário é apropriado
                if self._is_age_appropriate(treatment.age_group, patient_profile.get('age')):
                    relevant_treatments.append(treatment)
        
        # Se não houver tratamentos específicos, retornar opções gerais
        if not relevant_treatments:
            # Adicionar tratamentos gerais que podem ser úteis em casos de estagnação
            general_treatments = [
                t for t in self.evidence_based_treatments 
                if 'estagnacao' in t.name.lower() or 'alternativa' in t.description.lower() or 
                t.intervention_type == 'combined' or t.intervention_type == 'expressive'
            ]
            relevant_treatments.extend(general_treatments)
        
        # Se ainda não houver tratamentos, retornar todos
        if not relevant_treatments:
            relevant_treatments = self.evidence_based_treatments
        
        return relevant_treatments

    def _determine_target_conditions(self, analysis_result: EvolutionAnalysisResult, patient_profile: Dict) -> List[str]:
        """
        Determina as condições-alvo com base na análise de evolução e no perfil do paciente

        :param analysis_result: Resultado da análise de evolução
        :param patient_profile: Perfil do paciente
        :return: Lista de condições-alvo
        """
        conditions = []
        
        # Adicionar diagnóstico principal
        if patient_profile.get('diagnosis'):
            conditions.append(patient_profile['diagnosis'].lower())
        
        # Adicionar neurotype se existir
        if patient_profile.get('neurotype'):
            conditions.append(patient_profile['neurotype'].lower())
        
        # Adicionar condições baseadas no padrão de evolução
        if analysis_result.evolution_pattern == EvolutionPattern.STAGNANT:
            conditions.extend(['estagnacao_terapeutica', 'baixa_resposta_ao_tratamento'])
        elif analysis_result.evolution_pattern == EvolutionPattern.NEGATIVE:
            conditions.extend(['regressao_clinica', 'aumento_de_sintomas'])
        
        # Adicionar condições inferidas do histórico clínico
        clinical_notes = analysis_result.clinical_notes.lower()
        if 'ansiedade' in clinical_notes:
            conditions.append('ansiedade')
        if 'depress' in clinical_notes:
            conditions.append('depressão')
        if 'comportamento' in clinical_notes:
            conditions.append('transtornos_de_conduta')
        if 'socializacao' in clinical_notes:
            conditions.append('dificuldades_sociais')
        if 'atencao' in clinical_notes or 'foco' in clinical_notes:
            conditions.append('TDAH')
        if 'autismo' in clinical_notes or 'TEA' in clinical_notes:
            conditions.append('TEA')
        
        # Remover duplicatas
        conditions = list(set(conditions))
        
        return conditions

    def _is_age_appropriate(self, age_group: str, patient_age: Optional[int]) -> bool:
        """
        Verifica se o tratamento é apropriado para a faixa etária do paciente

        :param age_group: Grupo etário do tratamento
        :param patient_age: Idade do paciente
        :return: True se apropriado, False caso contrário
        """
        if not patient_age:
            return True  # Se não soubermos a idade, assumimos que é apropriado
        
        if age_group == "all":
            return True
        elif age_group == "child" and patient_age <= 12:
            return True
        elif age_group == "adult" and patient_age >= 18:
            return True
        elif age_group == "elderly" and patient_age >= 65:
            return True
        else:
            return False

    def _personalize_recommendations(self, 
                                   treatments: List[EvidenceBasedTreatment], 
                                   patient_profile: Dict, 
                                   analysis_result: EvolutionAnalysisResult) -> List[PersonalizedRecommendation]:
        """
        Personaliza as recomendações com base no perfil do paciente e na análise de evolução

        :param treatments: Lista de tratamentos relevantes
        :param patient_profile: Perfil do paciente
        :param analysis_result: Resultado da análise de evolução
        :return: Lista de recomendações personalizadas
        """
        personalized_recommendations = []
        
        for treatment in treatments:
            # Calcular score de relevância
            relevance_score = self._calculate_relevance_score(treatment, patient_profile, analysis_result)
            
            # Gerar notas de personalização
            personalization_notes = self._generate_personalization_notes(treatment, patient_profile, analysis_result)
            
            # Determinar nível de confiança
            confidence_level = self._determine_confidence_level(treatment, relevance_score)
            
            # Gerar notas de implementação
            implementation_notes = self._generate_implementation_notes(treatment, patient_profile)
            
            recommendation = PersonalizedRecommendation(
                treatment_option=treatment,
                relevance_score=relevance_score,
                personalization_notes=personalization_notes,
                confidence_level=confidence_level,
                implementation_notes=implementation_notes
            )
            
            personalized_recommendations.append(recommendation)
        
        return personalized_recommendations

    def _calculate_relevance_score(self, 
                                  treatment: EvidenceBasedTreatment, 
                                  patient_profile: Dict, 
                                  analysis_result: EvolutionAnalysisResult) -> float:
        """
        Calcula o score de relevância de um tratamento para o paciente

        :param treatment: Tratamento a ser avaliado
        :param patient_profile: Perfil do paciente
        :param analysis_result: Resultado da análise de evolução
        :return: Score de relevância (0.0 a 1.0)
        """
        score = 0.0
        
        # Fator: Adequação às condições-alvo
        target_conditions = self._determine_target_conditions(analysis_result, patient_profile)
        matching_conditions = [cond for cond in target_conditions if cond in treatment.target_conditions]
        if matching_conditions:
            score += 0.4  # 40% do score baseado em condições-alvo
        
        # Fator: Nível de evidência
        evidence_factor = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4}
        score += evidence_factor.get(treatment.evidence_level, 0.5) * 0.2  # 20% baseado em evidência
        
        # Fator: Apropriedade etária
        if self._is_age_appropriate(treatment.age_group, patient_profile.get('age')):
            score += 0.2  # 20% baseado em apropriedade etária
        
        # Fator: Eficácia estimada
        score += treatment.effectiveness_percentage * 0.2  # 20% baseado em eficácia
        
        # Ajustar score com base no padrão de evolução
        if analysis_result.evolution_pattern == EvolutionPattern.STAGNANT:
            # Para estagnação, valorizar mais tratamentos diferentes do atual
            if treatment.name.lower() in analysis_result.clinical_notes.lower():
                score *= 0.7  # Reduzir score se o tratamento já foi tentado
        
        return min(score, 1.0)  # Garantir que o score não ultrapasse 1.0

    def _generate_personalization_notes(self, 
                                       treatment: EvidenceBasedTreatment, 
                                       patient_profile: Dict, 
                                       analysis_result: EvolutionAnalysisResult) -> str:
        """
        Gera notas de personalização para o tratamento

        :param treatment: Tratamento
        :param patient_profile: Perfil do paciente
        :param analysis_result: Resultado da análise de evolução
        :return: Notas de personalização
        """
        notes = f"Este tratamento ({treatment.name}) é particularmente adequado para o paciente porque:\n"
        
        # Identificar razões específicas
        target_conditions = self._determine_target_conditions(analysis_result, patient_profile)
        matching_conditions = [cond for cond in target_conditions if cond in treatment.target_conditions]
        
        if matching_conditions:
            notes += f"- Aborda diretamente as condições identificadas: {', '.join(matching_conditions)}\n"
        
        if self._is_age_appropriate(treatment.age_group, patient_profile.get('age')):
            notes += "- É apropriado para a faixa etária do paciente\n"
        
        if analysis_result.evolution_pattern == EvolutionPattern.STAGNANT:
            notes += "- Oferece uma abordagem diferente da atualmente em uso, o que pode superar a estagnação\n"
        elif analysis_result.evolution_pattern == EvolutionPattern.NEGATIVE:
            notes += "- Pode ajudar a estabilizar e reverter a trajetória negativa observada\n"
        
        notes += f"- Tem um nível de evidência {treatment.evidence_level} e eficácia estimada de {treatment.effectiveness_percentage*100:.0f}%\n"
        
        return notes.strip()

    def _determine_confidence_level(self, treatment: EvidenceBasedTreatment, relevance_score: float) -> str:
        """
        Determina o nível de confiança na recomendação

        :param treatment: Tratamento
        :param relevance_score: Score de relevância
        :return: Nível de confiança
        """
        if relevance_score >= 0.8 and treatment.evidence_level == "A":
            return "high"
        elif relevance_score >= 0.6:
            return "medium"
        else:
            return "low"

    def _generate_implementation_notes(self, treatment: EvidenceBasedTreatment, patient_profile: Dict) -> List[str]:
        """
        Gera notas de implementação para o tratamento

        :param treatment: Tratamento
        :param patient_profile: Perfil do paciente
        :return: Lista de notas de implementação
        """
        notes = []
        
        # Duração estimada
        duration_map = {
            "short_term": "curto prazo (1-3 meses)",
            "medium_term": "médio prazo (3-6 meses)", 
            "long_term": "longo prazo (6+ meses)"
        }
        notes.append(f"Duração estimada: {duration_map.get(treatment.estimated_duration, 'variável')}")
        
        # Considerações especiais
        if patient_profile.get('age', 0) < 12 and treatment.age_group == "child":
            notes.append("Especialmente adequado para pacientes infantis")
        
        if treatment.evidence_level == "A":
            notes.append("Tratamento com forte suporte científico")
        
        # Notas específicas por tipo de tratamento
        if treatment.intervention_type == "expressive":
            notes.append("Pode ser especialmente útil para pacientes com dificuldades de expressão verbal")
        
        if "TEA" in treatment.target_conditions:
            notes.append("Considere adaptações específicas para necessidades de comunicação e socialização")
        
        return notes

    def search_evidence_based_treatments(self, patient_profile: Dict) -> List[EvidenceBasedTreatment]:
        """
        Busca tratamentos baseados em evidências para o perfil do paciente

        :param patient_profile: Perfil do paciente
        :return: Lista de tratamentos baseados em evidências
        """
        # Esta função pode ser usada para buscas mais amplas
        # Por enquanto, usamos a mesma lógica de seleção
        analysis_result_mock = EvolutionAnalysisResult(
            patient_id=patient_profile.get('id', 0),
            owner_id=0,  # Não utilizado aqui
            sessions_analyzed=0,
            evolution_pattern=EvolutionPattern.UNKNOWN,
            evolution_score=0.5,
            clinical_notes="",
            recommendations=[],
            alerts_needed=[],
            session_comparison={}
        )
        
        return self._select_relevant_treatments(analysis_result_mock, patient_profile)

    def get_top_recommendations(self, 
                               analysis_result: EvolutionAnalysisResult, 
                               count: int = 3) -> List[PersonalizedRecommendation]:
        """
        Obtém as principais recomendações para o paciente

        :param analysis_result: Resultado da análise de evolução
        :param count: Número de recomendações a retornar
        :return: Lista das principais recomendações
        """
        all_recommendations = self.recommend_alternative_therapy(analysis_result)
        
        # Ordenar por score de relevância e retornar as principais
        top_recommendations = sorted(
            all_recommendations, 
            key=lambda x: x.relevance_score, 
            reverse=True
        )[:count]
        
        return top_recommendations

    def generate_recommendation_summary(self, recommendations: List[PersonalizedRecommendation]) -> str:
        """
        Gera um sumário das recomendações

        :param recommendations: Lista de recomendações
        :return: Sumário textual das recomendações
        """
        if not recommendations:
            return "Nenhuma recomendação disponível no momento."
        
        summary = "Recomendações Terapêuticas Alternativas:\n\n"
        
        for i, rec in enumerate(recommendations, 1):
            summary += f"{i}. {rec.treatment_option.name}\n"
            summary += f"   - Relevância: {rec.relevance_score:.2f} ({rec.confidence_level.upper()} confiança)\n"
            summary += f"   - Evidência: Nível {rec.treatment_option.evidence_level}\n"
            summary += f"   - Duração: {rec.treatment_option.estimated_duration.replace('_', ' ').title()}\n"
            summary += f"   - Notas: {rec.personalization_notes.split('.')[0]}.\n\n"
        
        return summary.strip()


# Função auxiliar para uso externo
def create_therapy_recommendation_agent(
    db_manager: DatabaseManager,
    openai_interface: Optional[ClinicalOpenAIInterface] = None,
    gemini_interface: Optional[ClinicalGeminiInterface] = None
) -> TherapyRecommendationAgent:
    """
    Criar instância do agente de recomendação terapêutica
    
    :param db_manager: Gerenciador de banco de dados
    :param openai_interface: Interface OpenAI (opcional)
    :param gemini_interface: Interface Gemini (opcional)
    :return: Instância do agente de recomendação
    """
    return TherapyRecommendationAgent(db_manager, openai_interface, gemini_interface)