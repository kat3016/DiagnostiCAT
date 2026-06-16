"""
Router for the conversational medical chat.

Single adaptive pipeline: consent -> adaptive general interview (up to 10
non-repetitive questions) -> adaptive differentiator interview (up to 5
category-aware questions) -> evidence-based classification -> post-diagnosis
conversation.

A coverage map (see question_engine.py) is updated from every user answer in
every phase, so information volunteered ahead of being asked — or given in
response to a different question — is never asked for again.
"""

import html
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.models.medical_models import ChatRequest, ChatResponse, MessageRole
from app.services import question_engine as qe
from app.services import symptom_knowledge as sk
from app.services.llm_client import generate_differentiator_question, generate_preliminary_hypotheses_text

router = APIRouter()

CONVERSATIONS: Dict[str, Dict[str, Any]] = {}


class ConversationState:
    AWAITING_CONSENT = "awaiting_consent"
    COLLECTING_SYMPTOMS = "collecting_symptoms"
    SPECIFIC_QUESTIONS = "specific_questions"
    READY_FOR_CLASSIFICATION = "ready_for_classification"
    CLASSIFICATION_COMPLETE = "classification_complete"


def _matches_pattern(pattern: str, text: str) -> bool:
    """Multi-word phrases match as substrings; single words match on word
    boundaries only, so 'no' doesn't match inside 'now' and 'si' doesn't
    match inside 'consider'."""
    if " " in pattern:
        return pattern in text
    return re.search(rf"\b{re.escape(pattern)}\b", text) is not None


def _append_assistant_message(conversation: Dict[str, Any], content: str) -> None:
    conversation["messages"].append({
        "role": MessageRole.ASSISTANT,
        "content": content,
        "timestamp": datetime.now(),
    })


@router.post("/", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """Main endpoint for the conversational medical chat."""

    if not request.conversation_id:
        conversation_id = str(uuid.uuid4())
        CONVERSATIONS[conversation_id] = {
            "state": ConversationState.AWAITING_CONSENT,
            "messages": [],
            "consent_given": False,
            "coverage": qe.new_coverage_map(),
            "created_at": datetime.now(),
        }
    else:
        conversation_id = request.conversation_id
        if conversation_id not in CONVERSATIONS:
            raise HTTPException(status_code=404, detail="Conversation not found")

    conversation = CONVERSATIONS[conversation_id]
    conversation["messages"].append({
        "role": MessageRole.USER,
        "content": request.message,
        "timestamp": datetime.now(),
    })

    try:
        state = conversation["state"]
        if state == ConversationState.AWAITING_CONSENT:
            return await handle_consent(conversation_id, request.message)
        elif state == ConversationState.COLLECTING_SYMPTOMS:
            return await handle_general_interview(conversation_id, request.message)
        elif state == ConversationState.SPECIFIC_QUESTIONS:
            return await handle_differentiator_interview(conversation_id, request.message)
        elif state == ConversationState.READY_FOR_CLASSIFICATION:
            return await handle_classification(conversation_id, request.message)
        else:
            return await handle_post_classification_conversation(conversation_id, request.message)

    except Exception as e:
        error_response = ChatResponse(
            response=f"Sorry, an internal error occurred: {html.escape(str(e))}. Please try again or restart the conversation.",
            conversation_id=conversation_id,
            agent_type="error_handler",
            confidence_score=0.0,
            severity_assessment="low",
            suggestions=[],
            follow_up_questions=[],
        )
        _append_assistant_message(conversation, error_response.response)
        return error_response


# ---------------------------------------------------------------------------
# Phase 1: Consent
# ---------------------------------------------------------------------------

def _start_general_interview(conversation: Dict[str, Any]) -> str:
    coverage = conversation["coverage"]
    next_slot = qe.get_next_general_question(coverage)
    if next_slot is None:
        return "Can you describe what's bothering you today?"
    slot_key, question_text = next_slot
    qe.mark_general_asked(coverage, slot_key)
    return question_text


async def handle_consent(conversation_id: str, original_message: str) -> ChatResponse:
    conversation = CONVERSATIONS[conversation_id]
    message_lower = original_message.lower().strip()

    negative_patterns = [
        'no acepto', 'niego', 'rechazo', 'rechaza', 'no autorizo',
        'no estoy de acuerdo', 'en desacuerdo', 'no',
        'i do not agree', 'i disagree', "don't agree", 'disagree', 'refuse', 'decline',
    ]
    positive_patterns = [
        'si acepto', 'sí acepto', 'acepto', 'estoy de acuerdo', 'de acuerdo', 'conforme', 'autorizo',
        'i agree', 'i do', 'agree', 'proceed', 'continue', 'si', 'sí', 'yes', 'ok', 'okay',
    ]

    consent_denied = any(_matches_pattern(p, message_lower) for p in negative_patterns)
    consent_given = False
    if not consent_denied:
        consent_given = any(_matches_pattern(p, message_lower) for p in positive_patterns)

    if consent_given:
        conversation["state"] = ConversationState.COLLECTING_SYMPTOMS
        conversation["consent_given"] = True

        first_question = _start_general_interview(conversation)
        response_text = (
            "Perfect! Thank you for giving your consent.\n\n"
            "REMINDER: I'm DiagnostiCAT, an AI assistant. This conversation does NOT replace a real medical consultation.\n\n"
            "I will ask you some questions to better understand your situation.\n\n"
            f"{first_question}"
        )
        _append_assistant_message(conversation, response_text)
        return ChatResponse(
            response=response_text, conversation_id=conversation_id, agent_type="consent_handler",
            confidence_score=1.0, severity_assessment="low", suggestions=[], follow_up_questions=[],
        )

    elif consent_denied:
        response_text = (
            "I understand that you do not wish to give your consent. Without your consent, I cannot proceed "
            "with the medical consultation. If you change your mind, you can restart the conversation. Have a good day!"
        )
        _append_assistant_message(conversation, response_text)
        return ChatResponse(
            response=response_text, conversation_id=conversation_id, agent_type="consent_handler",
            confidence_score=1.0, severity_assessment="low", suggestions=[], follow_up_questions=[],
        )

    else:
        response_text = (
            "I couldn't clearly understand your answer about consent. Please respond clearly: Do you agree that "
            "I process your medical information to assist you? You can respond 'I agree' or 'I do not agree'."
        )
        _append_assistant_message(conversation, response_text)
        return ChatResponse(
            response=response_text, conversation_id=conversation_id, agent_type="consent_handler",
            confidence_score=0.5, severity_assessment="low", suggestions=[], follow_up_questions=[],
        )


# ---------------------------------------------------------------------------
# Phase 2: Adaptive general interview (up to 10 non-repetitive questions)
# ---------------------------------------------------------------------------

async def handle_general_interview(conversation_id: str, message: str) -> ChatResponse:
    conversation = CONVERSATIONS[conversation_id]
    coverage = conversation["coverage"]

    is_chief = coverage["chief_complaint"] is None
    qe.ingest_answer(coverage, message, is_chief_complaint=is_chief)

    next_slot = qe.get_next_general_question(coverage)
    if next_slot is None:
        conversation["state"] = ConversationState.SPECIFIC_QUESTIONS
        return await handle_differentiator_interview(conversation_id, message, just_transitioned=True)

    slot_key, question_text = next_slot
    qe.mark_general_asked(coverage, slot_key)

    _append_assistant_message(conversation, question_text)
    return ChatResponse(
        response=question_text,
        conversation_id=conversation_id,
        agent_type="symptom_collector",
        confidence_score=0.8,
        severity_assessment="low",
        suggestions=[],
        follow_up_questions=[],
    )


# ---------------------------------------------------------------------------
# Phase 3: Adaptive, category-aware differentiator interview (up to 5 Qs)
# ---------------------------------------------------------------------------

async def handle_differentiator_interview(conversation_id: str, message: str, just_transitioned: bool = False) -> ChatResponse:
    conversation = CONVERSATIONS[conversation_id]
    coverage = conversation["coverage"]

    if not just_transitioned:
        qe.ingest_answer(coverage, message)

    category = qe.tentative_category(coverage)
    is_first_differentiator = len(coverage["differentiator_asked"]) == 0

    next_slot = qe.get_next_differentiator_question(coverage, category)
    if next_slot is None:
        conversation["state"] = ConversationState.READY_FOR_CLASSIFICATION
        return await handle_classification(conversation_id, message)

    slot_key, default_question = next_slot
    qe.mark_differentiator_asked(coverage, slot_key)

    question_text = default_question
    llm_result = generate_differentiator_question(
        default_question, qe.coverage_summary_text(coverage), qe.already_known_text(coverage)
    )
    if llm_result["success"] and llm_result["question"]:
        question_text = html.escape(llm_result["question"])

    preamble = ""
    if is_first_differentiator:
        preamble = "**GENERAL QUESTIONS COMPLETED**\n\nI've reviewed your information so far.\n\n"
        hyp_result = generate_preliminary_hypotheses_text(qe.coverage_summary_text(coverage), category)
        if hyp_result["success"] and hyp_result["content"]:
            preamble += f"**Preliminary considerations (AI-generated, not a diagnosis):**\n{html.escape(hyp_result['content'])}\n\n"
        preamble += "A few more targeted questions will help refine this analysis:\n\n"

    response_text = f"{preamble}{question_text}"
    _append_assistant_message(conversation, response_text)
    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,
        agent_type="specific_questions_analyst",
        confidence_score=0.85,
        severity_assessment="medium",
        suggestions=[],
        follow_up_questions=[],
    )


# ---------------------------------------------------------------------------
# Phase 4: Classification
# ---------------------------------------------------------------------------

def generate_enhanced_diagnosis_summary(structured_data: Dict[str, Any], classification_result: Dict[str, Any]) -> str:
    """Builds the diagnosis summary. Free-text fields that originate from user
    input are HTML-escaped; everything else (canonicalized labels, our own
    condition names/descriptions) comes from a controlled vocabulary."""

    motivo_consulta = html.escape(str(structured_data.get("motivo_consulta", "medical consultation")))
    enfermedad_actual = structured_data.get("enfermedad_actual", {})
    sintoma_principal = html.escape(str(enfermedad_actual.get("sintoma_principal", "unspecified symptom")))
    inicio = enfermedad_actual.get("inicio", "not specified")
    intensidad = enfermedad_actual.get("intensidad", "not specified")

    antecedentes = structured_data.get("antecedentes_personales", [])
    sintomas_asociados = structured_data.get("sintomas_asociados", [])

    primary_category = classification_result.get("primary_category", "other")
    confidence_score = classification_result.get("confidence_score", 0.0)
    urgency_level = classification_result.get("urgency_level", "medium")
    recommendations = classification_result.get("recommendations", [])
    conditions = classification_result.get("conditions", [])

    category_names = {
        "neurological": "Neurological", "cardiovascular": "Cardiovascular", "respiratory": "Respiratory",
        "gastrointestinal": "Gastrointestinal", "musculoskeletal": "Musculoskeletal",
        "dermatological": "Dermatological", "psychiatric": "Psychiatric", "other": "General",
    }
    category_display = category_names.get(primary_category, "General")

    low_confidence = confidence_score < 0.5
    if low_confidence:
        conditions_header = "**LOW CONFIDENCE DIFFERENTIAL DIAGNOSIS**"
        confidence_display = f"Low ({confidence_score * 100:.0f}%)"
        confidence_note = (
            "\n*Note: Model confidence is below 50%. The following are broad differential "
            "possibilities, not ranked probabilities. Clinical evaluation is strongly recommended.*\n"
        )
    else:
        conditions_header = "**MOST LIKELY CONDITIONS:**"
        confidence_display = f"{confidence_score * 100:.0f}%"
        confidence_note = ""

    lines: List[str] = ["**MEDICAL ANALYSIS COMPLETED**", ""]
    lines.append("**SUMMARY OF COLLECTED INFORMATION:**")
    lines.append(f"- **Reason for consultation:** {motivo_consulta}")
    lines.append(f"- **Main symptom:** {sintoma_principal}")
    lines.append(f"- **Duration:** {inicio}")
    if intensidad and intensidad != "not specified":
        lines.append(f"- **Intensity:** {intensidad}")
    if antecedentes:
        lines.append(f"- **Medical history:** {', '.join(antecedentes[:3])}")
    if sintomas_asociados:
        lines.append(f"- **Associated symptoms:** {', '.join(sintomas_asociados[:5])}")
    lines.append("")

    lines.append("**MEDICAL CLASSIFICATION:**")
    lines.append(f"- **Category:** {category_display}")
    lines.append(f"- **Analysis confidence:** {confidence_display}")
    lines.append(f"- **Urgency level:** {urgency_level.upper()}")
    lines.append("")

    lines.append(conditions_header)
    if confidence_note:
        lines.append(confidence_note)
    for i, condition in enumerate(conditions[:3], 1):
        prob_display = f"{condition['probability_share'] * 100:.0f}%"
        lines.append(f"**{i}. {condition['name']}** ({prob_display})")
        lines.append(f"   - {condition['description']}")
        if condition.get("indicators"):
            readable = [ind.replace('_', ' ') for ind in condition["indicators"][:3]]
            lines.append(f"   - Indicators: {', '.join(readable)}")
        lines.append("")

    if recommendations:
        lines.append("**RECOMMENDATIONS:**")
        for rec in recommendations[:4]:
            lines.append(f"- {rec}")
        lines.append("")

    lines.append("**NEXT STEPS:**")
    if urgency_level in ("critical", "high"):
        lines.append("- **CONSULT A DOCTOR IMMEDIATELY**")
        lines.append("- Consider going to emergency care if symptoms worsen")
    elif urgency_level == "medium":
        lines.append("- **Schedule a medical appointment in the next 2-3 days**")
        lines.append("- Monitor how your symptoms evolve")
    else:
        lines.append("- **Monitor symptoms and seek care if they worsen**")
        lines.append("- Consider a routine medical consultation")
    lines.append("")

    lines.append("**IMPORTANT DISCLAIMER:**")
    lines.append("- This analysis is based on AI and structured conversation data")
    lines.append("- It does **NOT** replace professional medical diagnosis")
    lines.append("- Always consult a doctor for a definitive diagnosis and treatment plan")

    return "\n".join(lines)


def _build_fallback_diagnosis(conversation: Dict[str, Any]) -> str:
    """Used only if the classification pipeline itself throws. Reuses the same
    deterministic evidence engine as the main path — no separate keyword list."""
    coverage = conversation.get("coverage") or qe.new_coverage_map()
    symptoms = coverage.get("symptoms", set())
    rule_scores = sk.score_category_evidence(symptoms)
    category = max(rule_scores, key=rule_scores.get) if any(rule_scores.values()) else "other"
    conditions = sk.rank_conditions(category, symptoms)

    lines = [
        "**MEDICAL ANALYSIS COMPLETED**", "",
        "**SUMMARY OF COLLECTED INFORMATION:**",
        f"- **Medical category assessed:** {category.title()}",
        f"- **General questions answered:** {len(coverage.get('general_asked', []))}",
        f"- **Specific questions answered:** {len(coverage.get('differentiator_asked', []))}",
        "",
        "**LOW CONFIDENCE DIFFERENTIAL DIAGNOSIS**",
        "*Based on rule-based evidence matching only — the classification model was unavailable*",
        "",
        "**POSSIBLE CONDITIONS (estimated, not definitive):**", "",
    ]
    for i, condition in enumerate(conditions[:3], 1):
        lines.append(f"**{i}. {condition['name']}** (estimated range: {condition['probability_share'] * 100:.0f}%)")
        lines.append(f"   - {condition['description']}")
        lines.append("")
    lines += [
        "**RECOMMENDATIONS:**",
        "- Schedule an appointment with a healthcare professional for complete evaluation",
        "- Monitor symptom evolution and document any changes",
        "- Seek immediate care if symptoms worsen significantly",
        "",
        "**IMPORTANT DISCLAIMER:**",
        "- This analysis is generated by AI based on information you provided",
        "- It does NOT constitute a professional medical diagnosis",
        "- Always consult a certified doctor for definitive diagnosis and treatment",
    ]
    return "\n".join(lines)


async def handle_classification(conversation_id: str, message: str) -> ChatResponse:
    conversation = CONVERSATIONS[conversation_id]
    # Set terminal state BEFORE processing to prevent re-entry loops if anything below fails.
    conversation["state"] = ConversationState.CLASSIFICATION_COMPLETE

    try:
        from app.services.classification_service import classification_model
        from app.services.data_structuring_service import data_structuring_service

        structured_medical_data = await data_structuring_service.structure_conversation_data(conversation)
        conversation["structured_medical_data"] = structured_medical_data

        coverage = conversation["coverage"]
        classification_input = {
            "chief_complaint": structured_medical_data.get("motivo_consulta", "general consultation"),
            "symptoms": [structured_medical_data["enfermedad_actual"]["sintoma_principal"]]
                        + structured_medical_data.get("sintomas_asociados", []),
            "canonical_symptoms": sorted(coverage["symptoms"]),
            "quality": coverage.get("quality"),
            "laterality": coverage.get("laterality"),
            "severity": coverage.get("severity"),
            "duration": coverage.get("onset"),
            "history": structured_medical_data.get("antecedentes_personales", [])
                       + structured_medical_data.get("antecedentes_familiares", []),
            "current_medications": structured_medical_data.get("medicamentos_actuales", []),
            "habits": structured_medical_data.get("habitos", {}),
            "associated_factors": structured_medical_data.get("factores_agravantes", [])
                                  + structured_medical_data.get("factores_aliviantes", []),
        }

        classification_result = await classification_model.classify(classification_input)
        conversation["classification_result"] = classification_result
        conversation["final_structured_data"] = {
            "structured_medical_data": structured_medical_data,
            "classification_input": classification_input,
            "classification_result": classification_result,
            "processing_timestamp": datetime.now().isoformat(),
        }

        response_text = generate_enhanced_diagnosis_summary(structured_medical_data, classification_result)
        _append_assistant_message(conversation, response_text)

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            agent_type="evidence_based_classifier",
            confidence_score=classification_result.get("confidence_score", 0.0),
            severity_assessment=classification_result.get("urgency_level", "medium"),
            predicted_condition=classification_result.get("primary_category", "Analysis completed"),
            suggestions=classification_result.get("recommendations", []),
            follow_up_questions=[],
            is_diagnosis=True,
        )

    except Exception as e:
        print(f"ERROR in classification pipeline: {e}")
        response_text = _build_fallback_diagnosis(conversation)
        _append_assistant_message(conversation, response_text)
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            agent_type="fallback_medical_classifier",
            confidence_score=0.3,
            severity_assessment="medium",
            suggestions=["Consult a medical professional for a complete and definitive evaluation"],
            follow_up_questions=[],
            is_diagnosis=True,
        )


# ---------------------------------------------------------------------------
# Phase 5: Post-diagnosis conversation
# ---------------------------------------------------------------------------

def generate_contextual_response(message: str, category: str, classification_result: Dict) -> str:
    message_lower = message.lower()

    if any(word in message_lower for word in ['medication', 'medicine', 'medicamento', 'medicina', 'pill', 'pastilla', 'treatment', 'tratamiento']):
        return (f"Regarding medications for {category} conditions, it's important that you consult with a doctor "
                "before taking any medication. Based on my analysis, general recommendations include monitoring "
                "symptoms and professional medical evaluation.")

    elif any(word in message_lower for word in ['when', 'doctor', 'médico', 'physician', 'appointment', 'consulta']):
        severity = classification_result.get("urgency_level", "medium")
        if severity in ("critical", "high"):
            return "Given the nature of your symptoms, I recommend that you see a doctor as soon as possible, preferably today."
        return "I recommend that you schedule an appointment with your doctor in the next few days for a more detailed evaluation."

    return (f"I understand your concern. Based on my analysis related to {category}, I suggest you continue "
            "monitoring your symptoms and consult with a medical professional for a definitive diagnosis.")


async def handle_post_classification_conversation(conversation_id: str, message: str) -> ChatResponse:
    conversation = CONVERSATIONS[conversation_id]
    classification_result = conversation.get("classification_result", {})
    category = classification_result.get("primary_category", "general")

    response_text = generate_contextual_response(message, category, classification_result)
    _append_assistant_message(conversation, response_text)

    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,
        agent_type="post_classification_advisor",
        confidence_score=0.7,
        severity_assessment="low",
        suggestions=["Consult a medical specialist", "Monitor your symptoms", "Follow the general recommendations"],
        follow_up_questions=[],
    )


# ---------------------------------------------------------------------------
# Auxiliary endpoints
# ---------------------------------------------------------------------------

@router.get("/{conversation_id}/history")
async def get_conversation_history(conversation_id: str):
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation = CONVERSATIONS[conversation_id]
    return {
        "conversation_id": conversation_id,
        "state": conversation["state"],
        "consent_given": conversation["consent_given"],
        "messages": conversation["messages"],
        "created_at": conversation["created_at"],
    }


@router.get("/conversations/list")
async def list_conversations():
    return {
        "conversations": [
            {
                "conversation_id": conv_id,
                "state": conv_data["state"],
                "consent_given": conv_data["consent_given"],
                "message_count": len(conv_data["messages"]),
                "created_at": conv_data["created_at"],
            }
            for conv_id, conv_data in CONVERSATIONS.items()
        ],
        "total": len(CONVERSATIONS),
    }


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversation not found")
    del CONVERSATIONS[conversation_id]
    return {"message": f"Conversation {conversation_id} deleted successfully"}


@router.get("/{conversation_id}/structured-data")
async def get_structured_medical_data(conversation_id: str):
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation = CONVERSATIONS[conversation_id]

    if "final_structured_data" not in conversation:
        from app.services.data_structuring_service import data_structuring_service
        try:
            structured_data = await data_structuring_service.structure_conversation_data(conversation)
            conversation["structured_medical_data"] = structured_data
            return {
                "conversation_id": conversation_id,
                "structured_data": structured_data,
                "status": "newly_structured",
                "format_version": structured_data.get("metadata", {}).get("format_version", "2.0"),
                "processing_method": structured_data.get("metadata", {}).get("processing_method", "unknown"),
                "ready_for_classification": True,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error structuring data: {str(e)}")

    final_data = conversation["final_structured_data"]
    return {
        "conversation_id": conversation_id,
        "structured_data": final_data["structured_medical_data"],
        "classification_input": final_data.get("classification_input", {}),
        "classification_result": final_data.get("classification_result", {}),
        "status": "previously_structured",
        "processing_timestamp": final_data.get("processing_timestamp"),
        "ready_for_classification": True,
        "classification_completed": True,
    }


@router.post("/{conversation_id}/reprocess-structure")
async def reprocess_structured_data(conversation_id: str):
    if conversation_id not in CONVERSATIONS:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation = CONVERSATIONS[conversation_id]

    try:
        from app.services.data_structuring_service import data_structuring_service
        conversation.pop("structured_medical_data", None)
        conversation.pop("final_structured_data", None)

        structured_data = await data_structuring_service.structure_conversation_data(conversation)
        conversation["structured_medical_data"] = structured_data

        return {
            "conversation_id": conversation_id,
            "structured_data": structured_data,
            "status": "reprocessed",
            "message": "Medical data restructured successfully",
            "format_version": structured_data.get("metadata", {}).get("format_version", "2.0"),
            "processing_method": structured_data.get("metadata", {}).get("processing_method", "unknown"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reprocessing structure: {str(e)}")
