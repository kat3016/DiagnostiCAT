# 🎬 SCRIPT PARA VIDEO - DiagnostiCAT
## Sistema de Agentes de IA para Conversación Médica

**Duración estimada:** 8-10 minutos  
**Audiencia:** Desarrolladores, profesionales médicos, inversores  
**Objetivo:** Demostrar las capacidades y arquitectura de DiagnostiCAT

---

## 🎯 **ESTRUCTURA DEL VIDEO**

### **INTRODUCCIÓN (0:00 - 1:00)**
### **ARQUITECTURA (1:00 - 2:30)**
### **DEMOSTRACIÓN PRÁCTICA (2:30 - 6:30)**
### **TECNOLOGÍA (6:30 - 8:00)**
### **CONCLUSIÓN (8:00 - 8:30)**

---

## 📝 **GUIÓN DETALLADO**

### **🎬 ESCENA 1: INTRODUCCIÓN (0:00 - 1:00)**

**[PANTALLA: Logo DiagnostiCAT + Título]**

**NARRADOR:**
> "Hola, soy [Tu nombre] y hoy les voy a presentar DiagnostiCAT, un sistema revolucionario de asistencia médica basado en inteligencia artificial."

**[TRANSICIÓN: Animación de problemas médicos actuales]**

**NARRADOR:**
> "¿Te has preguntado qué pasaría si pudieras tener una primera consulta médica inteligente disponible 24/7? DiagnostiCAT combina múltiples agentes de IA especializados para realizar anamnesis médica conversacional y clasificación de síntomas de manera profesional."

**[PANTALLA: Estadísticas de problemas de acceso médico]**

**NARRADOR:**
> "En un mundo donde el acceso a atención médica inmediata es limitado, DiagnostiCAT ofrece una solución innovadora que utiliza CrewAI, modelos Hugging Face especializados, y LLMs avanzados."

---

### **🎬 ESCENA 2: ARQUITECTURA DEL SISTEMA (1:00 - 2:30)**

**[PANTALLA: Diagrama de arquitectura - Vista general]**

**NARRADOR:**
> "DiagnostiCAT no es solo otro chatbot médico. Es un sistema multi-agente sofisticado con tres componentes principales:"

**[ANIMACIÓN: Aparecen los 3 agentes uno por uno]**

**NARRADOR:**
> "Primero, el **Agente Entrevistador Conversacional** - un médico virtual especializado que realiza exactamente 7 preguntas médicas estructuradas, siguiendo protocolos clínicos reales."

**[PANTALLA: Lista de las 7 preguntas]**
1. ¿Cuál es el motivo principal de tu consulta?
2. ¿Cuándo comenzaron estos síntomas?
3. ¿Intensidad del 1 al 10?
4. ¿Antecedentes médicos relevantes?
5. ¿Medicamentos actuales?
6. ¿Antecedentes familiares?
7. ¿Hábitos relevantes?

**NARRADOR:**
> "Segundo, el **Agente Analista Especializado** que genera hasta 3 hipótesis preliminares y formula 5 preguntas específicas para refinar el diagnóstico."

**[PANTALLA: Ejemplo de hipótesis y preguntas específicas]**

**NARRADOR:**
> "Y tercero, el **Agente Estructurador de Datos** que convierte toda la información en formato JSON optimizado y se comunica directamente con nuestro modelo de clasificación médica especializado."

**[PANTALLA: Diagrama de flujo JSON → Hugging Face → Clasificación]**

---

### **🎬 ESCENA 3: DEMOSTRACIÓN PRÁCTICA (2:30 - 6:30)**

**[PANTALLA: Interfaz de DiagnostiCAT - Página inicial]**

**NARRADOR:**
> "Ahora veamos DiagnostiCAT en acción. Voy a simular una consulta médica real."

#### **DEMO 1: Consentimiento (2:30 - 3:00)**

**[ACCIÓN: Abrir la aplicación]**

**NARRADOR:**
> "Lo primero que vemos es la solicitud de consentimiento informado. DiagnostiCAT cumple con estándares éticos médicos y NUNCA procesa información sin consentimiento explícito."

**[PANTALLA: Formulario de consentimiento]**

**NARRADOR (leyendo):**
> "El sistema solicita autorización para procesar información médica con fines de asistencia inicial. Esto es crucial para la transparencia."

**[ACCIÓN: Hacer clic en "Sí acepto"]**

#### **DEMO 2: Entrevista Inicial (3:00 - 4:30)**

**[PANTALLA: Chat interface]**

**NARRADOR:**
> "Una vez otorgado el consentimiento, el Agente Entrevistador inicia las 7 preguntas estructuradas. Voy a simular un caso de dolor de cabeza."

**[ACCIÓN: Escribir respuestas paso a paso]**

**USUARIO SIMULA:**
- "Tengo dolor de cabeza intenso desde hace 2 días"
- "Comenzó el lunes por la mañana"
- "Intensidad 8 de 10"
- "No tengo antecedentes médicos importantes"
- "Solo tomo ibuprofeno ocasionalmente"
- "Mi madre sufre de migrañas"
- "No fumo, bebo alcohol socialmente"

**NARRADOR:**
> "Observen cómo el agente mantiene un flujo conversacional natural pero estructurado, recopilando exactamente la información necesaria para el análisis."

#### **DEMO 3: Preguntas Específicas (4:30 - 5:30)**

**[PANTALLA: Transición a fase de análisis]**

**NARRADOR:**
> "Ahora el sistema cambia automáticamente al Agente Analista, que ha generado hipótesis preliminares y formula preguntas específicas."

**[PANTALLA: Mostrar hipótesis generadas]**
- Cefalea tensional (probabilidad alta)
- Migraña (probabilidad media)  
- Cefalea secundaria (probabilidad baja)

**NARRADOR:**
> "Basándose en las respuestas iniciales, el sistema genera preguntas específicas para refinar el diagnóstico."

**[ACCIÓN: Responder preguntas específicas]**

**USUARIO SIMULA:**
- "El dolor se localiza en la sien derecha"
- "Sí, tengo sensibilidad a la luz"
- "El dolor empeora con el movimiento"
- "He tenido episodios similares antes"
- "El estrés parece desencadenarlo"

#### **DEMO 4: Clasificación y Resultados (5:30 - 6:30)**

**[PANTALLA: Proceso de clasificación en tiempo real]**

**NARRADOR:**
> "Ahora viene la magia. El Agente Estructurador convierte toda la información en formato JSON y la envía a nuestro modelo de clasificación médica especializado basado en Hugging Face."

**[PANTALLA: Mostrar JSON estructurado]**

**NARRADOR:**
> "El modelo analiza los datos usando BiomedNLP-PubMedBERT, un modelo entrenado específicamente en literatura médica, y genera una clasificación con nivel de confianza."

**[PANTALLA: Resultados de clasificación]**

**NARRADOR:**
> "¡Y aquí están los resultados! El sistema identifica las 3 condiciones más probables:"

**[PANTALLA: Mostrar resultados finales]**
1. **Migraña** (85%) - Dolor de cabeza vascular con sensibilidad
2. **Cefalea tensional** (12%) - Dolor por tensión o estrés  
3. **Cefalea por deshidratación** (3%) - Relacionada con falta de hidratación

**NARRADOR:**
> "Además, proporciona recomendaciones específicas y nivel de urgencia. En este caso, recomienda consulta médica en los próximos días."

---

### **🎬 ESCENA 4: TECNOLOGÍA AVANZADA (6:30 - 8:00)**

**[PANTALLA: Diagrama técnico detallado]**

**NARRADOR:**
> "¿Qué hace especial a DiagnostiCAT tecnológicamente?"

#### **Subsección: Stack Tecnológico (6:30 - 7:15)**

**[ANIMACIÓN: Stack tecnológico apareciendo por capas]**

**NARRADOR:**
> "Utilizamos **FastAPI** como backend moderno y rápido, **CrewAI** para coordinación de agentes inteligentes, **Hugging Face Transformers** con modelos médicos especializados, y **Ollama** para LLMs locales."

**[PANTALLA: Logos de tecnologías]**

**NARRADOR:**
> "El frontend está construido en **React con Vite**, proporcionando una experiencia de usuario moderna y responsiva."

#### **Subsección: IA Multi-Nivel (7:15 - 8:00)**

**[PANTALLA: Diagrama de flujo de IA]**

**NARRADOR:**
> "La verdadera innovación está en nuestro sistema de IA multi-nivel:"

**[ANIMACIÓN: Flujo de datos entre componentes]**

**NARRADOR:**
> "Nivel 1: **CrewAI** coordina tres agentes especializados trabajando en secuencia. Nivel 2: **Nemotron LLM** proporciona inteligencia conversacional avanzada. Nivel 3: **Modelo Hugging Face especializado** realiza clasificación médica precisa."

**[PANTALLA: Métricas de rendimiento]**

**NARRADOR:**
> "Esto resulta en clasificaciones con hasta 85% de precisión y capacidad de manejar 8 categorías médicas principales, desde neurológicas hasta psiquiátricas."

---

### **🎬 ESCENA 5: CONCLUSIÓN Y LLAMADA A LA ACCIÓN (8:00 - 8:30)**

**[PANTALLA: Resumen visual de beneficios]**

**NARRADOR:**
> "DiagnostiCAT representa el futuro de la asistencia médica inicial. Combina la precisión de múltiples agentes de IA con la seguridad de protocolos médicos establecidos."

**[PANTALLA: Estadísticas de impacto]**

**NARRADOR:**
> "Imaginen el impacto: acceso 24/7 a evaluación médica inicial, reducción de consultas innecesarias, y mejor triaje de pacientes."

**[PANTALLA: Disclaimer médico]**

**NARRADOR:**
> "Por supuesto, DiagnostiCAT NUNCA reemplaza la consulta médica profesional. Es una herramienta de asistencia inicial que siempre recomienda evaluación médica para diagnósticos definitivos."

**[PANTALLA: Call to action]**

**NARRADOR:**
> "¿Quieres probar DiagnostiCAT? Visita nuestro repositorio en GitHub, o contáctanos para una demostración personalizada. El futuro de la medicina digital está aquí."

**[PANTALLA: Información de contacto y enlaces]**

---

## 🎥 **ESPECIFICACIONES TÉCNICAS DE GRABACIÓN**

### **Configuración de Pantalla:**
- **Resolución:** 1920x1080 (Full HD)
- **Frame Rate:** 30 fps
- **Formato:** MP4 H.264

### **Audio:**
- **Micrófono:** Calidad profesional (evitar eco)
- **Volumen:** Consistente durante todo el video
- **Música de fondo:** Opcional, muy suave, instrumental

### **Herramientas Recomendadas:**
- **Grabación de pantalla:** OBS Studio, Camtasia, o ScreenFlow
- **Edición:** DaVinci Resolve, Adobe Premiere, o Final Cut Pro
- **Gráficos:** Canva, Adobe After Effects para animaciones

---

## 📋 **CHECKLIST PRE-GRABACIÓN**

### **Preparación del Sistema:**
- [ ] DiagnostiCAT ejecutándose correctamente
- [ ] Ollama con modelo Nemotron funcionando
- [ ] Base de datos limpia (sin conversaciones previas)
- [ ] Frontend compilado y funcionando
- [ ] Conexión a internet estable

### **Preparación del Contenido:**
- [ ] Script memorizado o teleprompter preparado
- [ ] Ejemplos de casos médicos preparados
- [ ] Screenshots de alta calidad tomados
- [ ] Diagramas y gráficos preparados
- [ ] Transiciones planificadas

### **Configuración Técnica:**
- [ ] Micrófono configurado y testeado
- [ ] Iluminación adecuada (si apareces en cámara)
- [ ] Software de grabación configurado
- [ ] Resolución de pantalla optimizada
- [ ] Notificaciones del sistema deshabilitadas

---

## 🎨 **ELEMENTOS VISUALES SUGERIDOS**

### **Gráficos Animados:**
1. **Logo DiagnostiCAT** con animación médica
2. **Diagrama de arquitectura** con elementos apareciendo progresivamente
3. **Flujo de datos** entre agentes con animaciones
4. **Métricas de rendimiento** con contadores animados
5. **Clasificación médica** con barras de probabilidad

### **Screenshots Necesarios:**
1. Página de inicio con consentimiento
2. Interfaz de chat durante entrevista
3. Transición entre fases del flujo
4. Resultados de clasificación
5. Panel de administración (opcional)

### **Overlays de Texto:**
- **Títulos de sección** con estilo médico
- **Estadísticas** con números destacados
- **Tecnologías utilizadas** con logos
- **Disclaimer médico** claramente visible
- **Información de contacto** al final

---

## 📞 **NOTAS PARA EL PRESENTADOR**

### **Tono y Estilo:**
- **Profesional pero accesible**
- **Entusiasta sobre la tecnología**
- **Responsable sobre limitaciones médicas**
- **Claro en explicaciones técnicas**

### **Puntos Clave a Enfatizar:**
1. **Naturaleza multi-agente** del sistema
2. **Precisión médica** y protocolos seguidos
3. **Tecnologías de vanguardia** utilizadas
4. **Disclaimer médico** y limitaciones
5. **Potencial de impacto** en salud digital

### **Errores a Evitar:**
- ❌ Presentar como reemplazo de médicos
- ❌ Prometer diagnósticos definitivos
- ❌ Usar jerga técnica sin explicar
- ❌ Mostrar casos médicos reales/sensibles
- ❌ Omitir disclaimers de seguridad

---

## 🚀 **POST-PRODUCCIÓN**

### **Edición Recomendada:**
1. **Intro dinámica** (5-10 segundos)
2. **Transiciones suaves** entre secciones
3. **Zoom in/out** para destacar elementos importantes
4. **Subtítulos** para términos técnicos
5. **Outro** con call-to-action claro

### **Elementos a Agregar:**
- **Música de fondo** instrumental suave
- **Efectos de sonido** para transiciones
- **Gráficos adicionales** si es necesario
- **Corrección de color** para consistencia
- **Logo/watermark** discreto

---

**¡Listo para grabar un video profesional que muestre todo el potencial de DiagnostiCAT!** 🎬🏥🤖
