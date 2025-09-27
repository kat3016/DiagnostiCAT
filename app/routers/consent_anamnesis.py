"""
Consentimiento y flujo de anamnesis estructurada.
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
import uuid

from app.models.consent_models import ConsentRequest, ConsentResponse
from app.services.anamnesis_service import anamnesis_service
from app.models.medical_models import AnamnesisStructured
from app.services.crew_service import crew_orchestrator

router = APIRouter()

# Memoria simple de consentimiento por conversación
CONSENTS: Dict[str, bool] = {}


@router.post("/consent", response_model=ConsentResponse)
async def consent(accepted: ConsentRequest):
    """Registra consentimiento. Si es rechazado, no se podrá continuar."""
    conversation_id = str(uuid.uuid4())
    CONSENTS[conversation_id] = accepted.accepted

    if not accepted.accepted:
        return ConsentResponse(message="No aceptaste el consentimiento. Sesión finalizada.", accepted=False)

    return ConsentResponse(message=f"Consentimiento aceptado. conversation_id={conversation_id}", accepted=True)


@router.get("/anamnesis/next")
async def anamnesis_next(conversation_id: str):
    """Devuelve la próxima pregunta de anamnesis o indica que se completó."""
    if not CONSENTS.get(conversation_id, False):
        raise HTTPException(status_code=403, detail="Consentimiento no otorgado o inválido")

    nxt = anamnesis_service.next_question(conversation_id)
    return nxt


@router.post("/anamnesis/answer")
async def anamnesis_answer(conversation_id: str, key: str, value: Any = Body(...)):
    """Registra respuesta a una pregunta de anamnesis."""
    if not CONSENTS.get(conversation_id, False):
        raise HTTPException(status_code=403, detail="Consentimiento no otorgado o inválido")

    state = anamnesis_service.submit_answer(conversation_id, key, value)
    return {"conversation_id": conversation_id, "state": state}


@router.get("/anamnesis/structured", response_model=AnamnesisStructured)
async def anamnesis_structured(conversation_id: str):
    """Devuelve la anamnesis en formato estándar JSON."""
    if not CONSENTS.get(conversation_id, False):
        raise HTTPException(status_code=403, detail="Consentimiento no otorgado o inválido")

    structured = anamnesis_service.build_structured(conversation_id)
    return structured


@router.get("/anamnesis/summary")
async def anamnesis_summary(conversation_id: str):
    """Resume la anamnesis y propone preguntas de seguimiento usando CrewAI (o stub)."""
    if not CONSENTS.get(conversation_id, False):
        raise HTTPException(status_code=403, detail="Consentimiento no otorgado o inválido")

    structured = anamnesis_service.build_structured(conversation_id)
    result = await crew_orchestrator.summarize_and_followups(structured.dict())
    return {"structured": structured, **result}


