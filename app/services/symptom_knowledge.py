"""
Canonical medical knowledge base — the single source of truth for symptom
detection, category classification, condition ranking, and adaptive question
selection.

Design decision: detection here is deterministic (bilingual phrase matching),
not LLM-based. Diagnosis-relevant logic must never silently change behavior
based on whether an LLM API key happens to be configured. LLM calls elsewhere
in the app (see llm_client.py) are used only for conversational phrasing of
questions/narratives — never to decide which symptom was reported or which
category/condition wins. This also makes the pipeline testable and reproducible.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import re


# ---------------------------------------------------------------------------
# 1. Canonical symptom/feature vocabulary (bilingual EN+ES phrase -> key)
# ---------------------------------------------------------------------------

SYMPTOM_PHRASES: Dict[str, List[str]] = {
    # Neurological
    "headache": ["headache", "head pain", "head hurts", "head aches", "cefalea", "dolor de cabeza", "jaqueca"],
    "migraine_history": ["history of migraine", "migraines before", "diagnosed with migraine", "antecedente de migraña", "historia de migraña"],
    "photophobia": ["photophobia", "light sensitiv", "sensitive to light", "bright light", "light bother", "light hurts", "light makes it worse", "sensibilidad a la luz", "molesta la luz", "la luz me molesta"],
    "phonophobia": ["phonophobia", "sound sensitiv", "noise bother", "sound bother", "noise hurts", "sound makes it worse", "sensibilidad al ruido", "molesta el ruido", "molesta el sonido"],
    "aura": ["aura", "visual aura", "see spots before", "flashing lights before", "zigzag lines", "aura visual"],
    "visual_disturbance": ["blurred vision", "visual changes", "double vision", "vision changes", "visión borrosa", "vision borrosa"],
    "throbbing_quality": ["throbbing", "pulsating", "pounding", "pulsátil", "pulsante", "palpitante"],
    "pressing_quality": ["pressing", "band-like", "tight band", "squeezing", "vice-like", "opresivo", "como una banda"],
    "sharp_quality": ["sharp pain", "stabbing pain", "punzante", "dolor agudo"],
    "burning_quality": ["burning sensation", "ardor", "quemante"],
    "dull_quality": ["dull pain", "dull ache", "dolor sordo"],
    "unilateral": ["one side of my head", "one-sided", "unilateral", "only on the left", "only on the right", "half of my head", "un lado de la cabeza", "solo un lado"],
    "bilateral": ["both sides of my head", "bilateral", "whole head", "all over my head", "ambos lados", "toda la cabeza"],
    "neck_stiffness": ["neck stiffness", "stiff neck", "rigidez cervical", "rigidez de cuello"],
    "focal_weakness": ["weakness in my arm", "weakness in my leg", "numbness", "can't move my", "limb weakness", "debilidad en", "entumecimiento"],
    "thunderclap_onset": ["worst headache of my life", "sudden severe headache", "came on instantly", "worst headache i've ever had", "el peor dolor de cabeza"],
    "vertigo_dizziness": ["dizzy", "dizziness", "lightheaded", "vertigo", "mareo", "mareado", "vértigo"],

    # Systemic
    "fever": ["fever", "feverish", "high temperature", "fiebre", "temperatura alta", "calentura"],
    "chills": ["chills", "shivering", "escalofríos", "escalofrios"],
    "fatigue": ["fatigue", "tired", "exhausted", "extreme tiredness", "weakness all over", "cansancio", "fatiga", "agotamiento"],
    "nausea": ["nausea", "nauseous", "feel sick", "queasy", "náuseas", "nauseas"],
    "vomiting": ["vomit", "vomiting", "threw up", "vómito", "vomito"],
    "weight_loss": ["weight loss", "losing weight", "pérdida de peso"],

    # Respiratory
    "cough": ["cough", "coughing", "tos", "toser"],
    "sputum": ["phlegm", "sputum", "coughing up mucus", "flema", "moco"],
    "sore_throat": ["sore throat", "throat pain", "throat hurts", "dolor de garganta"],
    "nasal_congestion": ["congestion", "runny nose", "stuffy nose", "congestión nasal", "moqueo", "nariz tapada"],
    "wheezing": ["wheezing", "whistling sound when breathing", "sibilancia"],
    "shortness_of_breath": ["shortness of breath", "difficulty breathing", "breathless", "can't breathe", "falta de aire", "dificultad para respirar", "disnea", "ahogo"],

    # Cardiovascular
    "chest_pain": ["chest pain", "chest hurts", "chest tightness", "dolor en el pecho", "dolor torácico", "dolor de pecho"],
    "palpitations": ["palpitations", "heart racing", "heart pounding", "fast heartbeat", "palpitaciones", "corazón acelerado"],
    "irregular_heartbeat": ["irregular heartbeat", "skipping beats", "heart skips a beat", "latido irregular"],
    "syncope": ["fainted", "fainting", "passed out", "loss of consciousness", "desmayo", "pérdida de conciencia"],
    "edema": ["swelling in my legs", "leg swelling", "ankle swelling", "edema", "hinchazón de piernas"],

    # Gastrointestinal
    "abdominal_pain": ["stomach pain", "abdominal pain", "belly pain", "stomach hurts", "stomach ache", "dolor de estómago", "dolor abdominal", "dolor de barriga"],
    "heartburn": ["heartburn", "acid reflux", "burning in my chest after eating", "acidez", "reflujo"],
    "diarrhea": ["diarrhea", "loose stools", "diarrea"],
    "constipation": ["constipation", "can't poop", "estreñimiento", "constipacion"],
    "blood_in_stool_or_vomit": ["blood in my stool", "blood in my vomit", "vomiting blood", "black stool", "sangre en las heces", "sangre en el vómito"],
    "bloating": ["bloating", "bloated", "distension", "hinchazón abdominal"],

    # Musculoskeletal
    "joint_pain": ["joint pain", "joint ache", "arthritis pain", "knee pain", "hip pain", "dolor articular", "dolor de articulaciones"],
    "muscle_pain": ["muscle pain", "muscle ache", "myalgia", "dolor muscular", "músculos adoloridos"],
    "back_pain": ["back pain", "backache", "lower back pain", "dolor de espalda", "dolor lumbar"],
    "swelling_joint": ["swollen joint", "joint swelling", "redness and warmth in the joint", "hinchazón en la articulación"],
    "recent_injury": ["had an injury", "i fell", "sprained", "twisted my", "lesión reciente", "me caí", "me torcí"],

    # Dermatological
    "rash": ["rash", "skin rash", "hives", "skin eruption", "erupción", "sarpullido", "urticaria"],
    "itching": ["itchy", "itching", "picazón", "comezón"],
    "skin_lesion": ["a lesion on my skin", "sore on my skin", "lesión en la piel", "llaga"],

    # Psychiatric
    "anxiety": ["anxiety", "anxious", "panic attack", "panic", "ansiedad", "pánico", "ataque de pánico"],
    "depression": ["depression", "depressed", "low mood", "depresión", "deprimido"],
    "insomnia": ["can't sleep", "insomnia", "trouble sleeping", "insomnio"],
}

# Negation cues that flip a detected phrase from "present" to explicitly absent.
NEGATION_CUES = [
    "no ", "not ", "never ", "don't ", "doesn't ", "haven't ", "hasn't ",
    "without ", "denies ", "no tengo", "no he tenido", "sin ",
]


def detect_symptoms(text: str) -> Set[str]:
    """Deterministically detects canonical symptom keys present in free text.

    Performs a simple negation check: if a negation cue appears within the
    8 words preceding the matched phrase, the symptom is NOT recorded as present.
    """
    text_lower = f" {text.lower()} "
    found: Set[str] = set()

    for canonical, phrases in SYMPTOM_PHRASES.items():
        for phrase in phrases:
            idx = text_lower.find(phrase)
            if idx == -1:
                continue
            window_start = max(0, idx - 40)
            preceding = text_lower[window_start:idx]
            # Negation never crosses a sentence boundary (a denial earlier in
            # the message must not suppress an affirmed symptom in the next sentence).
            last_boundary = max(preceding.rfind('.'), preceding.rfind('!'), preceding.rfind('?'), preceding.rfind('\n'))
            if last_boundary != -1:
                preceding = preceding[last_boundary + 1:]
            negated = any(cue in preceding for cue in NEGATION_CUES)
            if not negated:
                found.add(canonical)
            break

    return found


def detect_severity(text: str) -> Optional[str]:
    """Returns a normalized severity label, or None if not mentioned."""
    text_lower = text.lower()

    numeric_patterns = [
        r'(\d{1,2})\s*(?:/|out\s+of)\s*10',
        r'(\d{1,2})\s*on\s*(?:a\s*)?(?:scale|pain\s*scale)',
        r'intensity\s*(?:of\s*)?[:\-]?\s*(\d{1,2})',
        r'pain\s*(?:level|score|rating)\s*(?:of\s*)?[:\-]?\s*(\d{1,2})',
        r"(?:i'?d?\s*)?(?:say|rate|give)\s*(?:it\s*)?(?:a\s*)?(\d{1,2})\b",
    ]
    for pattern in numeric_patterns:
        m = re.search(pattern, text_lower)
        if m:
            score = int(m.group(1))
            if 1 <= score <= 10:
                return f"{score}/10"

    if any(w in text_lower for w in ['unbearable', 'excruciating', 'worst', 'terrible', 'horrible', 'agonizing', 'insoportable']):
        return "10/10 (unbearable)"
    if any(w in text_lower for w in ['severe', 'very strong', 'very bad', 'very intense', 'really bad', 'severo', 'muy fuerte', 'muy intenso']):
        return "severe"
    if any(w in text_lower for w in ['strong', 'intense', 'significant', 'quite bad', 'pretty bad', 'intenso', 'fuerte', 'bastante']):
        return "moderate-severe"
    if any(w in text_lower for w in ['moderate', 'medium', 'fairly', 'noticeable', 'moderado', 'regular']):
        return "moderate"
    if any(w in text_lower for w in ['mild', 'slight', 'minor', 'light pain', 'a little', 'a bit', 'not too bad', 'leve', 'ligero', 'poco', 'suave']):
        return "mild"

    return None


def severity_to_score(severity: Optional[str]) -> float:
    """Maps a severity label to a 0-1 numeric weight for ranking purposes."""
    if not severity:
        return 0.5
    if severity.startswith("10") or "unbearable" in severity:
        return 1.0
    m = re.match(r'(\d{1,2})/10', severity)
    if m:
        return min(int(m.group(1)) / 10, 1.0)
    return {"severe": 0.85, "moderate-severe": 0.7, "moderate": 0.5, "mild": 0.25}.get(severity, 0.5)


def detect_onset(text: str) -> Optional[str]:
    """Detects symptom onset/duration — bilingual."""
    text_lower = text.lower()
    patterns = [
        (r'(\d+)\s*days?\s*ago', lambda m: f"{m.group(1)} day(s)"),
        (r'(\d+)\s*weeks?\s*ago', lambda m: f"{m.group(1)} week(s)"),
        (r'(\d+)\s*months?\s*ago', lambda m: f"{m.group(1)} month(s)"),
        (r'(\d+)\s*hours?\s*ago', lambda m: f"{m.group(1)} hour(s)"),
        (r'for\s+(\d+)\s*days?', lambda m: f"{m.group(1)} day(s)"),
        (r'for\s+(\d+)\s*weeks?', lambda m: f"{m.group(1)} week(s)"),
        (r'for\s+(\d+)\s*months?', lambda m: f"{m.group(1)} month(s)"),
        (r'for\s+(\d+)\s*hours?', lambda m: f"{m.group(1)} hour(s)"),
        (r'since\s+yesterday', lambda m: "approximately 1 day"),
        (r'since\s+this\s+morning', lambda m: "a few hours"),
        (r'since\s+last\s+night', lambda m: "approximately 1 day"),
        (r'since\s+last\s+week', lambda m: "approximately 1 week"),
        (r'(?:started|began|began\s+feeling\s+it)\s+today', lambda m: "less than 1 day"),
        (r'(?:started|began)\s+yesterday', lambda m: "approximately 1 day"),
        (r'(?:started|began)\s+last\s+night', lambda m: "approximately 1 day"),
        (r'(?:started|began)\s+this\s+morning', lambda m: "a few hours"),
        (r'(?:started|began)\s+this\s+afternoon', lambda m: "a few hours"),
        (r'(?:started|began)\s+this\s+evening', lambda m: "a few hours"),
        (r'this\s+morning', lambda m: "a few hours"),
        (r'hace\s+(\d+)\s*días?', lambda m: f"{m.group(1)} day(s)"),
        (r'hace\s+(\d+)\s*semanas?', lambda m: f"{m.group(1)} week(s)"),
        (r'hace\s+(\d+)\s*mes(?:es)?', lambda m: f"{m.group(1)} month(s)"),
        (r'hace\s+(\d+)\s*horas?', lambda m: f"{m.group(1)} hour(s)"),
        (r'desde\s+ayer', lambda m: "approximately 1 day"),
        (r'desde\s+hoy', lambda m: "less than 1 day"),
        (r'anoche', lambda m: "approximately 1 day"),
    ]
    for pattern, formatter in patterns:
        m = re.search(pattern, text_lower)
        if m:
            return formatter(m)
    return None


def detect_quality(text: str) -> Optional[str]:
    found = detect_symptoms(text)
    for q in ["throbbing_quality", "pressing_quality", "sharp_quality", "burning_quality", "dull_quality"]:
        if q in found:
            return q.replace("_quality", "")
    return None


def detect_laterality(text: str) -> Optional[str]:
    found = detect_symptoms(text)
    if "unilateral" in found:
        return "unilateral"
    if "bilateral" in found:
        return "bilateral"
    return None


_WORD_NUMBERS = {
    "once": 1, "twice": 2, "three times": 3, "four times": 4, "five times": 5,
}


def detect_frequency(text: str) -> Optional[str]:
    text_lower = text.lower()
    if re.search(r'first\s+time|never\s+had\s+this\s+before|primera\s+vez', text_lower):
        return "first episode"
    m = re.search(r'(\d+)\s*times?\s*(?:a|per)\s*(week|month|year)', text_lower)
    if m:
        return f"{m.group(1)} times per {m.group(2)}"
    for phrase, count in _WORD_NUMBERS.items():
        m = re.search(rf'{phrase}\s*(?:a|per)\s*(week|month|year)', text_lower)
        if m:
            return f"{count} times per {m.group(1)}"
    if any(w in text_lower for w in ["recurrent", "keeps happening", "happens often", "regularly", "recurrente", "seguido"]):
        return "recurrent"
    return None


# ---------------------------------------------------------------------------
# 2. Categories — clean, single-concept English labels for zero-shot NLI
# ---------------------------------------------------------------------------

CATEGORIES = [
    "neurological", "cardiovascular", "respiratory", "gastrointestinal",
    "musculoskeletal", "dermatological", "psychiatric", "other",
]

# One concept per label, same language as the input text (English), used with
# hypothesis_template="This patient's symptoms are consistent with {}."
ZERO_SHOT_LABELS: Dict[str, str] = {
    "neurological": "a neurological condition",
    "cardiovascular": "a cardiovascular condition",
    "respiratory": "a respiratory condition",
    "gastrointestinal": "a gastrointestinal condition",
    "musculoskeletal": "a musculoskeletal condition",
    "dermatological": "a skin condition",
    "psychiatric": "a mental health condition",
    "other": "a general condition not specific to one body system",
}
LABEL_TO_CATEGORY = {v: k for k, v in ZERO_SHOT_LABELS.items()}


@dataclass(frozen=True)
class WeightedSymptom:
    symptom: str
    weight: float


# Evidence weights per category — used for deterministic rule-based scoring,
# combined with the zero-shot model score (see classification_service.py).
CATEGORY_SYMPTOM_WEIGHTS: Dict[str, Dict[str, float]] = {
    "neurological": {
        "headache": 1.0, "migraine_history": 1.2, "photophobia": 1.6, "phonophobia": 1.6,
        "aura": 1.6, "throbbing_quality": 1.0, "unilateral": 0.9, "vertigo_dizziness": 0.7,
        "visual_disturbance": 1.0, "neck_stiffness": 0.6, "focal_weakness": 1.3,
        "thunderclap_onset": 1.0, "nausea": 0.35, "vomiting": 0.35,
    },
    "respiratory": {
        "cough": 1.5, "sore_throat": 1.2, "nasal_congestion": 1.1, "wheezing": 1.6,
        "shortness_of_breath": 1.4, "sputum": 1.3, "fever": 0.4, "chills": 0.3,
    },
    "cardiovascular": {
        "chest_pain": 1.5, "palpitations": 1.5, "irregular_heartbeat": 1.4,
        "syncope": 1.3, "edema": 1.1, "shortness_of_breath": 0.5,
    },
    "gastrointestinal": {
        "abdominal_pain": 1.5, "heartburn": 1.3, "diarrhea": 1.3, "constipation": 1.0,
        "bloating": 1.0, "blood_in_stool_or_vomit": 1.4, "nausea": 0.5, "vomiting": 0.5,
    },
    "musculoskeletal": {
        "joint_pain": 1.5, "muscle_pain": 1.5, "back_pain": 1.3, "swelling_joint": 1.2,
        "recent_injury": 1.1,
    },
    "dermatological": {
        "rash": 1.6, "itching": 1.3, "skin_lesion": 1.3,
    },
    "psychiatric": {
        "anxiety": 1.5, "depression": 1.5, "insomnia": 1.0, "fatigue": 0.5,
    },
    "other": {
        "fatigue": 0.8, "fever": 0.6, "weight_loss": 0.6,
    },
}


def score_category_evidence(symptoms: Set[str]) -> Dict[str, float]:
    """Rule-based evidence score per category from a canonical symptom set.

    Returns raw (unnormalized) scores — sum of matched symptom weights.
    """
    scores: Dict[str, float] = {}
    for category, weights in CATEGORY_SYMPTOM_WEIGHTS.items():
        scores[category] = sum(weight for symptom, weight in weights.items() if symptom in symptoms)
    return scores


# ---------------------------------------------------------------------------
# 3. Condition profiles — evidence-driven ranking within a category
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConditionProfile:
    name: str
    category: str
    core: List[str]              # strongly defining symptoms
    supportive: List[str] = field(default_factory=list)   # increases likelihood
    negative: List[str] = field(default_factory=list)     # presence argues against this condition
    description: str = ""


CONDITION_PROFILES: List[ConditionProfile] = [
    # Neurological
    ConditionProfile(
        "Migraine", "neurological",
        core=["headache", "throbbing_quality", "unilateral"],
        supportive=["photophobia", "phonophobia", "nausea", "vomiting", "aura", "migraine_history", "visual_disturbance"],
        negative=[],
        description="Vascular headache, typically unilateral and throbbing, often with light/sound sensitivity, nausea, or vomiting",
    ),
    ConditionProfile(
        "Tension headache", "neurological",
        core=["headache", "pressing_quality", "bilateral"],
        supportive=[],
        negative=["photophobia", "phonophobia", "aura", "vomiting"],
        description="Headache caused by muscle tension or stress, typically bilateral and pressing/band-like, without migraine-specific features",
    ),
    ConditionProfile(
        "Secondary headache — red flag features", "neurological",
        core=["thunderclap_onset"],
        supportive=["fever", "neck_stiffness", "focal_weakness", "vomiting"],
        negative=[],
        description="Headache pattern with warning signs that warrant urgent evaluation to rule out a serious underlying cause",
    ),
    ConditionProfile(
        "Dehydration / benign headache", "neurological",
        core=["headache"],
        supportive=[],
        negative=["photophobia", "phonophobia", "aura", "throbbing_quality", "unilateral"],
        description="Mild, nonspecific headache without migraine or alarm features",
    ),

    # Respiratory
    ConditionProfile("Upper respiratory infection", "respiratory",
        core=["cough", "sore_throat"], supportive=["nasal_congestion", "fever", "chills"],
        description="Infection of the upper respiratory tract"),
    ConditionProfile("Bronchitis", "respiratory",
        core=["cough", "sputum"], supportive=["shortness_of_breath", "fever"],
        description="Inflammation of the bronchial airways, typically with productive cough"),
    ConditionProfile("Asthma / reactive airway", "respiratory",
        core=["wheezing", "shortness_of_breath"], supportive=["cough"],
        description="Reversible airway narrowing causing wheeze and breathlessness"),

    # Cardiovascular
    ConditionProfile("Benign tachycardia", "cardiovascular",
        core=["palpitations"], supportive=["shortness_of_breath"],
        negative=["chest_pain", "syncope"],
        description="Non-pathological increase in heart rate"),
    ConditionProfile("Possible arrhythmia", "cardiovascular",
        core=["irregular_heartbeat"], supportive=["palpitations", "syncope", "chest_pain"],
        description="Irregular heart rhythm warranting cardiology evaluation"),
    ConditionProfile("Cardiac-related chest pain", "cardiovascular",
        core=["chest_pain"], supportive=["shortness_of_breath", "syncope", "edema"],
        description="Chest pain with cardiovascular features requiring prompt evaluation"),

    # Gastrointestinal
    ConditionProfile("Gastritis / acid reflux", "gastrointestinal",
        core=["abdominal_pain", "heartburn"], supportive=["nausea"],
        description="Inflammation of the gastric lining or reflux disease"),
    ConditionProfile("Functional indigestion", "gastrointestinal",
        core=["abdominal_pain", "bloating"], supportive=[],
        description="Difficulty in the digestive process without alarm features"),
    ConditionProfile("Intestinal syndrome", "gastrointestinal",
        core=["diarrhea"], supportive=["constipation", "abdominal_pain"],
        description="Alteration in intestinal/bowel function"),

    # Musculoskeletal
    ConditionProfile("Muscle strain", "musculoskeletal",
        core=["muscle_pain"], supportive=["recent_injury"],
        description="Muscle tension, overuse, or strain"),
    ConditionProfile("Joint inflammation / mild arthritis", "musculoskeletal",
        core=["joint_pain"], supportive=["swelling_joint"],
        description="Joint inflammation, possibly early arthritis"),
    ConditionProfile("Soft tissue injury", "musculoskeletal",
        core=["recent_injury"], supportive=["swelling_joint", "muscle_pain", "back_pain"],
        description="Injury related to physical activity or trauma"),

    # Dermatological
    ConditionProfile("Contact dermatitis / allergic rash", "dermatological",
        core=["rash", "itching"], supportive=[],
        description="Allergic or irritant skin reaction"),
    ConditionProfile("Urticaria (hives)", "dermatological",
        core=["rash"], supportive=["itching"],
        description="Hives, often allergic in origin"),

    # Psychiatric
    ConditionProfile("Anxiety disorder", "psychiatric",
        core=["anxiety"], supportive=["insomnia", "palpitations"],
        description="Excessive worry/panic symptoms affecting daily function"),
    ConditionProfile("Depressive episode", "psychiatric",
        core=["depression"], supportive=["fatigue", "insomnia"],
        description="Persistent low mood and loss of interest"),

    # General
    ConditionProfile("Mild viral syndrome", "other",
        core=["fatigue", "fever"], supportive=["chills"],
        description="Low-intensity viral process"),
    ConditionProfile("Fatigue / stress-related symptoms", "other",
        core=["fatigue"], supportive=["insomnia", "anxiety"],
        description="Symptoms related to tiredness or tension"),
]


def rank_conditions(category: str, symptoms: Set[str]) -> List[Dict]:
    """Evidence-driven condition ranking within a category — no hardcoded priors.

    Score = (sum of matched core weights * 2 + sum of matched supportive weights)
            - (sum of matched negative weights * 1.5), floored at 0.1.
    This guarantees migraine outranks tension headache once migraine-specific
    evidence (photophobia/phonophobia/aura/throbbing/unilateral) is present,
    instead of a static prior favoring the more "common" condition.
    """
    candidates = [c for c in CONDITION_PROFILES if c.category == category]
    if not candidates:
        candidates = [c for c in CONDITION_PROFILES if c.category == "other"]

    scored = []
    for c in candidates:
        core_matches = [s for s in c.core if s in symptoms]
        supportive_matches = [s for s in c.supportive if s in symptoms]
        negative_matches = [s for s in c.negative if s in symptoms]

        core_score = len(core_matches) / max(len(c.core), 1) * 2.0
        supportive_score = len(supportive_matches) * 0.4
        negative_penalty = len(negative_matches) * 0.6

        raw_score = max(core_score + supportive_score - negative_penalty, 0.05)
        all_matches = core_matches + supportive_matches

        scored.append({
            "name": c.name,
            "description": c.description,
            "raw_score": raw_score,
            "indicators": all_matches,
        })

    total = sum(s["raw_score"] for s in scored) or 1.0
    for s in scored:
        s["probability_share"] = s["raw_score"] / total

    scored.sort(key=lambda s: s["raw_score"], reverse=True)
    return scored


# ---------------------------------------------------------------------------
# 4. Adaptive interview slots
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InformationSlot:
    key: str
    question: str
    detect_keys: List[str]   # coverage_map keys that, if non-empty, satisfy this slot


# Base slots asked during the general interview phase (cap: 10 questions).
# Lower-priority slots are skipped first when earlier answers already filled
# several slots at once.
GENERAL_SLOTS: List[InformationSlot] = [
    InformationSlot("chief_complaint", "What is the main reason for your consultation today?", ["chief_complaint"]),
    InformationSlot("onset", "When did these symptoms start?", ["onset"]),
    InformationSlot("severity", "How would you rate the intensity of your symptoms on a scale of 1 to 10?", ["severity"]),
    InformationSlot("quality", "How would you describe the sensation — for example sharp, dull, throbbing, pressing, or burning?", ["quality"]),
    InformationSlot("location", "Where exactly do you feel it, and is it on one side or both/all over?", ["laterality", "location"]),
    InformationSlot("associated_symptoms", "Are you experiencing any other symptoms along with this?", ["associated_symptoms"]),
    InformationSlot("aggravating_factors", "Is there anything that makes your symptoms worse?", ["aggravating_factors"]),
    InformationSlot("relieving_factors", "Is there anything that makes your symptoms better?", ["relieving_factors"]),
    InformationSlot("medications", "Are you currently taking any medications?", ["medications"]),
    InformationSlot("past_history", "Do you have any relevant medical history or similar past episodes?", ["past_history"]),
    InformationSlot("family_history", "Is there any family history of similar conditions?", ["family_history"]),
    InformationSlot("habits", "Do you smoke, drink alcohol, or have any other relevant habits?", ["habits"]),
]

MAX_GENERAL_QUESTIONS = 10
MAX_DIFFERENTIATOR_QUESTIONS = 5


@dataclass(frozen=True)
class DifferentiatorSlot:
    key: str
    category: str
    question: str
    detect_keys: List[str]


# ---------------------------------------------------------------------------
# 5. Free-text detectors for history / habits / factors / differentiators
#    (kept here so extraction logic has exactly one home)
# ---------------------------------------------------------------------------

_NO_MED_PHRASES = [
    'no medication', 'not taking', 'no medicine', "don't take", "not on any",
    'no meds', 'none currently', 'nothing currently', 'no drugs',
    'no tomo', 'no medicamento', 'no estoy tomando', 'ninguno', 'nada',
]

_COMMON_MEDS = [
    'ibuprofen', 'aspirin', 'acetaminophen', 'tylenol', 'advil', 'motrin',
    'paracetamol', 'naproxen', 'amoxicillin', 'antibiotic', 'antibiotics',
    'metformin', 'lisinopril', 'atorvastatin', 'omeprazole', 'losartan',
    'metoprolol', 'albuterol', 'inhaler', 'insulin', 'prednisone',
    'sertraline', 'fluoxetine', 'alprazolam', 'diazepam',
    'cetirizine', 'loratadine', 'pantoprazole',
    'ibuprofeno', 'aspirina', 'amoxicilina', 'antibiótico', 'metformina',
    'omeprazol', 'insulina', 'inhalador', 'sertralina', 'diclofenaco',
]


def detect_medications(text: str) -> Optional[List[str]]:
    """Returns [] if patient explicitly denies medications, None if not mentioned,
    or a list of detected medication names."""
    text_lower = text.lower()
    if any(p in text_lower for p in _NO_MED_PHRASES):
        return []
    found = [m.title() for m in _COMMON_MEDS if m in text_lower]
    return found or None


_AGGRAVATING_CUES = ['worse', 'worsens', 'worsened', 'aggravated', 'aggravates',
                      'triggers', 'triggered', 'makes it worse', 'increases', 'brings on',
                      'empeora', 'agrava', 'aumenta', 'provoca']
_FACTOR_MAP = {
    "physical activity": ['exercise', 'walking', 'movement', 'activity', 'exertion', 'running', 'physical'],
    "light exposure": ['light', 'bright', 'sunlight', 'screen', 'brightness', 'luz'],
    "stress": ['stress', 'anxiety', 'worry', 'tension', 'estrés'],
    "food or drink": ['eating', 'food', 'spicy', 'fatty', 'alcohol', 'coffee', 'caffeine', 'comida'],
    "lying down": ['lying down', 'lying flat', 'acostado'],
    "noise": ['noise', 'loud', 'sound', 'ruido'],
    "morning": ['morning', 'waking up', 'mañana'],
}
_RELIEVING_CUES = ['better', 'improves', 'improved', 'relieves', 'helps',
                    'reduces', 'eases', 'makes it better', 'go away',
                    'mejora', 'alivia', 'reduce', 'ayuda']
_RELIEF_FACTOR_MAP = {
    "rest": ['rest', 'resting', 'sleep', 'lying down', 'relaxation', 'descanso'],
    "medication": ['medication helps', 'pain reliever', 'ibuprofen', 'aspirin', 'paracetamol'],
    "cold compress": ['cold', 'ice', 'cold compress', 'frío', 'hielo'],
    "heat": ['heat', 'warm', 'hot shower', 'heating', 'calor'],
    "darkness": ['dark', 'dim', 'darkness', 'oscuridad'],
}


def detect_aggravating_factors(text: str) -> List[str]:
    text_lower = text.lower()
    if not any(cue in text_lower for cue in _AGGRAVATING_CUES):
        return []
    return [name for name, kws in _FACTOR_MAP.items() if any(kw in text_lower for kw in kws)][:3]


def detect_relieving_factors(text: str) -> List[str]:
    text_lower = text.lower()
    if not any(cue in text_lower for cue in _RELIEVING_CUES):
        return []
    return [name for name, kws in _RELIEF_FACTOR_MAP.items() if any(kw in text_lower for kw in kws)][:3]


_CONDITION_HISTORY_MAP = {
    "hypertension": ["hypertension", "high blood pressure", "hipertensión", "presión alta"],
    "diabetes": ["diabetes", "diabetic", "diabético", "blood sugar"],
    "asthma": ["asthma", "asthmatic", "asma"],
    "allergies": ["allergy", "allergies", "allergic", "alergia", "alergias"],
    "arthritis": ["arthritis", "rheumatoid", "artritis", "reuma"],
    "depression": ["depression", "depressed", "antidepressant", "depresión"],
    "anxiety disorder": ["anxiety disorder", "anxiety diagnosis", "trastorno de ansiedad"],
    "migraine": ["migraine history", "migraines", "antecedente de migraña", "historia de migraña"],
    "gastritis": ["gastritis", "ulcer", "acid reflux", "gerd", "acidez"],
    "high cholesterol": ["cholesterol", "high cholesterol", "colesterol"],
    "heart disease": ["heart disease", "cardiac", "heart attack", "coronary", "enfermedad cardíaca"],
    "thyroid disorder": ["thyroid", "hypothyroid", "hyperthyroid", "tiroides"],
}

_NO_HISTORY_PHRASES = ["no medical history", "no relevant history", "none", "nothing relevant",
                        "sin antecedentes", "ninguno"]


def detect_medical_history(text: str) -> List[str]:
    text_lower = text.lower()
    return [name for name, kws in _CONDITION_HISTORY_MAP.items() if any(kw in text_lower for kw in kws)][:5]


def detect_habits(text: str) -> Dict[str, str]:
    text_lower = text.lower()
    habits = {"smoking": "unknown", "alcohol": "unknown", "other": ""}

    if any(w in text_lower for w in ["don't smoke", "non-smoker", "never smoked", "no smoke", "not a smoker",
                                      "no fumo", "no fumar", "no soy fumador"]):
        habits["smoking"] = "no"
    elif any(w in text_lower for w in ["smoke", "smoker", "cigarette", "tobacco", "vaping",
                                        "fumo", "fumador", "cigarrillo", "tabaco"]):
        habits["smoking"] = "yes"

    if any(w in text_lower for w in ["don't drink", "no alcohol", "non-drinker", "teetotal", "i don't drink",
                                      "no bebo", "no tomo alcohol"]):
        habits["alcohol"] = "no"
    elif any(w in text_lower for w in ["occasionally", "socially", "social drinker", "sometimes drink",
                                        "ocasionalmente", "socialmente", "a veces"]):
        habits["alcohol"] = "occasional"
    elif any(w in text_lower for w in ["drink", "beer", "wine", "liquor", "spirits", "alcohol",
                                        "bebo", "cerveza", "vino", "copa"]):
        habits["alcohol"] = "yes"

    return habits


def habits_mentioned(text: str) -> bool:
    """Whether the message contains ANY smoking/alcohol signal (filled vs. unknown)."""
    h = detect_habits(text)
    return h["smoking"] != "unknown" or h["alcohol"] != "unknown"


# Differentiator free-text signal detectors (best-effort; absence just means the
# slot stays open and the engine will ask about it directly).
_DIFFERENTIATOR_CUES: Dict[str, List[str]] = {
    "frequency": ["times a week", "times a month", "times a year", "first time", "never had this before",
                  "recurrent", "keeps happening", "happens often", "regularly", "primera vez", "recurrente"],
    "prior_diagnosis": ["diagnosed with", "told i have", "told me i have", "doctor said i have", "diagnosticado con"],
    "exertion_pattern": ["at rest", "during exercise", "with activity", "with exertion", "even when resting",
                          "en reposo", "con esfuerzo"],
    "episode_duration": ["lasts for", "episode lasts", "each time it lasts", "for a few minutes", "for a few seconds",
                          "dura unos", "dura minutos"],
    "stimulant_use": ["caffeine", "coffee", "energy drink", "alcohol", "cafeína", "café"],
    "meal_relation": ["before eating", "after eating", "empty stomach", "with meals", "antes de comer", "después de comer"],
    "diet_changes": ["changed my diet", "new food", "started eating", "cambié mi dieta", "comida nueva"],
    "movement_pattern": ["only when i move", "only with movement", "even at rest", "solo al moverme"],
    "radiation": ["spreads to", "radiates to", "goes down my", "travels to", "se extiende a", "se irradia"],
    "lesion_evolution": ["spreading", "getting bigger", "shrinking", "same size", "se está extendiendo"],
    "exposure": ["new soap", "new detergent", "sick contact", "someone sick", "allergen", "travel", "traveled",
                 "expuesto a", "viajé"],
    "spreading_pattern": ["spreading to other", "other parts of my body", "se está extendiendo a"],
    "mood_duration": ["for weeks", "for months", "constantly feeling", "por semanas", "por meses"],
    "function_impact": ["can't work", "missing work", "affects my", "hard to function", "no puedo trabajar"],
    "triggers": ["triggered by", "happens when", "brought on by", "se desencadena", "ocurre cuando"],
    "timing_pattern": ["comes and goes", "constant", "all the time", "intermittent", "viene y va", "constante"],
}


def detect_differentiator_signals(text: str) -> Dict[str, str]:
    """Best-effort extraction of differentiator-slot signals from free text."""
    text_lower = text.lower()
    found: Dict[str, str] = {}
    for key, cues in _DIFFERENTIATOR_CUES.items():
        for cue in cues:
            if cue in text_lower:
                found[key] = text.strip()[:200]
                break
    freq = detect_frequency(text)
    if freq:
        found["frequency"] = freq
    return found


CATEGORY_DIFFERENTIATORS: Dict[str, List[DifferentiatorSlot]] = {
    "neurological": [
        DifferentiatorSlot("aura", "neurological", "Before the symptom starts, do you notice any visual changes such as flashing lights, zigzag lines, or blind spots (an aura)?", ["aura"]),
        DifferentiatorSlot("frequency", "neurological", "How often do these episodes happen, and is this the first time or have you had similar episodes before?", ["frequency"]),
        DifferentiatorSlot("family_history_migraine", "neurological", "Does anyone in your family have a history of migraines?", ["family_history"]),
        DifferentiatorSlot("red_flags", "neurological", "Was the onset sudden and the worst headache you've ever had, or do you have fever, neck stiffness, or weakness/numbness anywhere?", ["thunderclap_onset", "neck_stiffness", "focal_weakness", "fever"]),
        DifferentiatorSlot("prior_diagnosis", "neurological", "Has a doctor ever diagnosed you with migraines or tension headaches before?", ["prior_diagnosis"]),
    ],
    "respiratory": [
        DifferentiatorSlot("sputum_color", "respiratory", "If you're coughing up phlegm, what color is it?", ["sputum"]),
        DifferentiatorSlot("fever_pattern", "respiratory", "Have you had fever or chills along with these symptoms?", ["fever", "chills"]),
        DifferentiatorSlot("exposure", "respiratory", "Have you recently been exposed to sick contacts, allergens, or irritants?", ["exposure"]),
        DifferentiatorSlot("rest_vs_exertion", "respiratory", "Does the breathing difficulty happen at rest or only with physical activity?", ["exertion_pattern"]),
        DifferentiatorSlot("timing_pattern", "respiratory", "Do the symptoms follow a pattern, such as being worse at a particular time of day or season?", ["timing_pattern"]),
    ],
    "cardiovascular": [
        DifferentiatorSlot("trigger_pattern", "cardiovascular", "Do the palpitations or chest discomfort happen at rest, or only during physical exertion?", ["exertion_pattern"]),
        DifferentiatorSlot("syncope", "cardiovascular", "Have you felt dizzy, lightheaded, or actually fainted during these episodes?", ["syncope", "vertigo_dizziness"]),
        DifferentiatorSlot("rhythm", "cardiovascular", "Does your heartbeat feel irregular/skipping, or just fast and steady?", ["irregular_heartbeat"]),
        DifferentiatorSlot("duration", "cardiovascular", "How long do these episodes typically last — seconds, minutes, or longer?", ["episode_duration"]),
        DifferentiatorSlot("stimulants", "cardiovascular", "Do you regularly consume caffeine, alcohol, or stimulant medications?", ["stimulant_use"]),
    ],
    "gastrointestinal": [
        DifferentiatorSlot("meal_relation", "gastrointestinal", "Does the pain relate to eating — does it occur before, during, or after meals?", ["meal_relation"]),
        DifferentiatorSlot("bowel_changes", "gastrointestinal", "Have you noticed any change in your bowel habits, such as diarrhea or constipation?", ["diarrhea", "constipation"]),
        DifferentiatorSlot("blood", "gastrointestinal", "Have you noticed any blood in your stool or vomit?", ["blood_in_stool_or_vomit"]),
        DifferentiatorSlot("diet_changes", "gastrointestinal", "Have you made any recent changes to your diet?", ["diet_changes"]),
        DifferentiatorSlot("prior_gi", "gastrointestinal", "Have you been previously diagnosed with a digestive condition?", ["prior_diagnosis"]),
    ],
    "musculoskeletal": [
        DifferentiatorSlot("injury", "musculoskeletal", "Did this start after a specific injury, fall, or overexertion?", ["recent_injury"]),
        DifferentiatorSlot("swelling", "musculoskeletal", "Have you noticed any swelling, redness, or warmth in the affected area?", ["swelling_joint"]),
        DifferentiatorSlot("movement_pattern", "musculoskeletal", "Does the pain occur only with movement, or also at rest?", ["movement_pattern"]),
        DifferentiatorSlot("radiation", "musculoskeletal", "Does the pain spread or radiate to any other area?", ["radiation"]),
        DifferentiatorSlot("prior_episodes", "musculoskeletal", "Have you had similar episodes in this area before?", ["frequency"]),
    ],
    "dermatological": [
        DifferentiatorSlot("evolution", "dermatological", "How has the skin change evolved since it started — spreading, shrinking, or unchanged?", ["lesion_evolution"]),
        DifferentiatorSlot("exposure", "dermatological", "Have you been exposed to any new soaps, plants, foods, or other potential allergens?", ["exposure"]),
        DifferentiatorSlot("spreading", "dermatological", "Is it spreading to other parts of your body?", ["spreading_pattern"]),
        DifferentiatorSlot("systemic", "dermatological", "Do you have any fever or other symptoms along with the skin issue?", ["fever"]),
        DifferentiatorSlot("prior_skin", "dermatological", "Have you had similar skin issues before?", ["frequency"]),
    ],
    "psychiatric": [
        DifferentiatorSlot("duration_pattern", "psychiatric", "How long has this mood or anxiety pattern been going on, and is it constant or does it come in episodes?", ["mood_duration"]),
        DifferentiatorSlot("function_impact", "psychiatric", "How is this affecting your daily activities, work, or relationships?", ["function_impact"]),
        DifferentiatorSlot("triggers", "psychiatric", "Are there specific triggers for these feelings or panic episodes?", ["triggers"]),
        DifferentiatorSlot("sleep_appetite", "psychiatric", "Have you noticed changes in your sleep or appetite?", ["insomnia"]),
        DifferentiatorSlot("prior_history", "psychiatric", "Have you been diagnosed with or treated for a mental health condition before?", ["prior_diagnosis"]),
    ],
    "other": [
        DifferentiatorSlot("systemic_symptoms", "other", "Have you noticed fever, unexplained weight loss, or night sweats?", ["fever", "weight_loss"]),
        DifferentiatorSlot("travel_exposure", "other", "Have you traveled recently or been exposed to anyone sick?", ["exposure"]),
        DifferentiatorSlot("pattern", "other", "Are your symptoms constant or do they come and go?", ["timing_pattern"]),
        DifferentiatorSlot("function_impact", "other", "How much is this affecting your daily activities?", ["function_impact"]),
        DifferentiatorSlot("prior_episodes", "other", "Have you experienced something similar before?", ["frequency"]),
    ],
}
