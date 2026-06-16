"""
Router para chat médico conversacional
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import re

from app.models.medical_models import MessageModel, MessageRole, ChatResponse, ChatRequest
# from app.crew.anamnesis_crew import AnamnesisConversacionalCrew  # Comentado: no se usa aquí

router = APIRouter()

# Estado de conversaciones
CONVERSATIONS: Dict[str, Dict[str, Any]] = {}

class ConversationState:
    """Estados de la conversación"""
    AWAITING_CONSENT = "awaiting_consent"
    CONSENT_GIVEN = "consent_given"
    COLLECTING_SYMPTOMS = "collecting_symptoms"
    SPECIFIC_QUESTIONS = "specific_questions"  # 🆕 Nueva fase
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
            "min_questions": 7,  # Hacer las 7 preguntas completas
            "max_questions": 7,  # Máximo de preguntas
            "created_at": datetime.now()
        }
    else:
        conversation_id = request.conversation_id
        if conversation_id not in CONVERSATIONS:
            raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = CONVERSATIONS[conversation_id]
    user_message = request.message.lower().strip()

    # Debug: print conversation state
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
        
        # 🆕 Manejar preguntas específicas del analyst
        elif conversation["state"] == ConversationState.SPECIFIC_QUESTIONS:
            return await handle_specific_questions(conversation_id, request.message)
        
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
            response=f"Sorry, an internal error occurred: {str(e)}. Please try again or restart the conversation.",
            conversation_id=conversation_id,
            agent_type="error_handler",
            confidence_score=0.0,
            severity_assessment="BAJO",
            suggestions=[],
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
        'no estoy de acuerdo', 'en desacuerdo',
        'i do not agree', 'i disagree', "don't agree", 'disagree', 'refuse', 'decline'
    ]
    
    # Detectar consentimiento positivo
    positive_patterns = [
        'si acepto', 'sí acepto', 'acepto', 'si', 'sí', 'yes', 'ok', 'okay',
        'estoy de acuerdo', 'de acuerdo', 'conforme', 'autorizo',
        'i agree', 'i do', 'agree', 'proceed', 'continue'
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
        
        response_text = "Perfect! Thank you for giving your consent.\n\nREMINDER: I'm DiagnostiCAT, an AI assistant. This conversation does NOT replace a real medical consultation.\n\nNow I can help you collect basic medical information for informational purposes.\n\nI will ask you some questions to better understand your situation. What is your main symptom or the reason for your consultation?\n\nIMPORTANT: For real diagnosis and treatment, always consult a certified doctor."
        
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
            suggestions=[],
            follow_up_questions=[]
        )
    
    elif consent_denied:
        # Consentimiento denegado
        response_text = "I understand that you do not wish to give your consent. Without your consent, I cannot proceed with the medical consultation. If you change your mind, you can restart the conversation. Have a good day!"
        
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
            suggestions=[],
            follow_up_questions=[]
        )
    
    else:
        # Respuesta ambigua - pedir clarificación
        response_text = "I couldn't clearly understand your answer about consent. Please respond clearly: Do you agree that I process your medical information to assist you? You can respond 'I agree' or 'I do not agree'."
        
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
            suggestions=[],
            follow_up_questions=[]
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
            suggestions=[],
            follow_up_questions=[]
        )
        
    except Exception as e:
        # Fallback si algo falla
        fallback_response = f"I understand your question about: {message}. Sorry, I am experiencing technical difficulties with the medical analysis system. Could you rephrase your question or be more specific about your symptoms?"
        
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
            suggestions=["Rephrase the question", "Be more specific", "Restart if the problem persists"],
            follow_up_questions=["Can you describe your symptoms more specifically?"]
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
    
    # Determinar si hemos completado las 7 preguntas generales
    if conversation["questions_asked"] >= conversation["max_questions"]:
        
        print(f"🔍 DEBUG: Moving to specific questions phase")
        # Cambiar estado y proceder con preguntas específicas adaptativas
        conversation["state"] = ConversationState.SPECIFIC_QUESTIONS
        conversation["specific_questions_asked"] = 0
        conversation["specific_questions_max"] = 5  # Máximo 5 preguntas específicas
        conversation["specific_answers"] = []
        conversation["adaptive_context"] = []  # Para guardar contexto de respuestas
        return await handle_specific_questions(conversation_id, message)
    
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


def format_interview_data_for_agent(symptoms_data) -> str:
    """Formatea los datos de la entrevista para el agente de CrewAI"""
    interview_text = "CONVERSATIONAL INTERVIEW COMPLETED:\n"
    
    # Manejar tanto diccionarios como listas
    if isinstance(symptoms_data, dict):
        for i, (question, answer) in enumerate(symptoms_data.items(), 1):
            if question in ["motivo_consulta", "inicio_sintomas", "intensidad", "antecedentes_medicos", 
                           "medicamentos_actuales", "antecedentes_familiares", "habitos_relevantes"]:
                interview_text += f"{i}. {question.replace('_', ' ').title()}: {answer}\n"
    elif isinstance(symptoms_data, list):
        # Procesar lista de síntomas recopilados
        questions_map = {
            0: "Reason For Consultation",
            1: "Symptom Onset",
            2: "Intensity",
            3: "Aggravating/Relieving Factors",
            4: "Additional Symptoms",
            5: "Current Medications",
            6: "Medical History"
        }
        
        for i, symptom in enumerate(symptoms_data):
            question_type = questions_map.get(i, f"Information {i+1}")
            # Limpiar el formato "tipo: respuesta" 
            clean_answer = symptom.split(": ", 1)[-1] if ": " in symptom else symptom
            interview_text += f"{i+1}. {question_type}: {clean_answer}\n"
    
    return interview_text


def parse_agent_analysis(analysis_result: str) -> tuple[List[str], List[str]]:
    """Parsea el resultado del agente para extraer hipótesis y preguntas"""
    print(f"🔍 Parseando resultado del agente...")
    
    try:
        # Buscar hipótesis preliminares
        hypotheses = []
        questions = []
        
        lines = analysis_result.split('\n')
        in_hypotheses_section = False
        in_questions_section = False
        
        for line in lines:
            line = line.strip()
            
            # Buscar secciones con más variaciones
            if any(keyword in line.upper() for keyword in ["HIPÓTESIS", "HIPOTESIS", "HYPOTHESES", "PRELIMINAR"]):
                in_hypotheses_section = True
                in_questions_section = False
                continue
            
            if any(keyword in line.upper() for keyword in ["PREGUNTAS", "QUESTIONS", "ESPECÍFICAS", "ESPECIFICAS", "CLASIFICACIÓN", "CLASIFICACION"]):
                in_hypotheses_section = False
                in_questions_section = True
                continue
            
            # Extraer hipótesis (buscar patrones numerados)
            if in_hypotheses_section and line:
                if line.startswith(("1.", "2.", "3.", "•", "-", "*")) or line[0].isdigit():
                    hypothesis = line[2:].strip() if line.startswith(("1.", "2.", "3.")) else line.strip()
                    hypotheses.append(hypothesis)
            
            # Extraer preguntas con formato más flexible
            if in_questions_section and line:
                # Detectar líneas que empiecen con números o contienen preguntas
                if (line.startswith(("1.", "2.", "3.", "4.", "5.", "•", "-", "*")) or 
                    (line and line[0].isdigit()) or 
                    '?' in line):
                    
                    # Limpiar la pregunta
                    question = line
                    
                    # Remover número inicial si existe (formato "1. ", "2. ", etc.)
                    if len(line) > 2 and line[0].isdigit() and line[1] in ['.', ' ']:
                        if line[1] == '.':
                            question = line[2:].strip()
                        elif line[1] == ' ':
                            question = line[2:].strip()
                    
                    # Remover asteriscos y texto en negrita si existe
                    question = question.replace('**', '').strip()
                    
                    # Accept English and Spanish question formats.
                    if ('?' in question and len(question) > 10):
                        
                        # Extraer solo la pregunta principal (antes del guión si hay explicación)
                        if ' - ' in question:
                            question = question.split(' - ')[0].strip()
                        if '**Objetivo:**' in question:
                            question = question.split('**Objetivo:**')[0].strip()
                        
                        # Limpiar espacios extra
                        question = ' '.join(question.split())
                            
                        questions.append(question)
                        print(f"✅ Pregunta extraída: '{question}'")
        
        print(f"📊 Extraídas {len(hypotheses)} hipótesis y {len(questions)} preguntas")
        
        # Debug: Mostrar las preguntas extraídas
        if len(questions) < 5:
            print(f"⚠️ Solo se extrajeron {len(questions)} preguntas, esperadas 5")
            for i, q in enumerate(questions, 1):
                print(f"   Pregunta {i}: {q[:60]}...")
        
        # Solo usar fallback si NO se encontraron resultados del agente
        if len(hypotheses) == 0:
            print("⚠️  No se encontraron hipótesis del agente")
            hypotheses = [
                "Requires more detailed medical analysis",
                "More specific information is needed",
                "In-person medical evaluation is recommended"
            ]
        
        if len(questions) == 0:
            print("⚠️  No se encontraron preguntas del agente")
            questions = [
                "Can you provide more details about the location of your symptoms?",
                "Do your symptoms vary in intensity during the day?",
                "Have you noticed factors that improve or worsen your condition?",
                "Do you have a history of similar conditions?",
                "How would you describe the progression of your symptoms?"
            ]
        
        # Asegurar exactamente 3 hipótesis y 5 preguntas
        return hypotheses[:3], questions[:5]
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO en parseo: {e}")
        print(f"📄 Contenido que causó error:\n{analysis_result}")
        # Solo en caso de error crítico
        return [
            "Error processing the agent output",
            "Analysis restart is required", 
            "Technical review pending"
        ], [
            "Can you try describing your symptoms again?",
            "Is there any additional detail you can provide?",
            "Do you think any important information is missing?",
            "Can you be more specific about your current condition?",
            "Which aspects of your case do you consider most relevant?"
        ]


def format_hypotheses_display(hypotheses: List[str]) -> str:
    """Formatea las hipótesis para mostrar al usuario"""
    formatted = ""
    for i, hypothesis in enumerate(hypotheses, 1):
        formatted += f"{i}. {hypothesis}\n"
    return formatted.strip()


async def handle_specific_questions_fallback(conversation_id: str, message: str) -> ChatResponse:
    """Fallback handler when the LLM agent cannot generate specific questions."""
    conversation = CONVERSATIONS[conversation_id]

    fallback_hypotheses = [
        "Possible inflammatory condition based on reported symptoms",
        "Syndrome related to lifestyle or environmental factors",
        "Condition requiring specialized medical evaluation"
    ]

    fallback_questions = [
        "Can you describe the intensity of your symptoms on a scale from 1 to 10?",
        "Are the symptoms constant, or do they come and go?",
        "Have you noticed whether anything specific triggers or relieves your symptoms?",
        "Do you have any family history of similar conditions?",
        "Are you currently taking any medications or supplements?"
    ]

    conversation["preliminary_hypotheses"] = fallback_hypotheses
    conversation["specific_questions_list"] = fallback_questions
    conversation["specific_questions_max"] = 5
    conversation["specific_questions_asked"] = 1

    response_text = (
        "<strong>GENERAL QUESTIONS COMPLETED</strong>\n\n"
        "I have reviewed the information from the general interview. "
        "I will now ask 5 specific questions to refine the analysis.\n\n"
        f"<strong>Specific question 1/5:</strong>\n{fallback_questions[0]}"
    )

    conversation["messages"].append({
        "role": MessageRole.ASSISTANT,
        "content": response_text,
        "timestamp": datetime.now()
    })

    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,
        agent_type="specific_questions_analyst",
        confidence_score=0.8,
        severity_assessment="medium",
        suggestions=[],
        follow_up_questions=[]
    )


async def handle_specific_questions(conversation_id: str, message: str) -> ChatResponse:
    """Maneja las preguntas específicas usando el agente specific_questions_analyst de CrewAI"""
    conversation = CONVERSATIONS[conversation_id]
    
    # Si es la primera vez en esta fase, usar el agente de CrewAI para generar análisis y preguntas
    if conversation["specific_questions_asked"] == 0:
        print(f"🔍 DEBUG: Starting specific questions phase with CrewAI agent")
        
        try:
            # Preparar datos de la entrevista inicial para el agente
            interview_summary = format_interview_data_for_agent(conversation["symptoms_collected"])
            
            # Topics already answered in the general interview — LLM must not repeat these
            already_covered = (
                "1. Main symptom / reason for consultation\n"
                "2. When symptoms started / Duration of symptoms\n"
                "3. Symptom intensity on a numeric scale (1-10)\n"
                "4. Aggravating and relieving factors\n"
                "5. Other / associated symptoms present\n"
                "6. Current medications being taken\n"
                "7. Past medical history and similar previous episodes"
            )

            from app.crew.hybrid_agent import generate_questions_hybrid

            print(f"🧪 Calling hybrid agent (NVIDIA/OpenAI)...")
            hybrid_result = generate_questions_hybrid(interview_summary, already_covered)
            
            if hybrid_result["success"]:
                print(f"✅ Hybrid agent succeeded ({hybrid_result['provider'].upper()})")
                analysis_result = hybrid_result["content"]
                print(f"🤖 Agent output:")
                print(f"� {analysis_result[:200]}..." if len(analysis_result) > 200 else analysis_result)
            else:
                raise Exception(f"All agents failed: {hybrid_result['error']}")

            # Parse hypotheses and questions from agent output
            hypotheses, questions = parse_agent_analysis(analysis_result)

            # Dedup: replace questions that repeat already-answered general interview topics
            REPEAT_TOPIC_KEYWORDS = [
                ["how long", "since when", "when did it start", "how many days", "how many weeks",
                 "how many months", "duration", "how long ago", "when did these", "when did the",
                 "how long have you"],
                ["scale of 1", "1 to 10", "rate your", "intensity from", "rate the pain",
                 "how intense", "how severe", "on a scale", "pain level", "severity on"],
                ["medication", "medicine", "currently taking", "drugs you", "are you taking any",
                 "any supplements", "any pills", "taking anything for"],
                ["medical history", "family history", "have you had before", "similar in the past",
                 "past episodes", "previously had", "prior history", "past medical", "have you ever had"],
                ["other symptoms", "additional symptoms", "any other symptoms", "else you are feeling"],
            ]
            dedup_backups = [
                "Where exactly is the symptom located — can you point to a specific area of your body?",
                "How would you describe the quality of the sensation (sharp, dull, throbbing, burning, pressure-like)?",
                "Does the symptom spread or radiate to other areas of your body?",
                "Is there a specific body position or time of day when the symptom consistently changes in intensity?",
                "Have you noticed a consistent trigger or pattern that reliably precedes the onset of your symptoms?",
            ]
            dedup_idx = 0
            filtered_questions = []
            for q in questions:
                q_lower = q.lower()
                is_repeat = any(any(kw in q_lower for kw in topic_kws) for topic_kws in REPEAT_TOPIC_KEYWORDS)
                if not is_repeat:
                    filtered_questions.append(q)
                elif dedup_idx < len(dedup_backups):
                    filtered_questions.append(dedup_backups[dedup_idx])
                    dedup_idx += 1
            while len(filtered_questions) < 5 and dedup_idx < len(dedup_backups):
                filtered_questions.append(dedup_backups[dedup_idx])
                dedup_idx += 1
            questions = filtered_questions[:5]
            print(f"✅ Using {len(questions)} specific questions (after dedup filter)")

            # Store in conversation state
            conversation["preliminary_hypotheses"] = hypotheses
            conversation["specific_questions_list"] = questions
            conversation["specific_questions_max"] = 5
            conversation["specific_questions_asked"] = 1

            current_question = questions[0] if questions else "Can you describe more details about your symptoms?"

            response_text = (
                "<strong>GENERAL QUESTIONS COMPLETED</strong>\n\n"
                "Excellent — I have completed the general interview and analyzed your initial information.\n\n"
                f"<strong>PRELIMINARY HYPOTHESES:</strong>\n{format_hypotheses_display(hypotheses)}\n\n"
                "I will now ask 5 targeted questions to refine the clinical picture:\n\n"
                f"<strong>Specific question 1/5:</strong>\n{current_question}"
            )

            conversation["messages"].append({
                "role": MessageRole.ASSISTANT,
                "content": response_text,
                "timestamp": datetime.now()
            })

            return ChatResponse(
                response=response_text,
                conversation_id=conversation_id,
                agent_type="specific_questions_analyst",
                confidence_score=0.9,
                severity_assessment="MEDIO",
                suggestions=[],
                follow_up_questions=[]
            )

        except Exception as e:
            print(f"❌ ERROR: Agent failed: {e}")
            return await handle_specific_questions_fallback(conversation_id, message)
    
    else:
        # Procesar respuesta y tomar siguiente pregunta de la lista generada por el agente
        conversation["specific_answers"].append({
            "question_number": conversation["specific_questions_asked"],
            "answer": message
        })
        
        print(f"🔍 DEBUG: Specific questions asked: {conversation['specific_questions_asked']}/{conversation['specific_questions_max']}")
        
        # Verificar si hemos completado todas las preguntas específicas
        if conversation["specific_questions_asked"] >= conversation["specific_questions_max"]:
            print(f"🔍 DEBUG: Completed all specific questions, moving to classification")
            conversation["state"] = ConversationState.READY_FOR_CLASSIFICATION
            return await handle_classification(conversation_id, message)
        
        # Tomar siguiente pregunta de la lista generada por el agente
        next_question_index = conversation["specific_questions_asked"]
        current_question = conversation["specific_questions_list"][next_question_index]
        
        conversation["specific_questions_asked"] += 1
        
        response_text = f"<strong>Specific question {conversation['specific_questions_asked']}/5:</strong>\n{current_question}"
        
        conversation["messages"].append({
            "role": MessageRole.ASSISTANT,
            "content": response_text,
            "timestamp": datetime.now()
        })
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            agent_type="specific_questions_analyst",
            confidence_score=0.9,
            severity_assessment="MEDIO",
            suggestions=[],
            follow_up_questions=[]
        )


def _build_fallback_diagnosis(conversation: Dict[str, Any]) -> str:
    """
    Builds a basic diagnosis summary from collected conversation data when the
    full classification pipeline is unavailable.  Uses only in-memory data —
    no external calls.
    """
    symptoms_text = " ".join(conversation.get("symptoms_collected", [])).lower()
    specific_answers = conversation.get("specific_answers", [])
    specific_text = " ".join(
        (a.get("answer", "") if isinstance(a, dict) else str(a)) for a in specific_answers
    ).lower()
    all_text = f"{symptoms_text} {specific_text}"

    # Infer category from collected text
    if any(w in all_text for w in ["headache", "head", "migraine", "dizziness", "neurological", "dolor de cabeza", "cefalea"]):
        category = "Neurological"
        conditions = [
            ("Tension headache", "75%", "Headache caused by muscle tension or stress"),
            ("Migraine", "15%", "Vascular headache with possible light/sound sensitivity"),
            ("Dehydration headache", "10%", "Headache related to insufficient fluid intake"),
        ]
    elif any(w in all_text for w in ["chest", "heart", "palpitation", "cardiovascular", "pecho", "corazon"]):
        category = "Cardiovascular"
        conditions = [
            ("Benign tachycardia", "60%", "Non-pathological increase in heart rate"),
            ("Anxiety-related cardiac symptoms", "30%", "Cardiac symptoms driven by anxiety"),
            ("Mild arrhythmia", "10%", "Minor alteration of heart rhythm requiring evaluation"),
        ]
    elif any(w in all_text for w in ["cough", "breath", "respiratory", "lung", "tos", "respirar"]):
        category = "Respiratory"
        conditions = [
            ("Upper respiratory infection", "65%", "Infection of the upper respiratory tract"),
            ("Mild bronchitis", "25%", "Mild inflammation of the bronchi"),
            ("Respiratory allergy", "10%", "Allergic reaction affecting the airway"),
        ]
    elif any(w in all_text for w in ["stomach", "nausea", "vomit", "digestive", "gastro", "estomago"]):
        category = "Gastrointestinal"
        conditions = [
            ("Gastritis", "60%", "Inflammation of the gastric lining"),
            ("Indigestion", "30%", "Difficulty in the digestive process"),
            ("Intestinal syndrome", "10%", "Alteration in intestinal function"),
        ]
    elif any(w in all_text for w in ["muscle", "joint", "bone", "back", "arthritis", "musculo", "articular"]):
        category = "Musculoskeletal"
        conditions = [
            ("Muscle strain", "65%", "Muscle tension or overuse fatigue"),
            ("Mild arthritis", "25%", "Mild joint inflammation"),
            ("Sports or activity injury", "10%", "Injury related to physical exertion"),
        ]
    else:
        category = "General"
        conditions = [
            ("Mild viral syndrome", "50%", "Low-intensity viral process"),
            ("Fatigue or stress-related symptoms", "35%", "Symptoms related to tiredness or tension"),
            ("General malaise requiring evaluation", "15%", "Non-specific symptoms needing professional assessment"),
        ]

    lines = [
        "<strong>MEDICAL ANALYSIS COMPLETED</strong>",
        "",
        "<strong>SUMMARY OF COLLECTED INFORMATION:</strong>",
        f"- <strong>Medical category assessed:</strong> {category}",
        f"- <strong>General questions answered:</strong> {conversation.get('questions_asked', 0)}",
        f"- <strong>Specific questions answered:</strong> {len(specific_answers)}",
        "",
        "<strong>LOW CONFIDENCE DIFFERENTIAL DIAGNOSIS</strong>",
        "<em>Based on keyword pattern matching — consult a doctor for accurate diagnosis</em>",
        "",
        "<strong>POSSIBLE CONDITIONS (estimated ranges, not definitive probabilities):</strong>",
        "",
    ]

    prob_ranges = ["35–55%", "20–35%", "10–20%"]
    for i, (name, _prob, desc) in enumerate(conditions, 1):
        display_range = prob_ranges[i - 1] if i <= len(prob_ranges) else "< 10%"
        lines.append(f"<strong>{i}. {name}</strong> (estimated range: {display_range})")
        lines.append(f"   - {desc}")
        lines.append("")

    lines += [
        "<strong>RECOMMENDATIONS:</strong>",
        "- Schedule an appointment with a healthcare professional for complete evaluation",
        "- Monitor symptom evolution and document any changes",
        "- Seek immediate care if symptoms worsen significantly",
        "",
        "<strong>IMPORTANT DISCLAIMER:</strong>",
        "- This analysis is generated by AI based on information you provided",
        "- It does NOT constitute a professional medical diagnosis",
        "- Always consult a certified doctor for definitive diagnosis and treatment",
    ]

    return "\n".join(lines)


async def handle_classification(conversation_id: str, message: str) -> ChatResponse:
    """
    Handles classification using data structuring + Hugging Face.
    Step 3: Process collected information into a structured representation.
    """
    conversation = CONVERSATIONS[conversation_id]

    # CRITICAL: Set terminal state BEFORE any processing to prevent re-entry loops.
    # If anything below fails the conversation will still advance past this phase.
    conversation["state"] = ConversationState.CLASSIFICATION_COMPLETE

    try:
        from app.services.classification_service import classification_model
        from app.services.data_structuring_service import data_structuring_service

        print(f"🔄 Starting medical data structuring...")

        structured_medical_data = await data_structuring_service.structure_conversation_data(conversation)

        print(f"✅ Structured data generated:")
        print(f"   - Chief complaint: {structured_medical_data.get('motivo_consulta', 'N/A')}")
        print(f"   - Main symptom: {structured_medical_data.get('enfermedad_actual', {}).get('sintoma_principal', 'N/A')}")

        conversation["structured_medical_data"] = structured_medical_data

        classification_input = {
            "chief_complaint": structured_medical_data.get("motivo_consulta", "general consultation"),
            "symptoms": [
                structured_medical_data.get("enfermedad_actual", {}).get("sintoma_principal", "")
            ] + structured_medical_data.get("sintomas_asociados", []),
            "history": structured_medical_data.get("antecedentes_personales", []) +
                       structured_medical_data.get("antecedentes_familiares", []),
            "current_medications": structured_medical_data.get("medicamentos_actuales", []),
            "habits": structured_medical_data.get("habitos", {}),
            "duration": structured_medical_data.get("enfermedad_actual", {}).get("inicio", "unspecified"),
            "severity": structured_medical_data.get("enfermedad_actual", {}).get("intensidad", "unspecified"),
            "associated_factors": structured_medical_data.get("factores_agravantes", []) +
                                  structured_medical_data.get("factores_aliviantes", []),
            "conversation_metadata": {
                "questions_answered": conversation.get("questions_asked", 0),
                "specific_answers_count": len(conversation.get("specific_answers", [])),
                "preliminary_hypotheses": conversation.get("preliminary_hypotheses", []),
                "processing_method": structured_medical_data.get("metadata", {}).get("processing_method", "unknown")
            }
        }

        print(f"🔍 Sending structured data to classification model...")
        classification_result = await classification_model.classify(classification_input)

        print(f"✅ Classification complete: {classification_result.get('primary_category', 'N/A')} "
              f"({classification_result.get('confidence_score', 0.0):.2f})")

        conversation["classification_result"] = classification_result
        conversation["final_structured_data"] = {
            "structured_medical_data": structured_medical_data,
            "classification_input": classification_input,
            "classification_result": classification_result,
            "processing_timestamp": datetime.now().isoformat()
        }

        response_text = await generate_enhanced_diagnosis_summary(
            structured_medical_data,
            classification_result,
            conversation.get("preliminary_hypotheses", [])
        )

        conversation["messages"].append({
            "role": MessageRole.ASSISTANT,
            "content": response_text,
            "timestamp": datetime.now()
        })

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            agent_type="enhanced_medical_classifier",
            confidence_score=classification_result.get("confidence_score", 0.0),
            severity_assessment=classification_result.get("urgency_level", "medium"),
            predicted_condition=classification_result.get("primary_category", "Analysis completed"),
            suggestions=classification_result.get("recommendations", []),
            follow_up_questions=[],
            is_diagnosis=True
        )

    except Exception as e:
        print(f"❌ ERROR in classification pipeline: {e}")
        response_text = _build_fallback_diagnosis(conversation)

        conversation["messages"].append({
            "role": MessageRole.ASSISTANT,
            "content": response_text,
            "timestamp": datetime.now()
        })

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            agent_type="fallback_medical_classifier",
            confidence_score=0.5,
            severity_assessment="medium",
            suggestions=["Consult a medical professional for a complete and definitive evaluation"],
            follow_up_questions=[],
            is_diagnosis=True
        )


async def handle_post_classification_conversation(conversation_id: str, message: str) -> ChatResponse:
    """Handles conversation after the diagnosis has been presented."""
    conversation = CONVERSATIONS[conversation_id]

    classification_result = conversation.get("classification_result", {})
    # Use the correct key — classification stores "primary_category", not "category"
    category = classification_result.get("primary_category", "general")

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
            "Consult a medical specialist",
            "Monitor your symptoms",
            "Follow the general recommendations"
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
        extracted.append(f"general symptom: {message[:100]}")
    
    return extracted


def generate_next_question(symptoms_collected: List[str], questions_asked: int) -> str:
    """Generates the next question based on symptoms collected"""
    
    # Base questions according to question number
    base_questions = [
        "When did these symptoms start? Was it hours, days, or weeks ago?",
        "How would you rate the intensity of your symptoms on a scale of 1 to 10?",
        "Is there anything that makes your symptoms worse or better?",
        "Have you noticed any other symptoms that might be related?",
        "Are you taking any medications currently or have you taken anything for these symptoms?",
        "Have you had similar problems in the past?",
        "Is there a specific factor you think might have triggered these symptoms?"
    ]
    
    if questions_asked < len(base_questions):
        return base_questions[questions_asked - 1]
    else:
        return "Is there any other detail about your symptoms that you think is important to mention?"


def generate_contextual_response(message: str, category: str, classification_result: Dict) -> str:
    """Generates contextual response based on classification"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['medication', 'medicine', 'medicamento', 'medicina', 'pill', 'pastilla', 'treatment', 'tratamiento']):
        return f"Regarding medications for {category} conditions, it's important that you consult with a doctor before taking any medication. Based on my analysis, general recommendations include monitoring symptoms and professional medical evaluation."
    
    elif any(word in message_lower for word in ['when', 'doctor', 'médico', 'physician', 'appointment', 'consulta']):
        severity = classification_result.get("urgency_level", "medium")
        if severity in ["critical", "high", "CRITICAL", "HIGH"]:
            return "Given the nature of your symptoms, I recommend that you see a doctor as soon as possible, preferably today."
        else:
            return "I recommend that you schedule an appointment with your doctor in the next few days for a more detailed evaluation."
    
    else:
        return f"I understand your concern. Based on my analysis related to {category}, I suggest you continue monitoring your symptoms and consult with a medical professional for a definitive diagnosis."


def generate_basic_medical_response(message: str, conversation_history: list) -> str:
    """Generates a basic medical response based on keywords"""
    message_lower = message.lower()
    
    # Responses based on common symptoms
    if any(word in message_lower for word in ['pain', 'hurt', 'hurts', 'ache', 'headache', 'headaches', 'dolor', 'duele', 'molesta']):
        return "I understand you are experiencing pain. To help you better, I need more information: In what part of your body do you feel the pain? How would you describe the pain (sharp, dull, throbbing)? When did it start and what makes it worse or better?"
    
    elif any(word in message_lower for word in ['fever', 'temperature', 'hot', 'fiebre', 'temperatura', 'calentura']):
        return "Fever can be a symptom of various conditions. Have you taken your temperature? Do you have other symptoms like chills, headache, or general malaise? How long have you had the fever?"
    
    elif any(word in message_lower for word in ['cough', 'coughing', 'cough', 'tos', 'toso']):
        return "Cough can have multiple causes. Is your cough dry or do you have phlegm? How long have you had it? Do you have other symptoms like fever, difficulty breathing, or chest pain?"
    
    elif any(word in message_lower for word in ['fatigue', 'tired', 'cansancio', 'cansado', 'exhausted']):
        return "Fatigue can be related to many factors. How long have you been feeling this way? Is it constant or does it come and go? Do you have difficulty sleeping or other symptoms?"
    
    else:
        # General response for other cases
        return f"I understand you're consulting about: '{message}'. To help you appropriately, I would like to know more details. Can you describe your main symptoms, when they started, and how they have evolved?"


async def handle_advanced_conversation(conversation_id: str, message: str) -> ChatResponse:
    """Maneja conversaciones en estados más avanzados"""
    # Por ahora, redirigir a conversación médica normal
    return await handle_medical_conversation(conversation_id, message)


@router.get("/{conversation_id}/history")
async def get_conversation_history(conversation_id: str):
    """Obtiene el historial de una conversación"""
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
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
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    del CONVERSATIONS[conversation_id]
    return {"message": f"Conversation {conversation_id} deleted successfully"}


@router.get("/{conversation_id}/structured-data")
async def get_structured_medical_data(conversation_id: str):
    """
    Obtiene los datos médicos estructurados de una conversación
    Paso 3: Endpoint para acceder a la representación estructurada
    """
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = CONVERSATIONS[conversation_id]
    
    # Verificar si ya se han estructurado los datos
    if "final_structured_data" not in conversation:
        # Si no están estructurados, estructurarlos ahora
        from app.services.data_structuring_service import data_structuring_service
        
        try:
            structured_data = await data_structuring_service.structure_conversation_data(conversation)
            conversation["structured_medical_data"] = structured_data
            
            return {
                "conversation_id": conversation_id,
                "structured_data": structured_data,
                "status": "newly_structured",
                "format_version": structured_data.get("metadata", {}).get("format_version", "1.0"),
                "processing_method": structured_data.get("metadata", {}).get("processing_method", "unknown"),
                "ready_for_classification": True
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error structuring data: {str(e)}"
            )
    
    # Retornar datos ya estructurados
    final_data = conversation["final_structured_data"]
    
    return {
        "conversation_id": conversation_id,
        "structured_data": final_data["structured_medical_data"],
        "classification_input": final_data.get("classification_input", {}),
        "classification_result": final_data.get("classification_result", {}),
        "status": "previously_structured",
        "processing_timestamp": final_data.get("processing_timestamp"),
        "ready_for_classification": True,
        "classification_completed": True
    }


@router.post("/{conversation_id}/reprocess-structure")
async def reprocess_structured_data(conversation_id: str):
    """
    Reprocesa la estructuración de datos médicos de una conversación
    Útil para probar mejoras en el algoritmo de estructuración
    """
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation = CONVERSATIONS[conversation_id]
    
    try:
        from app.services.data_structuring_service import data_structuring_service
        
        # Limpiar datos estructurados previos
        conversation.pop("structured_medical_data", None)
        conversation.pop("final_structured_data", None)
        
        # Reestructurar datos
        structured_data = await data_structuring_service.structure_conversation_data(conversation)
        conversation["structured_medical_data"] = structured_data
        
        return {
            "conversation_id": conversation_id,
            "structured_data": structured_data,
            "status": "reprocessed",
            "message": "Medical data restructured successfully",
            "format_version": structured_data.get("metadata", {}).get("format_version", "1.0"),
            "processing_method": structured_data.get("metadata", {}).get("processing_method", "unknown")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reprocessing structure: {str(e)}"
        )


async def generate_diagnosis_summary(classification_result: Dict, symptoms_collected: List[str], ai_hypotheses: List[str] = None) -> str:
    """Genera un resumen de análisis con las 3 condiciones más probables usando Hugging Face"""
    
    # Usar las hipótesis de la IA si están disponibles
    possible_conditions = []
    
    # Siempre definir all_symptoms para uso posterior
    all_symptoms = " ".join(symptoms_collected).lower()
    
    if ai_hypotheses and len(ai_hypotheses) > 0:
        print(f"✅ Usando hipótesis de la IA: {len(ai_hypotheses)} hipótesis encontradas")
        
        # Convertir las hipótesis de la IA a formato de condiciones
        for i, hypothesis in enumerate(ai_hypotheses[:3]):  # Tomar máximo 3
            # Extraer el nombre de la condición (antes del primer ":")
            if "**" in hypothesis:
                # Formato: "**Nombre**: Descripción"
                parts = hypothesis.split("**")
                if len(parts) >= 3:
                    condition_name = parts[1].strip()
                    description = parts[2].split(":", 1)[-1].strip() if ":" in parts[2] else parts[2].strip()
                else:
                    condition_name = hypothesis[:50]
                    description = hypothesis
            elif ":" in hypothesis:
                # Formato: "Nombre: Descripción"
                parts = hypothesis.split(":", 1)
                condition_name = parts[0].strip()
                description = parts[1].strip()
            else:
                condition_name = hypothesis[:50] + "..." if len(hypothesis) > 50 else hypothesis
                description = hypothesis
            
            # Obtener probabilidad exacta del modelo Hugging Face si está disponible
            if classification_result and "confidence_score" in classification_result:
                # Para la primera hipótesis, usar la confianza principal del modelo
                if i == 0:
                    hf_confidence = classification_result["confidence_score"] * 100
                    probability = f"{hf_confidence:.1f}%"
                # Para hipótesis secundarias, usar confianzas decrecientes basadas en el modelo
                else:
                    # Distribuir la confianza restante entre las hipótesis secundarias
                    remaining_confidence = (1 - classification_result["confidence_score"]) * 100
                    secondary_prob = remaining_confidence / (len(ai_hypotheses) - 1) if len(ai_hypotheses) > 1 else remaining_confidence
                    probability = f"{secondary_prob:.1f}%"
            else:
                # Fallback a probabilidades decrecientes
                base_probs = [70.0, 20.0, 10.0]
                probability = f"{base_probs[i] if i < len(base_probs) else 5.0}%"
            
            possible_conditions.append({
                "name": condition_name,
                "probability": probability,
                "description": description,
                "hf_verified": True
            })
    else:
        print("⚠️ No se encontraron hipótesis de IA, usando condiciones por defecto")
        # Fallback a condiciones predeterminadas basadas en síntomas comunes
        
        if "dolor" in all_symptoms and ("cabeza" in all_symptoms or "neurological" in all_symptoms):
            possible_conditions = [
                {"name": "Tension headache", "probability": "75%", "description": "Headache caused by tension or stress"},
                {"name": "Mild migraine", "probability": "20%", "description": "Vascular headache with possible sensitivity"},
                {"name": "Dehydration headache", "probability": "5%", "description": "Headache related to insufficient hydration"}
            ]
        elif "fiebre" in all_symptoms or "temperatura" in all_symptoms:
            possible_conditions = [
                {"name": "Viral infection", "probability": "60%", "description": "Infectious process of viral origin"},
                {"name": "Mild bacterial infection", "probability": "30%", "description": "Low-intensity bacterial infectious process"},
                {"name": "Inflammatory reaction", "probability": "10%", "description": "Inflammatory response of the body"}
            ]
        elif "tos" in all_symptoms:
            possible_conditions = [
                {"name": "Upper respiratory infection", "probability": "65%", "description": "Infection in the upper respiratory tract"},
                {"name": "Mild bronchitis", "probability": "25%", "description": "Mild inflammation of the bronchi"},
                {"name": "Respiratory allergy", "probability": "10%", "description": "Allergic reaction in the respiratory tract"}
            ]
        elif "dolor" in all_symptoms:
            possible_conditions = [
                {"name": "Muscle pain", "probability": "50%", "description": "Muscle tension or fatigue"},
                {"name": "Joint pain", "probability": "35%", "description": "Joint discomfort"},
                {"name": "Neuropathic pain", "probability": "15%", "description": "Pain related to nerves"}
            ]
        else:
            # Condiciones generales
            possible_conditions = [
                {"name": "General malaise", "probability": "40%", "description": "Nonspecific symptoms requiring evaluation"},
                {"name": "Mild viral syndrome", "probability": "35%", "description": "Possible low-intensity viral process"},
                {"name": "Fatigue or stress", "probability": "25%", "description": "Symptoms related to tiredness or tension"}
            ]
    
    # Usar datos de clasificación Hugging Face si están disponibles (solo si no tenemos hipótesis de IA)
    if not ai_hypotheses and classification_result and "primary_category" in classification_result:
        primary_category = classification_result["primary_category"]
        confidence = classification_result.get("confidence_score", 0.5) * 100
        
        # Convertir categoria a nombre legible
        category_names = {
            "neurological": "Neurological condition",
            "cardiovascular": "Cardiovascular condition", 
            "respiratory": "Respiratory condition",
            "gastrointestinal": "Gastrointestinal condition",
            "musculoskeletal": "Musculoskeletal condition",
            "dermatological": "Dermatological condition",
            "psychiatric": "Psychiatric condition",
            "other": "General condition"
        }
        
        main_condition = category_names.get(primary_category, "Medical condition")
        possible_conditions[0] = {
            "name": main_condition,
            "probability": f"{confidence:.1f}%",
            "description": f"Classified by Hugging Face model - {classification_result.get('method', 'AI')}",
            "hf_verified": True
        }
        
        # Agregar categorías secundarias si existen
        secondary_categories = classification_result.get("secondary_categories", [])
        for i, sec_cat in enumerate(secondary_categories[:2], 1):  # Máximo 2 secundarias
            if i < len(possible_conditions):
                sec_name = category_names.get(sec_cat, "Medical condition")
                remaining_prob = (1 - classification_result.get("confidence_score", 0.5)) * 100 / len(secondary_categories)
                possible_conditions[i] = {
                    "name": sec_name,
                    "probability": f"{remaining_prob:.1f}%",
                    "description": f"Secondary category identified by the model",
                    "hf_verified": True
                }
    
    # Si tenemos hipótesis de IA, agregar información del modelo Hugging Face como confirmación
    elif ai_hypotheses and classification_result and "confidence_score" in classification_result:
        hf_confidence = classification_result.get("confidence_score", 0.5) * 100
        primary_category = classification_result.get("primary_category", "")
        
        # Agregar nota sobre confirmación del modelo al final
        if possible_conditions:
            possible_conditions[0]["description"] += f" - Hugging Face model: {hf_confidence:.1f}% confidence in the analysis"
    
    # Ordenar las condiciones por probabilidad (de mayor a menor)
    def extract_probability(condition):
        prob_str = condition['probability'].replace('%', '')
        try:
            return float(prob_str)
        except:
            return 0.0
    
    sorted_conditions = sorted(possible_conditions[:3], key=extract_probability, reverse=True)
    
    # Generar texto del análisis
    diagnosis_text = "Based on the information you provided and the analysis performed, these are the estimated probabilities:\n\n"
    
    for i, condition in enumerate(sorted_conditions, 1):
        diagnosis_text += f"- **{condition['name']}**: {condition['probability']}\n"
    
    diagnosis_text += f"\n**Reflection on your consultation:**\n"
    diagnosis_text += f"Thank you for trusting this system with personal health information. I understand that when we experience concerning symptoms, it is natural to look for answers and guidance. "
    
    # Agregar comentario empático basado en síntomas
    all_symptoms = " ".join(symptoms_collected).lower()
    if any(word in all_symptoms for word in ['dolor', 'intenso', 'fuerte']):
        diagnosis_text += f"I understand that dealing with pain can be very challenging and can affect both physical and emotional well-being. "
    elif any(word in all_symptoms for word in ['preocup', 'ansie', 'nervios']):
        diagnosis_text += f"I recognize that the symptoms you are experiencing can create anxiety and uncertainty. "
    else:
        diagnosis_text += f"I understand that any change in well-being can cause concern. "
    
    diagnosis_text += f"My goal is to provide useful information that complements, but does not replace, professional medical care.\n\n"
    diagnosis_text += f"It is important to clarify that these figures are statistical estimates generated by an artificial intelligence model and do not constitute a medical diagnosis.\n\n"
    
    # Agregar recomendación personalizada y humana basada en los síntomas
    diagnosis_text += f"**Care recommendations:**\n"
    
    if any(word in all_symptoms for word in ['dolor', 'intenso', 'fuerte', '8', '9', '10']):
        diagnosis_text += f"Given the intensity of your symptoms, it is important to seek medical care without delay. Your well-being is the priority, and a healthcare professional can perform a complete physical exam and any necessary studies. "
        diagnosis_text += f"Do not hesitate to go to emergency care if symptoms intensify."
    elif any(word in all_symptoms for word in ['fiebre', 'temperatura', 'escalofríos']):
        diagnosis_text += f"Your symptoms suggest the need for prompt medical evaluation. I recommend contacting your primary care doctor or going to a health center for appropriate care. "
        diagnosis_text += f"In the meantime, stay hydrated and get enough rest."
    else:
        diagnosis_text += f"Although your symptoms may seem minor, every person is unique and deserves personalized care. I suggest scheduling an appointment with a healthcare professional for a comprehensive evaluation. "
        diagnosis_text += f"Remember that caring for your health supports your quality of life."
    
    diagnosis_text += f"\n\nFinally, remember that you know your body best. If something does not feel right or if you have additional questions, do not hesitate to seek a second medical opinion. Your health and peace of mind matter."
    
    return diagnosis_text


def generate_preliminary_hypotheses(symptoms_collected: List[str]) -> List[Dict[str, str]]:
    """Genera hipótesis preliminares basadas en los síntomas recopilados"""
    all_symptoms = " ".join(symptoms_collected).lower()
    hypotheses = []
    
    # Hipótesis basadas en síntomas neurológicos
    if any(word in all_symptoms for word in ['cabeza', 'dolor de cabeza', 'cefalea', 'mareo']):
        hypotheses.extend([
            {"name": "Tension headache", "category": "neurological", "probability": "high"},
            {"name": "Migraine", "category": "neurological", "probability": "medium"},
            {"name": "Secondary headache", "category": "neurological", "probability": "low"}
        ])
    
    # Hipótesis basadas en síntomas respiratorios
    elif any(word in all_symptoms for word in ['tos', 'pecho', 'respirar', 'ahogo']):
        hypotheses.extend([
            {"name": "Upper respiratory infection", "category": "respiratory", "probability": "high"},
            {"name": "Bronchitis", "category": "respiratory", "probability": "medium"},
            {"name": "Mild asthma", "category": "respiratory", "probability": "low"}
        ])
    
    # Hipótesis basadas en síntomas cardiovasculares
    elif any(word in all_symptoms for word in ['corazón', 'palpitaciones', 'pecho y dolor']):
        hypotheses.extend([
            {"name": "Benign tachycardia", "category": "cardiovascular", "probability": "high"},
            {"name": "Cardiac anxiety", "category": "cardiovascular", "probability": "medium"},
            {"name": "Mild arrhythmia", "category": "cardiovascular", "probability": "low"}
        ])
    
    # Hipótesis basadas en síntomas musculoesqueléticos
    elif any(word in all_symptoms for word in ['dolor', 'músculo', 'articulación', 'espalda', 'rodilla']):
        hypotheses.extend([
            {"name": "Muscle pain", "category": "musculoskeletal", "probability": "high"},
            {"name": "Mild arthritis", "category": "musculoskeletal", "probability": "medium"},
            {"name": "Sports injury", "category": "musculoskeletal", "probability": "low"}
        ])
    
    # Hipótesis generales si no se identifica categoría específica
    else:
        hypotheses.extend([
            {"name": "General malaise", "category": "general", "probability": "high"},
            {"name": "Viral syndrome", "category": "general", "probability": "medium"},
            {"name": "Chronic fatigue", "category": "general", "probability": "low"}
        ])
    
    return hypotheses[:3]  # Máximo 3 hipótesis


def generate_specific_question(symptoms_collected: List[str], hypotheses: List[Dict], question_number: int) -> str:
    """Genera preguntas específicas basadas en síntomas e hipótesis"""
    
    all_symptoms = " ".join(symptoms_collected).lower()
    
    # Preguntas específicas basadas en la categoría principal de hipótesis
    main_category = hypotheses[0]["category"] if hypotheses else "general"
    
    neurological_questions = [
        "Is the headache located in a specific area or is it generalized?",
        "Have you noticed vision changes, light sensitivity, or nausea?",
        "Does the pain worsen with movement or stay constant?",
        "Have you had similar episodes in the past? How often?",
        "Are there specific factors that trigger the pain (stress, certain foods, lack of sleep)?"
    ]
    
    respiratory_questions = [
        "Is the cough dry or does it produce phlegm? What color is it?",
        "Do you feel short of breath at rest or only with exertion?",
        "Have you had fever or chills along with these symptoms?",
        "Do the symptoms worsen at certain times of day?",
        "Have you recently been exposed to irritants, allergens, or sick people?"
    ]
    
    cardiovascular_questions = [
        "Do the palpitations occur at rest or during physical activity?",
        "Have you felt chest pain, dizziness, or fainting?",
        "Do you notice an irregular heart rhythm, or is it only fast?",
        "Do the episodes last seconds, minutes, or hours?",
        "Do you regularly consume caffeine, alcohol, or any medication?"
    ]
    
    musculoskeletal_questions = [
        "Does the pain appear with movement or also at rest?",
        "Is there swelling, redness, or warmth in the affected area?",
        "Have you had a recent injury or done intense exercise?",
        "Does the pain radiate to other parts of the body?",
        "Which positions or movements relieve or worsen the pain?"
    ]
    
    general_questions = [
        "Have you noticed changes in appetite, weight, or sleep patterns?",
        "Do you have a family history of similar medical conditions?",
        "Are you currently taking any medication or supplement?",
        "Have you traveled recently or changed your usual routine?",
        "Is there anything else you consider relevant about your symptoms?"
    ]
    
    # Seleccionar conjunto de preguntas según la categoría
    if main_category == "neurological":
        questions = neurological_questions
    elif main_category == "respiratory":
        questions = respiratory_questions
    elif main_category == "cardiovascular":
        questions = cardiovascular_questions
    elif main_category == "musculoskeletal":
        questions = musculoskeletal_questions
    else:
        questions = general_questions
    
    # Retornar la pregunta correspondiente al número
    return questions[min(question_number - 1, len(questions) - 1)]


def should_ask_more_questions(adaptive_context: List[str], questions_asked: int, hypotheses: List[Dict]) -> tuple[bool, str]:
    """Determina si se necesitan más preguntas específicas basándose en el contexto"""
    
    # Si hemos hecho menos de 2 preguntas específicas, seguir preguntando
    if questions_asked < 2:
        return True, "We need minimum information"
    
    # Analizar si las respuestas han sido informativas
    context_text = " ".join(adaptive_context)
    
    # Si las respuestas son muy cortas o poco informativas, seguir preguntando
    if len(context_text) < 50 and questions_asked < 4:
        return True, "Answers are too brief; we need more details"
    
    # Si detectamos síntomas preocupantes, hacer más preguntas
    concerning_symptoms = ['sangre', 'desmayo', 'pecho', 'respirar', 'corazón', 'vision', 'paralisis', 'entumecimiento']
    if any(symptom in context_text for symptom in concerning_symptoms) and questions_asked < 4:
        return True, "Symptoms requiring further investigation detected"
    
    # Si tenemos información suficiente y clara, proceder al diagnóstico
    if questions_asked >= 3 and len(context_text) > 100:
        return False, "Enough information collected for analysis"
    
    # Por defecto, hacer al menos 3 preguntas específicas
    if questions_asked < 3:
        return True, "Specific basic information required"
    
    return False, "Information criteria complete"


def generate_adaptive_question(symptoms: List[str], hypotheses: List[Dict], context: List[str], question_num: int) -> str:
    """Genera preguntas específicas adaptativas basadas en respuestas anteriores"""
    
    # Obtener la categoría principal de la hipótesis
    main_category = hypotheses[0]["category"] if hypotheses else "general"
    context_text = " ".join(context).lower()
    
    # Preguntas adaptativas basadas en respuestas anteriores
    if question_num == 1:
        # Primera pregunta específica - siempre sobre localización/características
        if main_category == "neurological":
            return "Is the headache located in a specific area (forehead, temples, back of the neck), or is it generalized across the whole head?"
        elif main_category == "respiratory":
            return "Does the breathing difficulty or cough occur at rest or only during physical activity?"
        elif main_category == "cardiovascular":
            return "Do the palpitations or chest discomfort occur at rest or with exertion?"
        elif main_category == "musculoskeletal":
            return "Does the pain occur only with movement or also when you are at rest?"
        else:
            return "Could you describe the specific characteristics of your main symptom in more detail?"
    
    elif question_num == 2:
        # Segunda pregunta - adaptada a la primera respuesta
        if "movimiento" in context_text or "actividad" in context_text:
            return "Is there any specific movement or position that significantly relieves or worsens the symptoms?"
        elif "reposo" in context_text or "descanso" in context_text:
            return "Do the symptoms improve with rest, or do they persist even when you are not doing anything?"
        elif "localiza" in context_text or "área" in context_text:
            return "Have you noticed whether the affected area has swelling, redness, warmth, or visible changes?"
        else:
            return "Have you noticed any pattern in when the symptoms are most intense (time of day, specific situations)?"
    
    elif question_num == 3:
        # Tercera pregunta - buscar síntomas acompañantes o factores agravantes
        if any(word in context_text for word in ['dolor', 'molesta', 'duele']):
            return "Do you experience other symptoms along with the pain, such as nausea, dizziness, vision changes, or sensitivity?"
        elif any(word in context_text for word in ['mejor', 'alivia', 'mejora']):
            return "Have you tried any treatment, medication, or home remedy? What was the result?"
        else:
            return "Have you noticed anything specific that triggers or worsens these symptoms (food, stress, weather, activities)?"
    
    elif question_num == 4:
        # Cuarta pregunta - antecedentes y contexto médico
        if "medicamento" in context_text or "tratamiento" in context_text:
            return "Do you have a family history of similar conditions, or are you taking any medication regularly?"
        elif any(word in context_text for word in ['estrés', 'trabajo', 'sueño']):
            return "Have there been recent changes in your routine, stress level, diet, or sleep patterns?"
        else:
            return "Is this the first time you have experienced these symptoms, or have you had similar episodes before?"
    
    else:
        # Pregunta final - información adicional importante
        return "Is there any additional detail about your symptoms that you think is important to mention or that we have not covered?"


async def generate_enhanced_diagnosis_summary(
    structured_data: Dict[str, Any], 
    classification_result: Dict[str, Any],
    hypotheses: List[str]
) -> str:
    """
    Genera resumen diagnóstico mejorado usando datos estructurados
    Paso 3: Presenta los resultados de la representación estructurada
    """
    
    # Extraer información clave de los datos estructurados
    motivo_consulta = structured_data.get("motivo_consulta", "medical consultation")
    enfermedad_actual = structured_data.get("enfermedad_actual", {})
    sintoma_principal = enfermedad_actual.get("sintoma_principal", "unspecified symptom")
    inicio = enfermedad_actual.get("inicio", "unspecified")
    intensidad = enfermedad_actual.get("intensidad", "unspecified")
    
    antecedentes = structured_data.get("antecedentes_personales", [])
    sintomas_asociados = structured_data.get("sintomas_asociados", [])
    habitos = structured_data.get("habitos", {})
    
    # Información de clasificación
    primary_category = classification_result.get("primary_category", "other")
    confidence_score = classification_result.get("confidence_score", 0.0)
    urgency_level = classification_result.get("urgency_level", "medium")
    recommendations = classification_result.get("recommendations", [])
    reasoning = classification_result.get("reasoning", "Analysis based on structured data")
    
    # Map categories to display names
    category_names = {
        "neurological": "Neurological",
        "cardiovascular": "Cardiovascular", 
        "respiratory": "Respiratory",
        "gastrointestinal": "Gastrointestinal",
        "musculoskeletal": "Musculoskeletal",
        "dermatological": "Dermatological",
        "psychiatric": "Psychiatric",
        "other": "General"
    }
    
    category_display = category_names.get(primary_category, "General")
    
    # Generar condiciones probables basadas en la categoría y datos estructurados
    possible_conditions = await generate_conditions_from_structured_data(
        structured_data, 
        classification_result
    )
    
    # Field inference: if symptom is generic, fall back to motivo_consulta text
    generic_values = {
        "symptom requiring evaluation", "unspecified symptom", "unspecified",
        "requires additional analysis", "not specified", ""
    }
    if sintoma_principal.lower() in generic_values and motivo_consulta not in ("medical consultation", "general medical consultation"):
        sintoma_principal = motivo_consulta[:80]
    if inicio.lower() in generic_values:
        inicio = "not specified in interview"

    # Low-confidence handling
    low_confidence = confidence_score < 0.5
    if low_confidence:
        conditions_header = "<strong>LOW CONFIDENCE DIFFERENTIAL DIAGNOSIS</strong>"
        confidence_display = "Low (below 50%)"
        prob_ranges = ["30–50%", "15–30%", "< 15%"]
        confidence_note = (
            "\n<em>Note: Model confidence is below 50%. "
            "The following are broad differential possibilities — not ranked probabilities. "
            "A clinical evaluation is strongly recommended.</em>\n"
        )
    else:
        conditions_header = "<strong>MOST LIKELY CONDITIONS:</strong>"
        confidence_display = f"{confidence_score*100:.0f}%"
        prob_ranges = None
        confidence_note = ""

    # Build diagnosis text
    diagnosis_text = "<strong>MEDICAL ANALYSIS COMPLETED</strong>\n\n"

    # Summary of collected information
    diagnosis_text += "<strong>SUMMARY OF COLLECTED INFORMATION:</strong>\n"
    diagnosis_text += f"- <strong>Reason for consultation:</strong> {motivo_consulta}\n"
    diagnosis_text += f"- <strong>Main symptom:</strong> {sintoma_principal}\n"
    diagnosis_text += f"- <strong>Duration:</strong> {inicio}\n"

    if intensidad and intensidad.lower() not in generic_values:
        diagnosis_text += f"- <strong>Intensity:</strong> {intensidad}\n"

    if antecedentes:
        diagnosis_text += f"- <strong>Medical history:</strong> {', '.join(antecedentes[:3])}\n"

    if sintomas_asociados:
        diagnosis_text += f"- <strong>Associated symptoms:</strong> {', '.join(sintomas_asociados[:3])}\n"

    diagnosis_text += "\n"

    # Classification
    diagnosis_text += "<strong>MEDICAL CLASSIFICATION:</strong>\n"
    diagnosis_text += f"- <strong>Category:</strong> {category_display}\n"
    diagnosis_text += f"- <strong>Analysis confidence:</strong> {confidence_display}\n"
    diagnosis_text += f"- <strong>Urgency level:</strong> {urgency_level.upper()}\n\n"

    # Conditions
    diagnosis_text += f"{conditions_header}\n{confidence_note}\n"

    for i, condition in enumerate(possible_conditions[:3], 1):
        if low_confidence and prob_ranges:
            display_prob = prob_ranges[i - 1] if i <= len(prob_ranges) else "< 10%"
            diagnosis_text += f"<strong>{i}. {condition['name']}</strong> (estimated range: {display_prob})\n"
        else:
            diagnosis_text += f"<strong>{i}. {condition['name']}</strong> ({condition['probability']})\n"
        diagnosis_text += f"   - {condition['description']}\n"
        if condition.get('indicators'):
            diagnosis_text += f"   - Indicators: {', '.join(condition['indicators'][:2])}\n"
        diagnosis_text += "\n"

    # Clinical reasoning (only show if meaningful and non-trivial)
    if reasoning and reasoning not in ("Analysis based on structured data",) and not reasoning.startswith("Clasificación"):
        diagnosis_text += "<strong>CLINICAL REASONING:</strong>\n"
        diagnosis_text += f"{reasoning}\n\n"

    # Recommendations
    if recommendations:
        diagnosis_text += "<strong>RECOMMENDATIONS:</strong>\n"
        for rec in recommendations[:4]:
            diagnosis_text += f"- {rec}\n"
        diagnosis_text += "\n"

    # Next steps
    diagnosis_text += "<strong>NEXT STEPS:</strong>\n"
    if urgency_level in ["critical", "high"]:
        diagnosis_text += "- <strong>CONSULT A DOCTOR IMMEDIATELY</strong>\n"
        diagnosis_text += "- Consider going to emergency care if symptoms worsen\n"
    elif urgency_level == "medium":
        diagnosis_text += "- <strong>Schedule a medical appointment in the next 2–3 days</strong>\n"
        diagnosis_text += "- Monitor how your symptoms evolve\n"
    else:
        diagnosis_text += "- <strong>Monitor symptoms and seek care if they worsen</strong>\n"
        diagnosis_text += "- Consider a routine medical consultation\n"

    diagnosis_text += "\n"

    # Disclaimer
    diagnosis_text += "<strong>IMPORTANT DISCLAIMER:</strong>\n"
    diagnosis_text += "- This analysis is based on AI and structured conversation data\n"
    diagnosis_text += "- It does <strong>NOT</strong> replace professional medical diagnosis\n"
    diagnosis_text += "- Always consult a doctor for a definitive diagnosis and treatment plan\n"

    return diagnosis_text


async def generate_conditions_from_structured_data(
    structured_data: Dict[str, Any], 
    classification_result: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Genera condiciones probables basadas en datos médicos estructurados
    """
    
    enfermedad_actual = structured_data.get("enfermedad_actual", {})
    sintoma_principal = enfermedad_actual.get("sintoma_principal", "").lower()
    sintomas_asociados = [s.lower() for s in structured_data.get("sintomas_asociados", [])]
    primary_category = classification_result.get("primary_category", "other")
    confidence = classification_result.get("confidence_score", 0.5)
    
    # Conditions by category — bilingual keywords (EN + ES)
    conditions_by_category = {
        "neurological": [
            {
                "name": "Tension headache",
                "keywords": ["tension headache", "headache", "head pain", "cefalea", "dolor de cabeza", "tension"],
                "description": "Headache related to muscle tension or stress",
                "base_probability": 0.75
            },
            {
                "name": "Migraine",
                "keywords": ["migraine", "photophobia", "phonophobia", "aura", "throbbing", "migraña", "jaqueca", "pulsante"],
                "description": "Vascular headache with possible light/sound sensitivity",
                "base_probability": 0.65
            },
            {
                "name": "Dehydration headache",
                "keywords": ["dehydration", "headache", "deshidratacion", "poco liquido"],
                "description": "Headache related to insufficient hydration",
                "base_probability": 0.45
            }
        ],
        "respiratory": [
            {
                "name": "Upper respiratory infection",
                "keywords": ["cough", "sore throat", "congestion", "runny nose", "tos", "resfriado", "garganta"],
                "description": "Infection in the upper respiratory tract",
                "base_probability": 0.70
            },
            {
                "name": "Mild bronchitis",
                "keywords": ["persistent cough", "phlegm", "chest", "tos persistente", "flemas"],
                "description": "Mild inflammation of the bronchi",
                "base_probability": 0.55
            },
            {
                "name": "Respiratory allergy",
                "keywords": ["allergy", "allergic", "seasonal", "sneezing", "alergia", "estacional"],
                "description": "Allergic reaction in the respiratory tract",
                "base_probability": 0.50
            }
        ],
        "cardiovascular": [
            {
                "name": "Benign tachycardia",
                "keywords": ["palpitations", "heart racing", "fast heartbeat", "palpitaciones", "corazon rapido"],
                "description": "Non-pathological increase in heart rate",
                "base_probability": 0.65
            },
            {
                "name": "Cardiac anxiety",
                "keywords": ["anxiety", "stress", "nervous", "ansiedad", "estres"],
                "description": "Cardiac symptoms related to anxiety",
                "base_probability": 0.60
            },
            {
                "name": "Mild arrhythmia",
                "keywords": ["irregular heartbeat", "irregular", "pauses", "skipping beats", "irregular"],
                "description": "Mild alteration of heart rhythm",
                "base_probability": 0.45
            }
        ],
        "musculoskeletal": [
            {
                "name": "Muscle pain",
                "keywords": ["muscle pain", "muscle ache", "muscle tension", "dolor muscular", "contractura"],
                "description": "Muscle tension or fatigue",
                "base_probability": 0.70
            },
            {
                "name": "Mild arthritis",
                "keywords": ["joint pain", "joint ache", "joint", "arthritis", "articular", "articulaciones"],
                "description": "Mild joint inflammation",
                "base_probability": 0.55
            },
            {
                "name": "Sports injury",
                "keywords": ["exercise", "sport", "overuse", "injury", "strain", "ejercicio", "deporte"],
                "description": "Injury related to physical activity",
                "base_probability": 0.50
            }
        ],
        "gastrointestinal": [
            {
                "name": "Gastritis",
                "keywords": ["stomach", "heartburn", "acid", "burning", "estomago", "acidez"],
                "description": "Inflammation of the gastric lining",
                "base_probability": 0.65
            },
            {
                "name": "Indigestion",
                "keywords": ["digestion", "bloating", "heavy", "food", "digestion", "pesadez"],
                "description": "Difficulties in the digestive process",
                "base_probability": 0.60
            },
            {
                "name": "Intestinal syndrome",
                "keywords": ["bowel", "diarrhea", "constipation", "intestino", "diarrea"],
                "description": "Alteration in intestinal function",
                "base_probability": 0.50
            }
        ]
    }
    
    # Condiciones generales para categorías no específicas
    general_conditions = [
        {
            "name": "Mild viral syndrome",
            "keywords": ["fatigue", "fever", "malaise", "weakness", "malestar", "cansancio", "fiebre"],
            "description": "Low-intensity viral process",
            "base_probability": 0.60
        },
        {
            "name": "Fatigue or stress",
            "keywords": ["fatigue", "tired", "exhausted", "stress", "anxiety", "cansancio", "estres"],
            "description": "Symptoms related to tiredness or tension",
            "base_probability": 0.55
        },
        {
            "name": "General malaise",
            "keywords": ["general", "unspecified", "evaluation", "inespecifico"],
            "description": "Nonspecific symptoms requiring evaluation",
            "base_probability": 0.45
        }
    ]
    
    # Seleccionar condiciones relevantes
    relevant_conditions = conditions_by_category.get(primary_category, general_conditions)
    
    # Calcular probabilidades basadas en coincidencias de palabras clave
    all_symptoms_text = f"{sintoma_principal} {' '.join(sintomas_asociados)}"
    
    scored_conditions = []
    for condition in relevant_conditions:
        score = condition["base_probability"]
        
        # Bonificación por coincidencias de palabras clave
        keyword_matches = sum(1 for keyword in condition["keywords"] 
                            if keyword in all_symptoms_text)
        
        if keyword_matches > 0:
            score += keyword_matches * 0.1  # Bonificación por coincidencia
        
        # Ajustar por confianza del modelo
        score *= confidence
        
        # Agregar indicadores encontrados
        indicators = [kw for kw in condition["keywords"] if kw in all_symptoms_text]
        
        scored_conditions.append({
            "name": condition["name"],
            "probability": f"{min(score * 100, 95):.0f}%",
            "description": condition["description"],
            "indicators": indicators or ["Analysis based on medical category"]
        })
    
    # Ordenar por probabilidad y retornar top 3
    scored_conditions.sort(key=lambda x: float(x["probability"].rstrip('%')), reverse=True)
    
    return scored_conditions[:3]
