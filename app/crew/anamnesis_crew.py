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


@CrewBase
class AnamnesisConversacionalCrew:
    """Crew para flujo de anamnesis conversacional médica"""
    
    agents_config_path = os.path.join(os.path.dirname(__file__), 'config', 'agents.yaml')
    tasks_config_path = os.path.join(os.path.dirname(__file__), 'config', 'tasks.yaml')
    
    def __init__(self):
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
    def initial_interviewer(self) -> Agent:
        """Agente para entrevista inicial con preguntas fijas"""
        return Agent(
            config=self.agents_config['initial_interviewer'],
            verbose=True,
            allow_delegation=False,
            max_execution_time=300  # 5 minutos máximo
        )

    @agent
    def preliminary_analyst(self) -> Agent:
        """Agente para análisis preliminar e hipótesis"""
        return Agent(
            config=self.agents_config['preliminary_analyst'],
            verbose=True,
            allow_delegation=False,
            max_execution_time=180  # 3 minutos máximo
        )

    @agent
    def data_structurer(self) -> Agent:
        """Agente para estructuración de datos en JSON"""
        return Agent(
            config=self.agents_config['data_structurer'],
            verbose=True,
            allow_delegation=False,
            max_execution_time=120  # 2 minutos máximo
        )

    @agent
    def medical_classifier(self) -> Agent:
        """Agente para clasificación médica"""
        return Agent(
            config=self.agents_config['medical_classifier'],
            verbose=True,
            allow_delegation=False,
            max_execution_time=180  # 3 minutos máximo
        )

    @task
    def initial_interview_task(self) -> Task:
        """Tarea de entrevista inicial"""
        return Task(
            config=self.tasks_config['initial_interview_task'],
            agent=self.initial_interviewer()
        )

    @task
    def preliminary_analysis_task(self) -> Task:
        """Tarea de análisis preliminar"""
        return Task(
            config=self.tasks_config['preliminary_analysis_task'],
            agent=self.preliminary_analyst()
        )

    @task
    def data_structuring_task(self) -> Task:
        """Tarea de estructuración de datos"""
        return Task(
            config=self.tasks_config['data_structuring_task'],
            agent=self.data_structurer()
        )

    @task
    def medical_classification_task(self) -> Task:
        """Tarea de clasificación médica"""
        return Task(
            config=self.tasks_config['medical_classification_task'],
            agent=self.medical_classifier()
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
        """Ejecutar solo la entrevista inicial (para uso interactivo)"""
        
        # Crear crew solo con entrevista inicial
        interview_crew = Crew(
            agents=[self.initial_interviewer()],
            tasks=[self.initial_interview_task()],
            process=Process.sequential,
            verbose=True
        )
        
        result = interview_crew.kickoff(inputs=inputs)
        return result.raw if hasattr(result, 'raw') else str(result)
    
    def run_analysis_only(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar solo análisis preliminar"""
        
        analysis_crew = Crew(
            agents=[self.preliminary_analyst()],
            tasks=[self.preliminary_analysis_task()],
            process=Process.sequential,
            verbose=True
        )
        
        result = analysis_crew.kickoff(inputs=inputs)
        return result.raw if hasattr(result, 'raw') else str(result)
    
    def run_structuring_only(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar solo estructuración de datos"""
        
        structuring_crew = Crew(
            agents=[self.data_structurer()],
            tasks=[self.data_structuring_task()],
            process=Process.sequential,
            verbose=True
        )
        
        result = structuring_crew.kickoff(inputs=inputs)
        return result.raw if hasattr(result, 'raw') else str(result)
    
    def run_classification_only(self, inputs: Dict[str, Any]) -> str:
        """Ejecutar solo clasificación médica"""
        
        classification_crew = Crew(
            agents=[self.medical_classifier()],
            tasks=[self.medical_classification_task()],
            process=Process.sequential,
            verbose=True
        )
        
        result = classification_crew.kickoff(inputs=inputs)
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
