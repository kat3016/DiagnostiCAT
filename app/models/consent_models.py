"""
Modelos de consentimiento informado
"""

from pydantic import BaseModel, Field


class ConsentRequest(BaseModel):
    accepted: bool = Field(..., description="Si el usuario acepta el consentimiento")


class ConsentResponse(BaseModel):
    message: str
    accepted: bool


