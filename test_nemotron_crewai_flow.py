#!/usr/bin/env python3
"""
Script de prueba para el flujo completo de CrewAI + Nemotron + Hugging Face
"""

import asyncio
import json
import httpx
from datetime import datetime

# Configuración del servidor
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

class DiagnostiCATTester:
    """Tester para el flujo completo de anamnesis conversacional"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.conversation_id = None
        self.current_phase = None
    
    async def test_server_health(self):
        """Verificar que el servidor esté funcionando"""
        print("🔍 Verificando estado del servidor...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    print("✅ Servidor funcionando correctamente")
                    return True
                else:
                    print(f"❌ Servidor respondió con código: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Error conectando al servidor: {e}")
                return False
    
    async def test_model_info(self):
        """Verificar información del modelo"""
        print("\n🤖 Verificando información del modelo...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/api/v1/flow/model/info")
                if response.status_code == 200:
                    info = response.json()
                    print(f"✅ Modelo: {info['name']}")
                    print(f"   Versión: {info['version']}")
                    print(f"   Flujo: {' → '.join(info['flow'])}")
                    print(f"   Modelo HF: {info['hugging_face_model']}")
                    return True
                else:
                    print(f"❌ Error obteniendo info del modelo: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Error: {e}")
                return False
    
    async def test_consent(self):
        """Paso 1: Probar consentimiento"""
        print("\n📋 PASO 1: Probando consentimiento...")
        
        async with httpx.AsyncClient() as client:
            try:
                # Dar consentimiento
                consent_data = {"accepted": True}
                response = await client.post(
                    f"{self.base_url}/api/v1/flow/consent",
                    json=consent_data,
                    headers=HEADERS
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Consentimiento otorgado")
                    print(f"   Mensaje: {result['message']}")
                    
                    # Extraer conversation_id del mensaje
                    message = result['message']
                    if "conversation_id=" in message:
                        self.conversation_id = message.split("conversation_id=")[1]
                        print(f"   ID de conversación: {self.conversation_id}")
                        return True
                    else:
                        print("❌ No se encontró conversation_id en la respuesta")
                        return False
                else:
                    print(f"❌ Error en consentimiento: {response.status_code}")
                    print(f"   Respuesta: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                return False
    
    async def test_interview_start(self):
        """Paso 2: Iniciar entrevista conversacional"""
        print("\n🎤 PASO 2: Iniciando entrevista conversacional con Nemotron...")
        
        if not self.conversation_id:
            print("❌ No hay conversation_id disponible")
            return False
        
        async with httpx.AsyncClient(timeout=120.0) as client:  # Timeout largo para LLM
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/flow/interview/start",
                    params={"conversation_id": self.conversation_id},
                    headers=HEADERS
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Entrevista iniciada con {result.get('agent_used', 'agente')}")
                    print(f"   Fase: {result['phase']}")
                    print(f"   Pregunta 1/7: {result['question']}")
                    self.current_phase = result['phase']
                    return True
                else:
                    print(f"❌ Error iniciando entrevista: {response.status_code}")
                    print(f"   Respuesta: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                return False
    
    async def test_interview_answers(self):
        """Paso 2 continuación: Responder las 7 preguntas"""
        print("\n💬 PASO 2: Respondiendo preguntas de la entrevista...")
        
        # Respuestas de ejemplo para las 7 preguntas
        sample_answers = [
            "Tengo dolor de cabeza intenso desde hace 3 días",
            "Comenzó el lunes por la mañana de forma gradual",
            "El dolor es de intensidad 8 de 10, muy fuerte",
            "Tengo antecedentes de migrañas desde hace 5 años",
            "Tomo ibuprofeno 400mg cuando tengo dolor",
            "Mi madre también sufre de migrañas frecuentes",
            "No fumo, bebo alcohol ocasionalmente los fines de semana"
        ]
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            for i, answer in enumerate(sample_answers, 1):
                try:
                    print(f"   Respondiendo pregunta {i}/7...")
                    
                    response = await client.post(
                        f"{self.base_url}/api/v1/flow/interview/answer",
                        params={
                            "conversation_id": self.conversation_id,
                            "answer": answer
                        },
                        headers=HEADERS
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        if i < 7:
                            print(f"   ✅ Respuesta {i} procesada")
                            if 'response' in result:
                                print(f"      Siguiente pregunta: {result['response'][:100]}...")
                        else:
                            print(f"   ✅ Entrevista completada!")
                            print(f"      Fase actual: {result['phase']}")
                            self.current_phase = result['phase']
                    else:
                        print(f"   ❌ Error en respuesta {i}: {response.status_code}")
                        return False
                        
                except Exception as e:
                    print(f"   ❌ Error en respuesta {i}: {e}")
                    return False
            
            return True
    
    async def test_preliminary_analysis(self):
        """Paso 3: Análisis preliminar y preguntas específicas"""
        print("\n🔍 PASO 3: Generando análisis preliminar con Nemotron...")
        
        async with httpx.AsyncClient(timeout=180.0) as client:  # Timeout más largo para análisis
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/flow/analysis/preliminary",
                    params={"conversation_id": self.conversation_id},
                    headers=HEADERS
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Análisis completado con {result.get('agent_used', 'agente')}")
                    print(f"   Fase: {result['phase']}")
                    
                    # Mostrar parte del análisis
                    analysis = result['preliminary_analysis']
                    if len(analysis) > 200:
                        print(f"   Análisis: {analysis[:200]}...")
                    else:
                        print(f"   Análisis: {analysis}")
                    
                    self.current_phase = result['phase']
                    return True
                else:
                    print(f"❌ Error en análisis: {response.status_code}")
                    print(f"   Respuesta: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                return False
    
    async def test_specific_questions(self):
        """Paso 3 continuación: Responder preguntas específicas"""
        print("\n❓ PASO 3: Respondiendo preguntas específicas...")
        
        # Respuestas específicas de ejemplo
        specific_answers = [
            "El dolor es pulsátil y se localiza en el lado derecho",
            "Empeora con la luz y los ruidos fuertes",
            "No he tenido náuseas ni vómitos esta vez",
            "El dolor no se alivia completamente con ibuprofeno",
            "No he identificado factores desencadenantes específicos"
        ]
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/flow/questions/specific",
                    params={"conversation_id": self.conversation_id},
                    json={"answers": specific_answers},
                    headers=HEADERS
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Preguntas específicas respondidas")
                    print(f"   Respuestas procesadas: {result['answers_count']}")
                    print(f"   Fase: {result['phase']}")
                    self.current_phase = result['phase']
                    return True
                else:
                    print(f"❌ Error en preguntas específicas: {response.status_code}")
                    print(f"   Respuesta: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                return False
    
    async def test_structure_and_classify(self):
        """Paso 4: Estructuración JSON y clasificación con Hugging Face"""
        print("\n🏗️ PASO 4: Estructurando datos y clasificando con Nemotron + Hugging Face...")
        
        async with httpx.AsyncClient(timeout=300.0) as client:  # Timeout muy largo para clasificación
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/flow/structure-and-classify",
                    params={"conversation_id": self.conversation_id},
                    headers=HEADERS
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Proceso completado!")
                    print(f"   Agente usado: {result.get('agent_used', 'N/A')}")
                    print(f"   Modelo de clasificación: {result.get('model_used', 'N/A')}")
                    print(f"   Fase: {result['phase']}")
                    
                    # Mostrar parte del resultado
                    complete_result = result['complete_result']
                    if len(complete_result) > 300:
                        print(f"   Resultado: {complete_result[:300]}...")
                    else:
                        print(f"   Resultado: {complete_result}")
                    
                    return True
                else:
                    print(f"❌ Error en estructuración y clasificación: {response.status_code}")
                    print(f"   Respuesta: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                return False
    
    async def test_flow_status(self):
        """Verificar estado final del flujo"""
        print("\n📊 Verificando estado final del flujo...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/flow/status/{self.conversation_id}"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Estado del flujo:")
                    print(f"   Fase: {result['phase']}")
                    print(f"   Mensajes totales: {result['total_messages']}")
                    print(f"   Entrevista completada: {result['interview_completed']}")
                    print(f"   Análisis generado: {result['analysis_generated']}")
                    print(f"   Proceso completado: {result.get('process_completed', False)}")
                    return True
                else:
                    print(f"❌ Error obteniendo estado: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                return False
    
    async def run_complete_test(self):
        """Ejecutar prueba completa del flujo"""
        print("🚀 INICIANDO PRUEBA COMPLETA DEL FLUJO NEMOTRON + CREWAI + HUGGING FACE")
        print("=" * 80)
        
        start_time = datetime.now()
        
        # Ejecutar todas las pruebas en secuencia
        tests = [
            ("Verificar servidor", self.test_server_health),
            ("Información del modelo", self.test_model_info),
            ("Consentimiento", self.test_consent),
            ("Iniciar entrevista", self.test_interview_start),
            ("Responder preguntas", self.test_interview_answers),
            ("Análisis preliminar", self.test_preliminary_analysis),
            ("Preguntas específicas", self.test_specific_questions),
            ("Estructuración y clasificación", self.test_structure_and_classify),
            ("Estado final", self.test_flow_status)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                success = await test_func()
                if success:
                    passed += 1
                else:
                    failed += 1
                    print(f"\n⚠️  La prueba '{test_name}' falló. ¿Continuar? (y/n)")
                    # En modo automático, continuar
                    continue
            except Exception as e:
                print(f"\n💥 Error inesperado en '{test_name}': {e}")
                failed += 1
        
        # Resumen final
        end_time = datetime.now()
        duration = end_time - start_time
        
        print("\n" + "=" * 80)
        print("📊 RESUMEN DE PRUEBAS")
        print(f"✅ Pruebas exitosas: {passed}")
        print(f"❌ Pruebas fallidas: {failed}")
        print(f"⏱️  Duración total: {duration}")
        
        if self.conversation_id:
            print(f"🆔 ID de conversación: {self.conversation_id}")
        
        if failed == 0:
            print("\n🎉 ¡TODAS LAS PRUEBAS PASARON! El flujo Nemotron + CrewAI + Hugging Face está funcionando correctamente.")
        else:
            print(f"\n⚠️  {failed} pruebas fallaron. Revisa la configuración y logs del servidor.")
        
        return failed == 0


async def main():
    """Función principal"""
    print("DiagnostiCAT - Tester del Flujo Nemotron + CrewAI + Hugging Face")
    print("================================================================")
    
    tester = DiagnostiCATTester()
    success = await tester.run_complete_test()
    
    if success:
        print("\n🚀 ¡Sistema listo para producción!")
    else:
        print("\n🔧 Sistema necesita ajustes antes de usar en producción.")


if __name__ == "__main__":
    asyncio.run(main())
