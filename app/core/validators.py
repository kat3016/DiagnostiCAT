"""
Reports LLM provider availability.

The diagnosis pipeline (extraction, classification, ranking) is deterministic
and rule-based — see app/services/symptom_knowledge.py — and does not require
an LLM. When configured, NVIDIA Nemotron or OpenAI is used only for
conversational question phrasing and an optional hypotheses narrative.
"""

from app.core.config import settings


def get_configuration_status() -> dict:
    """Returns whether an LLM provider is configured, without raising."""
    nemotron_configured = bool(settings.NVIDIA_API_KEY)
    openai_configured = bool(settings.OPENAI_API_KEY)
    valid = nemotron_configured or openai_configured

    errors = []
    if not valid:
        errors.append(
            "No LLM provider configured (NVIDIA_API_KEY or OPENAI_API_KEY). "
            "Question phrasing will use default templates and the AI hypotheses "
            "narrative will be omitted; the diagnosis logic itself is unaffected."
        )

    provider = "nemotron" if nemotron_configured else ("openai" if openai_configured else "none")

    return {
        "provider": provider,
        "nemotron_configured": nemotron_configured,
        "openai_configured": openai_configured,
        "valid": valid,
        "errors": errors,
    }
