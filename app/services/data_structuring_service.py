"""
Medical data structuring service — bilingual NLP extraction (EN + ES)
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.models.medical_models import MessageRole
from app.crew.hybrid_agent import create_hybrid_agent


class MedicalDataStructuringService:
    """Structures medical conversation data into standardized JSON."""

    def __init__(self):
        self.standard_format_version = "1.0"
        self.semantic_normalizer = SemanticNormalizer()

    async def structure_conversation_data(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        try:
            basic_info = self._extract_basic_information(conversation)
            user_messages = self._extract_user_messages(conversation)

            structured_data = await self._extract_structured_fields(
                user_messages,
                conversation.get("symptoms_collected", []),
                conversation.get("specific_answers", [])
            )

            final_structure = {
                **basic_info,
                **structured_data,
                "metadata": {
                    "format_version": self.standard_format_version,
                    "structured_timestamp": datetime.now().isoformat(),
                    "total_messages": len(conversation.get("messages", [])),
                    "processing_method": "semantic_nlp_extraction"
                }
            }

            self._validate_structure(final_structure)
            return final_structure

        except Exception as e:
            print(f"❌ Error in data structuring: {e}")
            return self._create_fallback_structure(conversation)

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
            "specific_questions_asked": conversation.get("specific_questions_asked", 0)
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

    async def _extract_structured_fields(
        self,
        user_messages: List[str],
        symptoms_collected: List[str],
        specific_answers: List[Dict]
    ) -> Dict[str, Any]:
        all_text = " ".join(user_messages + symptoms_collected)
        if specific_answers:
            specific_text = " ".join([
                answer.get("answer", "") if isinstance(answer, dict) else str(answer)
                for answer in specific_answers
            ])
            all_text += " " + specific_text

        structured_fields = self._llm_extract_structured_data(all_text, user_messages)
        normalized_fields = await self.semantic_normalizer.normalize_medical_data(structured_fields)
        return normalized_fields

    def _llm_extract_structured_data(self, text: str, user_messages: List[str]) -> Dict[str, Any]:
        """Use LLM to extract structured data. Falls back to regex extraction on failure."""
        consent_words = {
            "i agree", "yes", "ok", "okay", "agree", "si", "sí", "acepto",
            "i do", "proceed", "continue", "sí acepto", "si acepto"
        }
        substantive = [m for m in user_messages if m.strip().lower() not in consent_words and len(m.strip()) > 3]

        question_labels = [
            "Q1 (Main symptom / reason for consultation)",
            "Q2 (When symptoms started / Duration)",
            "Q3 (Symptom intensity on scale 1-10)",
            "Q4 (Aggravating and relieving factors)",
            "Q5 (Other / associated symptoms)",
            "Q6 (Current medications)",
            "Q7 (Past medical history / similar episodes)",
        ]
        qa_context = "PATIENT RESPONSES (interview order):\n"
        for i, msg in enumerate(substantive[:7]):
            label = question_labels[i] if i < len(question_labels) else f"Q{i+1}"
            qa_context += f"{label}: {msg}\n"

        prompt = f"""You are a medical informatics specialist. Extract structured information from this medical interview.

{qa_context}
FULL TEXT: {text[:2000]}

EXTRACTION RULES:
- Q1 is ALWAYS the main symptom and reason for consultation
- Q2 is ALWAYS onset/duration (extract time expressions: "3 days", "since yesterday", "for a week")
- Q3 is ALWAYS intensity (extract numbers 1-10, or descriptive: "severe", "moderate", "mild")
- Q4 contains aggravating and relieving factors
- Q5 contains other/associated symptoms
- Q6 contains current medications (if patient says "no" or "none", set empty list)
- Q7 contains medical history

CRITICAL: Never return 'unspecified' if information was provided. Extract it directly.
All text values must be in English. Respond ONLY with valid JSON:
{{
    "motivo_consulta": "exact reason from Q1",
    "enfermedad_actual": {{
        "sintoma_principal": "main symptom from Q1 — specific (e.g. 'headache', NOT 'unspecified')",
        "inicio": "duration from Q2 — specific (e.g. '3 days', NOT 'unspecified')",
        "intensidad": "intensity from Q3 — specific (e.g. '7/10', NOT 'unspecified')",
        "caracteristicas": "any characteristics mentioned"
    }},
    "antecedentes_personales": ["list from Q7"],
    "antecedentes_familiares": [],
    "habitos": {{"smoking": "yes/no/unknown", "alcohol": "yes/no/occasional/unknown", "other": ""}},
    "sintomas_asociados": ["list from Q5"],
    "intensidad": "same as enfermedad_actual.intensidad",
    "factores_agravantes": ["worsening factors from Q4"],
    "factores_aliviantes": ["improving factors from Q4"],
    "medicamentos_actuales": ["medications from Q6"]
}}"""

        try:
            hybrid_llm, provider = create_hybrid_agent()
            llm_response_content = hybrid_llm.invoke(prompt).content

            json_match = re.search(r'\{.*\}', llm_response_content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError("No valid JSON in LLM response")

        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error in structuring: {e}")
            return self._create_basic_extraction(text, user_messages)
        except Exception as e:
            print(f"❌ LLM structuring error: {e}")
            return self._create_basic_extraction(text, user_messages)

    def _create_basic_extraction(self, text: str, user_messages: List[str]) -> Dict[str, Any]:
        """Enhanced bilingual regex extraction when LLM is unavailable."""
        text_lower = text.lower()

        consent_words = {
            "i agree", "yes", "ok", "okay", "agree", "si", "sí", "acepto",
            "i do", "proceed", "continue", "sí acepto", "si acepto"
        }
        motivo_consulta = "general medical consultation"
        for msg in user_messages:
            if msg.strip().lower() not in consent_words and len(msg.strip()) > 3:
                motivo_consulta = msg[:300]
                break

        sintoma_principal = self._detect_main_symptom(text_lower)
        inicio = self._detect_onset(text_lower)
        intensidad = self._detect_intensity(text_lower)
        antecedentes = self._detect_medical_history(text_lower)
        habitos = self._detect_habits(text_lower)
        sintomas_asociados = self._detect_associated_symptoms(text_lower)
        factores_agravantes = self._detect_aggravating_factors(text_lower)
        factores_aliviantes = self._detect_relieving_factors(text_lower)
        medicamentos = self._detect_medications(text_lower)

        return {
            "motivo_consulta": motivo_consulta,
            "enfermedad_actual": {
                "sintoma_principal": sintoma_principal,
                "inicio": inicio,
                "intensidad": intensidad,
                "caracteristicas": "extracted from conversation"
            },
            "antecedentes_personales": antecedentes,
            "antecedentes_familiares": [],
            "habitos": habitos,
            "sintomas_asociados": sintomas_asociados,
            "intensidad": intensidad,
            "factores_agravantes": factores_agravantes,
            "factores_aliviantes": factores_aliviantes,
            "medicamentos_actuales": medicamentos
        }

    def _detect_main_symptom(self, text: str) -> str:
        """Detect main symptom using bilingual keyword patterns."""
        patterns = {
            "headache": [
                "headache", "head pain", "head hurts", "head aches", "my head hurts",
                "dolor de cabeza", "cefalea", "jaqueca", "migraña", "migraine"
            ],
            "chest pain": [
                "chest pain", "chest hurts", "chest tightness", "tightness in chest",
                "dolor en el pecho", "dolor torácico", "dolor pecho"
            ],
            "cough": ["cough", "coughing", "dry cough", "tos", "toser"],
            "fever": ["fever", "high temperature", "feverish", "fiebre", "temperatura", "calentura"],
            "abdominal pain": [
                "stomach pain", "abdominal pain", "belly pain", "stomach hurts", "stomach ache",
                "dolor de estómago", "dolor abdominal", "dolor de barriga", "dolor de panza"
            ],
            "back pain": [
                "back pain", "lower back", "upper back", "backache", "back hurts",
                "dolor de espalda", "dolor lumbar", "dolor de espalda"
            ],
            "dizziness": ["dizziness", "dizzy", "lightheaded", "vertigo", "mareo", "mareado", "vértigo"],
            "fatigue": [
                "fatigue", "tired", "exhausted", "weakness", "extreme tiredness",
                "cansancio", "cansado", "debilidad", "fatiga", "agotamiento"
            ],
            "nausea": ["nausea", "nauseous", "feel sick", "queasy", "náuseas", "náusea"],
            "shortness of breath": [
                "shortness of breath", "difficulty breathing", "breathless", "can't breathe",
                "falta de aire", "dificultad para respirar", "disnea", "ahogo"
            ],
            "sore throat": [
                "sore throat", "throat pain", "swollen throat", "throat hurts",
                "dolor de garganta", "garganta inflamada"
            ],
            "joint pain": [
                "joint pain", "arthritis pain", "knee pain", "hip pain", "joint ache",
                "dolor articular", "dolor de articulaciones", "articulaciones"
            ],
            "muscle pain": [
                "muscle pain", "muscle ache", "muscle soreness", "myalgia",
                "dolor muscular", "músculos adoloridos", "contractura"
            ],
            "skin rash": [
                "rash", "skin rash", "hives", "itchy skin", "skin eruption",
                "erupción", "sarpullido", "picazón", "urticaria"
            ],
            "anxiety": ["anxiety", "panic attack", "anxious", "panic", "ansiedad", "pánico"],
            "depression": ["depression", "depressed", "low mood", "depresión", "deprimido"],
            "eye pain": ["eye pain", "eye hurts", "blurred vision", "dolor de ojo", "dolor ocular"],
            "ear pain": ["ear pain", "earache", "ear hurts", "dolor de oído", "oído"],
            "palpitations": ["palpitations", "heart racing", "heart pounding", "palpitaciones"],
        }

        for symptom_name, keywords in patterns.items():
            if any(kw in text for kw in keywords):
                return symptom_name

        return "symptom requiring evaluation"

    def _detect_onset(self, text: str) -> str:
        """Detect symptom onset/duration — bilingual regex."""
        patterns = [
            # English — with capturing groups
            (r'(\d+)\s*days?\s*ago',       lambda m: f"{m.group(1)} day(s)"),
            (r'(\d+)\s*weeks?\s*ago',      lambda m: f"{m.group(1)} week(s)"),
            (r'(\d+)\s*months?\s*ago',     lambda m: f"{m.group(1)} month(s)"),
            (r'(\d+)\s*hours?\s*ago',      lambda m: f"{m.group(1)} hour(s)"),
            (r'for\s+(\d+)\s*days?',       lambda m: f"{m.group(1)} day(s)"),
            (r'for\s+(\d+)\s*weeks?',      lambda m: f"{m.group(1)} week(s)"),
            (r'for\s+(\d+)\s*months?',     lambda m: f"{m.group(1)} month(s)"),
            (r'for\s+(\d+)\s*hours?',      lambda m: f"{m.group(1)} hour(s)"),
            (r'past\s+(\d+)\s*days?',      lambda m: f"{m.group(1)} day(s)"),
            (r'past\s+(\d+)\s*weeks?',     lambda m: f"{m.group(1)} week(s)"),
            (r'last\s+(\d+)\s*days?',      lambda m: f"{m.group(1)} day(s)"),
            (r'last\s+(\d+)\s*weeks?',     lambda m: f"{m.group(1)} week(s)"),
            # English — fixed phrases
            (r'since\s+yesterday',         lambda m: "approximately 1 day"),
            (r'since\s+this\s+morning',    lambda m: "a few hours"),
            (r'since\s+last\s+night',      lambda m: "approximately 1 day"),
            (r'since\s+last\s+week',       lambda m: "approximately 1 week"),
            (r'started\s+today',           lambda m: "less than 1 day"),
            (r'this\s+morning',            lambda m: "a few hours"),
            (r'for\s+a\s+few\s+hours?',    lambda m: "a few hours"),
            (r'for\s+a\s+few\s+days?',     lambda m: "a few days"),
            (r'for\s+a\s+few\s+weeks?',    lambda m: "a few weeks"),
            (r'for\s+about\s+a\s+week',    lambda m: "approximately 1 week"),
            (r'for\s+about\s+a\s+month',   lambda m: "approximately 1 month"),
            # Spanish — with capturing groups
            (r'hace\s+(\d+)\s*días?',      lambda m: f"{m.group(1)} day(s)"),
            (r'hace\s+(\d+)\s*semanas?',   lambda m: f"{m.group(1)} week(s)"),
            (r'hace\s+(\d+)\s*mes(?:es)?', lambda m: f"{m.group(1)} month(s)"),
            (r'hace\s+(\d+)\s*horas?',     lambda m: f"{m.group(1)} hour(s)"),
            # Spanish — fixed phrases
            (r'desde\s+ayer',              lambda m: "approximately 1 day"),
            (r'desde\s+hoy',               lambda m: "less than 1 day"),
            (r'esta\s+mañana',             lambda m: "a few hours"),
            (r'anoche',                    lambda m: "approximately 1 day"),
            (r'hace\s+una\s+semana',       lambda m: "approximately 1 week"),
            (r'hace\s+un\s+mes',           lambda m: "approximately 1 month"),
        ]

        for pattern, formatter in patterns:
            m = re.search(pattern, text)
            if m:
                return formatter(m)

        return "not specified"

    def _detect_intensity(self, text: str) -> str:
        """Detect symptom intensity — numeric scale or descriptive."""
        numeric_patterns = [
            r'(\d{1,2})\s*(?:/|out\s+of)\s*10',
            r'(\d{1,2})\s*on\s*(?:a\s*)?(?:scale|pain\s*scale)',
            r'intensity\s*(?:of\s*)?[:\-]?\s*(\d{1,2})',
            r'pain\s*(?:level|score|rating)\s*(?:of\s*)?[:\-]?\s*(\d{1,2})',
            r"(?:i'?d?\s*)?(?:say|rate|give)\s*(?:it\s*)?(?:a\s*)?(\d{1,2})\b",
        ]
        for pattern in numeric_patterns:
            m = re.search(pattern, text)
            if m:
                score = int(m.group(1))
                if 1 <= score <= 10:
                    return f"{score}/10"

        if any(w in text for w in ['unbearable', 'excruciating', 'worst', 'terrible', 'horrible', 'agonizing']):
            return "10/10 (unbearable)"
        if any(w in text for w in ['severe', 'very strong', 'very bad', 'very intense', 'really bad']):
            return "severe"
        if any(w in text for w in ['strong', 'intense', 'significant', 'quite bad', 'pretty bad']):
            return "moderate-severe"
        if any(w in text for w in ['moderate', 'medium', 'fairly', 'noticeable']):
            return "moderate"
        if any(w in text for w in ['mild', 'slight', 'minor', 'light', 'a little', 'a bit', 'not too bad']):
            return "mild"
        # Spanish descriptive
        if any(w in text for w in ['insoportable', 'muy fuerte', 'muy intenso', 'grave', 'severo']):
            return "severe"
        if any(w in text for w in ['intenso', 'fuerte', 'bastante', 'considerable']):
            return "moderate-severe"
        if any(w in text for w in ['moderado', 'regular']):
            return "moderate"
        if any(w in text for w in ['leve', 'ligero', 'poco', 'suave', 'no mucho']):
            return "mild"

        return "not specified"

    def _detect_medications(self, text: str) -> List[str]:
        """Detect medications mentioned in text."""
        no_med_phrases = [
            'no medication', 'not taking', 'no medicine', "don't take", "not on any",
            'no meds', 'none currently', 'nothing currently', 'no drugs',
            'no tomo', 'no medicamento', 'no estoy tomando', 'ninguno', 'nada'
        ]
        if any(phrase in text for phrase in no_med_phrases):
            return []

        common_meds = [
            'ibuprofen', 'aspirin', 'acetaminophen', 'tylenol', 'advil', 'motrin',
            'paracetamol', 'naproxen', 'amoxicillin', 'antibiotic', 'antibiotics',
            'metformin', 'lisinopril', 'atorvastatin', 'omeprazole', 'losartan',
            'metoprolol', 'albuterol', 'inhaler', 'insulin', 'prednisone',
            'sertraline', 'fluoxetine', 'alprazolam', 'diazepam',
            'cetirizine', 'loratadine', 'pantoprazole',
            # Spanish
            'ibuprofeno', 'aspirina', 'amoxicilina', 'antibiótico', 'metformina',
            'omeprazol', 'insulina', 'inhalador', 'sertralina', 'diclofenaco',
        ]

        found = []
        for med in common_meds:
            if med in text and med.title() not in found:
                found.append(med.title())
        return found

    def _detect_aggravating_factors(self, text: str) -> List[str]:
        """Detect factors that worsen symptoms."""
        cues = [
            'worse', 'worsens', 'worsened', 'aggravated', 'aggravates',
            'triggers', 'triggered', 'makes it worse', 'increases', 'brings on',
            'empeora', 'agrava', 'aumenta', 'provoca'
        ]
        factor_map = {
            "physical activity": ['exercise', 'walking', 'movement', 'activity', 'exertion', 'running', 'physical'],
            "light exposure": ['light', 'bright', 'sunlight', 'screen', 'brightness', 'luz'],
            "stress": ['stress', 'anxiety', 'worry', 'tension', 'estrés'],
            "food or drink": ['eating', 'food', 'spicy', 'fatty', 'alcohol', 'coffee', 'caffeine', 'comida'],
            "lying down": ['lying down', 'lying flat', 'acostado'],
            "noise": ['noise', 'loud', 'sound', 'ruido'],
            "morning": ['morning', 'waking up', 'mañana'],
        }

        if not any(cue in text for cue in cues):
            return []

        found = []
        for factor_name, keywords in factor_map.items():
            if any(kw in text for kw in keywords):
                found.append(factor_name)
        return found[:3]

    def _detect_relieving_factors(self, text: str) -> List[str]:
        """Detect factors that improve symptoms."""
        cues = [
            'better', 'improves', 'improved', 'relieves', 'helps',
            'reduces', 'eases', 'makes it better', 'go away',
            'mejora', 'alivia', 'reduce', 'ayuda'
        ]
        factor_map = {
            "rest": ['rest', 'resting', 'sleep', 'lying down', 'relaxation', 'descanso'],
            "medication": ['medication helps', 'pain reliever', 'ibuprofen', 'aspirin', 'paracetamol'],
            "cold compress": ['cold', 'ice', 'cold compress', 'frío', 'hielo'],
            "heat": ['heat', 'warm', 'hot shower', 'heating', 'calor'],
            "darkness": ['dark', 'dim', 'darkness', 'oscuridad'],
            "eating": ['eating', 'food', 'after eating', 'comer'],
        }

        if not any(cue in text for cue in cues):
            return []

        found = []
        for factor_name, keywords in factor_map.items():
            if any(kw in text for kw in keywords):
                found.append(factor_name)
        return found[:3]

    def _detect_medical_history(self, text: str) -> List[str]:
        """Detect medical history — bilingual."""
        condition_map = {
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

        found = []
        for condition_name, keywords in condition_map.items():
            if any(kw in text for kw in keywords):
                found.append(condition_name)
        return found[:5]

    def _detect_habits(self, text: str) -> Dict[str, str]:
        """Detect habits — bilingual."""
        habits = {"smoking": "unknown", "alcohol": "unknown", "other": ""}

        if any(w in text for w in ["don't smoke", "non-smoker", "never smoked", "no smoke", "not a smoker",
                                    "no fumo", "no fumar", "no soy fumador"]):
            habits["smoking"] = "no"
        elif any(w in text for w in ["smoke", "smoker", "cigarette", "tobacco", "vaping",
                                      "fumo", "fumador", "cigarrillo", "tabaco"]):
            habits["smoking"] = "yes"

        if any(w in text for w in ["don't drink", "no alcohol", "non-drinker", "teetotal", "i don't drink",
                                    "no bebo", "no alcohol", "no tomo alcohol"]):
            habits["alcohol"] = "no"
        elif any(w in text for w in ["occasionally", "socially", "social drinker", "sometimes drink",
                                      "ocasionalmente", "socialmente", "a veces"]):
            habits["alcohol"] = "occasional"
        elif any(w in text for w in ["drink", "beer", "wine", "liquor", "spirits", "alcohol",
                                      "bebo", "cerveza", "vino", "copa"]):
            habits["alcohol"] = "yes"

        return habits

    def _detect_associated_symptoms(self, text: str) -> List[str]:
        """Detect associated symptoms — bilingual."""
        symptom_map = {
            "nausea": ["nausea", "nauseous", "feel sick", "queasy", "náuseas"],
            "vomiting": ["vomit", "vomiting", "threw up", "vómito"],
            "dizziness": ["dizzy", "dizziness", "lightheaded", "mareo"],
            "fatigue": ["fatigue", "tired", "exhausted", "weakness", "cansancio"],
            "fever": ["fever", "feverish", "high temperature", "fiebre"],
            "chills": ["chills", "shivering", "escalofríos"],
            "photophobia": ["light sensitivity", "photophobia", "sensitive to light", "bright lights hurt", "sensibilidad a la luz"],
            "phonophobia": ["sound sensitivity", "phonophobia", "noise bothers", "sensibilidad al ruido"],
            "visual changes": ["blurred vision", "visual aura", "see spots", "double vision", "visión borrosa"],
            "neck stiffness": ["neck stiffness", "stiff neck", "rigidez cervical"],
            "loss of appetite": ["no appetite", "loss of appetite", "not hungry", "pérdida de apetito"],
            "shortness of breath": ["shortness of breath", "difficulty breathing", "falta de aire"],
            "palpitations": ["palpitations", "heart racing", "heart pounding", "palpitaciones"],
            "sweating": ["sweating", "night sweats", "sudoración"],
            "nasal congestion": ["congestion", "runny nose", "stuffy nose", "congestión", "moqueo"],
        }

        found = []
        for symptom_name, keywords in symptom_map.items():
            if any(kw in text for kw in keywords):
                found.append(symptom_name)
        return found[:6]

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
        consent_words = {"i agree", "yes", "ok", "okay", "agree", "si", "sí", "acepto", "i do"}
        first_message = "medical consultation"
        for msg in user_messages:
            if msg.strip().lower() not in consent_words and len(msg.strip()) > 3:
                first_message = msg[:200]
                break
        return {
            "motivo_consulta": first_message,
            "enfermedad_actual": {
                "sintoma_principal": "requires additional analysis",
                "inicio": "not specified",
                "intensidad": "not specified",
                "caracteristicas": "insufficient information"
            },
            "antecedentes_personales": [],
            "antecedentes_familiares": [],
            "habitos": {"smoking": "unknown", "alcohol": "unknown", "other": ""},
            "sintomas_asociados": [],
            "intensidad": "not specified",
            "factores_agravantes": [],
            "factores_aliviantes": [],
            "medicamentos_actuales": [],
            "metadata": {
                "format_version": self.standard_format_version,
                "structured_timestamp": datetime.now().isoformat(),
                "processing_method": "fallback_basic",
                "error": "Error in main processing"
            }
        }


class SemanticNormalizer:
    """Semantic normalization for medical terms — English output."""

    def __init__(self):
        self.symptom_normalization = self._load_symptom_normalization()
        self.condition_normalization = self._load_condition_normalization()

    async def normalize_medical_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = data.copy()

        if "enfermedad_actual" in normalized:
            symptom = normalized["enfermedad_actual"].get("sintoma_principal", "")
            normalized["enfermedad_actual"]["sintoma_principal"] = self._normalize_symptom(symptom)

        if "antecedentes_personales" in normalized:
            normalized["antecedentes_personales"] = [
                self._normalize_condition(c) for c in normalized["antecedentes_personales"]
            ]

        if "sintomas_asociados" in normalized:
            normalized["sintomas_asociados"] = [
                self._normalize_symptom(s) for s in normalized["sintomas_asociados"]
            ]

        return normalized

    def _normalize_symptom(self, symptom: str) -> str:
        symptom_lower = symptom.lower().strip()
        for standard_term, variants in self.symptom_normalization.items():
            if any(v in symptom_lower for v in variants):
                return standard_term
        return symptom

    def _normalize_condition(self, condition: str) -> str:
        condition_lower = condition.lower().strip()
        for standard_term, variants in self.condition_normalization.items():
            if any(v in condition_lower for v in variants):
                return standard_term
        return condition

    def _load_symptom_normalization(self) -> Dict[str, List[str]]:
        return {
            "headache": ["dolor de cabeza", "cefalea", "jaqueca", "head pain", "head ache"],
            "chest pain": ["dolor pecho", "dolor en el pecho", "dolor torácico"],
            "shortness of breath": ["falta de aire", "dificultad respirar", "disnea"],
            "nausea": ["náuseas", "nausea", "ganas de vomitar"],
            "dizziness": ["mareo", "mareado", "vertigo", "vértigo"],
            "fatigue": ["cansancio", "fatiga", "debilidad", "astenia"],
            "palpitations": ["palpitaciones", "taquicardia", "latidos fuertes"],
            "fever": ["fiebre", "temperatura alta", "calentura", "pirexia"],
            "migraine": ["migraña", "jaqueca"],
        }

    def _load_condition_normalization(self) -> Dict[str, List[str]]:
        return {
            "hypertension": ["hipertensión", "presión alta", "tensión alta", "high blood pressure"],
            "diabetes mellitus": ["diabetes", "azúcar alta"],
            "asthma": ["asma"],
            "gastritis": ["gastritis", "acidez", "acid reflux"],
            "migraine": ["migraña", "jaqueca"],
            "depression": ["depresión", "deprimido"],
            "anxiety disorder": ["ansiedad", "trastorno de ansiedad"],
        }


# Global service instance
data_structuring_service = MedicalDataStructuringService()
