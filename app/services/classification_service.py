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

from app.services.llm_service import llm_service


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
        self.hf_model_name = "microsoft/DialoGPT-medium"  # Modelo base para clasificación médica
        self.medical_model_name = "emilyalsentzer/Bio_ClinicalBERT"  # Modelo médico especializado
        self.use_medical_bert = True  # Usar BERT médico por defecto
        
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
                # Usar modelo BERT médico especializado
                model_name = self.medical_model_name
                print(f"📥 Cargando modelo médico: {model_name}")
                
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    model_name,
                    num_labels=len(self.categories)
                )
                
                # Crear pipeline de clasificación
                self.classifier = pipeline(
                    "text-classification",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    return_all_scores=True
                )
            else:
                # Usar modelo general
                print(f"📥 Cargando modelo general para clasificación médica")
                self.classifier = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli"
                )
                
        except Exception as e:
            print(f"❌ Error cargando modelos: {e}")
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
            return await self._classify_with_llm_fallback(structured_data)
    
    async def _classify_with_huggingface(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clasificación usando modelos de Hugging Face"""
        try:
            # Preparar texto para clasificación
            text_input = self._prepare_text_for_classification(structured_data)
            
            # Ejecutar clasificación en hilo separado para no bloquear
            loop = asyncio.get_event_loop()
            
            if self.use_medical_bert:
                # Usar BERT médico con clasificación directa
                results = await loop.run_in_executor(
                    self.executor,
                    self._run_bert_classification,
                    text_input
                )
            else:
                # Usar clasificación zero-shot
                results = await loop.run_in_executor(
                    self.executor,
                    self._run_zero_shot_classification,
                    text_input
                )
            
            # Procesar resultados y crear estructura de respuesta
            return self._process_hf_results(results, structured_data, text_input)
            
        except Exception as e:
            print(f"❌ Error en clasificación HF: {e}")
            return self._create_error_classification(str(e))
    
    def _run_bert_classification(self, text: str) -> List[Dict]:
        """Ejecutar clasificación BERT (en hilo separado)"""
        # Truncar texto si es muy largo
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]
        
        results = self.classifier(text)
        return results
    
    def _run_zero_shot_classification(self, text: str) -> Dict:
        """Ejecutar clasificación zero-shot (en hilo separado)"""
        candidate_labels = [
            "neurological disorder", "cardiovascular disease", "respiratory problem",
            "gastrointestinal issue", "musculoskeletal problem", "skin condition",
            "psychiatric condition", "other medical condition"
        ]
        
        results = self.classifier(text, candidate_labels)
        return results
    
    def _process_hf_results(self, results, structured_data: Dict[str, Any], text_input: str) -> Dict[str, Any]:
        """Procesar resultados de Hugging Face y crear estructura de respuesta"""
        try:
            if self.use_medical_bert:
                # Procesar resultados de BERT médico
                if isinstance(results, list) and len(results) > 0:
                    # Los resultados del pipeline pueden ser diferentes, verificar estructura
                    if isinstance(results[0], dict) and 'score' in results[0]:
                        # Tomar el resultado con mayor confianza
                        best_result = max(results, key=lambda x: x.get('score', 0))
                        primary_category = self._map_label_to_category(best_result.get('label', 'other'))
                        confidence_score = float(best_result.get('score', 0.5))
                        
                        # Obtener categorías secundarias
                        secondary_categories = [
                            self._map_label_to_category(r.get('label', ''))
                            for r in sorted(results, key=lambda x: x.get('score', 0), reverse=True)[1:3]
                            if r.get('score', 0) > 0.3
                        ]
                    else:
                        # Formato alternativo - usar análisis básico
                        primary_category = self._classify_by_keywords(text_input)
                        confidence_score = 0.6
                        secondary_categories = []
                else:
                    primary_category = self._classify_by_keywords(text_input)
                    confidence_score = 0.5
                    secondary_categories = []
            else:
                # Procesar resultados de zero-shot
                labels = results.get('labels', [])
                scores = results.get('scores', [])
                
                if labels and scores:
                    primary_category = self._map_zero_shot_label_to_category(labels[0])
                    confidence_score = float(scores[0])
                    
                    # Categorías secundarias
                    secondary_categories = [
                        self._map_zero_shot_label_to_category(label)
                        for label, score in zip(labels[1:3], scores[1:3])
                        if score > 0.3
                    ]
                else:
                    primary_category = "other"
                    confidence_score = 0.5
                    secondary_categories = []
            
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
    
    async def _classify_with_llm_fallback(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clasificación usando LLM como fallback"""
        classification_prompt = f"""Eres un modelo de clasificación médica experto. Analiza los datos estructurados de anamnesis y clasifica el caso.

CATEGORÍAS DISPONIBLES:
- neurological: Problemas neurológicos (cefaleas, migrañas, epilepsia, etc.)
- cardiovascular: Problemas cardíacos y vasculares
- respiratory: Problemas respiratorios
- gastrointestinal: Problemas digestivos
- musculoskeletal: Problemas músculo-esqueléticos
- dermatological: Problemas de piel
- psychiatric: Problemas de salud mental
- other: Otros casos no clasificables

FORMATO DE RESPUESTA (JSON):
{{
  "primary_category": "categoria_principal",
  "confidence_score": 0.85,
  "secondary_categories": ["categoria_secundaria"],
  "key_indicators": ["indicador1", "indicador2"],
  "recommendations": [
    "recomendacion1",
    "recomendacion2"
  ],
  "urgency_level": "low|medium|high|critical",
  "reasoning": "Explicación breve del diagnóstico"
}}

Analiza cuidadosamente y responde SOLO con el JSON válido."""
        
        try:
            llm_response = await llm_service.generate_response(
                system_prompt=classification_prompt,
                user_message=f"Datos de anamnesis para clasificar:\n{json.dumps(structured_data, ensure_ascii=False, indent=2)}",
                conversation_history=[]
            )
            
            # Intentar parsear la respuesta como JSON
            try:
                classification_result = json.loads(llm_response["response"])
                
                # Validar estructura
                required_fields = ["primary_category", "confidence_score", "recommendations", "urgency_level"]
                for field in required_fields:
                    if field not in classification_result:
                        raise ValueError(f"Campo requerido faltante: {field}")
                
                # Agregar metadata del modelo
                classification_result.update({
                    "model_name": self.model_name + "_llm_fallback",
                    "model_version": self.version,
                    "classification_timestamp": datetime.now().isoformat(),
                    "tokens_used": llm_response["tokens_used"],
                    "method": "llm_fallback"
                })
                
                return classification_result
                
            except json.JSONDecodeError:
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
            "Consulta médica para evaluación completa",
            "Seguimiento según evolución de síntomas"
        ]
        
        category_recommendations = {
            "neurological": [
                "Considera evaluación neurológica especializada",
                "Documenta frecuencia y duración de síntomas"
            ],
            "cardiovascular": [
                "Monitoreo de signos vitales recomendado",
                "Considera evaluación cardiológica"
            ],
            "respiratory": [
                "Evaluación de función pulmonar",
                "Monitoreo de saturación de oxígeno"
            ],
            "gastrointestinal": [
                "Evaluación gastroenterológica",
                "Considerar estudios de imagen si es necesario"
            ],
            "musculoskeletal": [
                "Evaluación ortopédica o reumatológica",
                "Considerar estudios de imagen"
            ],
            "dermatological": [
                "Evaluación dermatológica especializada",
                "Documentar cambios en lesiones cutáneas"
            ],
            "psychiatric": [
                "Evaluación psiquiátrica o psicológica",
                "Considera apoyo en salud mental"
            ]
        }
        
        recommendations = base_recommendations.copy()
        if category in category_recommendations:
            recommendations.extend(category_recommendations[category])
        
        # Agregar recomendación basada en confianza
        if confidence < 0.6:
            recommendations.append("Clasificación con baja confianza - revisar con especialista")
        
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
        
        return indicators if indicators else ["Síntomas generales identificados"]
    
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
        
        # Clasificación básica por palabras clave
        if any(word in text_content for word in ["dolor cabeza", "cefalea", "migraña", "mareo"]):
            primary_category = "neurological"
            confidence = 0.7
        elif any(word in text_content for word in ["dolor pecho", "corazón", "presión"]):
            primary_category = "cardiovascular"
            confidence = 0.7
        elif any(word in text_content for word in ["tos", "respirar", "pulmón", "aire"]):
            primary_category = "respiratory"
            confidence = 0.7
        elif any(word in text_content for word in ["estómago", "nausea", "vómito", "digestivo"]):
            primary_category = "gastrointestinal"
            confidence = 0.7
        
        return {
            "primary_category": primary_category,
            "confidence_score": confidence,
            "secondary_categories": [],
            "key_indicators": ["Análisis automático por palabras clave"],
            "recommendations": [
                "Consulta médica para evaluación completa",
                "Seguimiento según evolución de síntomas"
            ],
            "urgency_level": "medium",
            "reasoning": f"Clasificación automática basada en análisis de contenido. Respuesta original: {raw_response[:100]}...",
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
            "key_indicators": ["Error en clasificación"],
            "recommendations": [
                "Revisar datos de entrada",
                "Consulta médica recomendada"
            ],
            "urgency_level": "medium",
            "reasoning": f"Error en clasificación: {error_msg}",
            "model_name": self.model_name,
            "model_version": self.version,
            "classification_timestamp": datetime.now().isoformat(),
            "error": True,
            "error_message": error_msg
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Información del modelo de clasificación"""
        hf_status = "disponible" if HF_AVAILABLE and self.classifier is not None else "no disponible"
        current_model = self.medical_model_name if self.use_medical_bert else "zero-shot classification"
        
        return {
            "name": self.model_name,
            "version": self.version,
            "categories": self.categories,
            "description": "Modelo de clasificación médica usando Hugging Face con fallback a LLM",
            "input_format": "Datos estructurados de anamnesis en JSON",
            "output_format": "Clasificación con categoría, confianza y recomendaciones",
            "huggingface_status": hf_status,
            "current_model": current_model,
            "use_medical_bert": self.use_medical_bert,
            "fallback_available": True
        }
    
    async def switch_model(self, use_medical_bert: bool = True):
        """Cambiar entre modelo médico BERT y zero-shot"""
        if not HF_AVAILABLE:
            print("❌ Hugging Face no disponible")
            return False
        
        self.use_medical_bert = use_medical_bert
        self.classifier = None  # Reset classifier
        
        # Reinicializar con nuevo modelo
        await self._initialize_models()
        return True


# Instancia global del modelo
classification_model = ClassificationModel()
