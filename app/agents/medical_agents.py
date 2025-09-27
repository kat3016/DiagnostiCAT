"""
Implementaciones específicas de agentes médicos con Nemotron.
"""

from typing import List, Dict, Any, Optional
import time

from app.agents.base_agent import BaseAgent
from app.models.medical_models import MessageModel, Severity
from app.models.agent_models import AgentType, AgentResponse
from app.services.llm_service import llm_service


class GeneralPractitionerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Dr. García - Médico General",
            agent_type=AgentType.GENERAL_PRACTITIONER,
            system_prompt="""Eres el Dr. García, un médico general experimentado y empático con 15 años de experiencia en atención primaria.

Tu objetivo es:
1. Escuchar atentamente las preocupaciones del paciente
2. Realizar una anamnesis estructurada mediante preguntas específicas
3. Proporcionar orientación médica inicial responsable
4. Identificar signos de alarma que requieran atención urgente
5. Recomendar consulta presencial cuando sea necesario

IMPORTANTE:
- Nunca des diagnósticos definitivos por chat
- Siempre recomienda evaluación presencial para síntomas serios
- Mantén un tono profesional, cálido y empático
- Haz preguntas específicas sobre síntomas: localización, duración, intensidad, factores que mejoran/empeoran
- Considera siempre el contexto del paciente (edad, antecedentes, medicamentos)

Responde en español de manera clara y comprensible para cualquier paciente.""",
            specialties=["Medicina General", "Atención Primaria", "Prevención"],
            temperature=0.7,
            max_tokens=800,
        )

    async def process_message(
        self,
        message: str,
        conversation_history: List[MessageModel],
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        start_time = time.time()
        
        # Preparar historial para LLM
        llm_history = []
        for msg in conversation_history[-5:]:  # Últimos 5 mensajes
            llm_history.append({
                "role": "user" if msg.role == "user" else "assistant",
                "content": msg.content
            })
        
        # Agregar contexto del paciente al prompt si existe
        enhanced_prompt = self.system_prompt
        if patient_context:
            context_info = []
            for key, value in patient_context.items():
                if value:
                    context_info.append(f"{key}: {value}")
            if context_info:
                enhanced_prompt += f"\n\nCONTEXTO DEL PACIENTE:\n" + "\n".join(context_info)
        
        # Llamar al servicio LLM
        llm_response = await llm_service.generate_response(
            system_prompt=enhanced_prompt,
            user_message=message,
            conversation_history=llm_history
        )
        
        processing_time = time.time() - start_time
        confidence_score = self._calculate_confidence_score(
            llm_response["response"], len(message), bool(patient_context)
        )
        
        self.conversation_count += 1
        
        return AgentResponse(
            agent_id=self.id,
            agent_type=self.agent_type,
            response_text=llm_response["response"],
            confidence_score=confidence_score,
            processing_time=processing_time,
            tokens_used=llm_response["tokens_used"],
        )


    async def assess_urgency(self, message: str, context: Dict[str, Any]) -> Severity:
        """Evalúa urgencia usando LLM en lugar de palabras clave"""
        
        urgency_prompt = """Eres un médico experto en triaje. Evalúa ÚNICAMENTE el nivel de urgencia médica basándote en los síntomas descritos.

NIVELES DE URGENCIA:
- CRITICAL: Riesgo de vida inmediato (paro cardíaco, dificultad respiratoria severa, pérdida de consciencia, sangrado masivo)
- HIGH: Requiere atención urgente <1 hora (dolor torácico, dificultad respirar moderada, sangrado abundante, dolor abdominal severo)
- MEDIUM: Puede esperar pero necesita atención <4 horas (fiebre alta, vómitos persistentes, dolor intenso)
- LOW: No urgente, puede programarse (síntomas leves, consultas rutinarias)

Responde SOLO con una palabra: CRITICAL, HIGH, MEDIUM o LOW.

No des explicaciones, no hagas preguntas, solo evalúa la urgencia."""

        context_info = ""
        if context:
            context_parts = []
            for key, value in context.items():
                if value:
                    context_parts.append(f"{key}: {value}")
            if context_parts:
                context_info = f"\nContexto del paciente: {', '.join(context_parts)}"

        full_message = f"Síntomas: {message}{context_info}"
        
        try:
            llm_response = await llm_service.generate_response(
                system_prompt=urgency_prompt,
                user_message=full_message,
                conversation_history=[]
            )
            
            urgency_text = llm_response["response"].strip().upper()
            
            # Mapear respuesta a enum
            if "CRITICAL" in urgency_text:
                return Severity.CRITICAL
            elif "HIGH" in urgency_text:
                return Severity.HIGH
            elif "MEDIUM" in urgency_text:
                return Severity.MEDIUM
            else:
                return Severity.LOW
                
        except Exception:
            # Solo en caso de error técnico, usar evaluación básica
            m = message.lower()
            if any(k in m for k in ["no puedo respirar", "dolor pecho severo", "perdí conocimiento"]):
                return Severity.HIGH
            elif any(k in m for k in ["dolor pecho", "fiebre alta", "sangrado"]):
                return Severity.MEDIUM
            else:
                return Severity.LOW


class TriageNurseAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Enfermera Ana - Triaje",
            agent_type=AgentType.TRIAGE_NURSE,
            system_prompt="""Eres Ana, una enfermera especializada en triaje con 10 años de experiencia en servicios de urgencias.

Tu función principal es:
1. Evaluar rápidamente la urgencia de los síntomas del paciente
2. Clasificar la prioridad de atención médica
3. Determinar si requiere atención INMEDIATA, programada, o puede esperar
4. Recopilar información vital básica de forma eficiente
5. Tranquilizar al paciente mientras evalúas la situación

CLASIFICACIÓN DE PRIORIDAD:
- CRÍTICO/ROJO: Riesgo de vida inmediato (dolor pecho severo, dificultad respirar grave, pérdida consciencia)
- ALTO/NARANJA: Requiere atención urgente < 1 hora (dolor intenso, sangrado moderado, fiebre alta)
- MEDIO/AMARILLO: Puede esperar pero necesita atención < 4 horas (síntomas moderados)
- BAJO/VERDE: No urgente, puede programarse (síntomas leves, consultas rutinarias)

IMPORTANTE:
- Sé directa pero empática
- Ante cualquier duda de gravedad, escalá a prioridad mayor
- Siempre pregunta por signos vitales básicos cuando sea relevante
- Recomienda llamar al 911 para casos críticos

Responde en español de manera clara, profesional y tranquilizadora.""",
            specialties=["Triaje", "Urgencias"],
            temperature=0.6,
            max_tokens=600,
        )

    async def process_message(
        self,
        message: str,
        conversation_history: List[MessageModel],
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        start_time = time.time()
        
        # Preparar historial para LLM
        llm_history = []
        for msg in conversation_history[-5:]:
            llm_history.append({
                "role": "user" if msg.role == "user" else "assistant",
                "content": msg.content
            })
        
        # Evaluar urgencia usando LLM
        severity = await self.assess_urgency(message, patient_context or {})
        
        # Agregar contexto del paciente y urgencia al prompt
        enhanced_prompt = self.system_prompt
        if patient_context:
            context_info = []
            for key, value in patient_context.items():
                if value:
                    context_info.append(f"{key}: {value}")
            if context_info:
                enhanced_prompt += f"\n\nCONTEXTO DEL PACIENTE:\n" + "\n".join(context_info)
        
        enhanced_prompt += f"\n\nEVALUACIÓN INICIAL DE URGENCIA: {severity.value.upper()}"
        enhanced_prompt += "\nBasa tu respuesta en esta evaluación inicial, pero puedes ajustarla si detectas otros factores importantes."
        
        # Llamar al servicio LLM
        llm_response = await llm_service.generate_response(
            system_prompt=enhanced_prompt,
            user_message=message,
            conversation_history=llm_history
        )
        
        processing_time = time.time() - start_time
        confidence_score = self._calculate_confidence_score(
            llm_response["response"], len(message), bool(patient_context)
        )
        
        self.conversation_count += 1
        
        return AgentResponse(
            agent_id=self.id,
            agent_type=self.agent_type,
            response_text=llm_response["response"],
            confidence_score=confidence_score,
            processing_time=processing_time,
            tokens_used=llm_response["tokens_used"],
        )

    async def assess_urgency(self, message: str, context: Dict[str, Any]) -> Severity:
        """Evalúa urgencia usando LLM especializado en triaje"""
        
        triage_prompt = """Eres una enfermera experta en triaje de emergencias con 15 años de experiencia. Evalúa ÚNICAMENTE el nivel de urgencia.

PROTOCOLO DE TRIAJE:
- CRITICAL (ROJO): Riesgo de vida inmediato - requiere atención en <15 minutos
  * Paro cardiorespiratorio, shock, pérdida de consciencia, sangrado masivo, dificultad respiratoria severa
- HIGH (NARANJA): Urgente - requiere atención en <1 hora  
  * Dolor torácico, dificultad respirar moderada, sangrado abundante, dolor abdominal severo, fiebre >40°C
- MEDIUM (AMARILLO): Puede esperar - atención en <4 horas
  * Fiebre alta, vómitos persistentes, dolor intenso pero estable, heridas moderadas
- LOW (VERDE): No urgente - puede programarse
  * Síntomas leves, consultas rutinarias, seguimientos

Considera edad, antecedentes médicos y contexto. Ante duda, escala a mayor prioridad.

Responde SOLO: CRITICAL, HIGH, MEDIUM o LOW"""

        context_info = ""
        if context:
            context_parts = []
            for key, value in context.items():
                if value:
                    context_parts.append(f"{key}: {value}")
            if context_parts:
                context_info = f"\nDatos del paciente: {', '.join(context_parts)}"

        full_message = f"Consulta: {message}{context_info}"
        
        try:
            llm_response = await llm_service.generate_response(
                system_prompt=triage_prompt,
                user_message=full_message,
                conversation_history=[]
            )
            
            urgency_text = llm_response["response"].strip().upper()
            
            if "CRITICAL" in urgency_text:
                return Severity.CRITICAL
            elif "HIGH" in urgency_text:
                return Severity.HIGH
            elif "MEDIUM" in urgency_text:
                return Severity.MEDIUM
            else:
                return Severity.LOW
                
        except Exception:
            # Fallback mínimo solo por error técnico
            m = message.lower()
            if any(k in m for k in ["no respira", "inconsciente", "sangrado masivo"]):
                return Severity.CRITICAL
            elif any(k in m for k in ["dolor pecho", "no puedo respirar"]):
                return Severity.HIGH
            else:
                return Severity.MEDIUM


