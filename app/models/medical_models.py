"""
Modelos Pydantic para conversaciones médicas
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Roles de mensajes en la conversación"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Severity(str, Enum):
    """Niveles de severidad médica"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MessageModel(BaseModel):
    """Modelo para mensajes de conversación"""
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = {}
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationRequest(BaseModel):
    """Solicitud de conversación médica"""
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    patient_context: Optional[Dict[str, Any]] = {}
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('El mensaje no puede estar vacío')
        return v.strip()


class ConversationResponse(BaseModel):
    """Respuesta de conversación médica"""
    response: str
    conversation_id: str
    agent_type: str
    confidence_score: Optional[float] = None
    suggestions: Optional[List[str]] = []
    severity_assessment: Optional[Severity] = None
    follow_up_questions: Optional[List[str]] = []
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PatientContext(BaseModel):
    """Contexto del paciente"""
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = None
    medical_history: Optional[List[str]] = []
    current_medications: Optional[List[str]] = []
    allergies: Optional[List[str]] = []
    symptoms: Optional[List[str]] = []
    
    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('La edad debe estar entre 0 y 150 años')
        return v


class MedicalAssessment(BaseModel):
    """Evaluación médica generada por el agente"""
    primary_concerns: List[str] = []
    differential_diagnosis: List[str] = []
    recommended_actions: List[str] = []
    urgency_level: Severity = Severity.LOW
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    reasoning: str = ""
    
    @validator('confidence_score')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('El score de confianza debe estar entre 0.0 y 1.0')
        return v


class ConversationHistory(BaseModel):
    """Historial completo de conversación"""
    conversation_id: str
    messages: List[MessageModel] = []
    patient_context: Optional[PatientContext] = None
    assessments: List[MedicalAssessment] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnamnesisRequest(BaseModel):
    """Entrada para flujo de anamnesis paso a paso"""
    motivo_consulta: Optional[str] = None
    enfermedad_actual: Optional[Dict[str, Any]] = None  # {sintoma_principal, inicio, caracteristicas}
    antecedentes_personales: Optional[List[str]] = None
    antecedentes_familiares: Optional[List[str]] = None
    habitos: Optional[Dict[str, Any]] = None  # {tabaquismo, alcohol, otros}
    sintomas_asociados: Optional[List[str]] = None


class AnamnesisStructured(BaseModel):
    """Estructura estándar JSON de la anamnesis"""
    motivo_consulta: str
    enfermedad_actual: Dict[str, Any]
    antecedentes_personales: List[str] = []
    antecedentes_familiares: List[str] = []
    habitos: Dict[str, Any] = {}
    sintomas_asociados: List[str] = []


class ChatRequest(BaseModel):
    """Solicitud de chat médico"""
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    patient_context: Optional[Dict[str, Any]] = {}
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('El mensaje no puede estar vacío')
        return v.strip()


class ChatResponse(BaseModel):
    """Respuesta de chat médico"""
    response: str
    conversation_id: str
    agent_type: str
    confidence_score: Optional[float] = 0.0
    severity_assessment: Optional[str] = "BAJO"
    suggestions: Optional[List[str]] = []
    follow_up_questions: Optional[List[str]] = []
    predicted_condition: Optional[str] = None
    is_diagnosis: Optional[bool] = False
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
