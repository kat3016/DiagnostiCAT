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

    async def summarize_and_followups(self, anamnesis_json: Dict[str, Any]) -> Dict[str, Any]:
        """Devuelve resumen y preguntas de seguimiento usando LLM obligatorio."""
        
        if not self.enabled:
            raise ValueError("CrewAI no está habilitado. Configure NVIDIA_API_KEY o OPENAI_API_KEY y CREW_ENABLE=True")

        # Usar LLM directamente para el resumen y seguimiento
        from app.services.llm_service import llm_service
        
        summary_prompt = """Eres un médico especialista en medicina interna. Analiza la anamnesis completa y genera:

1. Un resumen clínico conciso en 3-4 líneas que destaque los puntos más relevantes
2. Exactamente 3 preguntas de seguimiento específicas y pertinentes para profundizar en el caso

Formato de respuesta:
RESUMEN: [tu resumen aquí]
PREGUNTAS:
1. [pregunta específica]
2. [pregunta específica] 
3. [pregunta específica]

Sé preciso, profesional y enfócate en lo clínicamente relevante."""

        anamnesis_text = f"""
ANAMNESIS COMPLETA:
Motivo de consulta: {anamnesis_json.get('motivo_consulta', 'No especificado')}

Enfermedad actual: {anamnesis_json.get('enfermedad_actual', {})}

Antecedentes personales: {', '.join(anamnesis_json.get('antecedentes_personales', []))}

Antecedentes familiares: {', '.join(anamnesis_json.get('antecedentes_familiares', []))}

Hábitos: {anamnesis_json.get('habitos', {})}

Síntomas asociados: {', '.join(anamnesis_json.get('sintomas_asociados', []))}
"""

        try:
            llm_response = await llm_service.generate_response(
                system_prompt=summary_prompt,
                user_message=anamnesis_text,
                conversation_history=[]
            )
            
            response_text = llm_response["response"]
            
            # Extraer resumen y preguntas
            lines = response_text.split('\n')
            summary = ""
            questions = []
            
            in_questions = False
            for line in lines:
                line = line.strip()
                if line.startswith("RESUMEN:"):
                    summary = line.replace("RESUMEN:", "").strip()
                elif line.startswith("PREGUNTAS:"):
                    in_questions = True
                elif in_questions and line and (line.startswith(("1.", "2.", "3.")) or line.startswith("•")):
                    # Limpiar numeración
                    question = line.replace("1.", "").replace("2.", "").replace("3.", "").replace("•", "").strip()
                    if question:
                        questions.append(question)
            
            # Fallback si no se extrajo correctamente
            if not summary:
                summary = response_text[:300] + "..." if len(response_text) > 300 else response_text
            
            if not questions:
                questions = [
                    "¿Puedes describir con más detalle la evolución temporal de los síntomas?",
                    "¿Hay factores específicos que mejoren o empeoren tu condición?",
                    "¿Has tenido episodios similares anteriormente?"
                ]
            
            return {
                "summary": summary,
                "follow_up_questions": questions[:3]  # Máximo 3
            }
            
        except Exception as e:
            raise Exception(f"Error generando resumen médico: {str(e)}")


crew_orchestrator = CrewOrchestrator()


