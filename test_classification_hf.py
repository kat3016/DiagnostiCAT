"""
Script de prueba para el sistema de clasificación con Hugging Face
"""

import asyncio
import json
from app.services.classification_service import classification_model

async def test_classification():
    """Prueba el sistema de clasificación médica"""
    
    print("🧪 Probando sistema de clasificación médica con Hugging Face")
    print("=" * 60)
    
    # Datos de prueba - síntomas neurológicos
    test_data_neuro = {
        "symptoms": ["dolor de cabeza intenso", "mareo", "náuseas"],
        "chief_complaint": "Dolor de cabeza muy fuerte desde hace 2 días",
        "history": "Paciente refiere cefalea pulsátil, especialmente en lado derecho",
        "current_medications": ["ibuprofeno"],
        "duration": "2 días"
    }
    
    # Datos de prueba - síntomas cardiovasculares
    test_data_cardio = {
        "symptoms": ["dolor en pecho", "palpitaciones", "dificultad para respirar"],
        "chief_complaint": "Dolor opresivo en el pecho",
        "history": "Dolor que aumenta con esfuerzo físico",
        "current_medications": [],
        "duration": "3 horas"
    }
    
    # Datos de prueba - síntomas respiratorios
    test_data_resp = {
        "symptoms": ["tos persistente", "falta de aire", "dolor al respirar"],
        "chief_complaint": "Tos con expectoración y dificultad respiratoria",
        "history": "Síntomas que empeoraron progresivamente",
        "current_medications": ["salbutamol"],
        "duration": "1 semana"
    }
    
    test_cases = [
        ("Caso Neurológico", test_data_neuro),
        ("Caso Cardiovascular", test_data_cardio),
        ("Caso Respiratorio", test_data_resp)
    ]
    
    # Obtener información del modelo
    model_info = classification_model.get_model_info()
    print("📊 Información del modelo:")
    print(json.dumps(model_info, indent=2, ensure_ascii=False))
    print("\n" + "=" * 60)
    
    # Probar cada caso
    for case_name, test_data in test_cases:
        print(f"\n🔍 {case_name}")
        print("-" * 40)
        print(f"Datos de entrada: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
        
        try:
            # Clasificar
            result = await classification_model.classify(test_data)
            
            print(f"\n✅ Resultado de clasificación:")
            print(f"   Categoría principal: {result['primary_category']}")
            print(f"   Confianza: {result['confidence_score']:.2f}")
            print(f"   Categorías secundarias: {result.get('secondary_categories', [])}")
            print(f"   Nivel de urgencia: {result['urgency_level']}")
            print(f"   Método usado: {result.get('method', 'N/A')}")
            print(f"   Modelo: {result.get('model_used', 'N/A')}")
            print(f"   Indicadores clave: {result.get('key_indicators', [])}")
            print(f"   Recomendaciones:")
            for rec in result.get('recommendations', []):
                print(f"     - {rec}")
            print(f"   Razonamiento: {result.get('reasoning', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Error en clasificación: {e}")
        
        print("\n" + "=" * 60)
    
    # Probar cambio de modelo si está disponible
    print("\n🔄 Probando cambio de modelo...")
    try:
        # Cambiar a zero-shot
        success = await classification_model.switch_model(use_medical_bert=False)
        if success:
            print("✅ Cambiado a modelo zero-shot")
            
            # Probar un caso con el nuevo modelo
            result = await classification_model.classify(test_data_neuro)
            print(f"   Nueva clasificación: {result['primary_category']} (confianza: {result['confidence_score']:.2f})")
            print(f"   Método: {result.get('method', 'N/A')}")
        else:
            print("❌ No se pudo cambiar el modelo")
    except Exception as e:
        print(f"❌ Error cambiando modelo: {e}")

if __name__ == "__main__":
    asyncio.run(test_classification())