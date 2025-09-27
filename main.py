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
from app.routers import medical_chat, agents
from app.core.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    # Inicialización
    await create_tables()
    print("🚀 DiagnostiCAT iniciado correctamente")
    yield
    # Limpieza al cerrar
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


# Incluir routers
app.include_router(
    medical_chat.router,
    prefix="/api/v1/chat",
    tags=["Conversación Médica"]
)

app.include_router(
    agents.router,
    prefix="/api/v1/agents",
    tags=["Agentes de IA"]
)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
