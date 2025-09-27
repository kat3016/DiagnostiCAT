"""
Servicio de modelo de clasificación médica
"""

import json
from typing import Dict, Any, List
from datetime import datetime

from app.services.llm_service import llm_service


class ClassificationModel:
    """Modelo de clasificación médica"""
    
    def __init__(self):
        self.model_name = "medical_classifier_v1"
        self.version = "1.0.0"
        self.categories = [
            "neurological",
            "cardiovascular", 
            "respiratory",
            "gastrointestinal",
            "musculoskeletal",
            "dermatological",
            "psychiatric",
            "other"
        ]
    
    async def classify(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clasifica los datos estructurados de la anamnesis
        
        Args:
            structured_data: Datos estructurados de la anamnesis
            
        Returns:
            Dict con clasificación, confianza y recomendaciones
        """
        
        # Usar LLM como modelo de clasificación (simulando ML)
        classification_prompt = f"""Eres un modelo de clasificación médica experto. Analiza los datos estructurados de anamnesis y clasifica el caso.

CATEGORÍAS DISPONIBLES:
- neurological: Problemas neurológicos (cefaleas, migrañas, epilepsia, etc.)
- cardiovascular: Problemas cardíacos y vasculares
- respiratory: Problemas respiratorios
- gastrointestinal: Problemas digestivos
- musculoskeletal: Problemas músculo-esqueléticos
- dermatological: Problemas de piel
- psychiatric: Problemas de salud mental
- other: Otros casos no clasificables

FORMATO DE RESPUESTA (JSON):
{{
  "primary_category": "categoria_principal",
  "confidence_score": 0.85,
  "secondary_categories": ["categoria_secundaria"],
  "key_indicators": ["indicador1", "indicador2"],
  "recommendations": [
    "recomendacion1",
    "recomendacion2"
  ],
  "urgency_level": "low|medium|high|critical",
  "reasoning": "Explicación breve del diagnóstico"
}}

Analiza cuidadosamente y responde SOLO con el JSON válido."""
        
        try:
            llm_response = await llm_service.generate_response(
                system_prompt=classification_prompt,
                user_message=f"Datos de anamnesis para clasificar:\n{json.dumps(structured_data, ensure_ascii=False, indent=2)}",
                conversation_history=[]
            )
            
            # Intentar parsear la respuesta como JSON
            try:
                classification_result = json.loads(llm_response["response"])
                
                # Validar estructura
                required_fields = ["primary_category", "confidence_score", "recommendations", "urgency_level"]
                for field in required_fields:
                    if field not in classification_result:
                        raise ValueError(f"Campo requerido faltante: {field}")
                
                # Agregar metadata del modelo
                classification_result.update({
                    "model_name": self.model_name,
                    "model_version": self.version,
                    "classification_timestamp": datetime.now().isoformat(),
                    "tokens_used": llm_response["tokens_used"]
                })
                
                return classification_result
                
            except json.JSONDecodeError:
                # Si no es JSON válido, crear estructura básica
                return self._create_fallback_classification(structured_data, llm_response["response"])
                
        except Exception as e:
            return self._create_error_classification(str(e))
    
    def _create_fallback_classification(self, structured_data: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Crear clasificación de fallback cuando el LLM no retorna JSON válido"""
        
        # Análisis básico de palabras clave
        text_content = json.dumps(structured_data, ensure_ascii=False).lower()
        
        primary_category = "other"
        confidence = 0.5
        
        # Clasificación básica por palabras clave
        if any(word in text_content for word in ["dolor cabeza", "cefalea", "migraña", "mareo"]):
            primary_category = "neurological"
            confidence = 0.7
        elif any(word in text_content for word in ["dolor pecho", "corazón", "presión"]):
            primary_category = "cardiovascular"
            confidence = 0.7
        elif any(word in text_content for word in ["tos", "respirar", "pulmón", "aire"]):
            primary_category = "respiratory"
            confidence = 0.7
        elif any(word in text_content for word in ["estómago", "nausea", "vómito", "digestivo"]):
            primary_category = "gastrointestinal"
            confidence = 0.7
        
        return {
            "primary_category": primary_category,
            "confidence_score": confidence,
            "secondary_categories": [],
            "key_indicators": ["Análisis automático por palabras clave"],
            "recommendations": [
                "Consulta médica para evaluación completa",
                "Seguimiento según evolución de síntomas"
            ],
            "urgency_level": "medium",
            "reasoning": f"Clasificación automática basada en análisis de contenido. Respuesta original: {raw_response[:100]}...",
            "model_name": self.model_name,
            "model_version": self.version,
            "classification_timestamp": datetime.now().isoformat(),
            "fallback_used": True
        }
    
    def _create_error_classification(self, error_msg: str) -> Dict[str, Any]:
        """Crear clasificación de error"""
        return {
            "primary_category": "other",
            "confidence_score": 0.0,
            "secondary_categories": [],
            "key_indicators": ["Error en clasificación"],
            "recommendations": [
                "Revisar datos de entrada",
                "Consulta médica recomendada"
            ],
            "urgency_level": "medium",
            "reasoning": f"Error en clasificación: {error_msg}",
            "model_name": self.model_name,
            "model_version": self.version,
            "classification_timestamp": datetime.now().isoformat(),
            "error": True,
            "error_message": error_msg
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Información del modelo de clasificación"""
        return {
            "name": self.model_name,
            "version": self.version,
            "categories": self.categories,
            "description": "Modelo de clasificación médica basado en LLM para anamnesis conversacional",
            "input_format": "Datos estructurados de anamnesis en JSON",
            "output_format": "Clasificación con categoría, confianza y recomendaciones"
        }


# Instancia global del modelo
classification_model = ClassificationModel()
