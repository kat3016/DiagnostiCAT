"""
Validadores para asegurar que los LLM estén configurados correctamente
"""

from app.core.config import settings
from typing import List


class LLMConfigurationError(Exception):
    """Error cuando la configuración de LLM no es válida"""
    pass


def validate_llm_configuration() -> None:
    """
    Valida que la configuración de LLM sea correcta y completa.
    Lanza LLMConfigurationError si no está bien configurada.
    """
    errors: List[str] = []
    
    # Verificar proveedor
    if not settings.LLM_PROVIDER:
        errors.append("LLM_PROVIDER no está configurado")
    
    # Verificar configuración específica del proveedor
    if settings.LLM_PROVIDER.lower() == "nemotron":
        if not settings.NVIDIA_API_KEY:
            errors.append("NVIDIA_API_KEY es requerido para usar Nemotron")
        if not settings.NVIDIA_BASE_URL:
            errors.append("NVIDIA_BASE_URL es requerido para usar Nemotron")
        if not settings.NEMOTRON_MODEL:
            errors.append("NEMOTRON_MODEL es requerido para usar Nemotron")
    
    elif settings.LLM_PROVIDER.lower() == "openai":
        if not settings.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY es requerido para usar OpenAI")
        if not settings.OPENAI_MODEL:
            errors.append("OPENAI_MODEL es requerido para usar OpenAI")
    
    else:
        errors.append(f"Proveedor LLM no soportado: {settings.LLM_PROVIDER}. Use 'nemotron' o 'openai'")
    
    # Verificar configuración de CrewAI si está habilitado
    if settings.CREW_ENABLE:
        if settings.LLM_PROVIDER.lower() == "nemotron" and not settings.NVIDIA_API_KEY:
            errors.append("NVIDIA_API_KEY es requerido para CrewAI con Nemotron")
        elif settings.LLM_PROVIDER.lower() == "openai" and not settings.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY es requerido para CrewAI con OpenAI")
    
    if errors:
        error_message = "Configuración de LLM incompleta:\n" + "\n".join(f"- {error}" for error in errors)
        error_message += "\n\nPara configurar correctamente:"
        
        if settings.LLM_PROVIDER.lower() == "nemotron":
            error_message += """
1. Obtén tu API key de NVIDIA: https://build.nvidia.com/
2. Configura en tu archivo .env:
   NVIDIA_API_KEY=tu-api-key-aqui
   LLM_PROVIDER=nemotron
   CREW_ENABLE=True"""
        
        elif settings.LLM_PROVIDER.lower() == "openai":
            error_message += """
1. Obtén tu API key de OpenAI: https://platform.openai.com/api-keys
2. Configura en tu archivo .env:
   OPENAI_API_KEY=tu-api-key-aqui
   LLM_PROVIDER=openai
   CREW_ENABLE=True"""
        
        else:
            error_message += """
1. Configura LLM_PROVIDER=nemotron o LLM_PROVIDER=openai
2. Agrega la API key correspondiente a tu archivo .env"""
        
        raise LLMConfigurationError(error_message)


def get_configuration_status() -> dict:
    """
    Retorna el estado de la configuración sin lanzar errores
    """
    status = {
        "provider": settings.LLM_PROVIDER,
        "nemotron_configured": bool(settings.NVIDIA_API_KEY),
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "crew_enabled": settings.CREW_ENABLE,
        "valid": False,
        "errors": []
    }
    
    try:
        validate_llm_configuration()
        status["valid"] = True
    except LLMConfigurationError as e:
        status["errors"] = str(e).split("\n")
    
    return status
