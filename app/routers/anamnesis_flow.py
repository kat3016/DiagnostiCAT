"""
Router para el flujo específico de anamnesis conversacional
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import uuid
from datetime import datetime

from app.models.consent_models import ConsentRequest, ConsentResponse
from app.models.medical_models import MessageModel, MessageRole
from app.models.agent_models import AgentType
from app.services.agent_service import agent_service
from app.services.llm_service import llm_service
from app.services.classification_service import classification_model

router = APIRouter()

# Estado del flujo por conversación
FLOW_STATE: Dict[str, Dict[str, Any]] = {}

class FlowPhase:
    """Fases del flujo de anamnesis"""
    CONSENT = "consent"
    INITIAL_INTERVIEW = "initial_interview"
    PRELIMINARY_ANALYSIS = "preliminary_analysis"
    SPECIFIC_QUESTIONS = "specific_questions"
    DATA_STRUCTURING = "data_structuring"
    COMPLETED = "completed"


@router.post("/consent", response_model=ConsentResponse)
async def request_consent(consent: ConsentRequest):
    """Paso 1: Solicitud de consentimiento"""
    conversation_id = str(uuid.uuid4())
    
    if not consent.accepted:
        return ConsentResponse(
            message="Consentimiento no otorgado. La aplicación termina inmediatamente según lo requerido.",
            accepted=False
        )
    
    # Inicializar estado del flujo
    FLOW_STATE[conversation_id] = {
        "phase": FlowPhase.INITIAL_INTERVIEW,
        "consent_given": True,
        "messages": [],
        "interview_data": {},
        "analysis_data": {},
        "specific_answers": [],
        "structured_data": {},
        "created_at": datetime.now()
    }
    
    return ConsentResponse(
        message=f"Consentimiento otorgado. Iniciando entrevista inicial. conversation_id={conversation_id}",
        accepted=True
    )


@router.post("/interview/start")
async def start_initial_interview(conversation_id: str):
    """Paso 2: Iniciar entrevista inicial con preguntas fijas"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.INITIAL_INTERVIEW:
        raise HTTPException(status_code=400, detail=f"Fase incorrecta. Actual: {state['phase']}")
    
    # Obtener agente de entrevista inicial
    interview_agent = agent_service.get_agent_by_type(AgentType.INITIAL_INTERVIEW)
    if not interview_agent:
        raise HTTPException(status_code=500, detail="Agente de entrevista no disponible")
    
    # Primera pregunta fija
    first_question = "¡Hola! Voy a hacerte algunas preguntas de rutina para conocer tu situación. ¿Cuál es el motivo principal de tu consulta hoy?"
    
    # Registrar mensaje
    message = MessageModel(
        role=MessageRole.ASSISTANT,
        content=first_question,
        timestamp=datetime.now()
    )
    state["messages"].append(message)
    
    return {
        "conversation_id": conversation_id,
        "phase": state["phase"],
        "question": first_question,
        "question_number": 1,
        "total_questions": 7
    }


@router.post("/interview/answer")
async def submit_interview_answer(conversation_id: str, answer: str):
    """Paso 2: Responder preguntas de la entrevista inicial"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.INITIAL_INTERVIEW:
        raise HTTPException(status_code=400, detail=f"Fase incorrecta. Actual: {state['phase']}")
    
    # Registrar respuesta del usuario
    user_message = MessageModel(
        role=MessageRole.USER,
        content=answer,
        timestamp=datetime.now()
    )
    state["messages"].append(user_message)
    
    # Obtener agente de entrevista
    interview_agent = agent_service.get_agent_by_type(AgentType.INITIAL_INTERVIEW)
    
    # Procesar respuesta y obtener siguiente pregunta
    agent_response = await interview_agent.process_message(
        message=answer,
        conversation_history=state["messages"],
        patient_context={}
    )
    
    # Registrar respuesta del agente
    assistant_message = MessageModel(
        role=MessageRole.ASSISTANT,
        content=agent_response.response_text,
        timestamp=datetime.now()
    )
    state["messages"].append(assistant_message)
    
    # Verificar si completó todas las preguntas
    user_responses = [msg for msg in state["messages"] if msg.role == MessageRole.USER]
    questions_completed = len(user_responses)
    
    if questions_completed >= 7:  # 7 preguntas fijas
        state["phase"] = FlowPhase.PRELIMINARY_ANALYSIS
        return {
            "conversation_id": conversation_id,
            "phase": state["phase"],
            "message": "Entrevista inicial completada. Procediendo al análisis preliminar.",
            "questions_completed": questions_completed
        }
    
    return {
        "conversation_id": conversation_id,
        "phase": state["phase"],
        "response": agent_response.response_text,
        "question_number": questions_completed + 1,
        "total_questions": 7
    }


@router.post("/analysis/preliminary")
async def generate_preliminary_analysis(conversation_id: str):
    """Paso 3: Generar análisis preliminar e hipótesis"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.PRELIMINARY_ANALYSIS:
        raise HTTPException(status_code=400, detail=f"Fase incorrecta. Actual: {state['phase']}")
    
    # Obtener agente de análisis preliminar
    analysis_agent = agent_service.get_agent_by_type(AgentType.PRELIMINARY_ANALYSIS)
    if not analysis_agent:
        raise HTTPException(status_code=500, detail="Agente de análisis no disponible")
    
    # Generar análisis preliminar
    analysis_response = await analysis_agent.process_message(
        message="Analizar entrevista inicial",
        conversation_history=state["messages"],
        patient_context={}
    )
    
    # Guardar análisis
    state["analysis_data"] = {
        "analysis": analysis_response.response_text,
        "timestamp": datetime.now()
    }
    
    # Cambiar a fase de preguntas específicas
    state["phase"] = FlowPhase.SPECIFIC_QUESTIONS
    
    return {
        "conversation_id": conversation_id,
        "phase": state["phase"],
        "preliminary_analysis": analysis_response.response_text,
        "next_step": "Responder preguntas específicas generadas"
    }


@router.post("/questions/specific")
async def answer_specific_questions(conversation_id: str, answers: List[str]):
    """Paso 4: Responder preguntas específicas para el modelo de clasificación"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.SPECIFIC_QUESTIONS:
        raise HTTPException(status_code=400, detail=f"Fase incorrecta. Actual: {state['phase']}")
    
    # Guardar respuestas específicas
    state["specific_answers"] = answers
    state["phase"] = FlowPhase.DATA_STRUCTURING
    
    return {
        "conversation_id": conversation_id,
        "phase": state["phase"],
        "message": "Respuestas específicas recibidas. Procediendo a estructurar datos.",
        "answers_count": len(answers)
    }


@router.post("/data/structure")
async def structure_data(conversation_id: str):
    """Paso 5: Estructurar datos en formato estandarizado"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.DATA_STRUCTURING:
        raise HTTPException(status_code=400, detail=f"Fase incorrecta. Actual: {state['phase']}")
    
    # Obtener agente de estructuración
    structuring_agent = agent_service.get_agent_by_type(AgentType.DATA_STRUCTURING)
    if not structuring_agent:
        raise HTTPException(status_code=500, detail="Agente de estructuración no disponible")
    
    # Estructurar todos los datos
    structuring_response = await structuring_agent.process_message(
        message="Estructurar datos completos",
        conversation_history=state["messages"],
        patient_context={
            "analysis": state["analysis_data"],
            "specific_answers": state["specific_answers"]
        }
    )
    
    # Guardar datos estructurados
    state["structured_data"] = structuring_response.response_text
    state["phase"] = FlowPhase.COMPLETED
    
    return {
        "conversation_id": conversation_id,
        "phase": state["phase"],
        "structured_data": structuring_response.response_text,
        "classification_ready": True,
        "message": "Proceso de anamnesis conversacional completado exitosamente."
    }


@router.get("/flow/status/{conversation_id}")
async def get_flow_status(conversation_id: str):
    """Obtener estado actual del flujo"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    state = FLOW_STATE[conversation_id]
    
    return {
        "conversation_id": conversation_id,
        "current_phase": state["phase"],
        "consent_given": state["consent_given"],
        "messages_count": len(state["messages"]),
        "created_at": state["created_at"],
        "completed": state["phase"] == FlowPhase.COMPLETED
    }


@router.get("/flow/data/{conversation_id}")
async def get_final_data(conversation_id: str):
    """Obtener datos estructurados finales para modelo de clasificación"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.COMPLETED:
        raise HTTPException(status_code=400, detail="Flujo no completado")
    
    return {
        "conversation_id": conversation_id,
        "structured_data": state["structured_data"],
        "ready_for_classification": True,
        "metadata": {
            "total_messages": len(state["messages"]),
            "analysis_generated": bool(state["analysis_data"]),
            "specific_answers_count": len(state["specific_answers"]),
            "completion_time": datetime.now()
        }
    }


@router.post("/classify/{conversation_id}")
async def classify_case(conversation_id: str):
    """Ejecutar modelo de clasificación sobre los datos estructurados"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.COMPLETED:
        raise HTTPException(status_code=400, detail="Flujo no completado. Complete la estructuración de datos primero.")
    
    # Preparar datos para clasificación
    try:
        # Intentar parsear los datos estructurados
        if isinstance(state["structured_data"], str):
            import json
            structured_data = json.loads(state["structured_data"])
        else:
            structured_data = state["structured_data"]
    except:
        # Si no se puede parsear, usar datos raw
        structured_data = {
            "raw_data": state["structured_data"],
            "messages": [msg.dict() for msg in state["messages"]],
            "analysis": state["analysis_data"],
            "specific_answers": state["specific_answers"]
        }
    
    # Ejecutar clasificación
    classification_result = await classification_model.classify(structured_data)
    
    # Guardar resultado de clasificación
    state["classification_result"] = classification_result
    
    return {
        "conversation_id": conversation_id,
        "classification": classification_result,
        "model_info": classification_model.get_model_info()
    }


@router.get("/model/info")
async def get_model_info():
    """Información del modelo de clasificación"""
    return classification_model.get_model_info()
