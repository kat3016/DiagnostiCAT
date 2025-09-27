"""
Router para chat médico conversacional
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import re

from app.models.medical_models import MessageModel, MessageRole, ChatResponse, ChatRequest
from app.crew.anamnesis_crew import AnamnesisConversacionalCrew

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
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    conversation = CONVERSATIONS[conversation_id]
    user_message = request.message.lower().strip()
    
    # 🔧 Limpiar conversaciones con configuración anterior (una sola vez al servidor iniciar)
    if conversation.get("min_questions", 3) == 3:
        print(f"🔧 Clearing old conversations and resetting")
        CONVERSATIONS.clear()
        raise HTTPException(status_code=404, detail="Conversación reiniciada - por favor inicie una nueva")
    
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
            response=f"Disculpe, ha ocurrido un error interno: {str(e)}. Por favor, intente de nuevo o reinicie la conversación.",
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
        
        response_text = "¡Perfecto! Gracias por otorgar su consentimiento.\n\n⚠️ **RECORDATORIO**: Soy DiagnostiCAT, un asistente de IA. Esta conversación NO sustituye una consulta médica profesional real.\n\nAhora puedo ayudarle a recopilar información médica básica para fines informativos.\n\nVoy a hacerle algunas preguntas para entender mejor su situación. ¿Cuál es el síntoma principal o la razón de su consulta?\n\n🏥 **Importante**: Para diagnóstico y tratamiento reales, consulte siempre a un médico certificado."
        
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
            suggestions=[],
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
    interview_text = "ENTREVISTA CONVERSACIONAL COMPLETADA:\n"
    
    # Manejar tanto diccionarios como listas
    if isinstance(symptoms_data, dict):
        for i, (question, answer) in enumerate(symptoms_data.items(), 1):
            if question in ["motivo_consulta", "inicio_sintomas", "intensidad", "antecedentes_medicos", 
                           "medicamentos_actuales", "antecedentes_familiares", "habitos_relevantes"]:
                interview_text += f"{i}. {question.replace('_', ' ').title()}: {answer}\n"
    elif isinstance(symptoms_data, list):
        # Procesar lista de síntomas recopilados
        questions_map = {
            0: "Motivo Consulta",
            1: "Inicio Sintomas", 
            2: "Intensidad",
            3: "Factores Agravantes/Mejorantes",
            4: "Síntomas Adicionales",
            5: "Medicamentos Actuales",
            6: "Antecedentes Medicos"
        }
        
        for i, symptom in enumerate(symptoms_data):
            question_type = questions_map.get(i, f"Información {i+1}")
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
                    
                    # Verificar que sea una pregunta válida (debe contener ¿ y ?)
                    if ('?' in question and '¿' in question and 
                        len(question) > 10):  # Preguntas válidas deben tener longitud mínima
                        
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
                "Requiere análisis médico más detallado",
                "Se necesita más información específica",
                "Evaluación médica presencial recomendada"
            ]
        
        if len(questions) == 0:
            print("⚠️  No se encontraron preguntas del agente")
            questions = [
                "¿Puede proporcionar más detalles sobre la localización de sus síntomas?",
                "¿Los síntomas varían en intensidad durante el día?",
                "¿Ha notado factores que mejoren o empeoren su condición?",
                "¿Tiene antecedentes de condiciones similares?",
                "¿Cómo describiría la progresión de sus síntomas?"
            ]
        
        # Asegurar exactamente 3 hipótesis y 5 preguntas
        return hypotheses[:3], questions[:5]
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO en parseo: {e}")
        print(f"📄 Contenido que causó error:\n{analysis_result}")
        # Solo en caso de error crítico
        return [
            "Error en el procesamiento del agente",
            "Se requiere reinicio del análisis", 
            "Consulta técnica pendiente"
        ], [
            "¿Puede reintentar describir sus síntomas?",
            "¿Hay algún detalle adicional que pueda proporcionar?",
            "¿Considera que falta información importante?",
            "¿Puede especificar más sobre su condición actual?",
            "¿Qué aspectos considera más relevantes de su caso?"
        ]


def format_hypotheses_display(hypotheses: List[str]) -> str:
    """Formatea las hipótesis para mostrar al usuario"""
    formatted = ""
    for i, hypothesis in enumerate(hypotheses, 1):
        formatted += f"{i}. {hypothesis}\n"
    return formatted.strip()


async def handle_specific_questions_fallback(conversation_id: str, message: str) -> ChatResponse:
    """Función de respaldo si el agente de CrewAI falla"""
    conversation = CONVERSATIONS[conversation_id]
    
    # Usar lógica simple de respaldo
    fallback_hypotheses = [
        "Posible condición inflamatoria basada en síntomas reportados",
        "Síndrome relacionado con factores de estilo de vida",
        "Condición que requiere evaluación médica especializada"
    ]
    
    fallback_questions = [
        "¿Puede describir la intensidad de sus síntomas en una escala del 1 al 10?",
        "¿Los síntomas son constantes o van y vienen?",
        "¿Ha notado si algo específico desencadena o alivia sus síntomas?",
        "¿Tiene algún historial familiar de condiciones similares?",
        "¿Está tomando algún medicamento o suplemento actualmente?"
    ]
    
    conversation["preliminary_hypotheses"] = fallback_hypotheses
    conversation["specific_questions_list"] = fallback_questions
    conversation["specific_questions_max"] = 5
    conversation["specific_questions_asked"] = 1
    
    response_text = f"✅ **PREGUNTAS GENERALES COMPLETADAS**\n\nHe completado las preguntas generales. Ahora procederé con preguntas específicas:\n\n🎯 **Pregunta específica 1/5:**\n{fallback_questions[0]}"
    
    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,
        agent_type="specific_questions_analyst",
        confidence_score=0.8,
        severity_assessment="MEDIO",
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
            
            # 🧪 USAR AGENTE HÍBRIDO (NVIDIA/OpenAI)
            from app.crew.hybrid_agent import generate_questions_hybrid
            
            print(f"🧪 PROBANDO AGENTE HÍBRIDO (NVIDIA/OpenAI)...")
            hybrid_result = generate_questions_hybrid(interview_summary)
            
            if hybrid_result["success"]:
                print(f"✅ AGENTE HÍBRIDO FUNCIONÓ CON {hybrid_result['provider'].upper()}!")
                analysis_result = hybrid_result["content"]
                
                # 🐛 Logging para debugging (puedes eliminar esto luego)
                print(f"🤖 Resultado del agente {hybrid_result['provider']}:")
                print(f"� {analysis_result[:200]}..." if len(analysis_result) > 200 else analysis_result)
            else:
                print(f"❌ AGENTE HÍBRIDO FALLÓ, ERROR CRÍTICO...")
                raise Exception(f"Todos los agentes fallaron: {hybrid_result['error']}")
            
            # Parsear el resultado del agente
            hypotheses, questions = parse_agent_analysis(analysis_result)
            
            # Asegurar que siempre tengamos exactamente 5 preguntas
            backup_questions = [
                "¿Hay algún patrón temporal en sus síntomas (empeoran a ciertas horas del día)?",
                "¿Los síntomas se relacionan con actividades específicas o posiciones corporales?",
                "¿Ha notado algún factor que consistentemente mejore o empeore su condición?",
                "¿Tiene algún antecedente médico personal o familiar relevante para estos síntomas?",
                "¿Cómo afectan estos síntomas su vida diaria y actividades cotidianas?"
            ]
            
            # Completar hasta 5 preguntas si es necesario
            while len(questions) < 5:
                needed_index = len(questions)
                if needed_index < len(backup_questions):
                    questions.append(backup_questions[needed_index])
                else:
                    questions.append(f"¿Puede proporcionar más detalles sobre el aspecto #{needed_index + 1} de sus síntomas?")
            
            # Tomar solo las primeras 5 preguntas
            questions = questions[:5]
            
            print(f"✅ Usando {len(questions)} preguntas específicas (completadas si era necesario)")
            
            # Guardar hipótesis y preguntas en la conversación
            conversation["preliminary_hypotheses"] = hypotheses
            conversation["specific_questions_list"] = questions
            conversation["specific_questions_max"] = 5  # Siempre 5 preguntas
            
            # Tomar la primera pregunta
            current_question = questions[0] if questions else "¿Puede describir más detalles sobre sus síntomas?"
            conversation["specific_questions_asked"] = 1
            
            response_text = f"✅ **PREGUNTAS GENERALES COMPLETADAS**\n\nExcelente, he completado las preguntas generales y analizado su información inicial.\n\n**HIPÓTESIS PRELIMINARES:**\n{format_hypotheses_display(hypotheses)}\n\nAhora procederé con 5 preguntas específicas diseñadas por nuestro agente especializado:\n\n🎯 **Pregunta específica 1/5:**\n{current_question}"
            
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
            print(f"❌ ERROR: CrewAI agent failed: {e}")
            # Fallback a lógica simple si el agente falla
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
        
        response_text = f"🎯 **Pregunta específica {conversation['specific_questions_asked']}/5:**\n{current_question}"
        
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


async def handle_classification(conversation_id: str, message: str) -> ChatResponse:
    """Maneja la clasificación usando Hugging Face"""
    conversation = CONVERSATIONS[conversation_id]
    
    try:
        # Importar el servicio de clasificación
        from app.services.classification_service import classification_model
        
        # Preparar datos para clasificación (incluyendo respuestas específicas)
        structured_data = {
            "symptoms": conversation["symptoms_collected"],
            "chief_complaint": conversation["symptoms_collected"][0] if conversation["symptoms_collected"] else "consulta general",
            "messages": [msg["content"] for msg in conversation["messages"] if msg["role"] == MessageRole.USER],
            "questions_answered": conversation["questions_asked"],
            "specific_answers": conversation.get("specific_answers", []),
            "preliminary_hypotheses": conversation.get("preliminary_hypotheses", []),
            "total_information_points": len(conversation["symptoms_collected"]) + len(conversation.get("specific_answers", []))
        }
        
        # print(f"🔍 DEBUG: Iniciando clasificación con datos: {structured_data}")
        
        # Ejecutar clasificación
        classification_result = await classification_model.classify(structured_data)
        
        # print(f"🔍 DEBUG: Resultado de clasificación: {classification_result}")
        
        # Cambiar estado
        conversation["state"] = ConversationState.CLASSIFICATION_COMPLETE
        conversation["classification_result"] = classification_result
        
        # Crear respuesta con las 3 condiciones más probables
        response_text = await generate_diagnosis_summary(
            classification_result, 
            conversation["symptoms_collected"],
            conversation.get("preliminary_hypotheses", [])
        )
        
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
            suggestions=[],  # Sin sugerencias
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
        "¿Hay algo que haga que los síntomas empeoren o mejoren?",
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
    
    # Usar datos de clasificación Hugging Face si están disponibles (solo si no tenemos hipótesis de IA)
    if not ai_hypotheses and classification_result and "primary_category" in classification_result:
        primary_category = classification_result["primary_category"]
        confidence = classification_result.get("confidence_score", 0.5) * 100
        
        # Convertir categoria a nombre legible
        category_names = {
            "neurological": "Condición Neurológica",
            "cardiovascular": "Condición Cardiovascular", 
            "respiratory": "Condición Respiratoria",
            "gastrointestinal": "Condición Gastrointestinal",
            "musculoskeletal": "Condición Musculoesquelética",
            "dermatological": "Condición Dermatológica",
            "psychiatric": "Condición Psiquiátrica",
            "other": "Condición General"
        }
        
        main_condition = category_names.get(primary_category, "Condición Médica")
        possible_conditions[0] = {
            "name": main_condition,
            "probability": f"{confidence:.1f}%",
            "description": f"Clasificada por modelo Hugging Face - {classification_result.get('method', 'AI')}",
            "hf_verified": True
        }
        
        # Agregar categorías secundarias si existen
        secondary_categories = classification_result.get("secondary_categories", [])
        for i, sec_cat in enumerate(secondary_categories[:2], 1):  # Máximo 2 secundarias
            if i < len(possible_conditions):
                sec_name = category_names.get(sec_cat, "Condición Médica")
                remaining_prob = (1 - classification_result.get("confidence_score", 0.5)) * 100 / len(secondary_categories)
                possible_conditions[i] = {
                    "name": sec_name,
                    "probability": f"{remaining_prob:.1f}%",
                    "description": f"Categoría secundaria identificada por el modelo",
                    "hf_verified": True
                }
    
    # Si tenemos hipótesis de IA, agregar información del modelo Hugging Face como confirmación
    elif ai_hypotheses and classification_result and "confidence_score" in classification_result:
        hf_confidence = classification_result.get("confidence_score", 0.5) * 100
        primary_category = classification_result.get("primary_category", "")
        
        # Agregar nota sobre confirmación del modelo al final
        if possible_conditions:
            possible_conditions[0]["description"] += f" - Modelo Hugging Face: {hf_confidence:.1f}% de confianza en análisis"
    
    # Ordenar las condiciones por probabilidad (de mayor a menor)
    def extract_probability(condition):
        prob_str = condition['probability'].replace('%', '')
        try:
            return float(prob_str)
        except:
            return 0.0
    
    sorted_conditions = sorted(possible_conditions[:3], key=extract_probability, reverse=True)
    
    # Generar texto del análisis
    diagnosis_text = "Con base en la información que me ha proporcionado y el análisis realizado, estas son las probabilidades estimadas:\n\n"
    
    for i, condition in enumerate(sorted_conditions, 1):
        diagnosis_text += f"• **{condition['name']}**: {condition['probability']}\n"
    
    diagnosis_text += f"\n**Reflexión sobre su consulta:**\n"
    diagnosis_text += f"Agradezco la confianza que ha depositado en este sistema al compartir información tan personal sobre su salud. Entiendo que cuando experimentamos síntomas que nos preocupan, es natural buscar respuestas y orientación. "
    
    # Agregar comentario empático basado en síntomas
    all_symptoms = " ".join(symptoms_collected).lower()
    if any(word in all_symptoms for word in ['dolor', 'intenso', 'fuerte']):
        diagnosis_text += f"Comprendo que lidiar con dolor puede ser una experiencia muy desafiante y que afecta no solo su bienestar físico, sino también emocional. "
    elif any(word in all_symptoms for word in ['preocup', 'ansie', 'nervios']):
        diagnosis_text += f"Reconozco que los síntomas que está experimentando pueden generar ansiedad e incertidumbre. "
    else:
        diagnosis_text += f"Entiendo que cualquier cambio en nuestro bienestar puede generar inquietud. "
    
    diagnosis_text += f"Mi objetivo es brindarle información útil que complemente, mas no reemplace, la atención médica profesional.\n\n"
    diagnosis_text += f"Es importante aclarar que estas cifras son estimaciones estadísticas generadas por un modelo de inteligencia artificial y no constituyen un diagnóstico médico.\n\n"
    
    # Agregar recomendación personalizada y humana basada en los síntomas
    diagnosis_text += f"**Recomendaciones para su cuidado:**\n"
    
    if any(word in all_symptoms for word in ['dolor', 'intenso', 'fuerte', '8', '9', '10']):
        diagnosis_text += f"Dado el nivel de intensidad de sus síntomas, es fundamental que busque atención médica sin demora. Su bienestar es prioritario, y un profesional de la salud podrá realizar un examen físico completo y los estudios necesarios para brindarle el cuidado que merece. "
        diagnosis_text += f"No dude en acudir a un servicio de urgencias si los síntomas se intensifican."
    elif any(word in all_symptoms for word in ['fiebre', 'temperatura', 'escalofríos']):
        diagnosis_text += f"Los síntomas que presenta sugieren la necesidad de una evaluación médica pronta. Le recomiendo contactar a su médico de cabecera o acudir a un centro de salud para recibir la atención adecuada. "
        diagnosis_text += f"Mientras tanto, manténgase hidratado y descanse lo suficiente."
    else:
        diagnosis_text += f"Aunque sus síntomas pueden parecer menores, cada persona es única y merece atención personalizada. Le sugiero programar una cita con un profesional de la salud quien podrá realizar una evaluación integral. "
        diagnosis_text += f"Recuerde que cuidar de su salud es una inversión en su calidad de vida."
    
    diagnosis_text += f"\n\nFinalmente, quiero recordarle que usted conoce su cuerpo mejor que nadie. Si algo no se siente bien o si tiene dudas adicionales, no dude en buscar una segunda opinión médica. Su salud y tranquilidad son invaluables."
    
    return diagnosis_text


def generate_preliminary_hypotheses(symptoms_collected: List[str]) -> List[Dict[str, str]]:
    """Genera hipótesis preliminares basadas en los síntomas recopilados"""
    all_symptoms = " ".join(symptoms_collected).lower()
    hypotheses = []
    
    # Hipótesis basadas en síntomas neurológicos
    if any(word in all_symptoms for word in ['cabeza', 'dolor de cabeza', 'cefalea', 'mareo']):
        hypotheses.extend([
            {"name": "Cefalea tensional", "category": "neurological", "probability": "alta"},
            {"name": "Migraña", "category": "neurological", "probability": "media"},
            {"name": "Cefalea secundaria", "category": "neurological", "probability": "baja"}
        ])
    
    # Hipótesis basadas en síntomas respiratorios
    elif any(word in all_symptoms for word in ['tos', 'pecho', 'respirar', 'ahogo']):
        hypotheses.extend([
            {"name": "Infección respiratoria alta", "category": "respiratory", "probability": "alta"},
            {"name": "Bronquitis", "category": "respiratory", "probability": "media"},
            {"name": "Asma leve", "category": "respiratory", "probability": "baja"}
        ])
    
    # Hipótesis basadas en síntomas cardiovasculares
    elif any(word in all_symptoms for word in ['corazón', 'palpitaciones', 'pecho y dolor']):
        hypotheses.extend([
            {"name": "Taquicardia benigna", "category": "cardiovascular", "probability": "alta"},
            {"name": "Ansiedad cardíaca", "category": "cardiovascular", "probability": "media"},
            {"name": "Arritmia leve", "category": "cardiovascular", "probability": "baja"}
        ])
    
    # Hipótesis basadas en síntomas musculoesqueléticos
    elif any(word in all_symptoms for word in ['dolor', 'músculo', 'articulación', 'espalda', 'rodilla']):
        hypotheses.extend([
            {"name": "Dolor muscular", "category": "musculoskeletal", "probability": "alta"},
            {"name": "Artritis leve", "category": "musculoskeletal", "probability": "media"},
            {"name": "Lesión deportiva", "category": "musculoskeletal", "probability": "baja"}
        ])
    
    # Hipótesis generales si no se identifica categoría específica
    else:
        hypotheses.extend([
            {"name": "Malestar general", "category": "general", "probability": "alta"},
            {"name": "Síndrome viral", "category": "general", "probability": "media"},
            {"name": "Fatiga crónica", "category": "general", "probability": "baja"}
        ])
    
    return hypotheses[:3]  # Máximo 3 hipótesis


def generate_specific_question(symptoms_collected: List[str], hypotheses: List[Dict], question_number: int) -> str:
    """Genera preguntas específicas basadas en síntomas e hipótesis"""
    
    all_symptoms = " ".join(symptoms_collected).lower()
    
    # Preguntas específicas basadas en la categoría principal de hipótesis
    main_category = hypotheses[0]["category"] if hypotheses else "general"
    
    neurological_questions = [
        "¿El dolor de cabeza se localiza en un área específica o es generalizado?",
        "¿Ha notado cambios en su visión, sensibilidad a la luz o náuseas?",
        "¿El dolor empeora con el movimiento o permanece constante?",
        "¿Ha tenido episodios similares en el pasado? ¿Con qué frecuencia?",
        "¿Hay factores específicos que desencadenan el dolor (estrés, ciertos alimentos, falta de sueño)?"
    ]
    
    respiratory_questions = [
        "¿La tos es seca o produce flemas? ¿De qué color?",
        "¿Siente dificultad para respirar en reposo o solo al hacer esfuerzo?",
        "¿Ha tenido fiebre o escalofríos junto con estos síntomas?",
        "¿Los síntomas empeoran en ciertos momentos del día?",
        "¿Ha estado expuesto a irritantes, alérgenos o personas enfermas recientemente?"
    ]
    
    cardiovascular_questions = [
        "¿Las palpitaciones ocurren en reposo o durante actividad física?",
        "¿Ha sentido dolor en el pecho, mareos o desmayos?",
        "¿Nota que el ritmo cardíaco es irregular o solo rápido?",
        "¿Los episodios duran segundos, minutos u horas?",
        "¿Consume cafeína, alcohol o algún medicamento regularmente?"
    ]
    
    musculoskeletal_questions = [
        "¿El dolor aparece con el movimiento o también en reposo?",
        "¿Hay hinchazón, enrojecimiento o calor en la zona afectada?",
        "¿Ha tenido alguna lesión reciente o ha hecho ejercicio intenso?",
        "¿El dolor se irradia hacia otras partes del cuerpo?",
        "¿Qué posiciones o movimientos alivian o empeoran el dolor?"
    ]
    
    general_questions = [
        "¿Ha notado cambios en su apetito, peso o patrones de sueño?",
        "¿Tiene antecedentes familiares de condiciones médicas similares?",
        "¿Está tomando algún medicamento o suplemento actualmente?",
        "¿Ha viajado recientemente o cambiado su rutina habitual?",
        "¿Hay algo más que considere relevante sobre sus síntomas?"
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
        return True, "Necesitamos información mínima"
    
    # Analizar si las respuestas han sido informativas
    context_text = " ".join(adaptive_context)
    
    # Si las respuestas son muy cortas o poco informativas, seguir preguntando
    if len(context_text) < 50 and questions_asked < 4:
        return True, "Respuestas demasiado breves, necesitamos más detalles"
    
    # Si detectamos síntomas preocupantes, hacer más preguntas
    concerning_symptoms = ['sangre', 'desmayo', 'pecho', 'respirar', 'corazón', 'vision', 'paralisis', 'entumecimiento']
    if any(symptom in context_text for symptom in concerning_symptoms) and questions_asked < 4:
        return True, "Síntomas que requieren más investigación detectados"
    
    # Si tenemos información suficiente y clara, proceder al diagnóstico
    if questions_asked >= 3 and len(context_text) > 100:
        return False, "Suficiente información recopilada para análisis"
    
    # Por defecto, hacer al menos 3 preguntas específicas
    if questions_asked < 3:
        return True, "Información básica específica requerida"
    
    return False, "Criterios de información completos"


def generate_adaptive_question(symptoms: List[str], hypotheses: List[Dict], context: List[str], question_num: int) -> str:
    """Genera preguntas específicas adaptativas basadas en respuestas anteriores"""
    
    # Obtener la categoría principal de la hipótesis
    main_category = hypotheses[0]["category"] if hypotheses else "general"
    context_text = " ".join(context).lower()
    
    # Preguntas adaptativas basadas en respuestas anteriores
    if question_num == 1:
        # Primera pregunta específica - siempre sobre localización/características
        if main_category == "neurological":
            return "¿El dolor de cabeza se localiza en un área específica (frente, sienes, nuca) o es generalizado por toda la cabeza?"
        elif main_category == "respiratory":
            return "¿La dificultad respiratoria o tos se presenta en reposo o solo durante actividad física?"
        elif main_category == "cardiovascular":
            return "¿Las palpitaciones o molestias en el pecho ocurren durante el reposo o al hacer esfuerzo?"
        elif main_category == "musculoskeletal":
            return "¿El dolor se presenta solo con el movimiento o también cuando está en reposo?"
        else:
            return "¿Podría describir con más detalle las características específicas de su síntoma principal?"
    
    elif question_num == 2:
        # Segunda pregunta - adaptada a la primera respuesta
        if "movimiento" in context_text or "actividad" in context_text:
            return "¿Hay algún movimiento o posición específica que alivie o empeore significativamente los síntomas?"
        elif "reposo" in context_text or "descanso" in context_text:
            return "¿Los síntomas mejoran con el reposo o persisten incluso cuando no está haciendo nada?"
        elif "localiza" in context_text or "área" in context_text:
            return "¿Ha notado si el área afectada presenta hinchazón, enrojecimiento, calor o cambios visibles?"
        else:
            return "¿Ha notado algún patrón en cuanto a cuándo los síntomas son más intensos (hora del día, situaciones específicas)?"
    
    elif question_num == 3:
        # Tercera pregunta - buscar síntomas acompañantes o factores agravantes
        if any(word in context_text for word in ['dolor', 'molesta', 'duele']):
            return "¿Experimenta otros síntomas junto con el dolor, como náuseas, mareos, cambios en la visión o sensibilidad?"
        elif any(word in context_text for word in ['mejor', 'alivia', 'mejora']):
            return "¿Ha probado algún tratamiento, medicamento o remedio casero? ¿Cuál ha sido el resultado?"
        else:
            return "¿Ha notado algo específico que desencadene o empeore estos síntomas (comida, estrés, clima, actividades)?"
    
    elif question_num == 4:
        # Cuarta pregunta - antecedentes y contexto médico
        if "medicamento" in context_text or "tratamiento" in context_text:
            return "¿Tiene antecedentes familiares de condiciones similares o está tomando algún medicamento regularmente?"
        elif any(word in context_text for word in ['estrés', 'trabajo', 'sueño']):
            return "¿Ha habido cambios recientes en su rutina, nivel de estrés, alimentación o patrones de sueño?"
        else:
            return "¿Es la primera vez que experimenta estos síntomas o ha tenido episodios similares anteriormente?"
    
    else:
        # Pregunta final - información adicional importante
        return "¿Hay algún detalle adicional sobre sus síntomas que considere importante mencionar o que no hayamos cubierto?"