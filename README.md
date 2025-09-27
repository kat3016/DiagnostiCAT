# DiagnostiCAT 🏥🤖
Sistema de Agentes de IA para Conversación Médica y Anamnesis Conversacional

DiagnostiCAT es una plataforma avanzada que utiliza múltiples agentes de inteligencia artificial especializados para proporcionar asistencia médica inicial, realizar anamnesis conversacional estructurada y clasificación automatizada de síntomas médicos.

🌟 Características Principales
🤖 Sistema Multi-Agente: Tres agentes especializados trabajando en secuencia

Agente Entrevistador Conversacional: Realiza 7 preguntas médicas estructuradas
Agente Analista Especializado: Genera hipótesis preliminares y preguntas específicas
Agente Estructurador de Datos: Convierte información a JSON y ejecuta clasificación
🔬 Clasificación Médica Avanzada: Integración con Hugging Face usando modelos médicos especializados

💬 Anamnesis Conversacional: Flujo completo de recopilación de datos médicos

📊 Estructuración Inteligente: Conversión automática de conversaciones a datos médicos estructurados

🚨 Evaluación de Urgencia: Clasificación automática de niveles de prioridad médica

⚕️ Cumplimiento Ético: Consentimiento informado y disclaimers médicos obligatorios

🏗️ Arquitectura del Sistema
```
DiagnostiCAT/
├── app/
│   ├── agents/                    # Agentes de IA especializados
│   │   ├── base_agent.py         # Clase base para agentes
│   │   └── medical_agents.py     # Agentes médicos específicos
│   ├── core/                     # Configuración central
│   │   ├── config.py            # Configuración de la aplicación
│   │   └── database.py          # Gestión de base de datos
│   ├── crew/                    # Configuración CrewAI
│   │   ├── config/
│   │   │   ├── agents.yaml      # Definición de agentes
│   │   │   └── tasks.yaml       # Definición de tareas
│   │   └── hybrid_agent.py      # Agente híbrido Nemotron/OpenAI
│   ├── models/                  # Modelos de datos
│   │   ├── medical_models.py    # Modelos médicos
│   │   ├── agent_models.py      # Modelos de agentes
│   │   └── structured_data_models.py # Modelos de datos estructurados
│   ├── routers/                 # Endpoints de la API
│   │   ├── medical_chat.py      # Chat médico principal
│   │   └── anamnesis_flow.py    # Flujo de anamnesis
│   └── services/                # Servicios de negocio
│       ├── agent_service.py     # Orquestación de agentes
│       ├── classification_service.py # Clasificación con Hugging Face
│       ├── data_structuring_service.py # Estructuración de datos
│       └── llm_service.py       # Servicio de modelos LLM
├── frontend/                    # Interfaz de usuario React
│   ├── src/
│   │   ├── components/          # Componentes React
│   │   └── services/            # Servicios API
│   └── vite.config.js
├── main.py                      # Aplicación FastAPI principal
├── docker-compose.yml           # Orquestación de contenedores
├── Dockerfile                   # Imagen de contenedor
└── requirements.txt             # Dependencias Python
```
🔄 Flujo de Trabajo
- Consentimiento Informado → Usuario acepta términos médicos
- Entrevista Inicial → Agente realiza 7 preguntas estructuradas
- Análisis Preliminar → Generación de hipótesis y preguntas específicas
- Estructuración JSON → Conversión de datos a formato estándar
- Clasificación Médica → Modelo Hugging Face clasifica síntomas
- Diagnóstico de IA → Presentación de resultados con disclaimers
📦 Dependencias Principales
- Backend (Python)
- fastapi>=0.104.1              # Framework web moderno
- uvicorn[standard]>=0.24.0     # Servidor ASGI
- pydantic>=2.4.2               # Validación de datos
- crewai>=0.28.8                # Framework de agentes de IA
- transformers>=4.36.0          # Modelos Hugging Face
- torch>=2.1.0                  # Framework de deep learning
- langchain-openai>=0.0.2       # Integración OpenAI
- sqlalchemy>=2.0.23            # ORM de base de datos
- httpx>=0.25.0                 # Cliente HTTP asíncrono
- python-dotenv>=1.0.0          # Gestión de variables de entorno
- Frontend (Node.js)
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "react-router-dom": "^6.8.0",
  "axios": "^1.6.0",
  "vite": "^5.0.0"
}
- Modelos de IA Utilizados
- NVIDIA Nemotron: meta/llama-3.1-8b-instruct (Principal)
- Hugging Face: emilyalsentzer/Bio_ClinicalBERT (Clasificación médica)
- OpenAI: gpt-4o-mini (Fallback)
🚀 Despliegue
Opción 1: Despliegue con Docker (Recomendado)
git clone <repository-url>
cd DiagnostiCAT
Clonar el repositorio
Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys
Ejecutar con Docker Compose
docker-compose up --build

Servicios disponibles:

- Backend API: http://localhost:8000
- Frontend React: http://localhost:3000
- PostgreSQL: localhost:5432
- Redis: localhost:6379
Opción 2: Despliegue Manual
Backend
Preparar entorno Python
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
Configurar variables de entorno
# Crear archivo .env con:
NVIDIA_API_KEY=your_nvidia_api_key_here
LLM_PROVIDER=nemotron
DEBUG=False
DATABASE_URL=sqlite:///./diagnosticat.db
Ejecutar servidor
uvicorn main:app --host 0.0.0.0 --port 8000
Frontend
Instalar dependencias
cd frontend
npm install
Ejecutar en desarrollo
npm run dev
Compilar para producción
npm run build
npm run preview
Opción 3: Despliegue en la Nube
AWS Lambda (Serverless)
# El proyecto incluye soporte para Mangum
pip install mangum
# Desplegar usando AWS SAM o Serverless Framework
- Railway/Render/Vercel
- ⚙️ Configuración
- Variables de Entorno Requeridas
- API Keys Necesarias
- NVIDIA API Key (Principal): https://build.nvidia.com/
- OpenAI API Key (Opcional/Fallback): https://platform.openai.com/
- 📊 Endpoints de la API
- Conversación Médica
- POST /api/v1/chat/ - Iniciar conversación médica
- GET /api/v1/chat/{id}/history - Historial de conversación
- Flujo de Anamnesis
- POST /api/v1/flow/consent - Registrar consentimiento
- POST /api/v1/flow/interview/answer - Responder preguntas de entrevista
- POST /api/v1/flow/analysis/preliminary - Análisis preliminar
- POST /api/v1/flow/structure-and-classify - Estructuración y clasificación
Documentación
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 🧪 Testing
- 🔒 Consideraciones de Seguridad
- ✅ Consentimiento informado obligatorio
- ✅ Disclaimers médicos en todas las respuestas
- ✅ Datos médicos tratados con confidencialidad
- ✅ Validación de entrada en todos los endpoints
- ✅ CORS configurado para dominios específicos
- ✅ Variables de entorno para información sensible
- ⚠️ Importante - Disclaimer Médico
- ADVERTENCIA CRÍTICA: DiagnostiCAT es una herramienta de asistencia médica inicial basada en IA.

❌ NO reemplaza la consulta médica profesional
❌ NO proporciona diagnósticos médicos definitivos
❌ NO prescribe medicamentos ni tratamientos
✅ SÍ proporciona orientación médica inicial informativos
✅ SÍ recomienda consulta médica profesional
En emergencias médicas, contacta inmediatamente los servicios de urgencias locales.

🎯 Casos de Uso
🏥 Triaje médico inicial en clínicas y hospitales
📱 Asistentes médicos digitales 24/7
📊 Recopilación estructurada de datos médicos
🔍 Pre-evaluación antes de consultas médicas
📈 Análisis de patrones en síntomas médicos
🤝 Contribuciones
Fork el proyecto
Crea una rama (git checkout -b feature/nueva-funcionalidad)
Commit cambios (git commit -m 'Agregar nueva funcionalidad')
Push a la rama (git push origin feature/nueva-funcionalidad)
Abre un Pull Request
📄 Licencia
Este proyecto está bajo la Licencia MIT. Ver archivo LICENSE para detalles.

👥 Equipo de Desarrollo
Desarrollado con ❤️ para mejorar el acceso a la asistencia médica inicial mediante inteligencia artificial.

🚀 ¿Listo para comenzar? Sigue las instrucciones de despliegue y ¡comienza a usar DiagnostiCAT!


