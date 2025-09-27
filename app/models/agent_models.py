"""
Modelos para agentes médicos
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AgentType(str, Enum):
    """Tipos de agentes médicos"""
    TRIAGE = "triage"
    INTERVIEWER = "interviewer"
    ANALYZER = "analyzer"
    CLASSIFIER = "classifier"
    STRUCTURER = "structurer"
    CONSENT_HANDLER = "consent_handler"
    MEDICAL_INTERVIEWER = "medical_interviewer"
    FALLBACK_HANDLER = "fallback_handler"
    ERROR_HANDLER = "error_handler"


class AgentInfo(BaseModel):
    """Información de un agente"""
    agent_type: AgentType
    name: str
    description: str
    capabilities: List[str] = []
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentMetrics(BaseModel):
    """Métricas de rendimiento de un agente"""
    agent_type: AgentType
    total_interactions: int = 0
    successful_interactions: int = 0
    average_confidence: float = 0.0
    average_response_time: float = 0.0
    last_interaction: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentResponse(BaseModel):
    """Respuesta de un agente"""
    agent_type: AgentType
    content: str
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }