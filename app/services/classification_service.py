"""
Medical classification service.

Architecture (replaces the old Spanish-label zero-shot + ad hoc keyword
"safety net" patch):

1. A deterministic, weighted, evidence-based rule scorer (symptom_knowledge.py)
   is the backbone. It is always available and always consistent — it does not
   depend on a downloaded model or an API key.
2. If a Hugging Face zero-shot model is available, its score is blended in as a
   secondary signal (same-language English single-concept labels, proper
   hypothesis template). It can nudge the result but can no longer single-
   handedly flip a clear-cut case the way the old Spanish/multi-concept labels
   did, because it is combined with — not substituted for — the evidence score.
3. Condition ranking within a category is evidence-weighted (symptom_knowledge.
   rank_conditions), not a hardcoded prior table.
4. Confidence is a heuristic derived from the score margin between the top and
   second category — explicitly documented as uncalibrated, not invented via
   arbitrary "+0.1 bonus" patches.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import asyncio

from app.services import symptom_knowledge as sk

try:
    from transformers import pipeline
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

ZERO_SHOT_MODEL = "facebook/bart-large-mnli"
HYPOTHESIS_TEMPLATE = "This patient's symptoms are consistent with {}."

# Blend weights: the rule-based evidence score is the backbone (60%); the
# zero-shot model is a secondary signal (40%) when available.
RULE_WEIGHT = 0.6
ZERO_SHOT_WEIGHT = 0.4

_RED_FLAG_SYMPTOMS = {
    "thunderclap_onset", "focal_weakness", "blood_in_stool_or_vomit", "syncope",
}


class ClassificationModel:
    """Evidence-driven medical category classifier."""

    def __init__(self):
        self.model_name = "diagnosticat_evidence_classifier"
        self.version = "3.0.0"
        self.categories = sk.CATEGORIES

        self.classifier = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._initialization_started = False
        self._init_failed = False

    async def _initialize_model(self):
        if not HF_AVAILABLE:
            return
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._load_model)
        except Exception as e:
            print(f"Zero-shot model unavailable, continuing in rule-only mode: {e}")
            self.classifier = None
            self._init_failed = True

    def _load_model(self):
        self.classifier = pipeline("zero-shot-classification", model=ZERO_SHOT_MODEL, device=-1)

    def _build_classification_text(self, structured_data: Dict[str, Any]) -> str:
        """Builds a clean English description for the zero-shot model — includes
        severity/quality/duration, which the old implementation discarded."""
        parts = []
        chief = structured_data.get("chief_complaint")
        if chief:
            parts.append(f"Chief complaint: {chief}.")

        symptoms = structured_data.get("symptoms") or []
        symptoms = [s for s in symptoms if s]
        if symptoms:
            parts.append("Reported symptoms: " + ", ".join(symptoms) + ".")

        quality = structured_data.get("quality")
        if quality:
            parts.append(f"Quality of sensation: {quality}.")

        laterality = structured_data.get("laterality")
        if laterality:
            parts.append(f"Location pattern: {laterality}.")

        severity = structured_data.get("severity")
        if severity and str(severity).lower() not in ("unspecified", "not specified", ""):
            parts.append(f"Severity: {severity}.")

        duration = structured_data.get("duration")
        if duration and str(duration).lower() not in ("unspecified", "not specified", ""):
            parts.append(f"Duration: {duration}.")

        factors = structured_data.get("associated_factors") or []
        if factors:
            parts.append("Associated factors: " + ", ".join(factors) + ".")

        return " ".join(parts) if parts else "General medical consultation with unspecified symptoms."

    def _resolve_canonical_symptoms(self, structured_data: Dict[str, Any]) -> set:
        """Prefers the caller-supplied canonical symptom set (built live by the
        question engine during the interview); falls back to re-detecting from
        the assembled text for callers that don't track a coverage map."""
        provided = structured_data.get("canonical_symptoms")
        if provided:
            return set(provided)
        return sk.detect_symptoms(self._build_classification_text(structured_data))

    async def classify(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        canonical_symptoms = self._resolve_canonical_symptoms(structured_data)
        rule_scores = sk.score_category_evidence(canonical_symptoms)

        zero_shot_scores: Optional[Dict[str, float]] = None
        if HF_AVAILABLE and not self._init_failed:
            if not self._initialization_started:
                self._initialization_started = True
                await self._initialize_model()
            if self.classifier is not None:
                text = self._build_classification_text(structured_data)
                try:
                    loop = asyncio.get_event_loop()
                    zero_shot_scores = await loop.run_in_executor(
                        self.executor, self._run_zero_shot, text
                    )
                except Exception as e:
                    print(f"Zero-shot inference failed, continuing on rule-based score alone: {e}")
                    zero_shot_scores = None

        combined_scores = self._combine_scores(rule_scores, zero_shot_scores)
        primary_category, confidence, secondary_categories = self._select_category(combined_scores)

        conditions = sk.rank_conditions(primary_category, canonical_symptoms)
        recommendations = self._generate_recommendations(primary_category, confidence)
        urgency_level = self._determine_urgency(canonical_symptoms, structured_data)

        method = "rule_based" if zero_shot_scores is None else "rule_based+zero_shot"
        reasoning = (
            f"Category selected from weighted clinical-evidence scoring"
            f"{' blended with zero-shot model output' if zero_shot_scores else ' (zero-shot model unavailable, rule-based evidence only)'}. "
            f"Matched evidence: {', '.join(sorted(canonical_symptoms)) or 'none detected'}."
        )

        return {
            "primary_category": primary_category,
            "confidence_score": confidence,
            "secondary_categories": secondary_categories,
            "key_indicators": sorted(canonical_symptoms)[:6] or ["No specific indicators detected"],
            "conditions": conditions,
            "recommendations": recommendations,
            "urgency_level": urgency_level,
            "reasoning": reasoning,
            "model_name": self.model_name,
            "model_version": self.version,
            "classification_timestamp": datetime.now().isoformat(),
            "method": method,
            "category_scores": combined_scores,
        }

    def _run_zero_shot(self, text: str) -> Dict[str, float]:
        labels = list(sk.ZERO_SHOT_LABELS.values())
        result = self.classifier(
            text, labels, hypothesis_template=HYPOTHESIS_TEMPLATE, multi_label=True
        )
        scores_by_label = dict(zip(result["labels"], result["scores"]))
        return {
            category: scores_by_label.get(label, 0.0)
            for category, label in sk.ZERO_SHOT_LABELS.items()
        }

    def _combine_scores(self, rule_scores: Dict[str, float], zero_shot_scores: Optional[Dict[str, float]]) -> Dict[str, float]:
        max_rule = max(rule_scores.values()) or 1.0
        # Normalize rule scores against the strongest category observed instead of
        # a fixed denominator, so a single dominant cluster of evidence (e.g. 5
        # matched neurological symptoms) reads as high-confidence rather than
        # being diluted by categories with naturally fewer defining symptoms.
        rule_norm = {cat: (score / max_rule if max_rule > 0 else 0.0) for cat, score in rule_scores.items()}

        if zero_shot_scores is None:
            return rule_norm

        combined = {}
        for category in sk.CATEGORIES:
            combined[category] = (
                RULE_WEIGHT * rule_norm.get(category, 0.0)
                + ZERO_SHOT_WEIGHT * zero_shot_scores.get(category, 0.0)
            )
        return combined

    def _select_category(self, scores: Dict[str, float]) -> tuple:
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        if not ranked or ranked[0][1] <= 0.0:
            return "other", 0.3, []

        primary_category, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0

        # Confidence is an explicit heuristic — not a calibrated probability —
        # derived from how clearly the top category separates from the runner-up.
        margin = top_score - second_score
        confidence = round(min(0.5 + margin * 0.6, 0.95), 2)
        confidence = max(confidence, 0.3)

        secondary_categories = [cat for cat, score in ranked[1:3] if score > 0.25]
        return primary_category, confidence, secondary_categories

    def _generate_recommendations(self, category: str, confidence: float) -> List[str]:
        base_recommendations = [
            "Medical consultation for complete evaluation",
            "Follow-up according to symptom evolution",
        ]
        category_recommendations = {
            "neurological": ["Consider specialized neurological evaluation", "Document symptom frequency and duration"],
            "cardiovascular": ["Vital sign monitoring is recommended", "Consider cardiology evaluation"],
            "respiratory": ["Pulmonary function evaluation", "Oxygen saturation monitoring"],
            "gastrointestinal": ["Gastroenterology evaluation", "Consider imaging studies if necessary"],
            "musculoskeletal": ["Orthopedic or rheumatology evaluation", "Consider imaging studies"],
            "dermatological": ["Specialized dermatology evaluation", "Document changes in skin lesions"],
            "psychiatric": ["Psychiatric or psychological evaluation", "Consider mental health support"],
        }
        recommendations = base_recommendations.copy()
        recommendations.extend(category_recommendations.get(category, []))
        if confidence < 0.6:
            recommendations.append("Low-confidence classification — review with a specialist")
        return recommendations

    def _determine_urgency(self, canonical_symptoms: set, structured_data: Dict[str, Any]) -> str:
        if canonical_symptoms & _RED_FLAG_SYMPTOMS:
            return "critical"

        severity = str(structured_data.get("severity") or "").lower()
        if severity.startswith(("9", "10")) or "unbearable" in severity:
            return "high"

        if {"chest_pain", "shortness_of_breath"} <= canonical_symptoms:
            return "high"
        if {"neck_stiffness", "fever"} <= canonical_symptoms:
            return "high"

        category_urgency = {
            "cardiovascular": "medium",
            "respiratory": "medium",
            "neurological": "medium",
            "psychiatric": "low",
            "dermatological": "low",
            "musculoskeletal": "low",
            "gastrointestinal": "low",
            "other": "medium",
        }
        rule_scores = sk.score_category_evidence(canonical_symptoms)
        top_category = max(rule_scores, key=rule_scores.get) if any(rule_scores.values()) else "other"
        return category_urgency.get(top_category, "medium")

    def get_model_info(self) -> Dict[str, Any]:
        hf_status = "available" if HF_AVAILABLE and self.classifier is not None else (
            "not_initialized" if HF_AVAILABLE else "not_installed"
        )
        return {
            "name": self.model_name,
            "version": self.version,
            "categories": self.categories,
            "description": "Deterministic evidence-weighted classifier blended with zero-shot NLI when available",
            "zero_shot_model": ZERO_SHOT_MODEL,
            "zero_shot_status": hf_status,
            "classification_method": "rule_based_evidence + optional zero_shot blend",
            "deterministic": True,
        }


# Global model instance
classification_model = ClassificationModel()
