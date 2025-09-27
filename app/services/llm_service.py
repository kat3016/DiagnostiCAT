"""
Servicio LLM que soporta múltiples proveedores (Nemotron, OpenAI, fallback)
"""

import asyncio
import httpx
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from app.core.config import settings


class LLMService:
    """Servicio unificado para modelos LLM"""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def generate_response(
        self, 
        system_prompt: str, 
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Genera respuesta usando el proveedor configurado
        
        Returns:
            Dict con 'response', 'tokens_used', 'provider_used'
        """
        
        if self.provider == "nemotron":
            return await self._nemotron_request(system_prompt, user_message, conversation_history)
        elif self.provider == "openai":
            return await self._openai_request(system_prompt, user_message, conversation_history)
        else:
            raise ValueError(f"Proveedor LLM no configurado correctamente: {self.provider}. Configure NVIDIA_API_KEY o OPENAI_API_KEY")
    
    async def _nemotron_request(
        self, 
        system_prompt: str, 
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Petición a NVIDIA Nemotron via NIM API"""
        
        if not settings.NVIDIA_API_KEY:
            raise ValueError("NVIDIA_API_KEY no configurado. Configure su API key para usar Nemotron.")
        
        # Construir mensajes
        messages = [{"role": "system", "content": system_prompt}]
        
        # Agregar historial si existe
        if conversation_history:
            messages.extend(conversation_history[-5:])  # Últimos 5 mensajes
        
        messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": settings.NEMOTRON_MODEL,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "stream": False
        }
        
        headers = {
            "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.post(
                f"{settings.NVIDIA_BASE_URL}/chat/completions",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "response": data["choices"][0]["message"]["content"],
                    "tokens_used": data.get("usage", {}).get("total_tokens", 0),
                    "provider_used": "nemotron",
                    "model_used": settings.NEMOTRON_MODEL
                }
            else:
                error_msg = f"Error Nemotron {response.status_code}: {response.text}"
                raise Exception(f"Error en API de Nemotron: {error_msg}")
                
        except Exception as e:
            raise Exception(f"Error conectando con Nemotron: {str(e)}")
    
    async def _openai_request(
        self, 
        system_prompt: str, 
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Petición a OpenAI (compatibilidad)"""
        
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY no configurado. Configure su API key para usar OpenAI.")
        
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-5:])
        messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS
        }
        
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "response": data["choices"][0]["message"]["content"],
                    "tokens_used": data.get("usage", {}).get("total_tokens", 0),
                    "provider_used": "openai",
                    "model_used": settings.OPENAI_MODEL
                }
            else:
                error_msg = f"Error OpenAI {response.status_code}: {response.text}"
                raise Exception(f"Error en API de OpenAI: {error_msg}")
                
        except Exception as e:
            raise Exception(f"Error conectando con OpenAI: {str(e)}")
    
    
    async def close(self):
        """Cerrar cliente HTTP"""
        await self.client.aclose()


# Instancia global del servicio
llm_service = LLMService()
