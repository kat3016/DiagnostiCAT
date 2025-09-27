"""
Script de prueba para el agente híbrido
"""

from app.crew.hybrid_agent import generate_questions_hybrid

test_data = '''
ENTREVISTA CONVERSACIONAL COMPLETADA:
1. Motivo consulta: Dolor de cabeza constante
2. Inicio síntomas: Hace 3 días  
3. Intensidad (1-10): 7
4. Antecedentes médicos: Hipertensión
5. Medicamentos actuales: Losartan
6. Antecedentes familiares: Diabetes tipo 2
7. Hábitos relevantes: Fumador social
'''

print('🧪 PROBANDO AGENTE HÍBRIDO...')

try:
    result = generate_questions_hybrid(test_data)

    if result['success']:
        print('🎉 ¡ÉXITO! Agente híbrido funciona')
        print('✅ Provider usado:', result['provider'])
        print('🤖 Modelo:', result['model'])
        print('📋 PREGUNTAS GENERADAS POR IA:')
        print('=' * 80)
        print(result['content'])
        print('=' * 80)
    else:
        print('❌ ERROR en agente híbrido:')
        print(result['error'])
        
except Exception as e:
    print(f'💥 EXCEPCIÓN: {e}')
    import traceback
    traceback.print_exc()