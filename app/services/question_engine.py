"""
Adaptive interview engine.

Maintains a "coverage map" that is updated from every user answer (regardless
of which phase asked the question), and selects the next highest-value
question by skipping any slot whose information is already known — either
because the patient volunteered it unprompted, or because it was already
asked and answered earlier in the conversation.

This replaces the old fixed 7-question script + a separate LLM-generated,
keyword-deduplicated 5-question script with a single deterministic engine.
"""

from typing import Dict, List, Optional, Set, Tuple

from app.services import symptom_knowledge as sk


def new_coverage_map() -> Dict:
    return {
        "chief_complaint": None,
        "onset": None,
        "severity": None,
        "quality": None,
        "laterality": None,
        "aggravating_factors": [],
        "relieving_factors": [],
        "medications": None,
        "past_history": [],
        "family_history": None,
        "habits": None,
        "symptoms": set(),
        "frequency": None,
        "prior_diagnosis": None,
        "exertion_pattern": None,
        "episode_duration": None,
        "stimulant_use": None,
        "meal_relation": None,
        "diet_changes": None,
        "movement_pattern": None,
        "radiation": None,
        "lesion_evolution": None,
        "exposure": None,
        "spreading_pattern": None,
        "mood_duration": None,
        "function_impact": None,
        "triggers": None,
        "timing_pattern": None,
        "raw_answers": [],
        "general_asked": [],          # GENERAL_SLOTS keys already asked, in order
        "differentiator_asked": [],   # differentiator keys already asked, in order
    }


def ingest_answer(coverage: Dict, text: str, is_chief_complaint: bool = False) -> None:
    """Updates the coverage map deterministically from one piece of free text.

    Called on every user message in both interview phases, so information
    volunteered ahead of being asked is captured immediately and never re-asked.
    """
    text = text.strip()
    if not text:
        return
    coverage["raw_answers"].append(text)

    if is_chief_complaint and not coverage["chief_complaint"]:
        coverage["chief_complaint"] = text

    coverage["symptoms"] |= sk.detect_symptoms(text)

    onset = sk.detect_onset(text)
    if onset and not coverage["onset"]:
        coverage["onset"] = onset

    severity = sk.detect_severity(text)
    if severity and not coverage["severity"]:
        coverage["severity"] = severity

    quality = sk.detect_quality(text)
    if quality and not coverage["quality"]:
        coverage["quality"] = quality

    laterality = sk.detect_laterality(text)
    if laterality and not coverage["laterality"]:
        coverage["laterality"] = laterality

    aggravating = sk.detect_aggravating_factors(text)
    if aggravating:
        coverage["aggravating_factors"] = list(dict.fromkeys(coverage["aggravating_factors"] + aggravating))

    relieving = sk.detect_relieving_factors(text)
    if relieving:
        coverage["relieving_factors"] = list(dict.fromkeys(coverage["relieving_factors"] + relieving))

    meds = sk.detect_medications(text)
    if meds is not None and coverage["medications"] is None:
        coverage["medications"] = meds

    history = sk.detect_medical_history(text)
    if history:
        coverage["past_history"] = list(dict.fromkeys(coverage["past_history"] + history))

    if sk.habits_mentioned(text) and not coverage["habits"]:
        coverage["habits"] = sk.detect_habits(text)

    for key, value in sk.detect_differentiator_signals(text).items():
        if not coverage.get(key):
            coverage[key] = value

    if "family_history" not in coverage or coverage["family_history"] is None:
        text_lower = text.lower()
        if any(p in text_lower for p in ["family history", "my mother", "my father", "runs in my family",
                                          "antecedentes familiares", "mi madre", "mi padre"]):
            coverage["family_history"] = text[:200]
        elif any(p in text_lower for p in ["no family history", "nobody in my family", "sin antecedentes familiares"]):
            coverage["family_history"] = "none reported"


def _is_filled(coverage: Dict, detect_keys: List[str], asked_list: List[str], slot_key: str) -> bool:
    """A slot counts as covered if it was already asked (even if the answer was
    a plain "no"), OR if any of its detect_keys are already known — checking
    coverage["symptoms"] for canonical symptom names and the coverage dict
    directly for everything else."""
    if slot_key in asked_list:
        return True
    for key in detect_keys:
        if key == "associated_symptoms":
            if len(coverage["symptoms"]) >= 2:
                return True
            continue
        if key == "location":
            continue
        if key in sk.SYMPTOM_PHRASES:
            if key in coverage["symptoms"]:
                return True
            continue
        if coverage.get(key):
            return True
    return False


def get_next_general_question(coverage: Dict) -> Optional[Tuple[str, str]]:
    """Returns (slot_key, question_text) for the next unfilled general slot,
    or None once all slots are covered or the question budget is exhausted."""
    if len(coverage["general_asked"]) >= sk.MAX_GENERAL_QUESTIONS:
        return None

    for slot in sk.GENERAL_SLOTS:
        if _is_filled(coverage, slot.detect_keys, coverage["general_asked"], slot.key):
            continue
        return slot.key, slot.question
    return None


def mark_general_asked(coverage: Dict, slot_key: str) -> None:
    if slot_key not in coverage["general_asked"]:
        coverage["general_asked"].append(slot_key)


def tentative_category(coverage: Dict) -> str:
    """Deterministic rule-based category guess from symptoms collected so far."""
    chief = coverage.get("chief_complaint") or ""
    scores = sk.score_category_evidence(coverage["symptoms"])
    if not any(scores.values()):
        return "other"
    return max(scores, key=scores.get)


def get_next_differentiator_question(coverage: Dict, category: str) -> Optional[Tuple[str, str]]:
    if len(coverage["differentiator_asked"]) >= sk.MAX_DIFFERENTIATOR_QUESTIONS:
        return None

    slots = sk.CATEGORY_DIFFERENTIATORS.get(category, sk.CATEGORY_DIFFERENTIATORS["other"])
    for slot in slots:
        if _is_filled(coverage, slot.detect_keys, coverage["differentiator_asked"], slot.key):
            continue
        return slot.key, slot.question
    return None


def mark_differentiator_asked(coverage: Dict, slot_key: str) -> None:
    if slot_key not in coverage["differentiator_asked"]:
        coverage["differentiator_asked"].append(slot_key)


def coverage_summary_text(coverage: Dict) -> str:
    """Human-readable summary of everything known so far — fed to the LLM only
    for conversational phrasing, never used to drive logic."""
    lines = []
    if coverage["chief_complaint"]:
        lines.append(f"Chief complaint: {coverage['chief_complaint']}")
    if coverage["onset"]:
        lines.append(f"Onset: {coverage['onset']}")
    if coverage["severity"]:
        lines.append(f"Severity: {coverage['severity']}")
    if coverage["quality"]:
        lines.append(f"Quality: {coverage['quality']}")
    if coverage["laterality"]:
        lines.append(f"Laterality: {coverage['laterality']}")
    if coverage["symptoms"]:
        lines.append(f"Symptoms detected: {', '.join(sorted(coverage['symptoms']))}")
    if coverage["aggravating_factors"]:
        lines.append(f"Aggravating factors: {', '.join(coverage['aggravating_factors'])}")
    if coverage["relieving_factors"]:
        lines.append(f"Relieving factors: {', '.join(coverage['relieving_factors'])}")
    if coverage["medications"]:
        lines.append(f"Medications: {', '.join(coverage['medications'])}")
    if coverage["past_history"]:
        lines.append(f"Past history: {', '.join(coverage['past_history'])}")
    return "\n".join(lines) if lines else "No information collected yet."


def already_known_text(coverage: Dict) -> str:
    """Short bullet list of topics already covered, for the LLM phrasing prompt."""
    topics = []
    for slot_key in coverage["general_asked"]:
        topics.append(slot_key.replace("_", " "))
    for slot_key in coverage["differentiator_asked"]:
        topics.append(slot_key.replace("_", " "))
    if coverage["symptoms"]:
        topics.append("symptoms: " + ", ".join(sorted(coverage["symptoms"])))
    return "; ".join(topics) if topics else "nothing yet"
