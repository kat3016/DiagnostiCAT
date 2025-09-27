#!/usr/bin/env python3
"""
Prueba interactiva de DiagnostiCAT - Elige qué probar
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def make_request(method: str, endpoint: str, data: Any = None, params: Dict = None) -> Dict:
    """Hacer petición HTTP"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params)
        else:
            response = requests.post(url, json=data, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error: {e}")
        return {}

def test_quick_chat():
    """Chat médico rápido"""
    print("\n🩺 CHAT MÉDICO RÁPIDO")
    print("Escribe tus síntomas y te responderá un agente médico")
    
    while True:
        message = input("\n💬 Tu mensaje (o 'salir'): ").strip()
        if message.lower() in ['salir', 'exit', 'quit']:
            break
        
        if not message:
            continue
            
        # Opcional: contexto del paciente
        age = input("🎂 Edad (opcional, Enter para omitir): ").strip()
        context = {"age": int(age)} if age.isdigit() else {}
        
        chat_data = {"message": message, "patient_context": context}
        result = make_request("POST", "/api/v1/chat/", data=chat_data)
        
        if result:
            print(f"\n🤖 {result['agent_type']}:")
            print(f"📝 {result['response']}")
            print(f"⚠️  Severidad: {result['severity_assessment']}")
            print(f"📊 Confianza: {result.get('confidence_score', 0):.2f}")

def test_anamnesis_manual():
    """Anamnesis paso a paso manual"""
    print("\n📋 ANAMNESIS INTERACTIVA")
    
    # Consentimiento
    accept = input("¿Aceptas el consentimiento informado? (s/n): ").lower().startswith('s')
    consent_result = make_request("POST", "/api/v1/consent", {"accepted": accept})
    print(f"✅ {consent_result.get('message', '')}")
    
    if not accept:
        return
    
    # Extraer conversation_id
    message = consent_result.get('message', '')
    conversation_id = message.split('conversation_id=')[1] if 'conversation_id=' in message else None
    
    if not conversation_id:
        print("❌ No se pudo obtener ID de conversación")
        return
    
    print(f"🆔 ID: {conversation_id}")
    
    # Anamnesis interactiva
    while True:
        next_q = make_request("GET", "/api/v1/anamnesis/next", params={"conversation_id": conversation_id})
        
        if next_q.get("done"):
            print("✅ Anamnesis completada")
            break
        
        print(f"\n❓ {next_q['question']}")
        answer = input("👤 Tu respuesta: ").strip()
        
        if not answer:
            continue
        
        # Intentar parsear como JSON si parece serlo
        try:
            if answer.startswith('{') or answer.startswith('['):
                answer = json.loads(answer)
        except:
            pass  # Usar como string
        
        make_request(
            "POST", "/api/v1/anamnesis/answer",
            data=answer,
            params={"conversation_id": conversation_id, "key": next_q['key']}
        )
        print("✅ Respuesta registrada")
    
    # Mostrar resultado final
    structured = make_request("GET", "/api/v1/anamnesis/structured", params={"conversation_id": conversation_id})
    if structured:
        print("\n📋 ANAMNESIS FINAL:")
        print(json.dumps(structured, indent=2, ensure_ascii=False))
    
    summary = make_request("GET", "/api/v1/anamnesis/summary", params={"conversation_id": conversation_id})
    if summary:
        print(f"\n📝 RESUMEN: {summary.get('summary', '')}")
        print("❓ SEGUIMIENTO:")
        for q in summary.get('follow_up_questions', []):
            print(f"  • {q}")

def test_scenarios():
    """Casos predefinidos"""
    scenarios = [
        {
            "name": "Emergencia cardíaca",
            "message": "Tengo dolor fuerte en el pecho, me duele el brazo izquierdo y sudo mucho",
            "context": {"age": 58, "gender": "masculino"}
        },
        {
            "name": "Resfriado común",
            "message": "Tengo tos, mocos y un poco de fiebre desde hace 2 días",
            "context": {"age": 25, "gender": "femenino"}
        },
        {
            "name": "Dolor de cabeza",
            "message": "Me duele la cabeza desde esta mañana, es como una presión",
            "context": {"age": 32}
        },
        {
            "name": "Consulta general",
            "message": "Me siento cansado últimamente y no sé por qué",
            "context": {"age": 40}
        }
    ]
    
    print("\n🎭 ESCENARIOS PREDEFINIDOS")
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
    
    try:
        choice = int(input("\nElige un escenario (1-4): ")) - 1
        if 0 <= choice < len(scenarios):
            scenario = scenarios[choice]
            print(f"\n🎬 Probando: {scenario['name']}")
            print(f"💬 Mensaje: {scenario['message']}")
            
            result = make_request("POST", "/api/v1/chat/", data={
                "message": scenario['message'],
                "patient_context": scenario['context']
            })
            
            if result:
                print(f"\n🤖 {result['agent_type']}:")
                print(f"📝 {result['response']}")
                print(f"⚠️  Severidad: {result['severity_assessment']}")
                if result.get('suggestions'):
                    print("💡 Sugerencias:")
                    for s in result['suggestions'][:3]:
                        print(f"  • {s}")
    except (ValueError, IndexError):
        print("❌ Opción inválida")

def main():
    """Menú principal"""
    print("🏥 DIAGNOSTICAT - PRUEBA INTERACTIVA")
    print("="*40)
    
    # Verificar servidor
    health = make_request("GET", "/health")
    if not health:
        print("❌ El servidor no está disponible en http://localhost:8000")
        print("💡 Ejecuta: uvicorn main:app --reload")
        return
    
    print(f"✅ Servidor funcionando: {health.get('status', 'OK')}")
    
    while True:
        print("\n📋 OPCIONES:")
        print("1. Chat médico rápido")
        print("2. Anamnesis paso a paso")
        print("3. Probar escenarios predefinidos")
        print("4. Salir")
        
        choice = input("\n👉 Elige una opción (1-4): ").strip()
        
        if choice == "1":
            test_quick_chat()
        elif choice == "2":
            test_anamnesis_manual()
        elif choice == "3":
            test_scenarios()
        elif choice == "4":
            print("👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción inválida")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
