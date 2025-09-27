#!/usr/bin/env python3
"""
Script para probar DiagnostiCAT con Nemotron
"""

import requests
import json
import os
from typing import Dict

BASE_URL = "http://localhost:8000"

def test_nemotron_integration():
    """Prueba la integración con Nemotron"""
    
    print("🤖 PRUEBA DE INTEGRACIÓN NEMOTRON")
    print("="*50)
    
    # Verificar configuración
    print("\n📋 Verificando configuración...")
    
    # Casos de prueba específicos para Nemotron
    test_cases = [
        {
            "name": "Consulta cardiológica compleja",
            "message": "Tengo 65 años, diabético, y desde hace 2 horas siento presión en el pecho que se irradia al brazo izquierdo. También tengo sudoración y náuseas.",
            "context": {
                "age": 65,
                "gender": "masculino",
                "medical_history": ["diabetes tipo 2", "hipertensión"],
                "current_medications": ["metformina", "enalapril"]
            },
            "expected": "Debería identificar signos de alarma cardíaca"
        },
        {
            "name": "Consulta pediátrica",
            "message": "Mi hijo de 3 años tiene fiebre de 39°C desde ayer, no quiere comer y está muy irritable. Le han salido manchitas rojas en el cuerpo.",
            "context": {
                "age": 3,
                "gender": "masculino",
                "symptoms": ["fiebre", "irritabilidad", "exantema"]
            },
            "expected": "Debería sugerir evaluación pediátrica urgente"
        },
        {
            "name": "Consulta de salud mental",
            "message": "Me siento muy ansioso últimamente, no puedo dormir bien, tengo taquicardia y sensación de que algo malo va a pasar. Esto empezó hace 2 semanas.",
            "context": {
                "age": 28,
                "gender": "femenino",
                "symptoms": ["ansiedad", "insomnio", "taquicardia"]
            },
            "expected": "Debería reconocer síntomas de ansiedad y sugerir evaluación"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n🧪 CASO {i}: {case['name']}")
        print(f"📝 Mensaje: {case['message'][:100]}...")
        print(f"🎯 Esperado: {case['expected']}")
        
        # Hacer petición
        chat_data = {
            "message": case["message"],
            "patient_context": case["context"]
        }
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/chat/", json=chat_data)
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"✅ Respuesta recibida:")
                print(f"   🤖 Agente: {result['agent_type']}")
                print(f"   ⚠️  Severidad: {result['severity_assessment']}")
                print(f"   📊 Confianza: {result['confidence_score']:.2f}")
                print(f"   🕒 Tiempo: {result.get('processing_time', 'N/A')} segundos")
                
                # Mostrar respuesta completa
                print(f"   💬 Respuesta completa:")
                response_lines = result['response'].split('\n')
                for line in response_lines[:5]:  # Primeras 5 líneas
                    print(f"      {line}")
                if len(response_lines) > 5:
                    print(f"      ... ({len(response_lines) - 5} líneas más)")
                
                # Verificar si menciona modelo usado
                if 'provider_used' in result:
                    print(f"   🔧 Proveedor: {result['provider_used']}")
                
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Excepción: {e}")
        
        print("-" * 50)

def check_configuration():
    """Verificar configuración del sistema"""
    print("🔧 VERIFICACIÓN DE CONFIGURACIÓN")
    print("="*40)
    
    # Variables de entorno importantes
    env_vars = [
        ("LLM_PROVIDER", "Proveedor de LLM"),
        ("NVIDIA_API_KEY", "API Key de NVIDIA"),
        ("NVIDIA_BASE_URL", "URL base de NVIDIA"),
        ("NEMOTRON_MODEL", "Modelo Nemotron"),
        ("LLM_TEMPERATURE", "Temperatura del modelo"),
        ("LLM_MAX_TOKENS", "Máximo de tokens")
    ]
    
    print("\n📋 Variables de entorno:")
    for var, desc in env_vars:
        value = os.getenv(var, "NO CONFIGURADO")
        if "API_KEY" in var and value != "NO CONFIGURADO":
            # Ocultar API key
            value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
        print(f"   {desc}: {value}")
    
    # Verificar servidor
    print(f"\n🌐 Verificando servidor en {BASE_URL}...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Servidor funcionando")
            return True
        else:
            print(f"   ❌ Servidor responde con error {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ No se puede conectar al servidor: {e}")
        return False

def main():
    """Función principal"""
    print("🏥 DIAGNOSTICAT - PRUEBA NEMOTRON")
    print("="*50)
    
    # Verificar configuración
    if not check_configuration():
        print("\n💡 INSTRUCCIONES:")
        print("1. Asegúrate de que el servidor esté corriendo:")
        print("   uvicorn main:app --reload")
        print("\n2. Configura las variables de entorno:")
        print("   - Copia config_nemotron.env a .env")
        print("   - Agrega tu NVIDIA_API_KEY")
        print("   - Configura LLM_PROVIDER=nemotron")
        return
    
    # Ejecutar pruebas
    test_nemotron_integration()
    
    print("\n🎉 PRUEBAS COMPLETADAS")
    print("\n💡 NOTAS:")
    print("- Si ves respuestas muy básicas, verifica tu NVIDIA_API_KEY")
    print("- El sistema usa fallback automático si Nemotron no está disponible")
    print("- Puedes cambiar LLM_PROVIDER=fallback para probar sin API")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Prueba interrumpida")
