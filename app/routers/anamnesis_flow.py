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

router = APIRouter()

# Estado del flujo por conversación
FLOW_STATE: Dict[str, Dict[str, Any]] = {}

class FlowPhase:
    """Fases del flujo de anamnesis"""
    CONSENT = "consent"
    CONVERSATIONAL_INTERVIEW = "conversational_interview"
    SPECIFIC_QUESTIONS_ANALYSIS = "specific_questions_analysis"
    JSON_STRUCTURING_AND_CLASSIFICATION = "json_structuring_and_classification"
    COMPLETED = "completed"


@router.post("/consent", response_model=ConsentResponse)
async def request_consent(consent: ConsentRequest):
    """Paso 1: Solicitud de consentimiento"""
    conversation_id = str(uuid.uuid4())
    
    if not consent.accepted:
        return ConsentResponse(
            message="Consent not granted. The application ends immediately as required.",
            accepted=False
        )
    
    # Inicializar estado del flujo
    FLOW_STATE[conversation_id] = {
        "phase": FlowPhase.CONVERSATIONAL_INTERVIEW,
        "consent_given": True,
        "messages": [],
        "interview_data": {},
        "analysis_data": {},
        "specific_answers": [],
        "structured_data": {},
        "created_at": datetime.now()
    }
    
    return ConsentResponse(
        message=f"Consent granted. Starting initial interview. conversation_id={conversation_id}",
        accepted=True
    )


@router.post("/interview/start")
async def start_initial_interview(conversation_id: str):
    """Paso 2: Iniciar entrevista inicial con preguntas fijas usando CrewAI"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.CONVERSATIONAL_INTERVIEW:
        raise HTTPException(status_code=400, detail=f"Incorrect phase. Current: {state['phase']}")
    
    try:
        # Preparar inputs para CrewAI
        inputs = {
            "consultation_topic": "general medical consultation",
            "patient_message": "Start the medical interview with the first fixed question",
            "conversation_id": conversation_id,
            "current_question": 1
        }
        
        # Ejecutar entrevista inicial con CrewAI
        first_question = await agent_service.run_initial_interview(inputs)
        
        # Registrar mensaje
        message = MessageModel(
            role=MessageRole.ASSISTANT,
            content=first_question,
            timestamp=datetime.now()
        )
        state["messages"].append(message)
        state["current_question"] = 1
        
        return {
            "conversation_id": conversation_id,
            "phase": state["phase"],
            "question": first_question,
            "question_number": 1,
            "total_questions": 7,
            "agent_used": "initial_interviewer"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting interview: {str(e)}")


@router.post("/interview/answer")
async def submit_interview_answer(conversation_id: str, answer: str):
    """Paso 2: Responder preguntas de la entrevista inicial usando CrewAI"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.CONVERSATIONAL_INTERVIEW:
        raise HTTPException(status_code=400, detail=f"Incorrect phase. Current: {state['phase']}")
    
    # Registrar respuesta del usuario
    user_message = MessageModel(
        role=MessageRole.USER,
        content=answer,
        timestamp=datetime.now()
    )
    state["messages"].append(user_message)
    
    try:
        # Verificar si completó todas las preguntas
        user_responses = [msg for msg in state["messages"] if msg.role == MessageRole.USER]
        questions_completed = len(user_responses)
        
        if questions_completed >= 7:  # 7 preguntas fijas completadas
            state["phase"] = FlowPhase.SPECIFIC_QUESTIONS_ANALYSIS
            
            # Guardar respuestas de entrevista
            state["interview_completed"] = True
            state["interview_data"] = {
                f"question_{i+1}": msg.content 
                for i, msg in enumerate(user_responses[:7])
            }
            
            return {
                "conversation_id": conversation_id,
                "phase": state["phase"],
                "message": "Initial 7-question interview completed. Proceeding to preliminary analysis.",
                "questions_completed": questions_completed,
                "interview_data": state["interview_data"]
            }
        
        # Preparar inputs para siguiente pregunta
        inputs = {
            "consultation_topic": "general medical consultation",
            "patient_message": answer,
            "conversation_id": conversation_id,
            "current_question": questions_completed + 1,
            "previous_answers": [msg.content for msg in user_responses]
        }
        
        # Obtener siguiente pregunta con CrewAI
        next_question = await agent_service.run_initial_interview(inputs)
        
        # Registrar respuesta del agente
        assistant_message = MessageModel(
            role=MessageRole.ASSISTANT,
            content=next_question,
            timestamp=datetime.now()
        )
        state["messages"].append(assistant_message)
        state["current_question"] = questions_completed + 1
        
        return {
            "conversation_id": conversation_id,
            "phase": state["phase"],
            "response": next_question,
            "question_number": questions_completed + 1,
            "total_questions": 7,
            "agent_used": "initial_interviewer"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing answer: {str(e)}")


@router.post("/analysis/preliminary")
async def generate_preliminary_analysis(conversation_id: str):
    """Paso 3: Generar análisis preliminar e hipótesis usando CrewAI"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.SPECIFIC_QUESTIONS_ANALYSIS:
        raise HTTPException(status_code=400, detail=f"Incorrect phase. Current: {state['phase']}")
    
    try:
        # Preparar datos de entrevista para análisis
        interview_summary = "\n".join([
            f"Question {i+1}: {msg.content}" 
            for i, msg in enumerate([msg for msg in state["messages"] if msg.role == MessageRole.USER][:7])
        ])
        
        inputs = {
            "consultation_topic": "general medical consultation",
            "interview_data": interview_summary,
            "conversation_id": conversation_id,
            "interview_responses": state.get("interview_data", {})
        }
        
        # Ejecutar análisis preliminar con CrewAI
        analysis_result = await agent_service.run_preliminary_analysis(inputs)
        
        # Guardar análisis
        state["analysis_data"] = {
            "analysis": analysis_result,
            "timestamp": datetime.now(),
            "agent_used": "preliminary_analyst"
        }
        
        # Cambiar a fase de estructuración y clasificación
        state["phase"] = FlowPhase.JSON_STRUCTURING_AND_CLASSIFICATION
        
        return {
            "conversation_id": conversation_id,
            "phase": state["phase"],
            "preliminary_analysis": analysis_result,
            "agent_used": "preliminary_analyst",
            "next_step": "Answer the specific questions generated by the analysis"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in preliminary analysis: {str(e)}")


@router.post("/questions/specific")
async def answer_specific_questions(conversation_id: str, answers: List[str]):
    """Paso 4: Responder preguntas específicas para el modelo de clasificación"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.SPECIFIC_QUESTIONS:
        raise HTTPException(status_code=400, detail=f"Incorrect phase. Current: {state['phase']}")
    
    # Guardar respuestas específicas
    state["specific_answers"] = answers
    state["phase"] = FlowPhase.DATA_STRUCTURING
    
    return {
        "conversation_id": conversation_id,
        "phase": state["phase"],
        "message": "Specific answers received. Proceeding to structure data.",
        "answers_count": len(answers)
    }


@router.post("/structure-and-classify")
async def structure_and_classify_data(conversation_id: str):
    """Paso 4: Estructurar datos JSON y ejecutar clasificación con modelo Hugging Face"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.JSON_STRUCTURING_AND_CLASSIFICATION:
        raise HTTPException(status_code=400, detail=f"Incorrect phase. Current: {state['phase']}")
    
    try:
        # Preparar todos los datos para estructuración y clasificación
        inputs = {
            "consultation_topic": "general medical consultation",
            "conversation_id": conversation_id,
            "interview_data": state.get("interview_data", {}),
            "analysis_data": state.get("analysis_data", {}),
            "specific_answers": state.get("specific_answers", []),
            "all_messages": [
                {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp.isoformat()}
                for msg in state["messages"]
            ]
        }
        
        # Ejecutar estructuración y clasificación con CrewAI + Hugging Face
        complete_result = await agent_service.run_structuring_and_classification(inputs)
        
        # Guardar resultado completo
        state["structured_data"] = complete_result
        state["phase"] = FlowPhase.COMPLETED
        state["classification_ready"] = True
        state["process_completed"] = True
        
        return {
            "conversation_id": conversation_id,
            "phase": state["phase"],
            "complete_result": complete_result,
            "classification_ready": True,
            "process_completed": True,
            "agent_used": "json_data_structurer",
            "model_used": "hugging_face_medical_classifier",
            "message": "Complete conversational anamnesis and classification process finished successfully."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in structuring and classification: {str(e)}")


@router.get("/flow/status/{conversation_id}")
async def get_flow_status(conversation_id: str):
    """Obtener estado actual del flujo"""
    if conversation_id not in FLOW_STATE:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
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
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    state = FLOW_STATE[conversation_id]
    if state["phase"] != FlowPhase.COMPLETED:
        raise HTTPException(status_code=400, detail="Flow not completed")
    
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


# ENDPOINT INTEGRADO EN /structure-and-classify - Ya no se usa por separado


@router.get("/model/info")
async def get_model_info():
    """Información del modelo de clasificación CrewAI + Hugging Face"""
    return {
        "name": "CrewAI + Hugging Face Medical Classification System",
        "version": "2.0",
        "description": "Medical classification system using CrewAI for structuring and Hugging Face for classification",
        "flow": [
            "1. Conversational Agent (CrewAI)",
            "2. Specific Questions Agent (CrewAI)", 
            "3. JSON Structuring Agent (CrewAI)",
            "4. Classification Model (Hugging Face)"
        ],
        "categories": [
            "neurological", "cardiovascular", "respiratory", 
            "gastrointestinal", "musculoskeletal", "dermatological", 
            "psychiatric", "other"
        ],
        "crew_info": agent_service.get_crew_info(),
        "hugging_face_model": "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"
    }
