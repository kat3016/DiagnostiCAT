"""
Script para debuggear exactamente qué está pasando con el parsing
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Simular la respuesta que recibimos del agente
analysis_result = """**HIPÓTESIS PRELIMINARES:**

1. **Cefalea Tensiva Agudizada**: Dado el inicio reciente (hace 3 días) y la descripción de dolor de cabeza constante, es plausible considerar una cefalea tensiva, especialmente si se relaciona con estrés o cambios en la rutina, aunque la intensidad (7/10) es relativamente alta para este tipo de cefalea.
2. **Hipertensión No Controlada con Cefalea Hipertensiva**: A pesar de la medicación (Losartan) para la hipertensión, es posible que los niveles de presión arterial no estén adecuadamente controlados, lo que podría provocar cefaleas, especialmente si hay variaciones en la adherencia al tratamiento o si la dosis necesita ajuste.
3. **Síndrome de Abstinencia o Efecto del Tabaco**: Dado el hábito de fumar social, aunque no se detalla la frecuencia, es posible que el dolor de cabeza esté relacionado con cambios en el patrón de consumo de tabaco, ya sea por un aumento, disminución o intento de cesación, lo que podría desencadenar síntomas de abstinencia o efectos directos del tabaco en la vasculatura cerebral.

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

print("🔍 DEBUGGING PARSING DE PREGUNTAS")
print("="*60)

lines = analysis_result.split('\n')
in_questions_section = False
questions = []

for i, line in enumerate(lines):
    line = line.strip()
    
    # Debug cada línea
    if 'PREGUNTA' in line or ('?' in line and '¿' in line):
        print(f"LÍNEA {i}: '{line}'")
    
    # Detectar sección de preguntas
    if 'PREGUNTAS' in line.upper():
        in_questions_section = True
        print(f"✅ Iniciando sección de preguntas en línea {i}")
        continue
    
    # Extraer preguntas
    if in_questions_section and line:
        # Debug: mostrar cada línea en la sección de preguntas
        if line.startswith(("1.", "2.", "3.", "4.", "5.")) or '?' in line:
            print(f"  CANDIDATA {i}: '{line}'")
            
            # Aplicar la lógica actual
            if (line.startswith(("1.", "2.", "3.", "4.", "5.", "•", "-", "*")) or 
                (line and line[0].isdigit()) or 
                '?' in line):
                
                question = line
                
                # Remover número inicial si existe
                if len(line) > 2 and line[0].isdigit() and line[1] in ['.', ' ']:
                    if line[1] == '.':
                        question = line[2:].strip()
                    elif line[1] == ' ':
                        question = line[2:].strip()
                
                # Remover asteriscos
                question = question.replace('**', '').strip()
                
                # Verificar que sea pregunta válida
                if ('?' in question and '¿' in question and len(question) > 10):
                    # Limpiar explicaciones
                    if ' - ' in question:
                        question = question.split(' - ')[0].strip()
                    if '**Objetivo:**' in question:
                        question = question.split('**Objetivo:**')[0].strip()
                    
                    question = ' '.join(question.split())
                    questions.append(question)
                    print(f"    ✅ EXTRAÍDA: '{question}'")
                else:
                    print(f"    ❌ NO VÁLIDA: '?' in question={('?' in question)}, '¿' in question={('¿' in question)}, len={len(question)}")

print(f"\n📊 RESULTADO FINAL: {len(questions)} preguntas extraídas")
for i, q in enumerate(questions, 1):
    print(f"  {i}. {q}")