"""
Test completo del flujo de preguntas específicas
"""

from app.crew.hybrid_agent import generate_questions_hybrid
from app.routers.medical_chat import parse_agent_analysis, format_interview_data_for_agent

# Simular datos de síntomas
test_symptoms = {
    "motivo_consulta": "Dolor de cabeza constante",
    "inicio_sintomas": "Hace 3 días",
    "intensidad": "7/10",
    "antecedentes_medicos": "Hipertensión",
    "medicamentos_actuales": "Losartan",
    "antecedentes_familiares": "Diabetes tipo 2",
    "habitos_relevantes": "Fumador social"
}

print("🧪 TEST COMPLETO DEL FLUJO:")
print("=" * 60)

# Paso 1: Formatear datos para el agente
print("📝 PASO 1: Formatear datos para el agente")
interview_summary = format_interview_data_for_agent(test_symptoms)
print(f"Datos formateados:\n{interview_summary}")
print("-" * 40)

# Paso 2: Llamar al agente híbrido
print("🤖 PASO 2: Llamar al agente híbrido")
hybrid_result = generate_questions_hybrid(interview_summary)

if hybrid_result["success"]:
    print(f"✅ Agente funcionó con {hybrid_result['provider']}")
    print(f"📄 RESPUESTA COMPLETA DEL AGENTE:")
    print(hybrid_result["content"])
    print("-" * 40)
    
    # Paso 3: Parsear el resultado
    print("🔍 PASO 3: Parsear resultado")
    hypotheses, questions = parse_agent_analysis(hybrid_result["content"])
    
    print(f"🎯 HIPÓTESIS EXTRAÍDAS ({len(hypotheses)}):")
    for i, h in enumerate(hypotheses, 1):
        print(f"  {i}. {h}")
    
    print(f"❓ PREGUNTAS EXTRAÍDAS ({len(questions)}):")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q}")
        
    # Verificar si las preguntas son del agente o fallback
    fallback_phrases = ["localización exacta", "actividad específica", "patrón temporal"]
    is_fallback = any(phrase in questions[0].lower() for phrase in fallback_phrases)
    
    if is_fallback:
        print("⚠️  PROBLEMA: Se están usando preguntas de fallback, no del agente")
    else:
        print("✅ Las preguntas parecen ser del agente de IA")
        
else:
    print(f"❌ Error en agente: {hybrid_result['error']}")