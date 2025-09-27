"""
CrewAI implementation for anamnesis conversacional flow
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from typing import List, Dict, Any
import yaml
import os
from datetime import datetime
import uuid

from app.core.config import settings
from app.crew.tools import classify_medical_data, validate_json_structure, format_medical_data_for_classification
from app.crew.llm_config import get_nemotron_llm, configure_crewai_llm
import os


@CrewBase
class AnamnesisConversacionalCrew:
    """Crew para flujo de anamnesis conversacional médica"""
    
    agents_config_path = os.path.join(os.path.dirname(__file__), 'config', 'agents.yaml')
    tasks_config_path = os.path.join(os.path.dirname(__file__), 'config', 'tasks.yaml')
    
    def __init__(self):
        # Configurar CrewAI para usar Nemotron
        configure_crewai_llm()
        
        # Crear instancia del LLM de Nemotron
        self.nemotron_llm = get_nemotron_llm()
        
        # Cargar configuraciones YAML
        with open(self.agents_config_path, 'r', encoding='utf-8') as f:
            self.agents_config = yaml.safe_load(f)
        
        with open(self.tasks_config_path, 'r', encoding='utf-8') as f:
            self.tasks_config = yaml.safe_load(f)
    
    @before_kickoff
    def before_kickoff_function(self, inputs):
        """Función ejecutada antes de iniciar el crew"""
        print(f"🚀 Iniciando flujo de anamnesis conversacional con inputs: {inputs}")
        
        # Agregar metadata
        inputs['patient_id'] = str(uuid.uuid4())
        inputs['session_start'] = datetime.now().isoformat()
        
        # Validar que consultation_topic esté presente
        if 'consultation_topic' not in inputs:
            inputs['consultation_topic'] = 'consulta médica general'
        
        return inputs
    
    @after_kickoff
    def after_kickoff_function(self, result):
        """Función ejecutada después de completar el crew"""
        print(f"✅ Flujo de anamnesis conversacional completado")
        print(f"📊 Resultado: {type(result)}")
        
        # Agregar timestamp de finalización
        if hasattr(result, 'raw'):
            completion_time = datetime.now().isoformat()
            print(f"🕒 Tiempo de finalización: {completion_time}")
        
        return result

    @agent
    def conversational_interviewer(self) -> Agent:
        """Agente para entrevista conversacional con preguntas fijas"""
        return Agent(
            config=self.agents_config['conversational_interviewer'],
            llm=self.nemotron_llm,  # Usar Nemotron directamente
            verbose=True,
            allow_delegation=False,
            max_execution_time=300  # 5 minutos máximo
        )

    @agent
    def specific_questions_analyst(self) -> Agent:
        """Agente para análisis y preguntas específicas"""
        return Agent(
            config=self.agents_config['specific_questions_analyst'],
            llm=self.nemotron_llm,  # Usar Nemotron directamente
            verbose=True,
            allow_delegation=False,
            max_execution_time=180  # 3 minutos máximo
        )

    @agent
    def json_data_structurer(self) -> Agent:
        """Agente para estructuración JSON y comunicación con modelo de clasificación"""
        return Agent(
            config=self.agents_config['json_data_structurer'],
            llm=self.nemotron_llm,  # Usar Nemotron directamente
            verbose=True,
            allow_delegation=False,
            max_execution_time=300,  # 5 minutos máximo (incluye tiempo de clasificación)
            tools=[classify_medical_data, validate_json_structure, format_medical_data_for_classification]  # Herramientas para comunicarse con el modelo HF
        )

    @task
    def conversational_interview_task(self) -> Task:
        """Tarea de entrevista conversacional"""
        return Task(
            config=self.tasks_config['conversational_interview_task'],
            agent=self.conversational_interviewer()
        )

    @task
    def specific_questions_analysis_task(self) -> Task:
        """Tarea de análisis y preguntas específicas"""
        return Task(
            config=self.tasks_config['specific_questions_analysis_task'],
            agent=self.specific_questions_analyst()
        )

    @task
    def json_structuring_and_classification_task(self) -> Task:
        """Tarea de estructuración JSON y clasificación con modelo externo"""
        return Task(
            config=self.tasks_config['json_structuring_and_classification_task'],
            agent=self.json_data_structurer()
        )

    @crew
    def crew(self) -> Crew:
        """Crea la crew de anamnesis conversacional"""
        return Crew(
            agents=self.agents,  # Creados automáticamente por @agent decorator
            tasks=self.tasks,    # Creadas automáticamente por @task decorator
            process=Process.sequential,  # Proceso secuencial según el flujo
            verbose=True,
            memory=True,  # Habilitar memoria entre tareas
            max_execution_time=900,  # 15 minutos máximo total
        )
    
    def run_interview_only(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar solo la entrevista conversacional (para uso interactivo)"""
        
        # Crear crew solo con entrevista conversacional
        interview_crew = Crew(
            agents=[self.conversational_interviewer()],
            tasks=[self.conversational_interview_task()],
            process=Process.sequential,
            verbose=True
        )
        
        result = interview_crew.kickoff(inputs=inputs)
        return result.raw if hasattr(result, 'raw') else str(result)
    
    def run_analysis_only(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar solo análisis y preguntas específicas"""
        
        analysis_crew = Crew(
            agents=[self.specific_questions_analyst()],
            tasks=[self.specific_questions_analysis_task()],
            process=Process.sequential,
            verbose=True
        )
        
        result = analysis_crew.kickoff(inputs=inputs)
        return result.raw if hasattr(result, 'raw') else str(result)
    
    def run_structuring_and_classification(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar estructuración JSON y clasificación con modelo Hugging Face"""
        
        # Importar el modelo de clasificación aquí para evitar dependencias circulares
        from app.services.classification_service import classification_model
        
        # Agregar el modelo de clasificación a los inputs para que el agente pueda usarlo
        inputs['classification_model'] = classification_model
        
        structuring_crew = Crew(
            agents=[self.json_data_structurer()],
            tasks=[self.json_structuring_and_classification_task()],
            process=Process.sequential,
            verbose=True
        )
        
        result = structuring_crew.kickoff(inputs=inputs)
        return result.raw if hasattr(result, 'raw') else str(result)
    
    def get_crew_info(self) -> Dict[str, Any]:
        """Información sobre la crew"""
        return {
            "name": "AnamnesisConversacionalCrew",
            "description": "Crew para flujo completo de anamnesis conversacional médica",
            "agents_count": len(self.agents_config),
            "tasks_count": len(self.tasks_config),
            "process": "sequential",
            "agents": list(self.agents_config.keys()),
            "tasks": list(self.tasks_config.keys()),
            "max_execution_time": 900,
            "memory_enabled": True
        }
