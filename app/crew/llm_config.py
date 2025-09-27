"""
Configuración de LLM personalizada para CrewAI usando NVIDIA Nemotron
"""

import os
from langchain_openai import ChatOpenAI
from app.core.config import settings


def get_nemotron_llm():
    """
    Crea y configura un LLM de Nemotron para CrewAI
    """
    # CrewAI usa LangChain internamente, así que podemos usar ChatOpenAI
    # con la API de NVIDIA que es compatible con OpenAI
    
    return ChatOpenAI(
        model=settings.NEMOTRON_MODEL,
        api_key=settings.NVIDIA_API_KEY,
        base_url=settings.NVIDIA_BASE_URL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        timeout=60,
        max_retries=3
    )


def configure_crewai_llm():
    """
    Configura las variables de entorno para que CrewAI use Nemotron
    """
    # Configurar variables de entorno que CrewAI puede usar
    os.environ['OPENAI_API_KEY'] = settings.NVIDIA_API_KEY  # CrewAI usa esta variable
    os.environ['OPENAI_API_BASE'] = settings.NVIDIA_BASE_URL
    os.environ['OPENAI_MODEL_NAME'] = settings.NEMOTRON_MODEL
    
    # Variables específicas de NVIDIA
    os.environ['NVIDIA_API_KEY'] = settings.NVIDIA_API_KEY
    os.environ['NVIDIA_BASE_URL'] = settings.NVIDIA_BASE_URL
    
    print(f"✅ CrewAI configurado para usar Nemotron: {settings.NEMOTRON_MODEL}")
    print(f"   API Base URL: {settings.NVIDIA_BASE_URL}")
    print(f"   Temperature: {settings.LLM_TEMPERATURE}")
    print(f"   Max Tokens: {settings.LLM_MAX_TOKENS}")
