"""
Servicio para gestión de agentes médicos con CrewAI
"""

from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime

from app.crew.anamnesis_crew import AnamnesisConversacionalCrew
from app.models.agent_models import AgentType, AgentInfo, AgentMetrics
from app.models.medical_models import MessageModel


class AgentService:
    """Servicio para gestionar agentes médicos con CrewAI"""
    
    def __init__(self):
        self.anamnesis_crew = AnamnesisConversacionalCrew()
        self._initialize_crew()
    
    def _initialize_crew(self):
        """Inicializa la crew de anamnesis conversacional"""
        try:
            crew_info = self.anamnesis_crew.get_crew_info()
            print(f"✅ CrewAI inicializada: {crew_info['agents_count']} agentes, {crew_info['tasks_count']} tareas")
            print(f"   Agentes: {', '.join(crew_info['agents'])}")
        except Exception as e:
            print(f"❌ Error inicializando CrewAI: {e}")
            raise
    
    def get_crew_info(self) -> Dict[str, Any]:
        """Obtiene información de la crew"""
        return self.anamnesis_crew.get_crew_info()
    
    async def run_initial_interview(self, inputs: Dict[str, Any]) -> str:
        """Ejecuta solo la entrevista inicial"""
        try:
            result = self.anamnesis_crew.run_interview_only(inputs)
            return result
        except Exception as e:
            print(f"❌ Error en entrevista inicial: {e}")
            raise
    
    async def run_preliminary_analysis(self, inputs: Dict[str, Any]) -> str:
        """Ejecuta análisis preliminar"""
        try:
            result = self.anamnesis_crew.run_analysis_only(inputs)
            return result
        except Exception as e:
            print(f"❌ Error en análisis preliminar: {e}")
            raise
    
    async def run_data_structuring(self, inputs: Dict[str, Any]) -> str:
        """Ejecuta estructuración de datos"""
        try:
            result = self.anamnesis_crew.run_structuring_only(inputs)
            return result
        except Exception as e:
            print(f"❌ Error en estructuración: {e}")
            raise
    
    async def run_classification(self, inputs: Dict[str, Any]) -> str:
        """Ejecuta clasificación médica"""
        try:
            result = self.anamnesis_crew.run_classification_only(inputs)
            return result
        except Exception as e:
            print(f"❌ Error en clasificación: {e}")
            raise
    
    async def run_complete_flow(self, inputs: Dict[str, Any]) -> Any:
        """Ejecuta el flujo completo de anamnesis conversacional"""
        try:
            crew = self.anamnesis_crew.crew()
            result = crew.kickoff(inputs=inputs)
            return result
        except Exception as e:
            print(f"❌ Error en flujo completo: {e}")
            raise
    
    def get_available_agents(self) -> List[str]:
        """Obtiene lista de agentes disponibles en la crew"""
        crew_info = self.get_crew_info()
        return crew_info.get('agents', [])
    
    def get_available_tasks(self) -> List[str]:
        """Obtiene lista de tareas disponibles en la crew"""
        crew_info = self.get_crew_info()
        return crew_info.get('tasks', [])
    
    def get_process_type(self) -> str:
        """Obtiene el tipo de proceso de la crew"""
        crew_info = self.get_crew_info()
        return crew_info.get('process', 'sequential')
    
    def is_memory_enabled(self) -> bool:
        """Verifica si la memoria está habilitada"""
        crew_info = self.get_crew_info()
        return crew_info.get('memory_enabled', False)
    
    def get_crew_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual de la crew"""
        crew_info = self.get_crew_info()
        return {
            "status": "ready",
            "agents_count": crew_info.get('agents_count', 0),
            "tasks_count": crew_info.get('tasks_count', 0),
            "process": crew_info.get('process', 'sequential'),
            "memory_enabled": crew_info.get('memory_enabled', False),
            "max_execution_time": crew_info.get('max_execution_time', 900),
            "available_agents": crew_info.get('agents', []),
            "available_tasks": crew_info.get('tasks', [])
        }


# Instancia global del servicio de agentes
agent_service = AgentService()