"""
Servicio para gestión de agentes médicos
"""

from typing import Dict, List, Optional
import asyncio
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.agents.medical_agents import GeneralPractitionerAgent
from app.models.agent_models import AgentType, AgentInfo, AgentMetrics
from app.models.medical_models import MessageModel


class AgentService:
    """Servicio para gestionar agentes médicos"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._initialize_default_agents()
    
    def _initialize_default_agents(self):
        """Inicializa agentes disponibles"""
        # Crear agente médico general
        general_agent = GeneralPractitionerAgent()
        
        # Registrar agente
        self.agents[general_agent.id] = general_agent
        
        print(f"✅ Agentes médicos inicializados: {len(self.agents)} agentes disponibles")
    
    def get_agent_by_id(self, agent_id: str) -> Optional[BaseAgent]:
        """Obtiene un agente por su ID"""
        return self.agents.get(agent_id)
    
    def get_agent_by_type(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Obtiene el primer agente del tipo especificado"""
        for agent in self.agents.values():
            if agent.agent_type == agent_type:
                return agent
        return None
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Obtiene todos los agentes disponibles"""
        return list(self.agents.values())
    
    def get_agents_info(self) -> List[AgentInfo]:
        """Obtiene información de todos los agentes"""
        agents_info = []
        for agent in self.agents.values():
            info = AgentInfo(
                id=agent.id,
                name=agent.name,
                agent_type=agent.agent_type,
                description=f"Agente especializado en {', '.join(agent.specialties)}",
                specialties=agent.specialties,
                status="active",  # Por simplicidad, todos están activos
                created_at=agent.created_at,
                updated_at=agent.created_at,
                metrics=AgentMetrics(
                    agent_id=agent.id,
                    total_conversations=agent.conversation_count,
                    avg_response_time=1.5,  # Simulado
                    avg_confidence_score=0.85,  # Simulado
                    success_rate=0.92,  # Simulado
                    last_active=datetime.now()
                )
            )
            agents_info.append(info)
        
        return agents_info
    
    def recommend_agent(
        self,
        message: str,
        conversation_history: List[MessageModel] = None
    ) -> BaseAgent:
        """
        Recomienda el mejor agente para un mensaje específico
        
        Args:
            message: Mensaje del usuario
            conversation_history: Historial de conversación
            
        Returns:
            BaseAgent: Agente recomendado (siempre médico general)
        """
        # Recomendar agente según la fase del flujo
        # Por defecto, empezar con entrevista inicial
        interview_agent = self.get_agent_by_type(AgentType.INITIAL_INTERVIEW)
        return interview_agent or list(self.agents.values())[0]
    
    async def process_message_with_agent(
        self,
        agent_id: str,
        message: str,
        conversation_history: List[MessageModel] = None,
        patient_context: Optional[Dict] = None
    ):
        """
        Procesa un mensaje con un agente específico
        
        Args:
            agent_id: ID del agente
            message: Mensaje a procesar
            conversation_history: Historial de conversación
            patient_context: Contexto del paciente
            
        Returns:
            AgentResponse: Respuesta del agente
        """
        agent = self.get_agent_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agente con ID {agent_id} no encontrado")
        
        return await agent.process_message(
            message=message,
            conversation_history=conversation_history or [],
            patient_context=patient_context
        )
    
    def add_agent(self, agent: BaseAgent) -> str:
        """
        Añade un nuevo agente al servicio
        
        Args:
            agent: Agente a añadir
            
        Returns:
            str: ID del agente añadido
        """
        self.agents[agent.id] = agent
        return agent.id
    
    def remove_agent(self, agent_id: str) -> bool:
        """
        Elimina un agente del servicio
        
        Args:
            agent_id: ID del agente a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False
    
    def get_agent_metrics(self, agent_id: str) -> Optional[AgentMetrics]:
        """
        Obtiene métricas de un agente específico
        
        Args:
            agent_id: ID del agente
            
        Returns:
            AgentMetrics: Métricas del agente
        """
        agent = self.get_agent_by_id(agent_id)
        if not agent:
            return None
        
        return AgentMetrics(
            agent_id=agent_id,
            total_conversations=agent.conversation_count,
            avg_response_time=1.5,  # Simulado - aquí calcularías el promedio real
            avg_confidence_score=0.85,  # Simulado
            success_rate=0.92,  # Simulado
            last_active=datetime.now()
        )


# Instancia global del servicio de agentes
agent_service = AgentService()
