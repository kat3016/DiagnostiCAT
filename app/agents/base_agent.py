"""
Agente base para todos los agentes médicos
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time
import uuid
from datetime import datetime

from app.models.medical_models import MessageModel, Severity
from app.models.agent_models import AgentType, AgentResponse


class BaseAgent(ABC):
    """Clase base abstracta para todos los agentes médicos"""

    def __init__(
        self,
        name: str,
        agent_type: AgentType,
        system_prompt: str,
        specialties: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.name = name
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.specialties = specialties or []
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.created_at = datetime.now()
        self.conversation_count = 0

    @abstractmethod
    async def process_message(
        self,
        message: str,
        conversation_history: List[MessageModel],
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """Procesa un mensaje y genera una respuesta"""
        raise NotImplementedError

    @abstractmethod
    async def assess_urgency(self, message: str, context: Dict[str, Any]) -> Severity:
        """Evalúa la urgencia médica del mensaje usando LLM"""
        raise NotImplementedError

    def _prepare_conversation_context(
        self,
        conversation_history: List[MessageModel],
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Prepara el contexto de conversación para el modelo de IA"""
        context_parts = [self.system_prompt]

        if patient_context:
            context_parts.append("\n--- CONTEXTO DEL PACIENTE ---")
            for key, value in patient_context.items():
                if value:
                    context_parts.append(f"{key.upper()}: {value}")

        if conversation_history:
            context_parts.append("\n--- HISTORIAL DE CONVERSACIÓN ---")
            for msg in conversation_history[-10:]:
                role = msg.role.upper()
                context_parts.append(f"{role}: {msg.content}")

        return "\n".join(context_parts)

    def _calculate_confidence_score(
        self, response: str, message_length: int, has_context: bool
    ) -> float:
        base_score = 0.7
        if len(response) > 100:
            base_score += 0.1
        if len(response) > 300:
            base_score += 0.1
        if has_context:
            base_score += 0.1
        medical_keywords = [
            "síntoma",
            "diagnóstico",
            "tratamiento",
            "medicamento",
            "consulta",
            "médico",
            "doctor",
            "hospital",
            "clínica",
        ]
        keyword_count = sum(
            1 for keyword in medical_keywords if keyword in response.lower()
        )
        base_score += min(keyword_count * 0.02, 0.1)
        return min(base_score, 1.0)

    def get_info(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.agent_type.value,
            "specialties": self.specialties,
            "created_at": self.created_at.isoformat(),
            "conversation_count": self.conversation_count,
        }


