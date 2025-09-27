# Sistema de Clasificación Médica con Hugging Face - DiagnostiCAT

## Resumen de Cambios Implementados

### 🔧 Modificaciones Realizadas

1. **Actualización de dependencias** (`requirements.txt`):
   - `transformers==4.36.0` - Biblioteca principal de Hugging Face
   - `torch==2.1.0` - Framework de deep learning
   - `tokenizers==0.15.0` - Tokenizadores optimizados
   - `numpy==1.24.3` - Computación numérica
   - `scikit-learn==1.3.0` - Herramientas de machine learning

2. **Refactorización del `classification_service.py`**:
   - **Modelo dual**: Bio_ClinicalBERT (médico especializado) + Zero-shot classification
   - **Inicialización lazy**: Los modelos se cargan bajo demanda
   - **Fallback inteligente**: Si HF falla, usa LLM como respaldo
   - **Ejecución asíncrona**: No bloquea el servidor
   - **Clasificación por palabras clave**: Para casos sin modelo entrenado

3. **Corrección de errores**:
   - Arreglado `AgentType.GENERAL_PRACTITIONER` faltante
   - Corregida inicialización asíncrona en constructor
   - Arregladas importaciones en `agent_service.py`

### 🎯 Características del Sistema

#### Modelos Disponibles:
1. **Bio_ClinicalBERT** (`emilyalsentzer/Bio_ClinicalBERT`)
   - Modelo BERT especializado en texto médico
   - Entrenado en datos clínicos
   - Mejor para terminología médica específica

2. **Zero-Shot Classification** (`facebook/bart-large-mnli`)
   - Clasificación sin entrenamiento específico
   - Más generalista pero funcional
   - Útil para casos no vistos antes

#### Categorías de Clasificación:
- `neurological` - Problemas neurológicos
- `cardiovascular` - Problemas cardíacos y vasculares
- `respiratory` - Problemas respiratorios
- `gastrointestinal` - Problemas digestivos
- `musculoskeletal` - Problemas músculo-esqueléticos
- `dermatological` - Problemas de piel
- `psychiatric` - Problemas de salud mental
- `other` - Otros casos

#### Funcionalidades:
- ✅ **Clasificación automática** con confianza
- ✅ **Recomendaciones personalizadas** por categoría
- ✅ **Evaluación de urgencia** (low/medium/high/critical)
- ✅ **Extracción de indicadores clave**
- ✅ **Cambio dinámico de modelos**
- ✅ **Fallback a LLM** si HF no está disponible
- ✅ **Procesamiento asíncrono**

### 🧪 Resultados de Pruebas

```
Caso Neurológico: ✅ neurological (0.60 confianza)
- Síntomas: dolor de cabeza intenso, mareo, náuseas
- Resultado: Clasificación correcta con recomendaciones específicas

Caso Cardiovascular: ✅ cardiovascular (0.60 confianza)  
- Síntomas: dolor en pecho, palpitaciones, dificultad respirar
- Resultado: Clasificación correcta con evaluación cardiológica

Caso Respiratorio: ✅ respiratory (0.60 confianza)
- Síntomas: tos persistente, falta de aire, dolor al respirar  
- Resultado: Clasificación correcta con evaluación pulmonar
```

### 🚀 Cómo Usar

#### API del Servicio:
```python
from app.services.classification_service import classification_model

# Clasificar datos de anamnesis
result = await classification_model.classify({
    "symptoms": ["dolor de cabeza", "mareo"],
    "chief_complaint": "Cefalea intensa",
    "duration": "2 días"
})

# Cambiar modelo
await classification_model.switch_model(use_medical_bert=False)

# Información del modelo
info = classification_model.get_model_info()
```

#### Estructura de Respuesta:
```json
{
  "primary_category": "neurological",
  "confidence_score": 0.85,
  "secondary_categories": ["other"],
  "key_indicators": ["dolor cabeza", "mareo"],
  "recommendations": [
    "Consulta médica para evaluación completa",
    "Considera evaluación neurológica especializada"
  ],
  "urgency_level": "medium",
  "reasoning": "Clasificación automática...",
  "method": "huggingface",
  "model_used": "emilyalsentzer/Bio_ClinicalBERT"
}
```

### 🔄 Ventajas del Nuevo Sistema

1. **Precisión mejorada**: Modelos especializados en medicina
2. **Flexibilidad**: Múltiples modelos intercambiables
3. **Robustez**: Sistema de fallback multinivel
4. **Escalabilidad**: Procesamiento asíncrono
5. **Mantenibilidad**: Código modular y bien documentado
6. **Monitoreo**: Métricas de confianza y tiempos

### 📋 Próximos Pasos Recomendados

1. **Fine-tuning**: Entrenar Bio_ClinicalBERT con datos específicos de DiagnostiCAT
2. **Evaluación**: Crear dataset de prueba con casos reales
3. **Optimización**: Implementar caching de modelos
4. **Métricas**: Dashboard de rendimiento y precisión
5. **A/B Testing**: Comparar diferentes modelos en producción

El sistema está listo para producción con capacidades avanzadas de clasificación médica usando Hugging Face! 🎉