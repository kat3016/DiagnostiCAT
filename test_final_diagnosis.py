"""
Test final para verificar que el diagnóstico usa las hipótesis de la IA
"""
import asyncio
import uuid
from datetime import datetime

# Importar las funciones necesarias
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.routers.medical_chat import generate_diagnosis_summary

async def test_final_diagnosis():
    print("🧪 TEST FINAL: Diagnóstico con hipótesis de IA")
    print("="*55)
    
    # Simular hipótesis generadas por la IA
    ai_hypotheses = [
        "**Cólico Renal**: Dada la intensidad del dolor (8) y su posible relación con el movimiento (agacharse), podría sugerir un cálculo renal que se está moviendo y causa dolor intermitente.",
        "**Apendicitis Temprana**: El dolor abdominal de intensidad alta que empeora con el movimiento podría indicar una inflamación apendicular en sus etapas iniciales.",
        "**Obstrucción Intestinal Parcial**: Los síntomas de dolor intenso que empeora con ciertos movimientos podrían sugerir una obstrucción intestinal de grado leve a moderado."
    ]
    
    # Simular síntomas recopilados
    symptoms_collected = [
        "dolor: me duele el abdomen",
        "síntoma general: hace un dia", 
        "síntoma general: 8",
        "dolor: me duele al agacharme",
        "síntoma general: no",
        "síntoma general: no",
        "síntoma general: no"
    ]
    
    # Simular resultado de clasificación de Hugging Face
    classification_result = {
        "primary_category": "gastrointestinal",
        "confidence_score": 0.87,
        "secondary_categories": ["musculoskeletal", "other"],
        "method": "huggingface",
        "model_used": "facebook/bart-large-mnli",
        "urgency_level": "medium"
    }
    
    try:
        print(f"📋 Hipótesis de la IA ({len(ai_hypotheses)}):")
        for i, hyp in enumerate(ai_hypotheses, 1):
            print(f"  {i}. {hyp[:80]}...")
        
        # Generar diagnóstico usando las hipótesis de la IA
        diagnosis_text = await generate_diagnosis_summary(
            classification_result, 
            symptoms_collected,
            ai_hypotheses
        )
        
        print(f"\n✅ DIAGNÓSTICO GENERADO:")
        print(diagnosis_text)
        
        # Verificar que las hipótesis de IA están presentes
        ai_terms = ["Cólico Renal", "Apendicitis", "Obstrucción Intestinal"]
        found_terms = [term for term in ai_terms if term in diagnosis_text]
        
        print(f"\n📊 ANÁLISIS:")
        print(f"✅ Términos de IA encontrados: {found_terms}")
        print(f"✅ Total encontrados: {len(found_terms)}/{len(ai_terms)}")
        
        if len(found_terms) >= 2:
            print("🎯 ¡EL DIAGNÓSTICO ESTÁ USANDO LAS HIPÓTESIS DE LA IA!")
        else:
            print("❌ El diagnóstico podría estar usando condiciones por defecto")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_final_diagnosis())