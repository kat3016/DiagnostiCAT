"""
Test específico para verificar que el parsing funciona correctamente
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.routers.medical_chat import parse_agent_analysis

def test_parsing():
    print("🧪 TEST: ¿El parsing extrae correctamente las preguntas?")
    print("="*60)
    
    # Ejemplo de respuesta real del agente NVIDIA
    sample_response = """**HIPÓTESIS PRELIMINARES:**

1. **Cefalea Tensiva Agudizada**: Dado el inicio reciente (hace 3 días) y la descripción de dolor de cabeza constante, es plausible considerar una cefalea tensiva, especialmente si se relaciona con estrés o cambios en la rutina.

2. **Hipertensión No Controlada con Cefalea Hipertensiva**: A pesar de la medicación (Losartan) para la hipertensión, es posible que los niveles de presión arterial no estén adecuadamente controlados.

3. **Síndrome de Abstinencia o Efecto del Tabaco**: Dado el hábito de fumar social, es posible que el dolor de cabeza esté relacionado con cambios en el patrón de consumo de tabaco.

**PREGUNTAS ESPECÍFICAS PARA MODELO DE CLASIFICACIÓN:**

1. **¿Ha notado algún patrón o factor desencadenante para el dolor de cabeza, como estrés, falta de sueño, ciertos alimentos o posiciones específicas?**
   - **Objetivo:** Explorar posibles desencadenantes de cefalea tensiva o migraña.

2. **¿Cuál es su frecuencia de consumo de tabaco como "fumador social"? ¿Ha cambiado recientemente este patrón?**
   - **Objetivo:** Evaluar la relación potencial entre el consumo de tabaco y el dolor de cabeza.

3. **¿Ha verificado su presión arterial en casa o en una farmacia desde que iniciaron los dolores de cabeza? ¿Cuáles han sido los resultados?**
   - **Objetivo:** Determinar si la hipertensión podría estar fuera de control y ser la causa subyacente.

4. **¿Experimenta otros síntomas además del dolor de cabeza, como náuseas, sensibilidad a la luz o sonido, o visión borrosa?**
   - **Objetivo:** Investigar la presencia de síntomas acompañantes que podrían apuntar hacia una migraña u otra condición específica.

5. **¿Ha realizado cambios en su rutina diaria, dieta o ha iniciado algún otro medicamento o suplemento en las últimas semanas?**
   - **Objetivo:** Identificar posibles cambios en el estilo de vida o terapias concomitantes que podrían influir en el dolor de cabeza."""
    
    try:
        # Probar el parsing
        hypotheses, questions = parse_agent_analysis(sample_response)
        
        print("📋 RESULTADOS DEL PARSING:")
        print(f"🎯 Hipótesis extraídas ({len(hypotheses)}):")
        for i, hyp in enumerate(hypotheses, 1):
            print(f"  {i}. {hyp[:100]}...")
            
        print(f"\n❓ Preguntas extraídas ({len(questions)}):")
        for i, question in enumerate(questions, 1):
            print(f"  {i}. {question}")
        
        # Verificar si las preguntas parecen ser de IA
        ai_indicators = [
            "presión arterial", "tabaco", "fumador", "estrés", 
            "patrón", "síntomas", "náuseas", "rutina", "desencadenante"
        ]
        
        ai_questions = 0
        for question in questions:
            if any(indicator in question.lower() for indicator in ai_indicators):
                ai_questions += 1
        
        print(f"\n📊 ANÁLISIS:")
        print(f"✅ Preguntas con contenido específico de IA: {ai_questions}/{len(questions)}")
        print(f"✅ Total de preguntas extraídas: {len(questions)}/5")
        
        if len(questions) == 5 and ai_questions >= 4:
            print("🎯 ¡EL PARSING FUNCIONA PERFECTAMENTE!")
        elif len(questions) >= 4:
            print("✅ El parsing funciona bien")
        else:
            print("❌ El parsing necesita mejoras")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parsing()