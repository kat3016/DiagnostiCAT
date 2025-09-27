"""
Endpoints para conversación médica
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import uuid
from datetime import datetime

from app.models.medical_models import (
    ConversationRequest, 
    ConversationResponse, 
    ConversationHistory,
    MessageModel,
    MessageRole
)
from app.services.agent_service import agent_service

router = APIRouter()

# Simulamos un almacenamiento en memoria para las conversaciones
# En producción, esto estaría en una base de datos
conversations_storage: dict = {}


@router.post("/", response_model=ConversationResponse)
async def chat_with_medical_agent(request: ConversationRequest):
    """
    Endpoint principal para conversación médica
    
    Args:
        request: Solicitud de conversación
        
    Returns:
        ConversationResponse: Respuesta del agente médico
    """
    try:
        # Obtener o crear conversación
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Obtener historial de conversación
        conversation_history = []
        if conversation_id in conversations_storage:
            conversation_history = conversations_storage[conversation_id]["messages"]
        
        # Recomendar agente apropiado
        agent = agent_service.recommend_agent(
            message=request.message,
            conversation_history=conversation_history
        )
        
        # Procesar mensaje con el agente
        agent_response = await agent_service.process_message_with_agent(
            agent_id=agent.id,
            message=request.message,
            conversation_history=conversation_history,
            patient_context=request.patient_context
        )
        
        # Crear mensajes para el historial
        user_message = MessageModel(
            role=MessageRole.USER,
            content=request.message,
            timestamp=datetime.now()
        )
        
        assistant_message = MessageModel(
            role=MessageRole.ASSISTANT,
            content=agent_response.response_text,
            timestamp=agent_response.timestamp
        )
        
        # Actualizar historial de conversación
        if conversation_id not in conversations_storage:
            conversations_storage[conversation_id] = {
                "messages": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        
        conversations_storage[conversation_id]["messages"].extend([
            user_message, assistant_message
        ])
        conversations_storage[conversation_id]["updated_at"] = datetime.now()
        
        # Evaluar severidad
        severity = agent.assess_urgency(request.message, request.patient_context or {})
        
        # Generar sugerencias de seguimiento
        follow_up_questions = _generate_follow_up_questions(
            request.message, agent_response.response_text
        )
        
        return ConversationResponse(
            response=agent_response.response_text,
            conversation_id=conversation_id,
            agent_type=agent.name,
            confidence_score=agent_response.confidence_score,
            suggestions=_generate_suggestions(request.message),
            severity_assessment=severity,
            follow_up_questions=follow_up_questions,
            timestamp=agent_response.timestamp
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando la consulta médica: {str(e)}"
        )


@router.get("/{conversation_id}/history", response_model=ConversationHistory)
async def get_conversation_history(conversation_id: str):
    """
    Obtiene el historial de una conversación específica
    
    Args:
        conversation_id: ID de la conversación
        
    Returns:
        ConversationHistory: Historial completo de la conversación
    """
    if conversation_id not in conversations_storage:
        raise HTTPException(
            status_code=404,
            detail="Conversación no encontrada"
        )
    
    conversation_data = conversations_storage[conversation_id]
    
    return ConversationHistory(
        conversation_id=conversation_id,
        messages=conversation_data["messages"],
        created_at=conversation_data["created_at"],
        updated_at=conversation_data["updated_at"]
    )


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Elimina una conversación
    
    Args:
        conversation_id: ID de la conversación a eliminar
        
    Returns:
        dict: Confirmación de eliminación
    """
    if conversation_id not in conversations_storage:
        raise HTTPException(
            status_code=404,
            detail="Conversación no encontrada"
        )
    
    del conversations_storage[conversation_id]
    
    return {
        "message": "Conversación eliminada exitosamente",
        "conversation_id": conversation_id
    }


@router.get("/conversations/list")
async def list_conversations():
    """
    Lista todas las conversaciones activas
    
    Returns:
        dict: Lista de conversaciones con información básica
    """
    conversations_list = []
    
    for conv_id, conv_data in conversations_storage.items():
        # Obtener último mensaje
        last_message = ""
        if conv_data["messages"]:
            last_message = conv_data["messages"][-1].content[:100] + "..."
        
        conversations_list.append({
            "conversation_id": conv_id,
            "created_at": conv_data["created_at"],
            "updated_at": conv_data["updated_at"],
            "message_count": len(conv_data["messages"]),
            "last_message": last_message
        })
    
    # Ordenar por fecha de actualización (más reciente primero)
    conversations_list.sort(key=lambda x: x["updated_at"], reverse=True)
    
    return {
        "conversations": conversations_list,
        "total_count": len(conversations_list)
    }


def _generate_suggestions(message: str) -> List[str]:
    """Genera sugerencias basadas en el mensaje del usuario"""
    message_lower = message.lower()
    suggestions = []
    
    if 'dolor' in message_lower:
        suggestions.extend([
            "Describe la intensidad del dolor del 1 al 10",
            "¿El dolor es constante o intermitente?",
            "¿Hay algo que mejore o empeore el dolor?"
        ])
    
    if 'fiebre' in message_lower:
        suggestions.extend([
            "¿Has medido tu temperatura exacta?",
            "¿Tienes otros síntomas acompañantes?",
            "¿Has tomado algún medicamento para la fiebre?"
        ])
    
    if not suggestions:
        suggestions = [
            "¿Cuándo comenzaron los síntomas?",
            "¿Tienes alguna condición médica previa?",
            "¿Tomas algún medicamento actualmente?"
        ]
    
    return suggestions[:3]  # Máximo 3 sugerencias


def _generate_follow_up_questions(user_message: str, agent_response: str) -> List[str]:
    """Genera preguntas de seguimiento relevantes"""
    follow_ups = []
    
    user_lower = user_message.lower()
    response_lower = agent_response.lower()
    
    if 'dolor' in user_lower and 'ubicación' not in response_lower:
        follow_ups.append("¿Puedes señalar exactamente dónde sientes el dolor?")
    
    if 'síntoma' in response_lower:
        follow_ups.append("¿Hay algún otro síntoma que no hayas mencionado?")
    
    if 'medicamento' in response_lower:
        follow_ups.append("¿Tienes alguna alergia a medicamentos?")
    
    # Preguntas generales de seguimiento
    if not follow_ups:
        follow_ups = [
            "¿Hay algo más que te preocupe sobre tu salud?",
            "¿Tienes alguna pregunta sobre lo que hemos discutido?",
            "¿Te gustaría programar una consulta presencial?"
        ]
    
    return follow_ups[:2]  # Máximo 2 preguntas de seguimiento
