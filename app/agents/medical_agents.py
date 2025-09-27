"""
Implementaciones específicas de agentes médicos (sin dependencias externas).
"""

from typing import List, Dict, Any, Optional
import time

from app.agents.base_agent import BaseAgent
from app.models.medical_models import MessageModel, Severity
from app.models.agent_models import AgentType, AgentResponse


class GeneralPractitionerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Dr. García - Médico General",
            agent_type=AgentType.GENERAL_PRACTITIONER,
            system_prompt=(
                "Eres un médico general experimentado. Guía con preguntas y orientación inicial."
            ),
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
        context = self._prepare_conversation_context(conversation_history, patient_context)

        response_text = self._rule_based_response(message)
        processing_time = time.time() - start_time
        confidence_score = self._calculate_confidence_score(
            response_text, len(message), bool(patient_context)
        )
        self.conversation_count += 1
        return AgentResponse(
            agent_id=self.id,
            agent_type=self.agent_type,
            response_text=response_text,
            confidence_score=confidence_score,
            processing_time=processing_time,
            tokens_used=len(response_text.split()),
        )

    def _rule_based_response(self, message: str) -> str:
        msg = message.lower()
        if any(w in msg for w in ["dolor", "duele", "molestia"]):
            return (
                "Entiendo que presentas dolor. Para orientarte mejor: "
                "¿dónde se localiza?, ¿desde cuándo?, ¿cómo lo describirías?, "
                "¿qué lo empeora o mejora?, y del 1 al 10 ¿qué intensidad tiene?"
            )
        if any(w in msg for w in ["fiebre", "temperatura", "calentura"]):
            return (
                "Sobre la fiebre: ¿qué temperatura exacta tienes?, ¿desde cuándo?, "
                "¿hay otros síntomas?, ¿tomaste algún medicamento?"
            )
        if any(w in msg for w in ["tos", "toser", "expectoración"]):
            return (
                "Para evaluar la tos necesito saber: si es seca o con flemas, "
                "¿cuánto tiempo llevas?, ¿empeora en algún momento?, y si hay "
                "síntomas como fiebre o dificultad para respirar."
            )
        return (
            "Gracias por tu consulta. Para darte una mejor orientación, indícame: "
            "síntoma principal, inicio, características, factores que lo modifican, "
            "antecedentes relevantes y medicamentos actuales."
        )

    def assess_urgency(self, message: str, context: Dict[str, Any]) -> Severity:
        m = message.lower()
        high = [
            "dolor pecho",
            "no puedo respirar",
            "desmayo",
            "sangrado abundante",
            "pérdida de conciencia",
            "convulsión",
        ]
        medium = ["fiebre alta", "vómito", "dolor fuerte", "sangrado", "mareo"]
        if any(k in m for k in high):
            return Severity.HIGH
        if any(k in m for k in medium):
            return Severity.MEDIUM
        return Severity.LOW


class TriageNurseAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Enfermera Ana - Triaje",
            agent_type=AgentType.TRIAGE_NURSE,
            system_prompt=(
                "Eres una enfermera de triaje que clasifica urgencias de forma empática y clara."
            ),
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
        severity = self.assess_urgency(message, patient_context or {})
        response_text = self._triage_response(severity)
        processing_time = time.time() - start_time
        confidence_score = self._calculate_confidence_score(
            response_text, len(message), bool(patient_context)
        )
        self.conversation_count += 1
        return AgentResponse(
            agent_id=self.id,
            agent_type=self.agent_type,
            response_text=response_text,
            confidence_score=confidence_score,
            processing_time=processing_time,
            tokens_used=len(response_text.split()),
        )

    def _triage_response(self, severity: Severity) -> str:
        if severity in (Severity.CRITICAL, Severity.HIGH):
            return (
                "EVALUACIÓN: ALTA/CRÍTICA. Recomendación: busca atención inmediata en emergencias "
                "o llama al 911. Prioriza seguridad y compañía."
            )
        if severity == Severity.MEDIUM:
            return (
                "EVALUACIÓN: MEDIA. Programa consulta en las próximas horas, monitorea síntomas y "
                "si empeoran acude a urgencias."
            )
        return (
            "EVALUACIÓN: BAJA. Programa consulta de rutina y aplica medidas de autocuidado."
        )

    def assess_urgency(self, message: str, context: Dict[str, Any]) -> Severity:
        m = message.lower()
        critical = [
            "no puedo respirar",
            "dolor pecho severo",
            "perdí el conocimiento",
            "sangrado masivo",
            "convulsiones",
        ]
        high = ["dolor pecho", "dificultad respirar", "sangrado abundante", "dolor abdominal severo"]
        medium = ["fiebre", "vómito persistente", "dolor intenso", "mareo fuerte"]
        if any(k in m for k in critical):
            return Severity.CRITICAL
        if any(k in m for k in high):
            return Severity.HIGH
        if any(k in m for k in medium):
            return Severity.MEDIUM
        return Severity.LOW


