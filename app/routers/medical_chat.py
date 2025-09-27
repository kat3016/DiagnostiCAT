"""
Router para chat médico conversacional
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import re

from app.models.medical_models import MessageModel, MessageRole, ChatResponse, ChatRequest

router = APIRouter()

# Estado de conversaciones
CONVERSATIONS: Dict[str, Dict[str, Any]] = {}

class ConversationState:
    """Estados de la conversación"""
    AWAITING_CONSENT = "awaiting_consent"
    CONSENT_GIVEN = "consent_given"
    INTERVIEWING = "interviewing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"


@router.post("/", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """Endpoint principal para chat médico conversacional"""
    
    # Si no hay conversation_id, crear una nueva conversación
    if not request.conversation_id:
        conversation_id = str(uuid.uuid4())
        CONVERSATIONS[conversation_id] = {
            "state": ConversationState.AWAITING_CONSENT,
            "messages": [],
            "consent_given": False,
            "interview_data": {},
            "created_at": datetime.now()
        }
    else:
        conversation_id = request.conversation_id
        if conversation_id not in CONVERSATIONS:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    conversation = CONVERSATIONS[conversation_id]
    user_message = request.message.lower().strip()
    
    # Registrar mensaje del usuario
    conversation["messages"].append({
        "role": MessageRole.USER,
        "content": request.message,
        "timestamp": datetime.now()
    })
    
    try:
        # Manejar consentimiento
        if conversation["state"] == ConversationState.AWAITING_CONSENT:
            return await handle_consent(conversation_id, user_message, request.message)
        
        # Manejar conversación normal después del consentimiento
        elif conversation["state"] == ConversationState.CONSENT_GIVEN:
            return await handle_medical_conversation(conversation_id, request.message)
        
        else:
            # Estados más avanzados del flujo
            return await handle_advanced_conversation(conversation_id, request.message)
    
    except Exception as e:
        # Registrar error
        error_response = ChatResponse(
            response=f"Disculpe, ha ocurrido un error interno: {str(e)}. Por favor, intente de nuevo o reinicie la conversación.",
            conversation_id=conversation_id,
            agent_type="error_handler",
            confidence_score=0.0,
            severity_assessment="BAJO",
            suggestions=["Reiniciar la conversación", "Verificar conexión"],
            follow_up_questions=[]
        )
        
        CONVERSATIONS[conversation_id]["messages"].append({
            "role": MessageRole.ASSISTANT,
            "content": error_response.response,
            "timestamp": datetime.now(),
            "is_error": True
        })
        
        return error_response


async def handle_consent(conversation_id: str, user_message_lower: str, original_message: str) -> ChatResponse:
    """Maneja la fase de consentimiento"""
    conversation = CONVERSATIONS[conversation_id]
    
    # Detectar consentimiento positivo
    positive_patterns = [
        r'sí\s+acepto', r'si\s+acepto', r'acepto', r'sí', r'si', r'yes', r'okay', r'ok', 
        r'estoy\s+de\s+acuerdo', r'de\s+acuerdo', r'conforme', r'autorizo'
    ]
    
    # Detectar consentimiento negativo
    negative_patterns = [
        r'no\s+acepto', r'no', r'niego', r'rechaz[oa]', r'no\s+autorizo', 
        r'no\s+estoy\s+de\s+acuerdo', r'en\s+desacuerdo'
    ]
    
    consent_given = False
    for pattern in positive_patterns:
        if re.search(pattern, user_message_lower):
            consent_given = True
            break
    
    consent_denied = False
    for pattern in negative_patterns:
        if re.search(pattern, user_message_lower):
            consent_denied = True
            break
    
    if consent_given:
        # Consentimiento otorgado
        conversation["state"] = ConversationState.CONSENT_GIVEN
        conversation["consent_given"] = True
        
        response_text = "¡Perfecto! Gracias por otorgar su consentimiento. Ahora puedo ayudarle con su consulta médica. Por favor, describa sus síntomas o la razón de su consulta."
        
        conversation["messages"].append({
            "role": MessageRole.ASSISTANT,
            "content": response_text,
            "timestamp": datetime.now()
        })
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            agent_type="consent_handler",
            confidence_score=1.0,
            severity_assessment="BAJO",
            suggestions=["Describir síntomas principales", "Mencionar duración de los síntomas", "Indicar nivel de dolor si aplica"],
            follow_up_questions=[
                "¿Cuáles son sus síntomas principales?",
                "¿Cuándo comenzaron estos síntomas?",
                "¿Ha tomado algún medicamento?"
            ]
        )
    
    elif consent_denied:
        # Consentimiento denegado
        response_text = "Entiendo que no desea otorgar el consentimiento. Sin su consentimiento, no puedo proceder con la consulta médica. Si cambia de opinión, puede reiniciar la conversación. ¡Que tenga un buen día!"
        
        conversation["messages"].append({
            "role": MessageRole.ASSISTANT,
            "content": response_text,
            "timestamp": datetime.now()
        })
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            agent_type="consent_handler",
            confidence_score=1.0,
            severity_assessment="BAJO",
            suggestions=["Reiniciar conversación si cambia de opinión"],
            follow_up_questions=[]
        )
    
    else:
        # Respuesta ambigua - pedir clarificación
        response_text = "No he podido interpretar claramente su respuesta sobre el consentimiento. Por favor, responda de manera clara: ¿Acepta que procese su información médica para brindarle asistencia? Puede responder 'sí acepto' o 'no acepto'."
        
        conversation["messages"].append({
            "role": MessageRole.ASSISTANT,
            "content": response_text,
            "timestamp": datetime.now()
        })
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            agent_type="consent_handler",
            confidence_score=0.5,
            severity_assessment="BAJO",
            suggestions=["Responder 'sí acepto'", "Responder 'no acepto'"],
            follow_up_questions=["¿Acepta el procesamiento de su información médica?"]
        )


async def handle_medical_conversation(conversation_id: str, message: str) -> ChatResponse:
    """Maneja la conversación médica después del consentimiento"""
    conversation = CONVERSATIONS[conversation_id]
    
    # Por ahora, usamos respuestas predeterminadas hasta que tengamos CrewAI funcionando
    try:
        # Analizar el mensaje para generar una respuesta médica básica
        agent_response = generate_basic_medical_response(message, conversation["messages"])
        
        # Registrar respuesta del agente
        conversation["messages"].append({
            "role": MessageRole.ASSISTANT,
            "content": agent_response,
            "timestamp": datetime.now()
        })
        
        return ChatResponse(
            response=agent_response,
            conversation_id=conversation_id,
            agent_type="medical_interviewer",
            confidence_score=0.7,
            severity_assessment="MEDIO",
            suggestions=[
                "Proporcionar más detalles sobre los síntomas",
                "Mencionar la duración exacta",
                "Indicar cualquier medicamento que esté tomando"
            ],
            follow_up_questions=[
                "¿Puede describir más detalladamente el síntoma?",
                "¿Ha notado algún patrón en cuanto al momento del día?",
                "¿Hay algo que mejore o empeore los síntomas?"
            ]
        )
        
    except Exception as e:
        # Fallback si algo falla
        fallback_response = f"Entiendo su consulta sobre: {message}. Me disculpo, pero estoy experimentando dificultades técnicas con el sistema de análisis médico. ¿Podría reformular su consulta o ser más específico sobre sus síntomas?"
        
        conversation["messages"].append({
            "role": MessageRole.ASSISTANT,
            "content": fallback_response,
            "timestamp": datetime.now()
        })
        
        return ChatResponse(
            response=fallback_response,
            conversation_id=conversation_id,
            agent_type="fallback_handler",
            confidence_score=0.3,
            severity_assessment="BAJO",
            suggestions=["Reformular la consulta", "Ser más específico", "Reiniciar si persiste el problema"],
            follow_up_questions=["¿Puede describir sus síntomas de forma más específica?"]
        )


def generate_basic_medical_response(message: str, conversation_history: list) -> str:
    """Genera una respuesta médica básica basada en palabras clave"""
    message_lower = message.lower()
    
    # Respuestas basadas en síntomas comunes
    if any(word in message_lower for word in ['dolor', 'duele', 'molesta']):
        return "Entiendo que experimenta dolor. Para poder ayudarle mejor, necesito más información: ¿En qué parte del cuerpo siente el dolor? ¿Cómo describiría el dolor (punzante, sordo, pulsante)? ¿Cuándo comenzó y qué lo hace empeorar o mejorar?"
    
    elif any(word in message_lower for word in ['fiebre', 'temperatura', 'calentura']):
        return "La fiebre puede ser síntoma de varias condiciones. ¿Ha medido su temperatura? ¿Tiene otros síntomas como escalofríos, dolor de cabeza, o malestar general? ¿Cuánto tiempo lleva con fiebre?"
    
    elif any(word in message_lower for word in ['tos', 'toser', 'expectoracion']):
        return "La tos puede tener varias causas. ¿Es una tos seca o produce flema? ¿Hay sangre en la expectoración? ¿Cuánto tiempo lleva con la tos? ¿Tiene otros síntomas respiratorios como dificultad para respirar?"
    
    elif any(word in message_lower for word in ['nausea', 'nauseas', 'vomito', 'vomitos', 'mareo']):
        return "Las náuseas y vómitos pueden ser síntomas de diferentes condiciones. ¿Cuándo comenzaron? ¿Ha vomitado y qué aspecto tiene el vómito? ¿Tiene dolor abdominal, fiebre o diarrea asociados?"
    
    elif any(word in message_lower for word in ['cabeza', 'dolor de cabeza', 'cefalea']):
        return "Los dolores de cabeza pueden variar mucho. ¿Cómo describiría el dolor (pulsante, presión, punzante)? ¿En qué parte de la cabeza lo siente? ¿Cuánto tiempo lleva con este dolor? ¿Hay algo que lo desencadene o lo alivie?"
    
    elif any(word in message_lower for word in ['estomago', 'abdominal', 'barriga', 'vientre']):
        return "El dolor abdominal requiere evaluación cuidadosa. ¿En qué parte del abdomen siente el dolor? ¿Es constante o viene en oleadas? ¿Se irradia a otras partes? ¿Tiene náuseas, vómitos, o cambios en las deposiciones?"
    
    elif any(word in message_lower for word in ['cansancio', 'fatiga', 'debilidad', 'agotamiento']):
        return "La fatiga puede tener múltiples causas. ¿Cuánto tiempo lleva sintiéndose así? ¿Ha notado pérdida de peso, cambios en el apetito, o dificultades para dormir? ¿Tiene otros síntomas acompañantes?"
    
    else:
        # Respuesta general para otros casos
        return f"Entiendo que me consulta sobre: '{message}'. Para poder ayudarle adecuadamente, me gustaría conocer más detalles. ¿Puede describir sus síntomas principales, cuándo comenzaron y cómo han evolucionado? También sería útil saber si tiene alguna condición médica previa o toma algún medicamento."


async def handle_advanced_conversation(conversation_id: str, message: str) -> ChatResponse:
    """Maneja conversaciones en estados más avanzados"""
    # Por ahora, redirigir a conversación médica normal
    return await handle_medical_conversation(conversation_id, message)


@router.get("/{conversation_id}/history")
async def get_conversation_history(conversation_id: str):
    """Obtiene el historial de una conversación"""
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    conversation = CONVERSATIONS[conversation_id]
    return {
        "conversation_id": conversation_id,
        "state": conversation["state"],
        "consent_given": conversation["consent_given"],
        "messages": conversation["messages"],
        "created_at": conversation["created_at"]
    }


@router.get("/conversations/list")
async def list_conversations():
    """Lista todas las conversaciones activas"""
    return {
        "conversations": [
            {
                "conversation_id": conv_id,
                "state": conv_data["state"],
                "consent_given": conv_data["consent_given"],
                "message_count": len(conv_data["messages"]),
                "created_at": conv_data["created_at"]
            }
            for conv_id, conv_data in CONVERSATIONS.items()
        ],
        "total": len(CONVERSATIONS)
    }


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Elimina una conversación"""
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    del CONVERSATIONS[conversation_id]
    return {"message": f"Conversación {conversation_id} eliminada exitosamente"}