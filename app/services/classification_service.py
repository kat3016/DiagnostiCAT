"""
Servicio de modelo de clasificación médica usando Hugging Face
"""

import json
import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np
from concurrent.futures import ThreadPoolExecutor

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    import torch
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

# Comentar import de llm_service que usa Ollama y usar hybrid_agent
# from app.services.llm_service import llm_service
from app.crew.hybrid_agent import create_hybrid_agent


# Clinical safety rules: symptom clusters that override ML classification
_NEUROLOGICAL_STRONG = [
    "headache", "migraine", "head pain", "head hurts", "dizziness", "vertigo",
    "photophobia", "phonophobia", "aura", "unilateral head", "throbbing head",
    "cefalea", "migraña", "mareo", "dolor de cabeza", "sensibilidad a la luz",
    "sensibilidad al ruido"
]

_RESPIRATORY_REQUIRED = [
    "cough", "sore throat", "congestion", "runny nose", "wheezing",
    "shortness of breath", "breathing difficulty", "dyspnea", "breathless",
    "tos", "garganta", "congestion nasal", "dificultad respirar", "ahogo"
]

_CARDIOVASCULAR_INDICATORS = [
    "chest pain", "palpitation", "irregular heartbeat", "edema", "leg swelling",
    "syncope", "chest tightness with exertion", "dolor en el pecho", "palpitaciones"
]


class ClassificationModel:
    """Modelo de clasificación médica usando Hugging Face"""
    
    def __init__(self):
        self.model_name = "medical_classifier_hf_v1"
        self.version = "2.0.0"
        self.categories = [
            "neurological",
            "cardiovascular", 
            "respiratory",
            "gastrointestinal",
            "musculoskeletal",
            "dermatological",
            "psychiatric",
            "other"
        ]
        
        # Configuración del modelo de Hugging Face
        # Modelos que realmente funcionan para clasificación médica
        self.medical_model_name = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"  # Modelo médico real
        self.zero_shot_model = "facebook/bart-large-mnli"  # Para zero-shot classification
        self.use_medical_bert = False  # Usar zero-shot por defecto (funciona mejor sin entrenamiento específico)
        
        # Inicializar modelos
        self.tokenizer = None
        self.model = None
        self.classifier = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Inicializar modelos será bajo demanda
        self._initialization_started = False
        if not HF_AVAILABLE:
            print("⚠️  Hugging Face no disponible, usando clasificación basada en LLM como fallback")
    
    async def _initialize_models(self):
        """Inicializar modelos de Hugging Face de forma asíncrona"""
        try:
            print("🤗 Inicializando modelos de Hugging Face...")
            
            # Ejecutar la carga de modelos en un hilo separado
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self._load_models)
            
            print("✅ Modelos de Hugging Face inicializados correctamente")
            
        except Exception as e:
            print(f"❌ Error al inicializar modelos de Hugging Face: {e}")
            self.tokenizer = None
            self.model = None
            self.classifier = None
    
    def _load_models(self):
        """Cargar modelos de Hugging Face (ejecutar en hilo separado)"""
        try:
            if self.use_medical_bert:
                # Usar modelo BERT médico con zero-shot classification
                # No intentamos crear un clasificador específico, sino usar zero-shot con modelo médico
                model_name = self.medical_model_name
                print(f"📥 Cargando modelo médico para zero-shot: {model_name}")
                
                self.classifier = pipeline(
                    "zero-shot-classification",
                    model=model_name,
                    device=-1  # CPU
                )
            else:
                # Usar modelo general para zero-shot classification
                print(f"📥 Cargando modelo BART para zero-shot classification")
                self.classifier = pipeline(
                    "zero-shot-classification",
                    model=self.zero_shot_model,
                    device=-1  # CPU
                )
                
        except Exception as e:
            print(f"❌ Error cargando modelos: {e}")
            # Fallback a modelo más simple si falla
            try:
                print("� Intentando modelo de respaldo...")
                self.classifier = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-base",
                    device=-1
                )
                print("✅ Modelo de respaldo cargado")
            except Exception as e2:
                print(f"❌ Error en modelo de respaldo: {e2}")
                raise e
    
    def _prepare_text_for_classification(self, structured_data: Dict[str, Any]) -> str:
        """Preparar texto de los datos estructurados para clasificación"""
        text_parts = []
        
        # Extraer información clave de los datos estructurados
        if "symptoms" in structured_data:
            symptoms = structured_data["symptoms"]
            if isinstance(symptoms, list):
                text_parts.append("Síntomas: " + ", ".join(symptoms))
            elif isinstance(symptoms, str):
                text_parts.append("Síntomas: " + symptoms)
        
        if "chief_complaint" in structured_data:
            text_parts.append("Motivo consulta: " + str(structured_data["chief_complaint"]))
        
        if "history" in structured_data:
            text_parts.append("Historia: " + str(structured_data["history"]))
        
        if "current_medications" in structured_data:
            meds = structured_data["current_medications"]
            if isinstance(meds, list) and meds:
                text_parts.append("Medicamentos: " + ", ".join(meds))
        
        # Si no hay información específica, usar toda la data como texto
        if not text_parts:
            text_parts.append(json.dumps(structured_data, ensure_ascii=False))
        
        return " | ".join(text_parts)
    
    async def classify(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clasifica los datos estructurados de la anamnesis usando Hugging Face
        
        Args:
            structured_data: Datos estructurados de la anamnesis
            
        Returns:
            Dict con clasificación, confianza y recomendaciones
        """
        
        # Inicializar modelos la primera vez si HF está disponible
        if HF_AVAILABLE and not self._initialization_started:
            self._initialization_started = True
            await self._initialize_models()
        
        # Si Hugging Face está disponible y los modelos están cargados, usar HF
        if HF_AVAILABLE and self.classifier is not None:
            return await self._classify_with_huggingface(structured_data)
        else:
            # Fallback al LLM original
            print("⚠️  Usando clasificación LLM como fallback")
            return self._classify_with_llm_fallback(structured_data)
    
    async def _classify_with_huggingface(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clasificación usando modelos de Hugging Face"""
        try:
            # Preparar texto para clasificación
            text_input = self._prepare_text_for_classification(structured_data)
            print(f"🔍 Clasificando texto: {text_input[:100]}...")
            
            # Ejecutar clasificación zero-shot en hilo separado para no bloquear
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                self._run_zero_shot_classification,
                text_input
            )
            
            print(f"📊 Resultados HF: {results}")
            
            # Procesar resultados y crear estructura de respuesta
            return self._process_hf_results(results, structured_data, text_input)
            
        except Exception as e:
            print(f"❌ Error en clasificación HF: {e}")
            return self._create_error_classification(str(e))
    
    def _run_zero_shot_classification(self, text: str) -> Dict:
        """Ejecutar clasificación zero-shot (en hilo separado)"""
        # Etiquetas más específicas y en contexto médico para mejor clasificación
        candidate_labels = [
            "dolor de cabeza, migraña, problemas neurológicos, mareos, problemas cerebrales",
            "dolor de pecho, problemas cardíacos, palpitaciones, presión arterial, cardiovascular", 
            "tos, problemas respiratorios, dificultad para respirar, pulmones, asma",
            "dolor de estómago, náuseas, vómitos, problemas digestivos, gastrointestinal",
            "dolor muscular, dolor articular, problemas de huesos, artritis, musculoesquelético",
            "problemas de piel, erupciones, picazón, dermatológico",
            "ansiedad, depresión, problemas mentales, estrés, psiquiátrico",
            "otros síntomas médicos generales"
        ]
        
        # Ejecutar clasificación
        results = self.classifier(text, candidate_labels)
        
        # Mapear resultados a nuestras categorías
        label_mapping = {
            candidate_labels[0]: "neurological",
            candidate_labels[1]: "cardiovascular", 
            candidate_labels[2]: "respiratory",
            candidate_labels[3]: "gastrointestinal",
            candidate_labels[4]: "musculoskeletal",
            candidate_labels[5]: "dermatological",
            candidate_labels[6]: "psychiatric",
            candidate_labels[7]: "other"
        }
        
        # Convertir las etiquetas largas a nuestras categorías
        mapped_results = {
            'labels': [label_mapping.get(label, 'other') for label in results['labels']],
            'scores': results['scores']
        }
        
        return mapped_results
    
    def _process_hf_results(self, results, structured_data: Dict[str, Any], text_input: str) -> Dict[str, Any]:
        """Procesar resultados de Hugging Face y crear estructura de respuesta"""
        try:
            # Procesar resultados de zero-shot classification
            labels = results.get('labels', [])
            scores = results.get('scores', [])
            
            if labels and scores:
                # La clasificación ya viene mapeada a nuestras categorías
                primary_category = labels[0]
                confidence_score = float(scores[0])
                
                # Categorías secundarias - solo si tienen score razonable
                secondary_categories = []
                for i in range(1, min(3, len(labels))):
                    if scores[i] > 0.15:  # Umbral más bajo para categorías secundarias
                        secondary_categories.append(labels[i])
                
                print(f"✅ Clasificación exitosa: {primary_category} ({confidence_score:.3f})")

            else:
                # Fallback a clasificación por palabras clave
                print("⚠️ Resultados HF vacíos, usando clasificación por palabras clave")
                primary_category = self._classify_by_keywords(text_input)
                confidence_score = 0.6
                secondary_categories = []

            # Apply clinical safety rules to catch contradictory classifications
            corrected_cat, corrected_conf, override_reason = self._apply_clinical_safety_rules(
                text_input, primary_category, confidence_score
            )
            if override_reason:
                print(f"⚕️ Clinical rule applied: {override_reason}")
                primary_category = corrected_cat
                confidence_score = corrected_conf

            # Generar recomendaciones basadas en la categoría
            recommendations = self._generate_recommendations(primary_category, confidence_score)
            
            # Determinar nivel de urgencia
            urgency_level = self._determine_urgency(structured_data, primary_category)
            
            # Generar explicación
            reasoning = f"Clasificación automática usando {self.model_name}. Categoría: {primary_category} con confianza {confidence_score:.2f}"
            
            return {
                "primary_category": primary_category,
                "confidence_score": confidence_score,
                "secondary_categories": secondary_categories,
                "key_indicators": self._extract_key_indicators(text_input, primary_category),
                "recommendations": recommendations,
                "urgency_level": urgency_level,
                "reasoning": reasoning,
                "model_name": self.model_name,
                "model_version": self.version,
                "classification_timestamp": datetime.now().isoformat(),
                "method": "huggingface",
                "model_used": self.medical_model_name if self.use_medical_bert else "zero-shot"
            }
            
        except Exception as e:
            return self._create_error_classification(f"Error procesando resultados HF: {str(e)}")
    
    def _classify_with_llm_fallback(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """Classification using LLM as fallback"""
        classification_prompt = f"""You are an expert medical classification model. Analyze the structured anamnesis data and classify the case.

AVAILABLE CATEGORIES:
- neurological: Neurological problems (headaches, migraines, epilepsy, etc.)
- cardiovascular: Heart and vascular problems
- respiratory: Respiratory problems
- gastrointestinal: Digestive problems
- musculoskeletal: Musculoskeletal problems
- dermatological: Skin problems
- psychiatric: Mental health problems
- other: Other unclassifiable cases

CRITICAL INSTRUCTIONS:
1. Respond ONLY with valid JSON, no additional text
2. Do not include explanations before or after the JSON
3. Use double quotes for all strings
4. Write all text values in English
5. Ensure all braces and brackets are balanced

RESPONSE FORMAT (JSON ONLY):
{{
  "primary_category": "main_category",
  "confidence_score": 0.85,
  "secondary_categories": ["secondary_category"],
  "key_indicators": ["indicator1", "indicator2"],
  "recommendations": [
    "recommendation1",
    "recommendation2"
  ],
  "urgency_level": "low",
  "reasoning": "Brief explanation of the classification in English"
}}

IMPORTANT: Respond ONLY with the valid JSON shown above, no additional text, explanations, or comments."""
        
        try:
            # Usar hybrid_agent en lugar de llm_service
            hybrid_llm, provider = create_hybrid_agent()
            
            # Crear el mensaje completo
            full_message = f"{classification_prompt}\n\nDatos de anamnesis para clasificar:\n{json.dumps(structured_data, ensure_ascii=False, indent=2)}"
            
            # Generar respuesta
            llm_response_content = hybrid_llm.invoke(full_message).content
            
            # Crear estructura de respuesta similar a llm_service
            llm_response = {
                "response": llm_response_content,
                "success": True,
                "model": provider
            }
            
            # Intentar parsear la respuesta como JSON
            try:
                # Intentar extraer JSON de la respuesta (podría tener texto adicional)
                json_str = self._extract_json_from_text(llm_response["response"])
                classification_result = json.loads(json_str)
                
                # Validar estructura
                required_fields = ["primary_category", "confidence_score", "recommendations", "urgency_level"]
                for field in required_fields:
                    if field not in classification_result:
                        raise ValueError(f"Campo requerido faltante: {field}")
                
                # Apply clinical safety rules
                text_content = json.dumps(structured_data, ensure_ascii=False).lower()
                corrected_cat, corrected_conf, override_reason = self._apply_clinical_safety_rules(
                    text_content,
                    classification_result.get("primary_category", "other"),
                    classification_result.get("confidence_score", 0.5)
                )
                if override_reason:
                    print(f"⚕️ Clinical rule applied (LLM fallback): {override_reason}")
                    classification_result["primary_category"] = corrected_cat
                    classification_result["confidence_score"] = corrected_conf
                    classification_result["reasoning"] = override_reason

                # Agregar metadata del modelo
                classification_result.update({
                    "model_name": self.model_name + "_llm_fallback",
                    "model_version": self.version,
                    "classification_timestamp": datetime.now().isoformat(),
                    "tokens_used": 0,  # hybrid_agent no provee esta información
                    "method": "llm_fallback",
                    "provider": llm_response.get("model", "unknown")
                })
                
                return classification_result
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"❌ Error parseando JSON del LLM: {str(e)}")
                print(f"🔍 Respuesta del LLM: {llm_response['response'][:500]}...")
                # Si no es JSON válido, crear estructura básica
                return self._create_fallback_classification(structured_data, llm_response["response"])
                
        except Exception as e:
            return self._create_error_classification(str(e))
    
    def _map_label_to_category(self, label: str) -> str:
        """Mapear etiquetas del modelo a nuestras categorías"""
        label_lower = label.lower()
        
        if any(word in label_lower for word in ["neuro", "brain", "head", "migraine"]):
            return "neurological"
        elif any(word in label_lower for word in ["cardio", "heart", "blood", "pressure"]):
            return "cardiovascular"
        elif any(word in label_lower for word in ["respiratory", "lung", "breath", "cough"]):
            return "respiratory"
        elif any(word in label_lower for word in ["gastro", "stomach", "digestive", "nausea"]):
            return "gastrointestinal"
        elif any(word in label_lower for word in ["muscle", "bone", "joint", "pain"]):
            return "musculoskeletal"
        elif any(word in label_lower for word in ["skin", "dermat", "rash"]):
            return "dermatological"
        elif any(word in label_lower for word in ["psych", "mental", "mood", "anxiety"]):
            return "psychiatric"
        else:
            return "other"
    
    def _map_zero_shot_label_to_category(self, label: str) -> str:
        """Mapear etiquetas zero-shot a nuestras categorías"""
        mapping = {
            "neurological disorder": "neurological",
            "cardiovascular disease": "cardiovascular",
            "respiratory problem": "respiratory",
            "gastrointestinal issue": "gastrointestinal",
            "musculoskeletal problem": "musculoskeletal",
            "skin condition": "dermatological",
            "psychiatric condition": "psychiatric",
            "other medical condition": "other"
        }
        return mapping.get(label, "other")
    
    def _generate_recommendations(self, category: str, confidence: float) -> List[str]:
        """Generar recomendaciones basadas en la categoría"""
        base_recommendations = [
            "Medical consultation for complete evaluation",
            "Follow-up according to symptom evolution"
        ]
        
        category_recommendations = {
            "neurological": [
                "Consider specialized neurological evaluation",
                "Document symptom frequency and duration"
            ],
            "cardiovascular": [
                "Vital sign monitoring is recommended",
                "Consider cardiology evaluation"
            ],
            "respiratory": [
                "Pulmonary function evaluation",
                "Oxygen saturation monitoring"
            ],
            "gastrointestinal": [
                "Gastroenterology evaluation",
                "Consider imaging studies if necessary"
            ],
            "musculoskeletal": [
                "Orthopedic or rheumatology evaluation",
                "Consider imaging studies"
            ],
            "dermatological": [
                "Specialized dermatology evaluation",
                "Document changes in skin lesions"
            ],
            "psychiatric": [
                "Psychiatric or psychological evaluation",
                "Consider mental health support"
            ]
        }
        
        recommendations = base_recommendations.copy()
        if category in category_recommendations:
            recommendations.extend(category_recommendations[category])
        
        # Agregar recomendación basada en confianza
        if confidence < 0.6:
            recommendations.append("Low-confidence classification - review with a specialist")
        
        return recommendations
    
    def _determine_urgency(self, structured_data: Dict[str, Any], category: str) -> str:
        """Determinar nivel de urgencia basado en datos y categoría"""
        # Palabras clave que indican alta urgencia
        high_urgency_keywords = [
            "severo", "intenso", "agudo", "súbito", "emergencia",
            "dolor pecho", "dificultad respirar", "pérdida conciencia"
        ]
        
        # Convertir datos a texto para análisis
        text_content = json.dumps(structured_data, ensure_ascii=False).lower()
        
        # Verificar palabras de alta urgencia
        if any(keyword in text_content for keyword in high_urgency_keywords):
            return "high"
        
        # Urgencia por categoría
        category_urgency = {
            "cardiovascular": "medium",
            "respiratory": "medium",
            "neurological": "medium",
            "psychiatric": "low",
            "dermatological": "low",
            "musculoskeletal": "low",
            "gastrointestinal": "low",
            "other": "medium"
        }
        
        return category_urgency.get(category, "medium")
    
    def _extract_key_indicators(self, text: str, category: str) -> List[str]:
        """Extraer indicadores clave del texto"""
        indicators = []
        text_lower = text.lower()
        
        # Indicadores por categoría
        category_indicators = {
            "neurological": ["dolor cabeza", "mareo", "cefalea", "migraña"],
            "cardiovascular": ["dolor pecho", "palpitaciones", "presión", "corazón"],
            "respiratory": ["tos", "dificultad respirar", "falta aire", "pulmón"],
            "gastrointestinal": ["nausea", "vómito", "dolor estómago", "digestivo"],
            "musculoskeletal": ["dolor muscular", "dolor articular", "rigidez"],
            "dermatological": ["erupción", "picazón", "lesión piel"],
            "psychiatric": ["ansiedad", "depresión", "estrés", "insomnio"]
        }
        
        if category in category_indicators:
            for indicator in category_indicators[category]:
                if indicator in text_lower:
                    indicators.append(indicator.title())
        
        # Si no se encuentran indicadores específicos, usar análisis general
        if not indicators:
            words = text_lower.split()
            symptom_words = [word for word in words if len(word) > 4 and word.isalpha()][:3]
            indicators = [word.title() for word in symptom_words]
        
        return indicators if indicators else ["General symptoms identified"]
    
    def _classify_by_keywords(self, text: str) -> str:
        """Clasificación básica por palabras clave como fallback"""
        text_lower = text.lower()
        
        # Clasificación básica por palabras clave
        if any(word in text_lower for word in ["dolor cabeza", "cefalea", "migraña", "mareo", "neurológico"]):
            return "neurological"
        elif any(word in text_lower for word in ["dolor pecho", "corazón", "presión", "cardio", "palpitaciones"]):
            return "cardiovascular"
        elif any(word in text_lower for word in ["tos", "respirar", "pulmón", "aire", "respiratory", "falta aire"]):
            return "respiratory"
        elif any(word in text_lower for word in ["estómago", "nausea", "vómito", "digestivo", "gastro"]):
            return "gastrointestinal"
        elif any(word in text_lower for word in ["dolor muscular", "articular", "hueso", "músculo"]):
            return "musculoskeletal"
        elif any(word in text_lower for word in ["piel", "dermat", "erupción", "picazón"]):
            return "dermatological"
        elif any(word in text_lower for word in ["ansiedad", "depresión", "psiq", "mental"]):
            return "psychiatric"
        else:
            return "other"
    
    def _create_fallback_classification(self, structured_data: Dict[str, Any], raw_response: str) -> Dict[str, Any]:
        """Crear clasificación de fallback cuando el LLM no retorna JSON válido"""
        
        # Análisis básico de palabras clave
        text_content = json.dumps(structured_data, ensure_ascii=False).lower()
        
        primary_category = "other"
        confidence = 0.5

        # Keyword classification
        if any(word in text_content for word in ["dolor cabeza", "cefalea", "migraña", "mareo",
                                                   "headache", "migraine", "dizziness"]):
            primary_category = "neurological"
            confidence = 0.7
        elif any(word in text_content for word in ["dolor pecho", "corazón", "presión",
                                                    "chest pain", "palpitation"]):
            primary_category = "cardiovascular"
            confidence = 0.7
        elif any(word in text_content for word in ["tos", "respirar", "pulmón", "aire",
                                                    "cough", "breathing", "respiratory"]):
            primary_category = "respiratory"
            confidence = 0.7
        elif any(word in text_content for word in ["estómago", "nausea", "vómito", "digestivo",
                                                    "stomach", "nausea", "vomit"]):
            primary_category = "gastrointestinal"
            confidence = 0.7

        # Apply clinical safety rules to keyword result too
        corrected_cat, corrected_conf, override_reason = self._apply_clinical_safety_rules(
            text_content, primary_category, confidence
        )
        if override_reason:
            print(f"⚕️ Clinical rule applied (keyword fallback): {override_reason}")
            primary_category = corrected_cat
            confidence = corrected_conf

        return {
            "primary_category": primary_category,
            "confidence_score": confidence,
            "secondary_categories": [],
            "key_indicators": ["Automatic keyword-based analysis"],
            "recommendations": [
                "Medical consultation for complete evaluation",
                "Follow-up according to symptom evolution"
            ],
            "urgency_level": "medium",
            "reasoning": f"Automatic classification based on content analysis. Original response: {raw_response[:100]}...",
            "model_name": self.model_name,
            "model_version": self.version,
            "classification_timestamp": datetime.now().isoformat(),
            "fallback_used": True
        }
    
    def _create_error_classification(self, error_msg: str) -> Dict[str, Any]:
        """Crear clasificación de error"""
        return {
            "primary_category": "other",
            "confidence_score": 0.0,
            "secondary_categories": [],
            "key_indicators": ["Classification error"],
            "recommendations": [
                "Review input data",
                "Medical consultation recommended"
            ],
            "urgency_level": "medium",
            "reasoning": f"Classification error: {error_msg}",
            "model_name": self.model_name,
            "model_version": self.version,
            "classification_timestamp": datetime.now().isoformat(),
            "error": True,
            "error_message": error_msg
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Información del modelo de clasificación"""
        hf_status = "available" if HF_AVAILABLE and self.classifier is not None else "not available"
        current_model = self.medical_model_name if self.use_medical_bert else self.zero_shot_model
        
        return {
            "name": self.model_name,
            "version": self.version,
            "categories": self.categories,
            "description": "Medical classification model using Zero-Shot Classification with specialized models",
            "input_format": "Structured anamnesis data in JSON",
            "output_format": "Classification with category, real confidence, and recommendations",
            "huggingface_status": hf_status,
            "current_model": current_model,
            "use_medical_bert": self.use_medical_bert,
            "classification_method": "zero-shot-classification",
            "fallback_available": True
        }
    
    def _apply_clinical_safety_rules(
        self, text: str, primary_category: str, confidence: float
    ) -> tuple:
        """Override ML category when it contradicts the detected symptom cluster.

        Returns (corrected_category, corrected_confidence, override_reason).
        """
        text_lower = text.lower()

        neuro_score = sum(1 for ind in _NEUROLOGICAL_STRONG if ind in text_lower)
        has_respiratory = any(ind in text_lower for ind in _RESPIRATORY_REQUIRED)
        has_cardiovascular = any(ind in text_lower for ind in _CARDIOVASCULAR_INDICATORS)

        # Rule 1: respiratory category with NO respiratory symptoms → reclassify
        if primary_category == "respiratory" and not has_respiratory:
            if neuro_score >= 2:
                return (
                    "neurological",
                    min(confidence + 0.10, 0.82),
                    "Clinical override: no respiratory indicators; neurological cluster detected"
                )
            if has_cardiovascular:
                return (
                    "cardiovascular",
                    min(confidence + 0.05, 0.75),
                    "Clinical override: no respiratory indicators; cardiovascular cluster detected"
                )

        # Rule 2: strong neurological cluster (≥ 3 indicators) always wins
        if neuro_score >= 3 and primary_category not in ("neurological",):
            return (
                "neurological",
                min(confidence + 0.10, 0.82),
                f"Clinical override: {neuro_score} neurological indicators detected"
            )

        # Rule 3: migraine-specific override (photophobia OR phonophobia present)
        migraine_specific = any(kw in text_lower for kw in [
            "photophobia", "phonophobia", "aura", "unilateral head",
            "sensibilidad a la luz", "sensibilidad al ruido"
        ])
        if migraine_specific and primary_category != "neurological":
            return (
                "neurological",
                min(confidence + 0.15, 0.85),
                "Clinical override: migraine-specific indicators (photophobia/phonophobia/aura)"
            )

        return primary_category, confidence, ""

    def _extract_json_from_text(self, text: str) -> str:
        """Extrae JSON válido de un texto que puede contener contenido adicional"""
        import re
        
        # Intentar encontrar JSON usando expresiones regulares
        # Buscar desde { hasta } balanceado
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        if matches:
            # Tomar el JSON más largo (probablemente el más completo)
            json_candidate = max(matches, key=len)
            return json_candidate
        
        # Si no encuentra JSON con llaves balanceadas, buscar manualmente
        start_idx = text.find('{')
        if start_idx == -1:
            raise ValueError("No se encontró inicio de JSON")
        
        # Buscar el final del JSON balanceando llaves
        brace_count = 0
        for i, char in enumerate(text[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start_idx:i+1]
        
        raise ValueError("JSON no balanceado - no se encontró cierre")
    
    async def switch_model(self, use_medical_bert: bool = False):
        """Cambiar entre modelo médico y modelo general para zero-shot"""
        if not HF_AVAILABLE:
            print("❌ Hugging Face no disponible")
            return False
        
        old_setting = self.use_medical_bert
        self.use_medical_bert = use_medical_bert
        self.classifier = None  # Reset classifier
        
        try:
            # Reinicializar con nuevo modelo
            await self._initialize_models()
            model_type = "médico" if use_medical_bert else "general"
            print(f"✅ Cambiado a modelo {model_type}")
            return True
        except Exception as e:
            print(f"❌ Error cambiando modelo: {e}")
            # Revertir cambio si falla
            self.use_medical_bert = old_setting
            return False


# Instancia global del modelo
classification_model = ClassificationModel()
