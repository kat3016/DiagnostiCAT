"""
Modelos Pydantic para datos médicos estructurados
Paso 3: Formato estándar para representación estructurada
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class HabitStatus(str, Enum):
    """Estados de hábitos"""
    YES = "sí"
    NO = "no"
    OCCASIONAL = "ocasional"
    UNKNOWN = "desconocido"


class UrgencyLevel(str, Enum):
    """Niveles de urgencia médica"""
    LOW = "bajo"
    MEDIUM = "medio"
    HIGH = "alto"
    CRITICAL = "crítico"


class ProcessingMethod(str, Enum):
    """Métodos de procesamiento de datos"""
    SEMANTIC_NLP = "semantic_nlp_extraction"
    BASIC_RULES = "basic_rules_extraction"
    FALLBACK = "fallback_basic"
    LLM_ENHANCED = "llm_enhanced_extraction"


class EnfermedadActual(BaseModel):
    """Modelo para enfermedad actual del paciente"""
    sintoma_principal: str = Field(..., description="Síntoma principal reportado")
    inicio: str = Field(..., description="Duración o momento de inicio de síntomas")
    caracteristicas: str = Field(..., description="Características del síntoma principal")
    intensidad: Optional[str] = Field(None, description="Intensidad del síntoma (1-10 o descriptivo)")
    localizacion: Optional[str] = Field(None, description="Localización anatómica del síntoma")
    patron_temporal: Optional[str] = Field(None, description="Patrón temporal (constante, intermitente, etc.)")
    
    @validator('sintoma_principal')
    def validate_sintoma_principal(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('El síntoma principal no puede estar vacío')
        return v.strip()


class Habitos(BaseModel):
    """Modelo para hábitos del paciente"""
    tabaquismo: HabitStatus = Field(HabitStatus.UNKNOWN, description="Estado de tabaquismo")
    alcohol: HabitStatus = Field(HabitStatus.UNKNOWN, description="Consumo de alcohol")
    drogas: Optional[HabitStatus] = Field(HabitStatus.UNKNOWN, description="Consumo de drogas")
    ejercicio: Optional[str] = Field(None, description="Nivel de actividad física")
    dieta: Optional[str] = Field(None, description="Características de la dieta")
    otros: Optional[str] = Field(None, description="Otros hábitos relevantes")
    
    class Config:
        use_enum_values = True


class StructuredMetadata(BaseModel):
    """Metadatos del procesamiento de estructuración"""
    format_version: str = Field("1.0", description="Versión del formato estándar")
    structured_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de estructuración")
    total_messages: int = Field(0, ge=0, description="Total de mensajes procesados")
    processing_method: ProcessingMethod = Field(ProcessingMethod.SEMANTIC_NLP, description="Método de procesamiento utilizado")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Score de confianza del procesamiento")
    extraction_errors: Optional[List[str]] = Field(default_factory=list, description="Errores durante extracción")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StructuredMedicalData(BaseModel):
    """
    Modelo principal para datos médicos estructurados
    Formato estándar único según requerimientos del Paso 3
    """
    
    # Campos básicos requeridos
    motivo_consulta: str = Field(..., min_length=1, max_length=500, description="Motivo principal de la consulta")
    enfermedad_actual: EnfermedadActual = Field(..., description="Información sobre la enfermedad actual")
    antecedentes_personales: List[str] = Field(default_factory=list, description="Antecedentes médicos personales")
    antecedentes_familiares: List[str] = Field(default_factory=list, description="Antecedentes médicos familiares")
    habitos: Habitos = Field(default_factory=Habitos, description="Hábitos del paciente")
    sintomas_asociados: List[str] = Field(default_factory=list, description="Síntomas asociados adicionales")
    
    # Campos adicionales para mejor clasificación
    medicamentos_actuales: Optional[List[str]] = Field(default_factory=list, description="Medicamentos que toma actualmente")
    alergias: Optional[List[str]] = Field(default_factory=list, description="Alergias conocidas")
    factores_agravantes: Optional[List[str]] = Field(default_factory=list, description="Factores que empeoran los síntomas")
    factores_aliviantes: Optional[List[str]] = Field(default_factory=list, description="Factores que mejoran los síntomas")
    signos_vitales: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Signos vitales si están disponibles")
    
    # Información contextual
    contexto_paciente: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Contexto adicional del paciente")
    urgencia_percibida: Optional[UrgencyLevel] = Field(None, description="Nivel de urgencia percibido")
    
    # Metadatos de procesamiento
    metadata: StructuredMetadata = Field(default_factory=StructuredMetadata, description="Metadatos del procesamiento")
    
    # Información de la conversación original
    conversation_id: Optional[str] = Field(None, description="ID de la conversación original")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="Timestamp de creación")
    
    @validator('motivo_consulta')
    def validate_motivo_consulta(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('El motivo de consulta no puede estar vacío')
        return v.strip()
    
    @validator('antecedentes_personales', 'antecedentes_familiares', 'sintomas_asociados')
    def validate_lists(cls, v):
        if v is None:
            return []
        # Filtrar elementos vacíos y normalizar
        return [item.strip() for item in v if item and item.strip()]
    
    def to_classification_format(self) -> Dict[str, Any]:
        """
        Convierte la estructura a formato optimizado para el modelo de clasificación
        """
        return {
            "chief_complaint": self.motivo_consulta,
            "symptoms": [self.enfermedad_actual.sintoma_principal] + self.sintomas_asociados,
            "history": self.antecedentes_personales + self.antecedentes_familiares,
            "current_medications": self.medicamentos_actuales or [],
            "habits": {
                "smoking": self.habitos.tabaquismo,
                "alcohol": self.habitos.alcohol,
                "others": self.habitos.otros or ""
            },
            "duration": self.enfermedad_actual.inicio,
            "severity": self.enfermedad_actual.intensidad or "no especificada",
            "associated_factors": (self.factores_agravantes or []) + (self.factores_aliviantes or []),
            "metadata": {
                "processing_timestamp": self.metadata.structured_timestamp.isoformat(),
                "confidence": self.metadata.confidence_score,
                "method": self.metadata.processing_method
            }
        }
    
    def get_summary(self) -> str:
        """
        Genera un resumen textual de los datos estructurados
        """
        summary_parts = [
            f"Motivo: {self.motivo_consulta}",
            f"Síntoma principal: {self.enfermedad_actual.sintoma_principal}",
            f"Duración: {self.enfermedad_actual.inicio}"
        ]
        
        if self.antecedentes_personales:
            summary_parts.append(f"Antecedentes: {', '.join(self.antecedentes_personales[:3])}")
        
        if self.sintomas_asociados:
            summary_parts.append(f"Síntomas asociados: {', '.join(self.sintomas_asociados[:3])}")
        
        return " | ".join(summary_parts)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True


class StructuringRequest(BaseModel):
    """Modelo para solicitud de estructuración de datos"""
    conversation_data: Dict[str, Any] = Field(..., description="Datos de conversación a estructurar")
    processing_options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Opciones de procesamiento")
    include_metadata: bool = Field(True, description="Incluir metadatos detallados")


class StructuringResponse(BaseModel):
    """Modelo para respuesta de estructuración de datos"""
    structured_data: StructuredMedicalData = Field(..., description="Datos médicos estructurados")
    processing_success: bool = Field(..., description="Éxito del procesamiento")
    processing_time_ms: Optional[float] = Field(None, description="Tiempo de procesamiento en milisegundos")
    warnings: Optional[List[str]] = Field(default_factory=list, description="Advertencias durante el procesamiento")
    errors: Optional[List[str]] = Field(default_factory=list, description="Errores durante el procesamiento")
    
    def is_ready_for_classification(self) -> bool:
        """Verifica si los datos están listos para clasificación"""
        return (
            self.processing_success and
            bool(self.structured_data.motivo_consulta) and
            bool(self.structured_data.enfermedad_actual.sintoma_principal) and
            len(self.errors or []) == 0
        )


class ValidationResult(BaseModel):
    """Resultado de validación de estructura"""
    is_valid: bool = Field(..., description="Si la estructura es válida")
    missing_required_fields: List[str] = Field(default_factory=list, description="Campos requeridos faltantes")
    validation_errors: List[str] = Field(default_factory=list, description="Errores de validación")
    completeness_score: float = Field(0.0, ge=0.0, le=1.0, description="Score de completitud (0-1)")
    recommendations: List[str] = Field(default_factory=list, description="Recomendaciones para mejorar la estructura")


# Funciones de utilidad para validación
def validate_structured_data(data: Dict[str, Any]) -> ValidationResult:
    """
    Valida datos estructurados contra el formato estándar
    """
    try:
        # Intentar crear el modelo
        structured = StructuredMedicalData(**data)
        
        # Calcular completitud
        completeness = calculate_completeness(structured)
        
        return ValidationResult(
            is_valid=True,
            completeness_score=completeness,
            recommendations=generate_recommendations(structured, completeness)
        )
        
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            validation_errors=[str(e)],
            completeness_score=0.0,
            recommendations=["Corregir errores de validación antes de proceder"]
        )


def calculate_completeness(data: StructuredMedicalData) -> float:
    """
    Calcula score de completitud de los datos estructurados
    """
    total_fields = 10  # Campos considerados importantes
    completed_fields = 0
    
    # Campos básicos (peso mayor)
    if data.motivo_consulta and len(data.motivo_consulta.strip()) > 0:
        completed_fields += 2
    if data.enfermedad_actual.sintoma_principal:
        completed_fields += 2
    if data.enfermedad_actual.inicio != "no especificado":
        completed_fields += 1
    
    # Campos adicionales
    if data.antecedentes_personales:
        completed_fields += 1
    if data.sintomas_asociados:
        completed_fields += 1
    if data.habitos.tabaquismo != HabitStatus.UNKNOWN:
        completed_fields += 1
    if data.medicamentos_actuales:
        completed_fields += 1
    if data.enfermedad_actual.intensidad:
        completed_fields += 1
    
    return min(completed_fields / total_fields, 1.0)


def generate_recommendations(data: StructuredMedicalData, completeness: float) -> List[str]:
    """
    Genera recomendaciones para mejorar la estructura de datos
    """
    recommendations = []
    
    if completeness < 0.5:
        recommendations.append("Datos insuficientes para clasificación confiable")
    
    if not data.antecedentes_personales:
        recommendations.append("Considerar recopilar antecedentes médicos")
    
    if data.enfermedad_actual.inicio == "no especificado":
        recommendations.append("Especificar duración o inicio de síntomas")
    
    if not data.enfermedad_actual.intensidad:
        recommendations.append("Obtener información sobre intensidad de síntomas")
    
    if data.habitos.tabaquismo == HabitStatus.UNKNOWN and data.habitos.alcohol == HabitStatus.UNKNOWN:
        recommendations.append("Recopilar información sobre hábitos relevantes")
    
    return recommendations
