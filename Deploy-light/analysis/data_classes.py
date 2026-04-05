"""
Classes de dados compartilhadas para o sistema de análise de evolução clínica
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class EvolutionPattern(Enum):
    """Padrões de evolução clínica"""
    POSITIVE = "positive"
    STAGNANT = "stagnant"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


@dataclass
class SessionData:
    """Dados de uma sessão clínica"""
    id: int
    patient_id: int
    owner_id: int
    date: datetime
    content: str
    assessment_score: Optional[float] = None
    keywords: Optional[List[str]] = None


@dataclass
class EvolutionAnalysisResult:
    """Resultado da análise de evolução"""
    patient_id: int
    owner_id: int
    sessions_analyzed: int
    evolution_pattern: EvolutionPattern
    evolution_score: float  # 0.0 a 1.0, onde >0.7 é positivo, <0.3 é negativo
    clinical_notes: str
    recommendations: List[str]
    alerts_needed: List[str]
    session_comparison: Dict[str, any]