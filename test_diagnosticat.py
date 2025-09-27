#!/usr/bin/env python3
"""
Script de prueba para DiagnostiCAT - Flujo completo de consentimiento y anamnesis
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def print_header(title: str):
    print(f"\n{'='*50}")
    print(f"🏥 {title}")
    print(f"{'='*50}")

def print_step(step: str):
    print(f"\n📋 {step}")
    print("-" * 30)

def make_request(method: str, endpoint: str, data: Any = None, params: Dict = None) -> Dict:
    """Hacer petición HTTP y manejar errores"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, params=params)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en {method} {endpoint}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Detalle: {e.response.text}")
        sys.exit(1)

def test_health():
    """Verificar que el servidor esté funcionando"""
    print_step("Verificando servidor")
    result = make_request("GET", "/health")
    print(f"✅ Servidor funcionando: {result['status']}")

def test_consent() -> str:
    """Probar consentimiento y obtener conversation_id"""
    print_step("Consentimiento informado")
    
    # Probar rechazo primero
    print("🔸 Probando rechazo...")
    reject_result = make_request("POST", "/api/v1/consent", {"accepted": False})
    print(f"   Rechazo: {reject_result['message']}")
    
    # Aceptar consentimiento
    print("🔸 Aceptando consentimiento...")
    accept_result = make_request("POST", "/api/v1/consent", {"accepted": True})
    print(f"   ✅ {accept_result['message']}")
    
    # Extraer conversation_id del mensaje
    message = accept_result['message']
    conversation_id = message.split('conversation_id=')[1] if 'conversation_id=' in message else None
    
    if not conversation_id:
        print("❌ No se pudo obtener conversation_id")
        sys.exit(1)
    
    print(f"   🆔 ID de conversación: {conversation_id}")
    return conversation_id

def test_anamnesis_flow(conversation_id: str):
    """Probar el flujo completo de anamnesis"""
    print_step("Flujo de anamnesis")
    
    # Datos de ejemplo para la anamnesis
    anamnesis_data = {
        "motivo_consulta": "Dolor de cabeza persistente",
        "enfermedad_actual": {
            "sintoma_principal": "cefalea",
            "inicio": "hace 3 días",
            "caracteristicas": "dolor sordo, empeora por las tardes"
        },
        "antecedentes_personales": ["migraña ocasional"],
        "antecedentes_familiares": ["hipertensión materna"],
        "habitos": {
            "tabaquismo": "no",
            "alcohol": "social, fines de semana",
            "ejercicio": "caminar 3 veces por semana"
        },
        "sintomas_asociados": ["náusea leve", "sensibilidad a la luz"]
    }
    
    # Completar anamnesis paso a paso
    for key, value in anamnesis_data.items():
        # Obtener próxima pregunta
        next_q = make_request("GET", "/api/v1/anamnesis/next", params={"conversation_id": conversation_id})
        
        if next_q.get("done"):
            print("✅ Anamnesis completada")
            break
        
        print(f"🔸 Pregunta: {next_q['question']}")
        
        # Responder pregunta
        answer_result = make_request(
            "POST", 
            "/api/v1/anamnesis/answer",
            data=value,
            params={"conversation_id": conversation_id, "key": key}
        )
        print(f"   ✅ Respuesta registrada para: {key}")
    
    # Obtener estructura JSON final
    print("\n🔸 Obteniendo anamnesis estructurada...")
    structured = make_request("GET", "/api/v1/anamnesis/structured", params={"conversation_id": conversation_id})
    
    print("📋 ANAMNESIS ESTRUCTURADA:")
    print(f"   • Motivo: {structured['motivo_consulta']}")
    print(f"   • Síntoma principal: {structured['enfermedad_actual'].get('sintoma_principal', 'N/A')}")
    print(f"   • Antecedentes personales: {', '.join(structured['antecedentes_personales'])}")
    print(f"   • Hábitos: {structured['habitos']}")
    
    # Obtener resumen y seguimiento
    print("\n🔸 Generando resumen y preguntas de seguimiento...")
    summary = make_request("GET", "/api/v1/anamnesis/summary", params={"conversation_id": conversation_id})
    
    print("📝 RESUMEN:")
    print(f"   {summary['summary']}")
    print("\n❓ PREGUNTAS DE SEGUIMIENTO:")
    for i, question in enumerate(summary['follow_up_questions'], 1):
        print(f"   {i}. {question}")

def test_medical_chat():
    """Probar el chat médico con agentes"""
    print_step("Chat médico con agentes")
    
    test_cases = [
        {
            "message": "Tengo dolor de pecho desde hace 30 minutos y me cuesta respirar",
            "context": {"age": 55, "gender": "masculino"},
            "description": "Caso de urgencia alta"
        },
        {
            "message": "He tenido tos seca por una semana",
            "context": {"age": 28, "gender": "femenino"},
            "description": "Consulta general"
        },
        {
            "message": "Tengo dolor de cabeza leve desde ayer",
            "context": {"age": 35},
            "description": "Síntoma menor"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n🔸 Caso {i}: {case['description']}")
        print(f"   Mensaje: \"{case['message']}\"")
        
        chat_data = {
            "message": case["message"],
            "patient_context": case["context"]
        }
        
        result = make_request("POST", "/api/v1/chat/", data=chat_data)
        
        print(f"   🤖 Agente: {result['agent_type']}")
        print(f"   ⚠️  Severidad: {result['severity_assessment']}")
        print(f"   📊 Confianza: {result['confidence_score']:.2f}")
        print(f"   💬 Respuesta: {result['response'][:100]}...")
        
        if result.get('follow_up_questions'):
            print("   ❓ Preguntas de seguimiento:")
            for q in result['follow_up_questions'][:2]:
                print(f"      • {q}")

def main():
    """Función principal"""
    print_header("PRUEBA COMPLETA DE DIAGNOSTICAT")
    
    try:
        # 1. Verificar servidor
        test_health()
        
        # 2. Probar consentimiento
        conversation_id = test_consent()
        
        # 3. Probar anamnesis completa
        test_anamnesis_flow(conversation_id)
        
        # 4. Probar chat médico
        test_medical_chat()
        
        print_header("PRUEBAS COMPLETADAS EXITOSAMENTE ✅")
        print("🎉 Todos los endpoints funcionan correctamente!")
        print("💡 Puedes ver la documentación completa en: http://localhost:8000/docs")
        
    except KeyboardInterrupt:
        print("\n👋 Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Iniciando pruebas de DiagnostiCAT...")
    print("📍 Asegúrate de que el servidor esté ejecutándose en http://localhost:8000")
    print("   Comando: uvicorn main:app --reload")
    
    input("\n📱 Presiona ENTER para continuar...")
    main()
