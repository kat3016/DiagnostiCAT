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
        Genera respuesta usando el proveedor configurado con fallback
        
        Returns:
            Dict con 'response', 'tokens_used', 'provider_used'
        """
        
        # Intentar con el proveedor configurado primero
        try:
            if self.provider == "nemotron":
                return await self._nemotron_request(system_prompt, user_message, conversation_history)
            elif self.provider == "openai":
                return await self._openai_request(system_prompt, user_message, conversation_history)
        except Exception as e:
            print(f"Error con proveedor {self.provider}: {e}")
            # Si falla, intentar con fallback
            
        # Fallback: intentar con OpenAI si Nemotron falla
        if self.provider == "nemotron" and settings.OPENAI_API_KEY:
            try:
                print("Intentando con OpenAI como fallback...")
                return await self._openai_request(system_prompt, user_message, conversation_history)
            except Exception as e:
                print(f"Error con OpenAI fallback: {e}")
        
        # Fallback final: respuesta simulada para demo
        print("Usando respuesta de fallback para demo...")
        return await self._fallback_response(system_prompt, user_message, conversation_history)
    
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
    
    async def _fallback_response(
        self, 
        system_prompt: str, 
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Respuesta de fallback inteligente para demo"""
        
        # Analizar el mensaje del usuario para dar respuestas contextualizada
        user_lower = user_message.lower()
        
        # Respuestas médicas básicas contextualizadas
        if any(keyword in user_lower for keyword in ["dolor de cabeza", "dolor cabeza", "cefalea"]):
            response = """Entiendo que tienes dolor de cabeza. Para poder ayudarte mejor, me gustaría saber:

1. ¿Desde cuándo tienes este dolor?
2. ¿En qué parte de la cabeza es más intenso?
3. ¿Del 1 al 10, qué tan fuerte es el dolor?
4. ¿Has tomado algún medicamento?

Mientras tanto, te recomiendo:
- Descansar en un lugar tranquilo y oscuro
- Aplicar compresas frías en la frente
- Mantenerte hidratado
- Evitar pantallas y ruidos fuertes

Si el dolor es muy intenso, repentino o se acompaña de fiebre, náuseas o problemas de visión, es importante que busques atención médica inmediata."""

        elif any(keyword in user_lower for keyword in ["fiebre", "temperatura", "calentura"]):
            response = """La fiebre puede indicar que tu cuerpo está luchando contra una infección. Te hago algunas preguntas:

1. ¿Qué temperatura tienes exactamente?
2. ¿Desde cuándo tienes fiebre?
3. ¿Tienes otros síntomas como dolor de garganta, tos, o malestar general?
4. ¿Has tomado algún medicamento para bajar la fiebre?

Recomendaciones inmediatas:
- Mantente bien hidratado (agua, jugos, caldos)
- Descansa adecuadamente
- Viste ropa ligera
- Puedes tomar paracetamol o ibuprofeno según las indicaciones del paquete

⚠️ Busca atención médica inmediata si:
- La temperatura supera los 39.5°C
- Tienes dificultad para respirar
- Dolor de pecho severo
- Confusión o somnolencia extrema"""

        elif any(keyword in user_lower for keyword in ["dolor pecho", "dolor en el pecho", "pecho duele"]):
            response = """⚠️ **IMPORTANTE**: El dolor en el pecho puede ser serio y requiere evaluación médica.

Por favor, describe:
1. ¿Cómo es el dolor? (opresivo, punzante, ardiente)
2. ¿Se irradia a brazos, cuello o mandíbula?
3. ¿Empeoró con ejercicio o esfuerzo?
4. ¿Tienes dificultad para respirar?
5. ¿Sudoración o náuseas?

**BUSCA ATENCIÓN MÉDICA INMEDIATA** si:
- El dolor es intenso y repentino
- Se acompaña de dificultad para respirar
- Hay sudoración profusa
- Sensación de muerte inminente
- Irradiación a brazo izquierdo

🚨 **No esperes - llama al 123 o ve a urgencias si tienes dudas**

Mientras esperas ayuda médica, siéntate cómodamente y mantén la calma."""

        elif any(keyword in user_lower for keyword in ["tos", "toser", "gripa", "gripe", "resfriado"]):
            response = """Entiendo que tienes síntomas respiratorios. Para evaluar mejor tu condición:

1. ¿La tos es seca o con flema?
2. ¿Tienes fiebre?
3. ¿Dolor de garganta?
4. ¿Congestión nasal?
5. ¿Cuántos días llevas con estos síntomas?

Cuidados en casa:
- Aumenta la ingesta de líquidos calientes
- Miel con limón puede aliviar la garganta
- Humidifica el ambiente
- Descansa lo suficiente
- Evita cambios bruscos de temperatura

Consulta médica si:
- Fiebre por más de 3 días
- Dificultad para respirar
- Dolor en el pecho al toser
- Flema con sangre
- Síntomas que empeoran después de mejorar"""

        elif any(keyword in user_lower for keyword in ["dolor estómago", "dolor abdominal", "estomago duele", "nauseas"]):
            response = """El dolor abdominal puede tener muchas causas. Ayúdame a entender mejor:

1. ¿Dónde exactamente te duele? (parte alta, baja, lado derecho/izquierdo)
2. ¿Cuándo empezó el dolor?
3. ¿Es constante o viene y va?
4. ¿Tienes náuseas o vómitos?
5. ¿Has tenido diarrea o estreñimiento?
6. ¿Qué comiste en las últimas 24 horas?

Medidas generales:
- Mantente hidratado con pequeños sorbos de agua
- Evita alimentos sólidos por ahora
- Descansa en posición cómoda
- Aplica calor suave en la zona (bolsa de agua tibia)

⚠️ **Busca atención médica inmediata** si:
- Dolor intenso y repentino en lado derecho bajo
- Vómitos persistentes
- Fiebre alta
- Sangre en vómito o heces
- Dolor que te impide moverte"""

        else:
            # Respuesta general médica
            response = f"""Gracias por consultar con DiagnostiCAT. He registrado tu consulta sobre: "{user_message}"

Como asistente médico virtual, mi objetivo es orientarte, pero recuerda que esta consulta no reemplaza una evaluación médica presencial.

Para poder ayudarte mejor, me gustaría conocer:
1. ¿Cuándo comenzaron estos síntomas?
2. ¿Hay algo que mejore o empeore la situación?
3. ¿Tienes antecedentes médicos relevantes?
4. ¿Tomas algún medicamento actualmente?

Basándome en tu consulta, mi recomendación inicial es que describas más detalladamente tus síntomas para poder orientarte mejor.

⚠️ **Recuerda**: Si tienes síntomas severos, dolor intenso, dificultad para respirar, o cualquier emergencia médica, contacta inmediatamente el servicio de emergencias (123) o acude a un centro médico.

¿Podrías contarme más detalles sobre lo que te está molestando?"""

        return {
            "response": response,
            "tokens_used": len(response.split()),  # Aproximación simple
            "provider_used": "fallback_demo",
            "model_used": "local_medical_responses"
        }
    
    
    async def close(self):
        """Cerrar cliente HTTP"""
        await self.client.aclose()


# Instancia global del servicio
llm_service = LLMService()
