"""
Herramientas personalizadas para CrewAI
"""

import json
import asyncio
from typing import Dict, Any
from crewai_tools import tool

from app.services.classification_service import classification_model


@tool("medical_classifier")
def classify_medical_data(structured_json_data: str) -> str:
    """
    Herramienta para clasificar datos médicos estructurados usando el modelo Hugging Face.
    
    Args:
        structured_json_data: Datos médicos en formato JSON string
        
    Returns:
        Resultado de clasificación en formato JSON string
    """
    try:
        # Parsear los datos JSON
        if isinstance(structured_json_data, str):
            data = json.loads(structured_json_data)
        else:
            data = structured_json_data
        
        # Ejecutar clasificación de forma síncrona
        # (CrewAI tools deben ser síncronos, pero el modelo puede ser async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(classification_model.classify(data))
        finally:
            loop.close()
        
        # Convertir resultado a JSON string
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "error": f"Error en clasificación: {str(e)}",
            "primary_category": "other",
            "confidence_score": 0.0,
            "reasoning": f"Error procesando datos: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@tool("json_validator")
def validate_json_structure(json_string: str) -> str:
    """
    Herramienta para validar que un string sea JSON válido.
    
    Args:
        json_string: String a validar
        
    Returns:
        Resultado de validación
    """
    try:
        data = json.loads(json_string)
        return json.dumps({
            "valid": True,
            "message": "JSON válido",
            "keys_count": len(data) if isinstance(data, dict) else 0
        }, ensure_ascii=False)
    except json.JSONDecodeError as e:
        return json.dumps({
            "valid": False,
            "error": str(e),
            "message": "JSON inválido"
        }, ensure_ascii=False)


@tool("medical_data_formatter")
def format_medical_data_for_classification(raw_data: str) -> str:
    """
    Herramienta para formatear datos médicos en el formato esperado por el clasificador.
    
    Args:
        raw_data: Datos médicos sin formato
        
    Returns:
        Datos formateados para clasificación
    """
    try:
        # Estructura básica esperada por el clasificador
        formatted_data = {
            "patient_data": raw_data,
            "symptoms": [],
            "medical_history": "",
            "current_medications": "",
            "severity": "unknown",
            "duration": "unknown"
        }
        
        return json.dumps(formatted_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Error formateando datos: {str(e)}",
            "raw_data": raw_data
        }, ensure_ascii=False)
