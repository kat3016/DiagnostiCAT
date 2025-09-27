from crewai import Agent
import json
from transformers import pipeline

# === Clase de lógica de estructuración ===
class AgenteEstructuracionIA:
    def __init__(self):
        try:
            self.ner_pipeline = pipeline("ner", model="d4data/biomedical-ner-all", aggregation_strategy="simple")
            self.use_ner = True
        except Exception:
            self.ner_pipeline = None
            self.use_ner = False

        self.key_map = {
            "frecuencia alcohol": "frecuencia_alcohol",
            "cantidad alcohol": "cantidad_alcohol",
            "ocupación": "ocupacion",
            "sexo": "sexo_genero"
        }

    def normalizar_claves(self, datos_crudos):
        normalizados = {}
        for k, v in datos_crudos.items():
            key_norm = self.key_map.get(k.lower(), k.lower())
            normalizados[key_norm] = v
        return normalizados

    def extraer_sintomas(self, texto):
        if not texto:
            return ["no especificado"]
        if self.use_ner:
            try:
                entidades = self.ner_pipeline(texto)
                sintomas = [ent["word"] for ent in entidades if ent["entity_group"] in ["SYMPTOM","DISEASE"]]
                return list(dict.fromkeys(sintomas)) if sintomas else [texto]
            except:
                return [texto]
        return [texto]

    def estructurar(self, datos_crudos):
        datos = self.normalizar_claves(datos_crudos)
        return {
            "datos_identificacion": {
                "nombre_completo": datos.get("nombre", "no especificado"),
                "edad": datos.get("edad", "no especificado"),
                "sexo_genero": datos.get("sexo_genero", "no especificado"),
                "ocupacion": datos.get("ocupacion", "no especificado"),
                "lugar_residencia": datos.get("residencia", "no especificado")
            },
            "motivo_consulta": {
                "descripcion": datos.get("motivo_consulta", "no especificado"),
                "tiempo_evolucion": datos.get("tiempo_evolucion", "no especificado")
            },
            "enfermedad_actual": {
                "sintomas": self.extraer_sintomas(datos.get("sintomas", "")),
                "inicio": datos.get("inicio", "no especificado"),
                "localizacion": datos.get("localizacion", "no especificado"),
                "caracteristicas": datos.get("caracteristicas", "no especificado"),
                "factores_modificadores": datos.get("factores_modificadores", "no especificado"),
                "evolucion": datos.get("evolucion", "no especificado"),
                "intensidad": datos.get("intensidad", "no especificado"),
                "medicacion_autoadministrada": datos.get("medicacion_autoadministrada", "no especificado")
            },
            "antecedentes_personales": {
                "enfermedades_previas": datos.get("antecedentes_personales", []),
                "hospitalizaciones_cirugias": datos.get("hospitalizaciones", []),
                "medicacion_actual": datos.get("medicacion_actual", []),
                "alergias": datos.get("alergias", [])
            },
            "antecedentes_familiares": {
                "enfermedades_familia": datos.get("antecedentes_familiares", []),
                "enfermedades_hereditarias": datos.get("hereditarias", [])
            },
            "habitos_estilo_vida": {
                "tabaquismo": {
                    "consume": datos.get("tabaquismo", "no especificado"),
                    "cantidad": datos.get("cantidad_tabaco", "no especificado"),
                    "tiempo_consumo": datos.get("tiempo_tabaco", "no especificado")
                },
                "alcohol": {
                    "consume": datos.get("alcohol", "no especificado"),
                    "frecuencia": datos.get("frecuencia_alcohol", "no especificado"),
                    "cantidad": datos.get("cantidad_alcohol", "no especificado")
                },
                "cafe_u_otras_bebidas": datos.get("cafe", "no especificado"),
                "ejercicio_fisico": {
                    "realiza": datos.get("ejercicio", "no especificado"),
                    "frecuencia": datos.get("frecuencia_ejercicio", "no especificado")
                },
                "alimentacion": datos.get("alimentacion", "no especificado"),
                "drogas_recreativas": datos.get("drogas", "no especificado")
            },
            "revision_por_sistemas": {
                "generales": {"fiebre": "no especificado", "escalofrios": "no especificado", "perdida_peso": "no especificado"},
                "respiratorio": {"tos": "no especificado", "dificultad_respirar": "no especificado", "dolor_pecho": "no especificado"},
                "digestivo": {"dolor_abdominal": "no especificado", "vomito": "no especificado", "diarrea": "no especificado"},
                "urinario": {"cambios_orina": "no especificado", "dolor_orinar": "no especificado"},
                "musculoesqueletico": {"dolor_muscular": "no especificado", "dolor_articular": "no especificado", "dolor_oseo": "no especificado"},
                "neurologico_psiquico": {"alteraciones_sueno": "no especificado", "alteraciones_animo": "no especificado", "alteraciones_memoria": "no especificado"}
            }
        }

# === Agente CrewAI que envuelve la lógica ===
class CrewAgenteEstructuracion(Agent):
    def __init__(self):
        super().__init__(
            role="Estructurador",
            goal="Convertir datos crudos de la anamnesis en JSON estandarizado",
            backstory="Este agente recibe las respuestas del paciente y organiza toda la información en un formato médico estructurado."
        )

    def run(self, datos_crudos):
        structurer = AgenteEstructuracionIA()
        json_final = structurer.estructurar(datos_crudos)
        return json.dumps(json_final, indent=2, ensure_ascii=False)


# === Simulación de input desde otro agente CrewAI ===
datos_crudos = {
    "nombre": "Laura Gómez",
    "edad": "32",
    "sexo": "Femenino",
    "ocupación": "Abogada",
    "residencia": "Medellín",
    "motivo_consulta": "dolor en el pecho",
    "sintomas": "Tengo dolor opresivo en el pecho desde anoche, con mareo y sudoración",
    "antecedentes_personales": ["hipertensión"],
    "antecedentes_familiares": ["infarto en padre"],
    "tabaquismo": "no",
    "alcohol": "sí",
    "frecuencia alcohol": "ocasional",
    "ejercicio": "sí",
    "alimentacion": "balanceada",
    "droga": "cocaína"
}

# Invocar el agente de CrewAI
agente3 = CrewAgenteEstructuracion()
print(agente3.run(datos_crudos))


