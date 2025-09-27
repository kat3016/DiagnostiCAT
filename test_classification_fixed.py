"""
Script de prueba para el sistema de clasificación arreglado con Hugging Face
"""

import asyncio
import json
from app.services.classification_service import classification_model

async def test_classification_fixed():
    """Prueba el sistema de clasificación médica corregido"""
    
    print("🧪 Probando sistema de clasificación médica CORREGIDO")
    print("=" * 60)
    
    # Casos de prueba más diversos
    test_cases = [
        {
            "name": "Caso Neurológico Fuerte",
            "data": {
                "symptoms": ["dolor de cabeza severo", "migraña", "mareos intensos", "visión borrosa"],
                "chief_complaint": "Cefalea pulsátil muy intensa desde hace 3 días",
                "history": "Dolor que empeora con la luz, náuseas asociadas",
                "duration": "3 días",
                "severity": "severo"
            }
        },
        {
            "name": "Caso Cardiovascular Claro", 
            "data": {
                "symptoms": ["dolor en el pecho", "palpitaciones fuertes", "falta de aire", "sudoración"],
                "chief_complaint": "Dolor torácico opresivo con palpitaciones",
                "history": "Dolor que aumenta con esfuerzo, sensación de presión en pecho",
                "duration": "2 horas",
                "severity": "moderado a severo"
            }
        },
        {
            "name": "Caso Respiratorio",
            "data": {
                "symptoms": ["tos persistente", "dificultad para respirar", "dolor al respirar profundo"],
                "chief_complaint": "Tos con expectoración y disnea",
                "history": "Síntomas que empeoraron gradualmente, fiebre leve",
                "duration": "1 semana"
            }
        },
        {
            "name": "Caso Gastrointestinal",
            "data": {
                "symptoms": ["dolor de estómago", "náuseas constantes", "vómitos", "pérdida de apetito"],
                "chief_complaint": "Dolor abdominal con náuseas y vómitos",
                "history": "Dolor que empeora después de comer",
                "duration": "2 días"
            }
        },
        {
            "name": "Caso Mixto/Ambiguo",
            "data": {
                "symptoms": ["fatiga extrema", "dolor generalizado", "insomnio"],
                "chief_complaint": "Cansancio y dolor generalizado",
                "history": "Síntomas vagos, múltiples molestias",
                "duration": "2 semanas"
            }
        }
    ]
    
    # Obtener información del modelo
    model_info = classification_model.get_model_info()
    print("📊 Información del modelo:")
    print(json.dumps(model_info, indent=2, ensure_ascii=False))
    print("\n" + "=" * 60)
    
    # Probar cada caso
    for case in test_cases:
        print(f"\n🔍 {case['name']}")
        print("-" * 50)
        print(f"Síntomas: {', '.join(case['data']['symptoms'])}")
        print(f"Motivo: {case['data']['chief_complaint']}")
        
        try:
            # Clasificar
            result = await classification_model.classify(case['data'])
            
            print(f"\n✅ Resultado de clasificación:")
            print(f"   🎯 Categoría principal: {result['primary_category']}")
            print(f"   📊 Confianza: {result['confidence_score']:.3f}")
            print(f"   📋 Categorías secundarias: {result.get('secondary_categories', [])}")
            print(f"   🚨 Nivel de urgencia: {result['urgency_level']}")
            print(f"   🔧 Método usado: {result.get('method', 'N/A')}")
            print(f"   🤖 Modelo: {result.get('model_used', 'N/A')}")
            print(f"   🔍 Indicadores clave: {result.get('key_indicators', [])}")
            print(f"   💡 Recomendaciones:")
            for rec in result.get('recommendations', []):
                print(f"     - {rec}")
            print(f"   📝 Razonamiento: {result.get('reasoning', 'N/A')}")
            
            # Mostrar si la confianza es razonable
            confidence = result['confidence_score']
            if confidence > 0.7:
                print(f"   ✅ Confianza ALTA ({confidence:.3f})")
            elif confidence > 0.5:
                print(f"   ⚠️  Confianza MEDIA ({confidence:.3f})")
            else:
                print(f"   ❌ Confianza BAJA ({confidence:.3f})")
            
        except Exception as e:
            print(f"❌ Error en clasificación: {e}")
        
        print("\n" + "=" * 60)
    
    # Probar cambio de modelo
    print("\n🔄 Probando cambio a modelo médico especializado...")
    try:
        success = await classification_model.switch_model(use_medical_bert=True)
        if success:
            print("✅ Cambiado a modelo médico especializado")
            
            # Probar un caso con el nuevo modelo
            test_case = test_cases[0]  # Caso neurológico
            result = await classification_model.classify(test_case['data'])
            print(f"   Nueva clasificación: {result['primary_category']} (confianza: {result['confidence_score']:.3f})")
            print(f"   Método: {result.get('method', 'N/A')}")
        else:
            print("❌ No se pudo cambiar el modelo")
    except Exception as e:
        print(f"❌ Error cambiando modelo: {e}")
    
    print("\n🎉 Prueba completada!")

if __name__ == "__main__":
    asyncio.run(test_classification_fixed())