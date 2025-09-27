"""
Agente híbrido que puede usar NVIDIA o OpenAI según disponibilidad
"""

from langchain_openai import ChatOpenAI
from app.core.config import settings
import os

def test_nvidia_availability():
    """Prueba si NVIDIA API está disponible"""
    
    if not settings.NVIDIA_API_KEY:
        return False, "No API key configurada"
    
    try:
        # Probar con un modelo simple
        llm = ChatOpenAI(
            model="nvidia/llama-3.1-nemotron-70b-instruct",
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=0.1,
            timeout=30
        )
        
        # Prueba simple
        response = llm.invoke("Hello, respond with 'OK' if you can read this.")
        return True, f"NVIDIA funcionando: {response.content}"
        
    except Exception as e:
        return False, f"Error NVIDIA: {str(e)}"

def create_hybrid_agent():
    """Crea agente que funciona con NVIDIA o OpenAI"""
    
    # Probar NVIDIA primero
    nvidia_works, nvidia_msg = test_nvidia_availability()
    print(f"🧪 Test NVIDIA: {nvidia_msg}")
    
    if nvidia_works:
        print("✅ Usando NVIDIA API")
        return ChatOpenAI(
            model="nvidia/llama-3.1-nemotron-70b-instruct",
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=0.7,
            timeout=60
        ), "nvidia"
    
    # Fallback a OpenAI si está configurado
    elif settings.OPENAI_API_KEY:
        print("⚡ Fallback a OpenAI API")
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.7,
            timeout=60
        ), "openai"
    
    else:
        raise Exception("Ni NVIDIA ni OpenAI están configurados correctamente")

def generate_questions_hybrid(interview_data: str) -> dict:
    """Genera preguntas usando el mejor agente disponible"""
    
    try:
        llm, provider = create_hybrid_agent()
        
        prompt = f"""
Eres un médico especialista en diagnóstico diferencial. Analiza esta entrevista médica y genera:

1. Exactamente 3 hipótesis preliminares (NO diagnósticos definitivos)
2. Exactamente 5 preguntas específicas

INFORMACIÓN DE LA ENTREVISTA:
{interview_data}

FORMATO REQUERIDO:
HIPÓTESIS PRELIMINARES:
1. [Hipótesis preliminar 1]
2. [Hipótesis preliminar 2]  
3. [Hipótesis preliminar 3]

PREGUNTAS ESPECÍFICAS PARA MODELO DE CLASIFICACIÓN:
1. [Pregunta específica 1]
2. [Pregunta específica 2]
3. [Pregunta específica 3]
4. [Pregunta específica 4]
5. [Pregunta específica 5]
"""
        
        print(f"🤖 Generando preguntas con {provider.upper()}...")
        response = llm.invoke(prompt)
        
        print(f"✅ Preguntas generadas exitosamente por {provider.upper()}")
        
        return {
            "success": True,
            "content": response.content,
            "provider": provider,
            "model": "nvidia/llama-3.1-nemotron-70b-instruct" if provider == "nvidia" else settings.OPENAI_MODEL
        }
        
    except Exception as e:
        print(f"❌ Error en agente híbrido: {e}")
        return {
            "success": False,
            "error": str(e),
            "content": None
        }