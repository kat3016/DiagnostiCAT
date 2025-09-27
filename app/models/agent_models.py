"""
Modelos para agentes de IA médicos
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AgentType(str, Enum):
    """Tipos de agentes según el flujo específico"""
    INITIAL_INTERVIEW = "initial_interview"
    PRELIMINARY_ANALYSIS = "preliminary_analysis"
    DATA_STRUCTURING = "data_structuring"


class AgentStatus(str, Enum):
    """Estados de los agentes"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BUSY = "busy"
    MAINTENANCE = "maintenance"


class AgentConfig(BaseModel):
    """Configuración de un agente"""
    name: str
    agent_type: AgentType
    description: str
    specialties: List[str] = []
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(1000, ge=100, le=4000)
    system_prompt: str
    knowledge_base: Optional[Dict[str, Any]] = {}
    
    class Config:
        use_enum_values = True


class AgentResponse(BaseModel):
    """Respuesta de un agente"""
    agent_id: str
    agent_type: AgentType
    response_text: str
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    processing_time: float  # en segundos
    tokens_used: int
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentMetrics(BaseModel):
    """Métricas de rendimiento de un agente"""
    agent_id: str
    total_conversations: int = 0
    avg_response_time: float = 0.0
    avg_confidence_score: float = 0.0
    success_rate: float = 0.0
    last_active: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateAgentRequest(BaseModel):
    """Solicitud para crear un nuevo agente"""
    name: str = Field(..., min_length=1, max_length=100)
    agent_type: AgentType
    description: str = Field(..., min_length=1, max_length=500)
    specialties: List[str] = []
    system_prompt: Optional[str] = None
    
    class Config:
        use_enum_values = True


class UpdateAgentRequest(BaseModel):
    """Solicitud para actualizar un agente"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    specialties: Optional[List[str]] = None
    status: Optional[AgentStatus] = None
    system_prompt: Optional[str] = None
    
    class Config:
        use_enum_values = True


class AgentInfo(BaseModel):
    """Información completa de un agente"""
    id: str
    name: str
    agent_type: AgentType
    description: str
    specialties: List[str]
    status: AgentStatus
    created_at: datetime
    updated_at: datetime
    metrics: Optional[AgentMetrics] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True
