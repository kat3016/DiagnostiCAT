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
    COLLECTING_SYMPTOMS = "collecting_symptoms"
    READY_FOR_CLASSIFICATION = "ready_for_classification"
    CLASSIFICATION_COMPLETE = "classification_complete"
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
            "symptoms_collected": [],
            "questions_asked": 0,
            "min_questions": 3,  # Mínimo de preguntas antes de clasificar
            "max_questions": 7,  # Máximo de preguntas
            "created_at": datetime.now()
        }
    else:
        conversation_id = request.conversation_id
        if conversation_id not in CONVERSATIONS:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    conversation = CONVERSATIONS[conversation_id]
    user_message = request.message.lower().strip()
    
    # Debug: Imprimir estado de la conversación
    print(f"🔍 DEBUG: Conversation state: {conversation['state']}")
    print(f"🔍 DEBUG: User message: '{request.message}'")
    print(f"🔍 DEBUG: User message lower: '{user_message}'")
    
    # Registrar mensaje del usuario
    conversation["messages"].append({
        "role": MessageRole.USER,
        "content": request.message,
        "timestamp": datetime.now()
    })
    
    try:
        # Manejar consentimiento
        if conversation["state"] == ConversationState.AWAITING_CONSENT:
            print(f"🔍 DEBUG: Handling consent...")
            return await handle_consent(conversation_id, user_message, request.message)
        
        # Manejar recolección de síntomas
        elif conversation["state"] == ConversationState.COLLECTING_SYMPTOMS:
            return await handle_symptom_collection(conversation_id, request.message)
        
        # Manejar clasificación y resultados
        elif conversation["state"] == ConversationState.READY_FOR_CLASSIFICATION:
            return await handle_classification(conversation_id, request.message)
        
        # Manejar conversación después de clasificación
        elif conversation["state"] == ConversationState.CLASSIFICATION_COMPLETE:
            return await handle_post_classification_conversation(conversation_id, request.message)
        
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
    
    # Detectar consentimiento negativo PRIMERO (para evitar conflictos)
    negative_patterns = [
        'no acepto', 'no', 'niego', 'rechazo', 'rechaza', 'no autorizo',
        'no estoy de acuerdo', 'en desacuerdo'
    ]
    
    # Detectar consentimiento positivo
    positive_patterns = [
        'si acepto', 'sí acepto', 'acepto', 'si', 'sí', 'yes', 'ok', 'okay',
        'estoy de acuerdo', 'de acuerdo', 'conforme', 'autorizo'
    ]
    
    # Verificar patrones negativos PRIMERO
    consent_denied = False
    for pattern in negative_patterns:
        if pattern in user_message_lower:  # Usar 'in' en lugar de regex
            # print(f"🔍 DEBUG: Matched negative pattern: {pattern}")
            consent_denied = True
            break
    
    # Solo verificar patrones positivos si no hay negativo
    consent_given = False
    if not consent_denied:
        for pattern in positive_patterns:
            if pattern in user_message_lower:  # Usar 'in' en lugar de regex
                # print(f"🔍 DEBUG: Matched positive pattern: {pattern}")
                consent_given = True
                break
    
    # print(f"🔍 DEBUG: consent_given={consent_given}, consent_denied={consent_denied}")
    
    if consent_given:
        # Consentimiento otorgado
        conversation["state"] = ConversationState.COLLECTING_SYMPTOMS
        conversation["consent_given"] = True
        
        response_text = "¡Perfecto! Gracias por otorgar su consentimiento. Ahora puedo ayudarle con su consulta médica.\n\nVoy a hacerle algunas preguntas para entender mejor su situación. ¿Cuál es el síntoma principal o la razón de su consulta?"
        
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


async def handle_symptom_collection(conversation_id: str, message: str) -> ChatResponse:
    """Maneja la recolección progresiva de síntomas"""
    conversation = CONVERSATIONS[conversation_id]
    
    # Analizar el mensaje y extraer información relevante
    extracted_info = extract_medical_info(message)
    conversation["symptoms_collected"].extend(extracted_info)
    conversation["questions_asked"] += 1
    
    print(f"🔍 DEBUG: Questions asked: {conversation['questions_asked']}/{conversation['max_questions']}")
    print(f"🔍 DEBUG: Symptoms collected: {conversation['symptoms_collected']}")
    print(f"🔍 DEBUG: Current message: {message}")
    
    # Determinar si tenemos suficiente información para clasificar
    if (conversation["questions_asked"] >= conversation["min_questions"] and 
        len(conversation["symptoms_collected"]) >= 2) or \
       conversation["questions_asked"] >= conversation["max_questions"]:
        
        print(f"🔍 DEBUG: Moving to classification phase")
        # Cambiar estado y proceder con clasificación
        conversation["state"] = ConversationState.READY_FOR_CLASSIFICATION
        return await handle_classification(conversation_id, message)
    
    # Generar siguiente pregunta
    next_question = generate_next_question(conversation["symptoms_collected"], conversation["questions_asked"])
    
    print(f"🔍 DEBUG: Generated next question: {next_question}")
    
    conversation["messages"].append({
        "role": MessageRole.ASSISTANT,
        "content": next_question,
        "timestamp": datetime.now()
    })
    
    return ChatResponse(
        response=next_question,
        conversation_id=conversation_id,
        agent_type="symptom_collector",
        confidence_score=0.8,
        severity_assessment="BAJO",
        suggestions=[],
        follow_up_questions=[]
    )


async def handle_classification(conversation_id: str, message: str) -> ChatResponse:
    """Maneja la clasificación usando Hugging Face"""
    conversation = CONVERSATIONS[conversation_id]
    
    try:
        # Importar el servicio de clasificación
        from app.services.classification_service import classification_model
        
        # Preparar datos para clasificación
        structured_data = {
            "symptoms": conversation["symptoms_collected"],
            "chief_complaint": conversation["symptoms_collected"][0] if conversation["symptoms_collected"] else "consulta general",
            "messages": [msg["content"] for msg in conversation["messages"] if msg["role"] == MessageRole.USER],
            "questions_answered": conversation["questions_asked"]
        }
        
        # print(f"🔍 DEBUG: Iniciando clasificación con datos: {structured_data}")
        
        # Ejecutar clasificación
        classification_result = await classification_model.classify(structured_data)
        
        # print(f"🔍 DEBUG: Resultado de clasificación: {classification_result}")
        
        # Cambiar estado
        conversation["state"] = ConversationState.CLASSIFICATION_COMPLETE
        conversation["classification_result"] = classification_result
        
        # Crear respuesta con las 3 condiciones más probables
        response_text = await generate_diagnosis_summary(classification_result, conversation["symptoms_collected"])
        
        # Registrar respuesta
        conversation["messages"].append({
            "role": MessageRole.ASSISTANT,
            "content": response_text,
            "timestamp": datetime.now()
        })
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            agent_type="medical_classifier",
            confidence_score=classification_result.get("confidence_score", 0.0),
            severity_assessment=classification_result.get("severity", "MEDIO"),
            predicted_condition=classification_result.get("predicted_condition", "Análisis completado"),
            suggestions=classification_result.get("recommendations", []),
            follow_up_questions=[],  # Sin preguntas de seguimiento
            is_diagnosis=True  # Marcar como diagnóstico para mostrar el recuadro especial
        )
        
    except Exception as e:
        print(f"❌ ERROR en clasificación: {e}")
        # Fallback a respuesta básica
        return await handle_basic_medical_response(conversation_id, message)


async def handle_post_classification_conversation(conversation_id: str, message: str) -> ChatResponse:
    """Maneja la conversación después de mostrar la clasificación"""
    conversation = CONVERSATIONS[conversation_id]
    
    # Generar respuesta contextual basada en la clasificación previa
    classification_result = conversation.get("classification_result", {})
    category = classification_result.get("category", "general")
    
    response_text = generate_contextual_response(message, category, classification_result)
    
    conversation["messages"].append({
        "role": MessageRole.ASSISTANT,
        "content": response_text,
        "timestamp": datetime.now()
    })
    
    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,
        agent_type="post_classification_advisor",
        confidence_score=0.7,
        severity_assessment="BAJO",
        suggestions=[
            "Consultar con un médico especialista",
            "Monitorear los síntomas",
            "Seguir las recomendaciones generales"
        ],
        follow_up_questions=[]
    )


async def handle_basic_medical_response(conversation_id: str, message: str) -> ChatResponse:
    """Respuesta médica básica como fallback"""
    conversation = CONVERSATIONS[conversation_id]
    
    response_text = generate_basic_medical_response(message, conversation["messages"])
    
    conversation["messages"].append({
        "role": MessageRole.ASSISTANT,
        "content": response_text,
        "timestamp": datetime.now()
    })
    
    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,
        agent_type="basic_medical_advisor",
        confidence_score=0.6,
        severity_assessment="BAJO",
        suggestions=[],
        follow_up_questions=[]
    )


def extract_medical_info(message: str) -> List[str]:
    """Extrae información médica relevante del mensaje del usuario"""
    message_lower = message.lower()
    extracted = []
    
    # Palabras clave para síntomas
    symptom_keywords = {
        'dolor': ['dolor', 'duele', 'molesta', 'pinchazos', 'punzadas'],
        'fiebre': ['fiebre', 'temperatura', 'calentura', 'calor'],
        'respiratorio': ['tos', 'toser', 'respirar', 'pecho', 'pulmones', 'ahogo'],
        'digestivo': ['nausea', 'vomito', 'estomago', 'barriga', 'diarrea'],
        'neurologico': ['cabeza', 'mareo', 'desmayo', 'vision', 'confusion'],
        'musculoesqueletico': ['muscular', 'articular', 'hueso', 'artritis', 'rigidez'],
        'cardiovascular': ['corazon', 'palpitaciones', 'presion', 'taquicardia'],
        'dermatologico': ['piel', 'erupcion', 'picazon', 'mancha', 'herida']
    }
    
    for category, keywords in symptom_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            extracted.append(f"{category}: {message[:100]}")
    
    # Si no se encontró nada específico, agregar el mensaje completo
    if not extracted:
        extracted.append(f"síntoma general: {message[:100]}")
    
    return extracted


def generate_next_question(symptoms_collected: List[str], questions_asked: int) -> str:
    """Genera la siguiente pregunta basada en los síntomas recopilados"""
    
    # Preguntas base según el número de pregunta
    base_questions = [
        "¿Cuándo comenzaron estos síntomas? ¿Hace horas, días o semanas?",
        "¿Cómo describiría la intensidad de sus síntomas en una escala del 1 al 10?",
        "¿Hay algo que haga que los síntomas empeoren or mejoren?",
        "¿Ha notado otros síntomas adicionales que puedan estar relacionados?",
        "¿Está tomando algún medicamento actualmente o ha tomado algo para estos síntomas?",
        "¿Ha tenido problemas similares en el pasado?",
        "¿Hay algún factor específico que cree que pudo haber desencadenado estos síntomas?"
    ]
    
    if questions_asked < len(base_questions):
        return base_questions[questions_asked - 1]
    else:
        return "¿Hay algún detalle adicional sobre sus síntomas que considere importante mencionar?"


def generate_contextual_response(message: str, category: str, classification_result: Dict) -> str:
    """Genera respuesta contextual basada en la clasificación"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['medicamento', 'medicina', 'pastilla', 'tratamiento']):
        return f"Respecto a medicamentos para condiciones {category}, es importante que consulte con un médico antes de tomar cualquier medicamento. Basándome en el análisis previo, las recomendaciones generales incluyen monitoreo de síntomas y evaluación médica profesional."
    
    elif any(word in message_lower for word in ['cuando', 'médico', 'doctor', 'consulta']):
        severity = classification_result.get("severity", "MEDIO")
        if severity in ["CRÍTICO", "ALTO"]:
            return "Dada la naturaleza de sus síntomas, le recomiendo que consulte con un médico lo antes posible, preferiblemente hoy mismo."
        else:
            return "Le recomiendo que programe una cita con su médico de cabecera en los próximos días para una evaluación más detallada."
    
    else:
        return f"Entiendo su consulta. Basándome en el análisis previo relacionado con {category}, le sugiero seguir monitoreando sus síntomas y consultar con un profesional médico para un diagnóstico definitivo."


def generate_basic_medical_response(message: str, conversation_history: list) -> str:
    """Genera una respuesta médica básica basada en palabras clave"""
    message_lower = message.lower()
    
    # Respuestas basadas en síntomas comunes
    if any(word in message_lower for word in ['dolor', 'duele', 'molesta']):
        return "Entiendo que experimenta dolor. Para poder ayudarle mejor, necesito más información: ¿En qué parte del cuerpo siente el dolor? ¿Cómo describiría el dolor (punzante, sordo, pulsante)? ¿Cuándo comenzó y qué lo hace empeorar o mejorar?"
    
    elif any(word in message_lower for word in ['fiebre', 'temperatura', 'calentura']):
        return "La fiebre puede ser síntoma de varias condiciones. ¿Ha medido su temperatura? ¿Tiene otros síntomas como escalofríos, dolor de cabeza, o malestar general? ¿Cuánto tiempo lleva con fiebre?"
    
    else:
        # Respuesta general para otros casos
        return f"Entiendo que me consulta sobre: '{message}'. Para poder ayudarle adecuadamente, me gustaría conocer más detalles. ¿Puede describir sus síntomas principales, cuándo comenzaron y cómo han evolucionado?"


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


async def generate_diagnosis_summary(classification_result: Dict, symptoms_collected: List[str]) -> str:
    """Genera un resumen de diagnóstico con las 3 condiciones más probables"""
    
    # Condiciones predeterminadas basadas en síntomas comunes
    possible_conditions = []
    
    # Extraer información de los síntomas
    all_symptoms = " ".join(symptoms_collected).lower()
    
    if "dolor" in all_symptoms and ("cabeza" in all_symptoms or "neurological" in all_symptoms):
        possible_conditions = [
            {"name": "Cefalea tensional", "probability": "75%", "description": "Dolor de cabeza por tensión o estrés"},
            {"name": "Migraña leve", "probability": "20%", "description": "Dolor de cabeza vascular con posible sensibilidad"},
            {"name": "Cefalea por deshidratación", "probability": "5%", "description": "Dolor de cabeza relacionado con falta de hidratación"}
        ]
    elif "fiebre" in all_symptoms or "temperatura" in all_symptoms:
        possible_conditions = [
            {"name": "Infección viral", "probability": "60%", "description": "Proceso infeccioso de origen viral"},
            {"name": "Infección bacteriana leve", "probability": "30%", "description": "Proceso infeccioso bacteriano de intensidad leve"},
            {"name": "Reacción inflamatoria", "probability": "10%", "description": "Respuesta inflamatoria del organismo"}
        ]
    elif "tos" in all_symptoms:
        possible_conditions = [
            {"name": "Infección respiratoria alta", "probability": "65%", "description": "Infección en vías respiratorias superiores"},
            {"name": "Bronquitis leve", "probability": "25%", "description": "Inflamación leve de los bronquios"},
            {"name": "Alergia respiratoria", "probability": "10%", "description": "Reacción alérgica en vías respiratorias"}
        ]
    elif "dolor" in all_symptoms:
        possible_conditions = [
            {"name": "Dolor muscular", "probability": "50%", "description": "Tensión o fatiga muscular"},
            {"name": "Dolor articular", "probability": "35%", "description": "Molestias en articulaciones"},
            {"name": "Dolor neuropático", "probability": "15%", "description": "Dolor relacionado con nervios"}
        ]
    else:
        # Condiciones generales
        possible_conditions = [
            {"name": "Malestar general", "probability": "40%", "description": "Síntomas inespecíficos que requieren evaluación"},
            {"name": "Síndrome viral leve", "probability": "35%", "description": "Posible proceso viral de baja intensidad"},
            {"name": "Fatiga o estrés", "probability": "25%", "description": "Síntomas relacionados con cansancio o tensión"}
        ]
    
    # Usar datos de clasificación si están disponibles
    if classification_result and "predicted_condition" in classification_result:
        main_condition = classification_result["predicted_condition"]
        confidence = classification_result.get("confidence", 0.5) * 100
        possible_conditions[0] = {
            "name": main_condition,
            "probability": f"{confidence:.0f}%",
            "description": f"Condición identificada por análisis de síntomas"
        }
    
    # Generar texto del diagnóstico
    diagnosis_text = "🔍 **ANÁLISIS PRELIMINAR COMPLETADO**\n\n"
    diagnosis_text += "Basándome en sus síntomas, estas son las **3 condiciones más probables**:\n\n"
    
    for i, condition in enumerate(possible_conditions[:3], 1):
        diagnosis_text += f"**{i}. {condition['name']}** ({condition['probability']})\n"
        diagnosis_text += f"   • {condition['description']}\n\n"
    
    diagnosis_text += "⚠️ **IMPORTANTE:**\n"
    diagnosis_text += "• Este es un análisis preliminar basado en IA\n"
    diagnosis_text += "• NO reemplaza el diagnóstico médico profesional\n"
    diagnosis_text += "• Consulte a un médico para confirmación y tratamiento\n\n"
    
    # Agregar recomendaciones según severidad
    severity = classification_result.get("severity", "MEDIO") if classification_result else "MEDIO"
    if severity in ["CRÍTICO", "ALTO"]:
        diagnosis_text += "🚨 **RECOMENDACIÓN:** Consulte a un médico INMEDIATAMENTE"
    elif severity == "MEDIO":
        diagnosis_text += "📋 **RECOMENDACIÓN:** Programe una cita médica en los próximos días"
    else:
        diagnosis_text += "💡 **RECOMENDACIÓN:** Monitoree síntomas y consulte si empeoran"
    
    return diagnosis_text