"""
Servicio de estructuración de datos médicos
Paso 3: Procesar y transformar información recolectada en formato estructurado
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from app.models.medical_models import MessageRole
from app.services.llm_service import llm_service


class MedicalDataStructuringService:
    """Servicio para estructurar datos médicos de conversaciones en formato JSON estándar"""
    
    def __init__(self):
        self.standard_format_version = "1.0"
        self.semantic_normalizer = SemanticNormalizer()
    
    async def structure_conversation_data(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte una conversación médica completa en formato JSON estructurado
        
        Args:
            conversation: Datos de conversación del medical_chat
            
        Returns:
            Dict con formato JSON estándar para clasificación
        """
        try:
            # Extraer información básica de la conversación
            basic_info = self._extract_basic_information(conversation)
            
            # Procesar mensajes del usuario
            user_messages = self._extract_user_messages(conversation)
            
            # Extraer información específica usando normalización semántica
            structured_data = await self._extract_structured_fields(
                user_messages, 
                conversation.get("symptoms_collected", []),
                conversation.get("specific_answers", [])
            )
            
            # Combinar información básica con datos estructurados
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
            
            # Validar estructura final
            self._validate_structure(final_structure)
            
            return final_structure
            
        except Exception as e:
            print(f"❌ Error en estructuración de datos: {e}")
            return self._create_fallback_structure(conversation)
    
    def _extract_basic_information(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae información básica de la conversación"""
        return {
            "conversation_id": conversation.get("conversation_id", "unknown"),
            "created_at": conversation.get("created_at", datetime.now()).isoformat() if hasattr(conversation.get("created_at", datetime.now()), 'isoformat') else str(conversation.get("created_at", datetime.now())),
            "state": conversation.get("state", "unknown"),
            "consent_given": conversation.get("consent_given", False),
            "questions_asked": conversation.get("questions_asked", 0),
            "specific_questions_asked": conversation.get("specific_questions_asked", 0)
        }
    
    def _extract_user_messages(self, conversation: Dict[str, Any]) -> List[str]:
        """Extrae solo los mensajes del usuario de la conversación"""
        user_messages = []
        messages = conversation.get("messages", [])
        
        for message in messages:
            if isinstance(message, dict):
                role = message.get("role")
                content = message.get("content", "")
            else:
                # Si es un objeto MessageModel
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
        """
        Extrae campos estructurados usando normalización semántica avanzada
        """
        # Combinar toda la información del usuario
        all_text = " ".join(user_messages + symptoms_collected)
        if specific_answers:
            specific_text = " ".join([
                answer.get("answer", "") if isinstance(answer, dict) else str(answer) 
                for answer in specific_answers
            ])
            all_text += " " + specific_text
        
        # Usar LLM para extracción estructurada
        structured_fields = await self._llm_extract_structured_data(all_text, user_messages)
        
        # Normalizar semánticamente los campos extraídos
        normalized_fields = await self.semantic_normalizer.normalize_medical_data(structured_fields)
        
        return normalized_fields
    
    async def _llm_extract_structured_data(self, text: str, user_messages: List[str]) -> Dict[str, Any]:
        """Usa LLM para extraer datos estructurados del texto médico"""
        
        extraction_prompt = f"""Eres un especialista en informática médica. Extrae información estructurada de esta conversación médica.

TEXTO DE LA CONVERSACIÓN:
{text}

MENSAJES INDIVIDUALES DEL PACIENTE:
{json.dumps(user_messages, ensure_ascii=False, indent=2)}

INSTRUCCIONES:
1. Identifica el motivo de consulta principal
2. Extrae el síntoma principal y sus características
3. Identifica antecedentes médicos mencionados
4. Detecta hábitos relevantes (tabaquismo, alcohol, etc.)
5. Lista síntomas asociados adicionales
6. Determina duración/inicio de síntomas

FORMATO DE RESPUESTA (JSON válido):
{{
    "motivo_consulta": "descripción clara del motivo principal",
    "enfermedad_actual": {{
        "sintoma_principal": "síntoma más relevante",
        "inicio": "duración o momento de inicio",
        "caracteristicas": "descripción de características del síntoma"
    }},
    "antecedentes_personales": ["lista de antecedentes médicos mencionados"],
    "antecedentes_familiares": ["antecedentes familiares si se mencionan"],
    "habitos": {{
        "tabaquismo": "sí/no/desconocido",
        "alcohol": "sí/no/ocasional/desconocido",
        "otros": "otros hábitos relevantes"
    }},
    "sintomas_asociados": ["lista de síntomas adicionales"],
    "intensidad": "nivel de intensidad si se menciona (1-10 o descriptivo)",
    "factores_agravantes": ["factores que empeoran"],
    "factores_aliviantes": ["factores que mejoran"]
}}

Responde SOLO con el JSON válido, sin explicaciones adicionales."""

        try:
            llm_response = await llm_service.generate_response(
                system_prompt=extraction_prompt,
                user_message="Extrae la información estructurada según las instrucciones.",
                conversation_history=[],
                temperature=0.3  # Baja temperatura para respuestas consistentes
            )
            
            # Intentar parsear la respuesta JSON
            response_text = llm_response.get("response", "{}")
            
            # Limpiar la respuesta para extraer solo el JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group()
                structured_data = json.loads(json_text)
                return structured_data
            else:
                raise ValueError("No se encontró JSON válido en la respuesta")
                
        except json.JSONDecodeError as e:
            print(f"❌ Error parseando JSON del LLM: {e}")
            return self._create_basic_extraction(text, user_messages)
        except Exception as e:
            print(f"❌ Error en extracción LLM: {e}")
            return self._create_basic_extraction(text, user_messages)
    
    def _create_basic_extraction(self, text: str, user_messages: List[str]) -> Dict[str, Any]:
        """Extracción básica usando reglas y patrones cuando el LLM falla"""
        text_lower = text.lower()
        
        # Extracción básica del motivo de consulta (primer mensaje del usuario)
        motivo_consulta = user_messages[0] if user_messages else "consulta médica general"
        
        # Detectar síntoma principal usando palabras clave
        sintoma_principal = self._detect_main_symptom(text_lower)
        
        # Detectar duración/inicio
        inicio = self._detect_onset(text_lower)
        
        # Detectar antecedentes
        antecedentes = self._detect_medical_history(text_lower)
        
        # Detectar hábitos
        habitos = self._detect_habits(text_lower)
        
        # Detectar síntomas asociados
        sintomas_asociados = self._detect_associated_symptoms(text_lower)
        
        return {
            "motivo_consulta": motivo_consulta[:200],  # Limitar longitud
            "enfermedad_actual": {
                "sintoma_principal": sintoma_principal,
                "inicio": inicio,
                "caracteristicas": "requiere más información específica"
            },
            "antecedentes_personales": antecedentes,
            "antecedentes_familiares": [],
            "habitos": habitos,
            "sintomas_asociados": sintomas_asociados,
            "intensidad": "no especificada",
            "factores_agravantes": [],
            "factores_aliviantes": []
        }
    
    def _detect_main_symptom(self, text: str) -> str:
        """Detecta el síntoma principal usando patrones"""
        symptom_patterns = {
            "dolor de cabeza": ["dolor de cabeza", "cefalea", "jaqueca", "migraña"],
            "dolor torácico": ["dolor en el pecho", "dolor torácico", "dolor pecho"],
            "tos": ["tos", "toser"],
            "fiebre": ["fiebre", "temperatura", "calentura"],
            "dolor abdominal": ["dolor de estómago", "dolor abdominal", "dolor barriga"],
            "mareo": ["mareo", "mareado", "vértigo"],
            "dolor muscular": ["dolor muscular", "dolor músculo"],
            "dificultad respiratoria": ["falta de aire", "dificultad respirar", "ahogo"]
        }
        
        for symptom, patterns in symptom_patterns.items():
            if any(pattern in text for pattern in patterns):
                return symptom
        
        return "síntoma no especificado"
    
    def _detect_onset(self, text: str) -> str:
        """Detecta el inicio/duración de los síntomas"""
        time_patterns = [
            (r"hace (\d+) día[s]?", r"\1 día(s)"),
            (r"hace (\d+) semana[s]?", r"\1 semana(s)"),
            (r"hace (\d+) mes[es]?", r"\1 mes(es)"),
            (r"desde ayer", "1 día"),
            (r"desde hoy", "horas"),
            (r"esta mañana", "horas"),
            (r"anoche", "1 día")
        ]
        
        for pattern, replacement in time_patterns:
            match = re.search(pattern, text)
            if match:
                return re.sub(pattern, replacement, match.group())
        
        return "no especificado"
    
    def _detect_medical_history(self, text: str) -> List[str]:
        """Detecta antecedentes médicos mencionados"""
        conditions = []
        medical_terms = [
            "hipertensión", "diabetes", "asma", "alergias", "artritis",
            "depresión", "ansiedad", "migraña", "gastritis", "colesterol"
        ]
        
        for term in medical_terms:
            if term in text:
                conditions.append(term)
        
        return conditions
    
    def _detect_habits(self, text: str) -> Dict[str, str]:
        """Detecta hábitos mencionados"""
        habits = {
            "tabaquismo": "desconocido",
            "alcohol": "desconocido",
            "otros": ""
        }
        
        # Tabaquismo
        if any(word in text for word in ["no fumo", "no fumar"]):
            habits["tabaquismo"] = "no"
        elif any(word in text for word in ["fumo", "cigarrillo", "tabaco"]):
            habits["tabaquismo"] = "sí"
        
        # Alcohol
        if any(word in text for word in ["no bebo", "no alcohol"]):
            habits["alcohol"] = "no"
        elif any(word in text for word in ["bebo", "alcohol", "copa", "cerveza"]):
            habits["alcohol"] = "sí"
        elif "socialmente" in text or "ocasional" in text:
            habits["alcohol"] = "ocasional"
        
        return habits
    
    def _detect_associated_symptoms(self, text: str) -> List[str]:
        """Detecta síntomas asociados mencionados"""
        associated = []
        symptom_keywords = [
            "náuseas", "vómito", "mareo", "fatiga", "cansancio",
            "sudoración", "palpitaciones", "diarrea", "estreñimiento"
        ]
        
        for symptom in symptom_keywords:
            if symptom in text:
                associated.append(symptom)
        
        return associated
    
    def _validate_structure(self, structure: Dict[str, Any]) -> bool:
        """Valida que la estructura tenga los campos mínimos requeridos"""
        required_fields = [
            "motivo_consulta",
            "enfermedad_actual",
            "antecedentes_personales",
            "habitos",
            "sintomas_asociados"
        ]
        
        for field in required_fields:
            if field not in structure:
                raise ValueError(f"Campo requerido faltante: {field}")
        
        # Validar estructura de enfermedad_actual
        if not isinstance(structure["enfermedad_actual"], dict):
            raise ValueError("enfermedad_actual debe ser un diccionario")
        
        required_subfields = ["sintoma_principal", "inicio", "caracteristicas"]
        for subfield in required_subfields:
            if subfield not in structure["enfermedad_actual"]:
                raise ValueError(f"Subcampo requerido faltante en enfermedad_actual: {subfield}")
        
        return True
    
    def _create_fallback_structure(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Crea estructura de fallback cuando falla el procesamiento principal"""
        user_messages = self._extract_user_messages(conversation)
        first_message = user_messages[0] if user_messages else "consulta médica"
        
        return {
            "motivo_consulta": first_message,
            "enfermedad_actual": {
                "sintoma_principal": "requiere análisis adicional",
                "inicio": "no especificado",
                "caracteristicas": "información insuficiente"
            },
            "antecedentes_personales": [],
            "antecedentes_familiares": [],
            "habitos": {
                "tabaquismo": "desconocido",
                "alcohol": "desconocido",
                "otros": ""
            },
            "sintomas_asociados": [],
            "metadata": {
                "format_version": self.standard_format_version,
                "structured_timestamp": datetime.now().isoformat(),
                "processing_method": "fallback_basic",
                "error": "Error en procesamiento principal"
            }
        }


class SemanticNormalizer:
    """Módulo de normalización semántica para términos médicos"""
    
    def __init__(self):
        self.medical_synonyms = self._load_medical_synonyms()
        self.severity_mapping = self._load_severity_mapping()
    
    async def normalize_medical_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza términos médicos en los datos estructurados"""
        normalized_data = data.copy()
        
        # Normalizar síntoma principal
        if "enfermedad_actual" in normalized_data:
            symptom = normalized_data["enfermedad_actual"].get("sintoma_principal", "")
            normalized_data["enfermedad_actual"]["sintoma_principal"] = self._normalize_symptom(symptom)
        
        # Normalizar antecedentes
        if "antecedentes_personales" in normalized_data:
            normalized_data["antecedentes_personales"] = [
                self._normalize_condition(condition) 
                for condition in normalized_data["antecedentes_personales"]
            ]
        
        # Normalizar síntomas asociados
        if "sintomas_asociados" in normalized_data:
            normalized_data["sintomas_asociados"] = [
                self._normalize_symptom(symptom) 
                for symptom in normalized_data["sintomas_asociados"]
            ]
        
        return normalized_data
    
    def _normalize_symptom(self, symptom: str) -> str:
        """Normaliza un síntoma individual"""
        symptom_lower = symptom.lower().strip()
        
        for standard_term, synonyms in self.medical_synonyms.items():
            if any(synonym in symptom_lower for synonym in synonyms):
                return standard_term
        
        return symptom  # Retorna original si no encuentra normalización
    
    def _normalize_condition(self, condition: str) -> str:
        """Normaliza una condición médica"""
        condition_lower = condition.lower().strip()
        
        condition_mapping = {
            "hipertensión arterial": ["hipertension", "presion alta", "tension alta"],
            "diabetes mellitus": ["diabetes", "azucar alta"],
            "asma bronquial": ["asma"],
            "gastritis": ["gastritis", "acidez"],
            "migraña": ["migraña", "jaqueca"]
        }
        
        for standard_condition, variants in condition_mapping.items():
            if any(variant in condition_lower for variant in variants):
                return standard_condition
        
        return condition
    
    def _load_medical_synonyms(self) -> Dict[str, List[str]]:
        """Carga diccionario de sinónimos médicos"""
        return {
            "cefalea": ["dolor de cabeza", "jaqueca", "migraña", "dolor cabeza"],
            "dolor torácico": ["dolor pecho", "dolor en el pecho", "dolor toracico"],
            "disnea": ["falta de aire", "dificultad respirar", "ahogo"],
            "náuseas": ["nausea", "ganas de vomitar", "asco"],
            "vértigo": ["mareo", "mareado", "vertigo"],
            "astenia": ["cansancio", "fatiga", "debilidad"],
            "palpitaciones": ["taquicardia", "corazon rapido", "latidos fuertes"],
            "pirexia": ["fiebre", "temperatura", "calentura"]
        }
    
    def _load_severity_mapping(self) -> Dict[str, str]:
        """Mapeo de términos de severidad"""
        return {
            "leve": ["leve", "ligero", "poco", "suave"],
            "moderado": ["moderado", "medio", "regular"],
            "severo": ["severo", "fuerte", "intenso", "grave"],
            "muy severo": ["muy fuerte", "insoportable", "extremo"]
        }


# Instancia global del servicio
data_structuring_service = MedicalDataStructuringService()
