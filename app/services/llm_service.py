"""
Servicio de LLM para generar respuestas usando Ollama
"""

import aiohttp
import json
import asyncio
from typing import Dict, List, Optional, Any
from app.core.config import settings


class LLMService:
    """Servicio para interactuar con modelos LLM usando Ollama"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model_name = getattr(settings, 'OLLAMA_MODEL', 'llama3.2')
        self.timeout = 60  # Timeout en segundos
    
    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Genera una respuesta usando el modelo LLM
        
        Args:
            system_prompt: Prompt del sistema
            user_message: Mensaje del usuario
            conversation_history: Historial de conversación
            temperature: Temperatura para la generación
            max_tokens: Máximo número de tokens
        
        Returns:
            Dict con la respuesta y metadatos
        """
        try:
            # Construir los mensajes
            messages = []
            
            # Agregar prompt del sistema
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Agregar historial de conversación
            if conversation_history:
                messages.extend(conversation_history)
            
            # Agregar mensaje del usuario
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Preparar payload para Ollama
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            # Hacer la petición a Ollama
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        return {
                            "response": result.get("message", {}).get("content", ""),
                            "model": self.model_name,
                            "tokens_used": result.get("eval_count", 0),
                            "success": True
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"Error del modelo LLM: {response.status} - {error_text}")
        
        except asyncio.TimeoutError:
            return {
                "response": "Lo siento, el modelo está tardando mucho en responder. Por favor, intente de nuevo.",
                "model": self.model_name,
                "tokens_used": 0,
                "success": False,
                "error": "timeout"
            }
        
        except Exception as e:
            print(f"❌ Error en LLM Service: {e}")
            # Respuesta de fallback con lógica médica básica
            fallback_response = await self._generate_fallback_response(user_message, system_prompt)
            return {
                "response": fallback_response,
                "model": "fallback",
                "tokens_used": 0,
                "success": False,
                "error": str(e)
            }
    
    async def health_check(self) -> bool:
        """Verifica si el servicio LLM está disponible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except:
            return False
    
    async def list_available_models(self) -> List[str]:
        """Lista los modelos disponibles en Ollama"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return [model["name"] for model in result.get("models", [])]
                    else:
                        return []
        except:
            return []
    
    async def _generate_fallback_response(self, user_message: str, system_prompt: str) -> str:
        """Genera una respuesta de fallback cuando el LLM no está disponible"""
        user_lower = user_message.lower()
        
        # Respuestas de fallback basadas en palabras clave
        if "dolor de cabeza" in user_lower or "cefalea" in user_lower:
            if "clasificación" in system_prompt.lower():
                return '''{"predicted_condition": "Cefalea tensional", "confidence": 0.75, "category": "neurological", "severity": "MEDIO", "recommendations": ["Descanso", "Hidratación", "Analgésicos de venta libre"], "reasoning": "Síntomas compatibles con cefalea tensional común"}'''
            else:
                return "Entiendo que tiene dolor de cabeza. Esto puede deberse a varias causas como tensión, deshidratación o estrés. ¿Puede describirme más detalles sobre el dolor? ¿Dónde lo siente exactamente y cuándo comenzó?"
        
        elif "fiebre" in user_lower or "temperatura" in user_lower:
            if "clasificación" in system_prompt.lower():
                return '''{"predicted_condition": "Síndrome febril", "confidence": 0.70, "category": "infectious", "severity": "MEDIO", "recommendations": ["Monitoreo de temperatura", "Hidratación", "Reposo"], "reasoning": "Presencia de fiebre sugiere posible proceso infeccioso"}'''
            else:
                return "La fiebre puede indicar una infección u otro proceso inflamatorio. ¿Cuál es su temperatura actual? ¿Tiene otros síntomas acompañantes como dolor de garganta, tos o malestar general?"
        
        elif "tos" in user_lower:
            if "clasificación" in system_prompt.lower():
                return '''{"predicted_condition": "Síndrome respiratorio", "confidence": 0.65, "category": "respiratory", "severity": "BAJO", "recommendations": ["Hidratación", "Reposo", "Evitar irritantes"], "reasoning": "Síntomas respiratorios que requieren evaluación"}'''
            else:
                return "La tos puede tener varias causas. ¿Es una tos seca o con flemas? ¿Cuánto tiempo lleva con este síntoma? ¿Tiene fiebre u otros síntomas respiratorios?"
        
        elif "dolor" in user_lower:
            if "clasificación" in system_prompt.lower():
                return '''{"predicted_condition": "Síndrome doloroso", "confidence": 0.60, "category": "general", "severity": "MEDIO", "recommendations": ["Evaluación médica", "Analgésicos según indicación"], "reasoning": "Síntomas dolorosos que requieren evaluación específica"}'''
            else:
                return "Entiendo que presenta dolor. ¿Puede ubicar exactamente dónde siente el dolor? ¿Cómo describiría la intensidad del 1 al 10? ¿Cuándo comenzó?"
        
        else:
            if "clasificación" in system_prompt.lower():
                return '''{"predicted_condition": "Consulta general", "confidence": 0.50, "category": "general", "severity": "BAJO", "recommendations": ["Evaluación médica completa"], "reasoning": "Síntomas requieren evaluación médica profesional"}'''
            else:
                return "Entiendo su consulta. Para poder ayudarle mejor, ¿podría describirme con más detalle los síntomas que está experimentando? ¿Cuándo comenzaron y cómo se sienten?"


# Instancia global del servicio
llm_service = LLMService()