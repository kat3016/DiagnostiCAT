"""
Integración básica con CrewAI (opcional). Si CrewAI no está disponible, se usa un stub.
"""

from typing import Any, Dict
from app.core.config import settings

try:
    from crewai import Agent as CrewAgent, Task as CrewTask, Crew
    CREW_AVAILABLE = True
except Exception:
    CREW_AVAILABLE = False
    CrewAgent = CrewTask = Crew = None  # type: ignore


class CrewOrchestrator:
    """Orquesta una Crew para resumir y proponer preguntas de seguimiento."""

    def __init__(self) -> None:
        self.enabled = settings.CREW_ENABLE and CREW_AVAILABLE

        if self.enabled:
            self._init_crew()

    def _init_crew(self) -> None:
        system_prompt = (
            "Eres un asistente clínico que organiza la anamnesis y sugiere preguntas de seguimiento."
        )

        self.intake_agent = CrewAgent(
            role="clinical_intake",
            goal="Estructurar anamnesis y generar preguntas de seguimiento claras",
            backstory="Agente diseñado para entrevistas clínicas iniciales",
            verbose=False
        )

        self.intake_task = CrewTask(
            description=(
                "Dado un JSON con datos de anamnesis, devuelve un breve resumen en 4-6 líneas y 3-4 preguntas de seguimiento específicas."
            ),
            agent=self.intake_agent,
        )

        self.crew = Crew(agents=[self.intake_agent], tasks=[self.intake_task])

    def summarize_and_followups(self, anamnesis_json: Dict[str, Any]) -> Dict[str, Any]:
        """Devuelve resumen y preguntas de seguimiento a partir de la anamnesis."""
        if not self.enabled:
            # Stub: retorno simple sin LLM
            return {
                "summary": "Resumen no-LLM: datos recibidos correctamente.",
                "follow_up_questions": [
                    "¿Puedes detallar la intensidad del síntoma principal?",
                    "¿Desde cuándo inició y cómo ha evolucionado?",
                    "¿Qué factores lo mejoran o empeoran?"
                ]
            }

        # CrewAI real
        try:
            result = self.crew.kickoff(inputs={"anamnesis": anamnesis_json})
            text = str(result)
            # Extracción naive
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            summary = " ".join(lines[:5])[:800]
            followups = [l for l in lines if l.endswith("?")][:4]
            return {"summary": summary, "follow_up_questions": followups}
        except Exception:
            return {
                "summary": "Error al invocar CrewAI. Usando fallback.",
                "follow_up_questions": [
                    "¿Cuál es la localización del síntoma?",
                    "¿Qué características presenta? (punzante, opresivo, etc.)"
                ]
            }


crew_orchestrator = CrewOrchestrator()


