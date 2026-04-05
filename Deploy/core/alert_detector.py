"""
Módulo para detecção inteligente de alertas baseado em análise de respostas da IA
"""
import re
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class SmartAlertDetector:
    """
    Classe para detectar automaticamente situações que mereçam alertas inteligentes
    baseado na análise da resposta da IA e do contexto clínico
    """
    
    def __init__(self):
        # Padrões de alerta para diferentes categorias
        self.alert_patterns = {
            'regression': [
                r'regressão',
                r'piora',
                r'agravamento',
                r'volta ao quadro anterior',
                r'recuperou poucos ganhos',
                r'voltou a apresentar',
                r'recuperou sintomas',
                r'relapse',
                r'recaída',
                r'voltou a ter',
                r'piora significativa',
                r'deterioração',
                r'declínio',
                r'comprometimento crescente'
            ],
            
            'treatment_change_needed': [
                r'necessário mudar tratamento',
                r'ajustar intervenção',
                r'considerar nova abordagem',
                r'indicado mudança de protocolo',
                r'falha na intervenção atual',
                r'resistência ao tratamento',
                r'necessário reavaliar plano terapêutico',
                r'indicado tratamento alternativo',
                r'necessário intensificar intervenção',
                r'ajuste de conduta recomendado'
            ],
            
            'risk': [
                r'risco de',
                r'potencial perigo',
                r'possível dano',
                r'alerta para',
                r'cuidado especial',
                r'risco iminente',
                r'perigo potencial',
                r'vulnerabilidade aumentada',
                r'fator de risco',
                r'risco elevado',
                r'ameaça à segurança',
                r'risco de automutilação',
                r'risco de isolamento',
                r'risco de abandono'
            ],
            
            'positive_trend': [
                r'melhora significativa',
                r'progresso notável',
                r'avanço importante',
                r'grandes conquistas',
                r'evolução positiva',
                r'bons resultados',
                r'resultados promissores',
                r'indicadores positivos',
                r'avanços consistentes',
                r'melhora contínua',
                r'progresso estável'
            ],
            
            'insufficient_data': [
                r'informações insuficientes',
                r'dados limitados',
                r'necessário mais informações',
                r'dificuldade de avaliação',
                r'falta de dados claros',
                r'informações inconclusivas',
                r'necessário reavaliação',
                r'dados insatisfatórios',
                r'informações vagas',
                r'dados inconsistentes'
            ]
        }
        
        # Mapeamento de severidade baseado em termos encontrados
        self.severity_indicators = {
            'high': [
                r'emergência',
                r'crise',
                r'grave',
                r'sério',
                r'urgente',
                r'perigo imediato',
                r'risco alto',
                r'crítico',
                r'alarmante',
                r'grave deterioração'
            ],
            
            'medium': [
                r'preocupante',
                r'razoável preocupação',
                r'moderadamente grave',
                r'alguma preocupação',
                r'intermediário',
                r'cuidado necessário',
                r'atenção requerida'
            ],
            
            'low': [
                r'leve',
                r'minor',
                r'pequeno',
                r'pontual',
                r'isolado',
                r'ocasional'
            ]
        }

    def detect_alerts(self, query: str, response: str, patient_info: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Detecta automaticamente situações que mereçam alertas inteligentes
        
        :param query: Consulta original do usuário
        :param response: Resposta gerada pela IA
        :param patient_info: Informações do paciente (opcional)
        :return: Lista de alertas detectados
        """
        alerts = []
        
        # Combina todo o texto para análise
        full_text = f"{query} {response}".lower()
        
        # Detectar alertas baseados em padrões
        for alert_type, patterns in self.alert_patterns.items():
            detected_alerts = self._detect_pattern_alerts(full_text, alert_type, patterns)
            alerts.extend(detected_alerts)
        
        # Determinar severidade dos alertas
        for alert in alerts:
            alert['severity'] = self._determine_severity(alert['description'].lower())
        
        # Adicionar contexto do paciente se disponível
        if patient_info:
            for alert in alerts:
                alert['metadata'] = {'patient_context': patient_info}
        
        return alerts

    def _detect_pattern_alerts(self, text: str, alert_type: str, patterns: List[str]) -> List[Dict[str, Any]]:
        """
        Detecta alertas baseados em padrões específicos
        
        :param text: Texto para análise
        :param alert_type: Tipo de alerta
        :param patterns: Padrões para busca
        :return: Lista de alertas detectados
        """
        detected = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Pegar contexto ao redor da correspondência
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                alert = {
                    'alert_type': alert_type,
                    'description': f"Padrão detectado: '{match.group()}'",
                    'context': context,
                    'matched_pattern': pattern,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Evitar duplicatas
                if not any(a['description'] == alert['description'] for a in detected):
                    detected.append(alert)
        
        return detected

    def _determine_severity(self, text: str) -> str:
        """
        Determina a severidade de um alerta baseado em indicadores no texto
        
        :param text: Texto para análise
        :return: Nível de severidade ('high', 'medium', 'low', 'critical')
        """
        # Verificar indicadores de alta severidade
        for indicator in self.severity_indicators['high']:
            if re.search(indicator, text, re.IGNORECASE):
                return 'high'
        
        # Verificar indicadores de média severidade
        for indicator in self.severity_indicators['medium']:
            if re.search(indicator, text, re.IGNORECASE):
                return 'medium'
        
        # Verificar indicadores de baixa severidade
        for indicator in self.severity_indicators['low']:
            if re.search(indicator, text, re.IGNORECASE):
                return 'low'
        
        # Padrão é média severidade
        return 'medium'

    def generate_recommendations(self, alert_type: str) -> List[str]:
        """
        Gera recomendações automatizadas baseadas no tipo de alerta
        
        :param alert_type: Tipo de alerta detectado
        :return: Lista de recomendações
        """
        recommendations_map = {
            'regression': [
                "Reavaliar plano terapêutico",
                "Considerar ajustes na intervenção",
                "Agendar sessão de acompanhamento",
                "Consultar equipe multidisciplinar"
            ],
            
            'treatment_change_needed': [
                "Revisar abordagem terapêutica",
                "Considerar alternativas de tratamento",
                "Consultar supervisor clínico",
                "Planejar transição de intervenção"
            ],
            
            'risk': [
                "Aumentar frequência de sessões",
                "Implementar medidas de segurança",
                "Notificar equipe de apoio",
                "Estabelecer plano de contingência"
            ],
            
            'positive_trend': [
                "Continuar abordagem atual",
                "Documentar progressos alcançados",
                "Celebrar conquistas com paciente",
                "Planejar próximas metas"
            ],
            
            'insufficient_data': [
                "Coletar mais informações",
                "Realizar nova avaliação",
                "Solicitar informações complementares",
                "Agendar sessão de triagem"
            ]
        }
        
        return recommendations_map.get(alert_type, ["Avaliar caso individualmente"])