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
                        raise Exception(f"LLM model error: {response.status} - {error_text}")
        
        except asyncio.TimeoutError:
            return {
                "response": "Sorry, the model is taking too long to respond. Please try again.",
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
            if "classification" in system_prompt.lower() or "clasificación" in system_prompt.lower():
                return '''{"predicted_condition": "Tension headache", "confidence": 0.75, "category": "neurological", "severity": "MEDIUM", "recommendations": ["Rest", "Hydration", "Over-the-counter pain relievers"], "reasoning": "Symptoms compatible with a common tension headache"}'''
            else:
                return "I understand you have a headache. This can have several causes, such as tension, dehydration, or stress. Can you describe more details about the pain? Where exactly do you feel it, and when did it start?"
        
        elif "fiebre" in user_lower or "temperatura" in user_lower:
            if "classification" in system_prompt.lower() or "clasificación" in system_prompt.lower():
                return '''{"predicted_condition": "Fever syndrome", "confidence": 0.70, "category": "infectious", "severity": "MEDIUM", "recommendations": ["Temperature monitoring", "Hydration", "Rest"], "reasoning": "Presence of fever suggests a possible infectious process"}'''
            else:
                return "Fever can indicate an infection or another inflammatory process. What is your current temperature? Do you have accompanying symptoms such as sore throat, cough, or general malaise?"
        
        elif "tos" in user_lower:
            if "classification" in system_prompt.lower() or "clasificación" in system_prompt.lower():
                return '''{"predicted_condition": "Respiratory syndrome", "confidence": 0.65, "category": "respiratory", "severity": "LOW", "recommendations": ["Hydration", "Rest", "Avoid irritants"], "reasoning": "Respiratory symptoms requiring evaluation"}'''
            else:
                return "Cough can have several causes. Is it a dry cough or does it produce phlegm? How long have you had this symptom? Do you have fever or other respiratory symptoms?"
        
        elif "dolor" in user_lower:
            if "classification" in system_prompt.lower() or "clasificación" in system_prompt.lower():
                return '''{"predicted_condition": "Pain syndrome", "confidence": 0.60, "category": "general", "severity": "MEDIUM", "recommendations": ["Medical evaluation", "Pain relievers as directed"], "reasoning": "Pain symptoms requiring specific evaluation"}'''
            else:
                return "I understand that you are experiencing pain. Can you locate exactly where you feel the pain? How would you describe the intensity from 1 to 10? When did it start?"
        
        else:
            if "classification" in system_prompt.lower() or "clasificación" in system_prompt.lower():
                return '''{"predicted_condition": "General consultation", "confidence": 0.50, "category": "general", "severity": "LOW", "recommendations": ["Complete medical evaluation"], "reasoning": "Symptoms require professional medical evaluation"}'''
            else:
                return "I understand your concern. To help you better, could you describe in more detail the symptoms you are experiencing? When did they start and how do they feel?"


# Instancia global del servicio
llm_service = LLMService()
