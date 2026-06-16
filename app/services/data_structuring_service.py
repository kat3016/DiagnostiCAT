"""
Builds the standardized structured medical record consumed by the
classification service and the /structured-data endpoints.

Primary path: derives the record directly from the live coverage map built
incrementally by question_engine.py during the adaptive interview — this
guarantees the structured record matches exactly what was asked and answered,
deterministically (see symptom_knowledge.py for the detection logic).

Fallback path: if no coverage map exists yet (e.g. the structured-data
endpoint is called before any interview turns happened), one is reconstructed
from the raw conversation messages. This fallback is flagged explicitly via
metadata.degraded_mode rather than silently blending into the normal result.
"""

from typing import Dict, Any, List
from datetime import datetime

from app.models.medical_models import MessageRole
from app.services import symptom_knowledge as sk
from app.services import question_engine as qe

_CONSENT_WORDS = {
    "i agree", "yes", "ok", "okay", "agree", "si", "sí", "acepto",
    "i do", "proceed", "continue", "sí acepto", "si acepto",
}

# Canonical symptom keys that read well as a standalone "main symptom" label.
_HEADLINE_SYMPTOMS = [
    "headache", "chest_pain", "abdominal_pain", "cough", "shortness_of_breath",
    "joint_pain", "muscle_pain", "back_pain", "rash", "anxiety", "depression", "fatigue",
]


class MedicalDataStructuringService:
    """Structures medical conversation data into standardized JSON."""

    def __init__(self):
        self.standard_format_version = "2.0"

    async def structure_conversation_data(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        try:
            coverage = conversation.get("coverage")
            degraded = False
            if not coverage:
                coverage = self._build_coverage_from_messages(conversation)
                degraded = True

            basic_info = self._extract_basic_information(conversation)
            structured_fields = self._coverage_to_structured_fields(coverage)

            final_structure = {
                **basic_info,
                **structured_fields,
                "canonical_symptoms": sorted(coverage["symptoms"]),
                "metadata": {
                    "format_version": self.standard_format_version,
                    "structured_timestamp": datetime.now().isoformat(),
                    "total_messages": len(conversation.get("messages", [])),
                    "processing_method": "coverage_map" if not degraded else "reconstructed_from_messages",
                    "degraded_mode": degraded,
                },
            }
            self._validate_structure(final_structure)
            return final_structure

        except Exception as e:
            print(f"Error in data structuring: {e}")
            return self._create_fallback_structure(conversation)

    def _build_coverage_from_messages(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Reconstructs a coverage map from raw messages when none was tracked live."""
        coverage = qe.new_coverage_map()
        user_messages = self._extract_user_messages(conversation)
        is_first_substantive = True
        for msg in user_messages:
            stripped = msg.strip()
            if not stripped or stripped.lower() in _CONSENT_WORDS or len(stripped) <= 3:
                continue
            qe.ingest_answer(coverage, msg, is_chief_complaint=is_first_substantive)
            is_first_substantive = False
        return coverage

    def _extract_basic_information(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "conversation_id": conversation.get("conversation_id", "unknown"),
            "created_at": (
                conversation.get("created_at", datetime.now()).isoformat()
                if hasattr(conversation.get("created_at", datetime.now()), 'isoformat')
                else str(conversation.get("created_at", datetime.now()))
            ),
            "state": conversation.get("state", "unknown"),
            "consent_given": conversation.get("consent_given", False),
            "questions_asked": conversation.get("questions_asked", 0),
            "specific_questions_asked": conversation.get("specific_questions_asked", 0),
        }

    def _extract_user_messages(self, conversation: Dict[str, Any]) -> List[str]:
        user_messages = []
        for message in conversation.get("messages", []):
            if isinstance(message, dict):
                role = message.get("role")
                content = message.get("content", "")
            else:
                role = getattr(message, 'role', None)
                content = getattr(message, 'content', "")
            if role == MessageRole.USER or role == "user":
                user_messages.append(content.strip())
        return user_messages

    def _primary_symptom_label(self, coverage: Dict[str, Any]) -> str:
        chief = coverage.get("chief_complaint") or ""
        chief_symptoms = sk.detect_symptoms(chief) if chief else set()

        for headline in _HEADLINE_SYMPTOMS:
            if headline in chief_symptoms:
                return headline.replace("_", " ")
        for headline in _HEADLINE_SYMPTOMS:
            if headline in coverage["symptoms"]:
                return headline.replace("_", " ")
        if chief:
            return chief[:80]
        return "symptom requiring evaluation"

    def _characteristics_text(self, coverage: Dict[str, Any]) -> str:
        parts = []
        if coverage.get("quality"):
            parts.append(f"{coverage['quality']} quality")
        if coverage.get("laterality"):
            parts.append(coverage["laterality"])
        return ", ".join(parts) if parts else "extracted from conversation"

    def _coverage_to_structured_fields(self, coverage: Dict[str, Any]) -> Dict[str, Any]:
        sintoma_principal = self._primary_symptom_label(coverage)
        primary_key = sintoma_principal.replace(" ", "_")
        associated = sorted(s.replace("_", " ") for s in coverage["symptoms"] if s != primary_key)

        family_history = coverage.get("family_history")
        antecedentes_familiares = (
            [family_history] if family_history and family_history != "none reported" else []
        )

        return {
            "motivo_consulta": coverage.get("chief_complaint") or "general medical consultation",
            "enfermedad_actual": {
                "sintoma_principal": sintoma_principal,
                "inicio": coverage.get("onset") or "not specified",
                "intensidad": coverage.get("severity") or "not specified",
                "caracteristicas": self._characteristics_text(coverage),
            },
            "antecedentes_personales": coverage.get("past_history") or [],
            "antecedentes_familiares": antecedentes_familiares,
            "habitos": coverage.get("habits") or {"smoking": "unknown", "alcohol": "unknown", "other": ""},
            "sintomas_asociados": associated[:8],
            "intensidad": coverage.get("severity") or "not specified",
            "factores_agravantes": coverage.get("aggravating_factors") or [],
            "factores_aliviantes": coverage.get("relieving_factors") or [],
            "medicamentos_actuales": coverage.get("medications") or [],
        }

    def _validate_structure(self, structure: Dict[str, Any]) -> bool:
        required_fields = ["motivo_consulta", "enfermedad_actual", "antecedentes_personales", "habitos", "sintomas_asociados"]
        for field in required_fields:
            if field not in structure:
                raise ValueError(f"Required field missing: {field}")
        if not isinstance(structure["enfermedad_actual"], dict):
            raise ValueError("enfermedad_actual must be a dictionary")
        for subfield in ["sintoma_principal", "inicio", "caracteristicas"]:
            if subfield not in structure["enfermedad_actual"]:
                raise ValueError(f"Required subfield missing in enfermedad_actual: {subfield}")
        return True

    def _create_fallback_structure(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        user_messages = self._extract_user_messages(conversation)
        first_message = "medical consultation"
        for msg in user_messages:
            if msg.strip().lower() not in _CONSENT_WORDS and len(msg.strip()) > 3:
                first_message = msg[:200]
                break
        return {
            "motivo_consulta": first_message,
            "enfermedad_actual": {
                "sintoma_principal": "requires additional analysis",
                "inicio": "not specified",
                "intensidad": "not specified",
                "caracteristicas": "insufficient information",
            },
            "antecedentes_personales": [],
            "antecedentes_familiares": [],
            "habitos": {"smoking": "unknown", "alcohol": "unknown", "other": ""},
            "sintomas_asociados": [],
            "intensidad": "not specified",
            "factores_agravantes": [],
            "factores_aliviantes": [],
            "medicamentos_actuales": [],
            "canonical_symptoms": [],
            "metadata": {
                "format_version": self.standard_format_version,
                "structured_timestamp": datetime.now().isoformat(),
                "processing_method": "fallback_basic",
                "degraded_mode": True,
                "error": "Error in main processing",
            },
        }


# Global service instance
data_structuring_service = MedicalDataStructuringService()
