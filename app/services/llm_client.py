"""
LLM client — single entry point for all LLM calls (NVIDIA Nemotron with OpenAI fallback).

Replaces the old app/crew/hybrid_agent.py now that the unused CrewAI orchestration
layer has been removed. This is the one place that talks to an LLM provider.
"""

from langchain_openai import ChatOpenAI
from app.core.config import settings

# Deterministic temperature for extraction/classification — these tasks have a
# correct answer and must not vary run-to-run on identical input.
DETERMINISTIC_TEMPERATURE = 0.0

# Slightly creative temperature for conversational question phrasing only.
CONVERSATIONAL_TEMPERATURE = 0.3


def create_llm_client(temperature: float = DETERMINISTIC_TEMPERATURE):
    """Creates an LLM client, preferring NVIDIA Nemotron and falling back to OpenAI.

    Raises if neither provider is configured — callers must catch this and apply
    their own explicit degraded-mode handling rather than silently guessing.
    """

    if settings.NVIDIA_API_KEY:
        return ChatOpenAI(
            model=settings.NEMOTRON_MODEL,
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=temperature,
            timeout=60,
            max_retries=2,
        ), "nvidia"

    if settings.OPENAI_API_KEY:
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=temperature,
            timeout=60,
            max_retries=2,
        ), "openai"

    raise RuntimeError(
        "No LLM provider configured (missing NVIDIA_API_KEY and OPENAI_API_KEY). "
        "Extraction/classification will run in degraded keyword-only mode."
    )


def generate_differentiator_question(missing_slot_description: str, context_summary: str, already_known: str) -> dict:
    """Asks the LLM to phrase ONE natural-language question for a specific missing
    clinical data point, given everything already known (so it never re-asks it).
    """
    try:
        llm, provider = create_llm_client(temperature=CONVERSATIONAL_TEMPERATURE)

        prompt = f"""You are a physician conducting a focused follow-up interview.

INFORMATION ALREADY COLLECTED (do not ask about any of this again):
{already_known}

CLINICAL CONTEXT:
{context_summary}

Write exactly ONE natural, specific question in English to obtain this missing piece of information:
{missing_slot_description}

Respond with ONLY the question text, ending in a question mark. No preamble, no explanation."""

        response = llm.invoke(prompt)
        question = response.content.strip().strip('"')
        if "?" not in question:
            question = question.rstrip(".") + "?"
        return {"success": True, "question": question, "provider": provider}

    except Exception as e:
        return {"success": False, "error": str(e), "question": None}


def generate_preliminary_hypotheses_text(context_summary: str, category_hint: str) -> dict:
    """Best-effort LLM narrative of preliminary hypotheses for display purposes only.

    This text is NEVER used to drive question selection or classification logic —
    those are deterministic (see symptom_knowledge.py / question_engine.py). If this
    call fails, callers should simply omit the narrative rather than fall back to
    parsing free text.
    """
    try:
        llm, provider = create_llm_client(temperature=CONVERSATIONAL_TEMPERATURE)

        prompt = f"""You are a specialist physician. Based on this clinical picture, list up to 3 preliminary
differential hypotheses (NOT a definitive diagnosis, one short line each, in English).

CLINICAL PICTURE:
{context_summary}

LIKELY CATEGORY (for reference only): {category_hint}

Respond with ONLY a numbered list of up to 3 short hypotheses, no other text."""

        response = llm.invoke(prompt)
        return {"success": True, "content": response.content.strip(), "provider": provider}

    except Exception as e:
        return {"success": False, "error": str(e), "content": None}
