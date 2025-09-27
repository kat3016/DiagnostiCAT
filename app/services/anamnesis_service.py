"""
Servicio para gestionar el flujo de anamnesis estructurada.
"""

from typing import Dict, Any, List

from app.models.medical_models import AnamnesisRequest, AnamnesisStructured


class AnamnesisState:
    """Mantiene el estado temporal por conversación en memoria."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, conversation_id: str) -> Dict[str, Any]:
        return self._store.setdefault(conversation_id, {})

    def update(self, conversation_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        state = self.get(conversation_id)
        state.update(data)
        return state

    def clear(self, conversation_id: str) -> None:
        self._store.pop(conversation_id, None)


class AnamnesisService:
    """Orquestra preguntas y estructura respuestas."""

    QUESTIONS = [
        ("motivo_consulta", "¿Cuál es el motivo principal de tu consulta?"),
        (
            "enfermedad_actual",
            "Sobre tu síntoma principal: ¿cuál es?, ¿cuándo inició? y ¿qué características tiene?"
        ),
        ("antecedentes_personales", "¿Tienes antecedentes personales relevantes? (lista)"),
        ("antecedentes_familiares", "¿Antecedentes familiares relevantes? (lista)"),
        (
            "habitos",
            "Hábitos: ¿fumas? ¿consumes alcohol? ¿otros hábitos importantes?"
        ),
        ("sintomas_asociados", "¿Qué otros síntomas acompañan a tu motivo principal? (lista)"),
    ]

    def __init__(self) -> None:
        self.state = AnamnesisState()

    def next_question(self, conversation_id: str) -> Dict[str, Any]:
        state = self.state.get(conversation_id)
        for key, question in self.QUESTIONS:
            if key not in state:
                return {"key": key, "question": question}
        return {"done": True}

    def submit_answer(self, conversation_id: str, key: str, value: Any) -> Dict[str, Any]:
        return self.state.update(conversation_id, {key: value})

    def build_structured(self, conversation_id: str) -> AnamnesisStructured:
        state = self.state.get(conversation_id)
        structured = AnamnesisStructured(
            motivo_consulta=state.get("motivo_consulta", ""),
            enfermedad_actual=state.get("enfermedad_actual", {}),
            antecedentes_personales=state.get("antecedentes_personales", []) or [],
            antecedentes_familiares=state.get("antecedentes_familiares", []) or [],
            habitos=state.get("habitos", {}) or {},
            sintomas_asociados=state.get("sintomas_asociados", []) or [],
        )
        return structured

    def reset(self, conversation_id: str) -> None:
        self.state.clear(conversation_id)


anamnesis_service = AnamnesisService()


