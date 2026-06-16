"""
DiagnostiCAT - Sistema de Agentes de IA para Conversación Médica
Aplicación FastAPI principal
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.validators import get_configuration_status
from app.routers import medical_chat

# Mangum solo necesario para AWS Lambda, comentado para desarrollo local
try:
    from mangum import Mangum
    MANGUM_AVAILABLE = True
except ImportError:
    MANGUM_AVAILABLE = False
    print("⚠️ Mangum no disponible - solo necesario para AWS Lambda")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    status = get_configuration_status()
    if status["valid"]:
        print(f"✅ Configuración de LLM válida (proveedor: {status['provider']})")
    else:
        print("⚠️ Configuración de LLM incompleta — el sistema seguirá funcionando en modo")
        print("   determinista basado en reglas clínicas, pero sin frases generadas por LLM.")
        for error in status["errors"]:
            print(f"   - {error}")

    print("🚀 DiagnostiCAT iniciado correctamente")
    yield
    print("👋 DiagnostiCAT cerrando...")


# Crear instancia de FastAPI
app = FastAPI(
    title="DiagnostiCAT",
    description="Sistema de Agentes de IA para Conversación Médica",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Manejador global de excepciones
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Error interno del servidor", "detail": str(exc)}
    )


# Rutas principales
@app.get("/")
async def root():
    """Endpoint de bienvenida"""
    return {
        "message": "Bienvenido a DiagnostiCAT",
        "description": "Sistema de Agentes de IA para Conversación Médica",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Endpoint de verificación de salud"""
    return {
        "status": "healthy",
        "service": "DiagnostiCAT",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@app.get("/config/status")
async def configuration_status():
    """Endpoint para verificar el estado de configuración de LLM"""
    status = get_configuration_status()
    return {
        "service": "DiagnostiCAT",
        "llm_configuration": status,
        # The diagnosis pipeline is rule-based and deterministic regardless of
        # LLM availability — an LLM, when configured, only improves question
        # phrasing and adds an optional hypotheses narrative.
        "ready_for_medical_consultations": True
    }


# Incluir routers
app.include_router(
    medical_chat.router,
    prefix="/api/v1/chat",
    tags=["Conversación Médica"]
)

# Handler para AWS Lambda (solo si mangum está disponible)
if MANGUM_AVAILABLE:
    handler = Mangum(app)
else:
    handler = None


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
