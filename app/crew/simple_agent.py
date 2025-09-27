"""
Agente simplificado para generar preguntas específicas sin depender de CrewAI complejo
"""

from langchain_openai import ChatOpenAI
from app.core.config import settings
import json

def create_simple_questions_agent(model_name=None):
    """Crea un agente LLM simple para generar preguntas específicas"""
    
    # Lista de modelos disponibles en NVIDIA (en orden de preferencia)
    available_models = [
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "meta/llama-3.1-8b-instruct", 
        "meta/llama-3.1-70b-instruct",
        "mistralai/mixtral-8x7b-instruct-v0.1",
        "microsoft/phi-3-medium-128k-instruct"
    ]
    
    model_to_use = model_name or settings.NEMOTRON_MODEL
    
    print(f"🤖 Intentando crear agente con modelo: {model_to_use}")
    
    llm = ChatOpenAI(
        model=model_to_use,
        api_key=settings.NVIDIA_API_KEY,
        base_url=settings.NVIDIA_BASE_URL,
        temperature=0.7,
        timeout=60,
        max_retries=2
    )
    
    return llm, model_to_use

def generate_specific_questions_with_simple_agent(interview_data: str) -> dict:
    """
    Genera preguntas específicas usando el agente simple
    Prueba múltiples modelos disponibles en NVIDIA
    """
    
    # Lista de modelos para probar en orden
    models_to_try = [
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "meta/llama-3.1-8b-instruct", 
        "meta/llama-3.1-70b-instruct",
        "mistralai/mixtral-8x7b-instruct-v0.1"
    ]
    
    prompt = f"""
Eres un médico especialista en diagnóstico diferencial. Tu tarea es analizar la información de una entrevista médica inicial y generar:

1. Exactamente 3 hipótesis preliminares (NO diagnósticos definitivos)
2. Exactamente 5 preguntas específicas para obtener más información precisa

INFORMACIÓN DE LA ENTREVISTA:
{interview_data}

INSTRUCCIONES IMPORTANTES:
- Las hipótesis deben ser preliminares, NO diagnósticos definitivos
- Las preguntas deben ser específicas y dirigidas
- Las preguntas deben ayudar a recopilar datos para clasificación médica
- Usa formato exacto como se muestra abajo

FORMATO DE RESPUESTA REQUERIDO:
HIPÓTESIS PRELIMINARES:
1. [Primera hipótesis preliminar basada en síntomas]
2. [Segunda hipótesis preliminar alternativa]
3. [Tercera hipótesis preliminar diferencial]

PREGUNTAS ESPECÍFICAS PARA MODELO DE CLASIFICACIÓN:
1. [Primera pregunta específica y dirigida]
2. [Segunda pregunta específica y dirigida]
3. [Tercera pregunta específica y dirigida]
4. [Cuarta pregunta específica y dirigida]
5. [Quinta pregunta específica y dirigida]
"""
    
    # Probar cada modelo hasta que uno funcione
    for model_name in models_to_try:
        try:
            print(f"� Probando modelo: {model_name}")
            
            llm, model_used = create_simple_questions_agent(model_name)
            
            print(f"�🤖 Enviando prompt al agente NVIDIA:")
            print(f"📝 Modelo: {model_used}")
            print(f"🔑 API Key configurada: {bool(settings.NVIDIA_API_KEY)}")
            
            response = llm.invoke(prompt)
            
            print(f"✅ ¡ÉXITO! Respuesta recibida del modelo {model_used}:")
            print(f"📄 Contenido: {response.content}")
            
            return {
                "success": True,
                "content": response.content,
                "model_used": model_used
            }
            
        except Exception as e:
            print(f"❌ Error con modelo {model_name}: {e}")
            continue
    
    # Si ningún modelo funcionó
    return {
        "success": False,
        "error": "Ningún modelo de NVIDIA funcionó",
        "content": None,
        "models_tried": models_to_try
    }