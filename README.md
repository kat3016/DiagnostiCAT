# DiagnostiCAT 🏥🤖

Sistema de Agentes de IA para Conversación Médica - Una plataforma avanzada que utiliza inteligencia artificial para proporcionar asistencia médica inicial y triaje automatizado.

## 🌟 Características

- **Múltiples Agentes Especializados**: Médico General, Enfermera de Triaje, y más
- **Evaluación de Urgencia Automática**: Clasificación inteligente de síntomas
- **Conversaciones Contextuales**: Historial de conversación persistente
- **API RESTful Completa**: Endpoints bien documentados
- **Arquitectura Escalable**: Diseño modular y extensible
- **Interfaz Swagger**: Documentación interactiva automática

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.11+
- PostgreSQL (opcional, usa SQLite por defecto)
- Redis (opcional, para caché)

### Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd DiagnostiCAT
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

5. **Ejecutar la aplicación**
```bash
uvicorn main:app --reload
```

La aplicación estará disponible en: http://localhost:8000

## 🐳 Docker

Para ejecutar con Docker:

```bash
# Construir y ejecutar
docker-compose up --build

# Solo ejecutar (si ya está construido)
docker-compose up
```

## 📚 Uso de la API

### Conversación Médica

```bash
# Iniciar conversación
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tengo dolor de cabeza desde hace 2 días",
    "patient_context": {
      "age": 30,
      "gender": "femenino"
    }
  }'
```

### Gestión de Agentes

```bash
# Listar todos los agentes
curl -X GET "http://localhost:8000/api/v1/agents/"

# Obtener recomendación de agente
curl -X POST "http://localhost:8000/api/v1/agents/recommend" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tengo una emergencia médica"}'
```

## 🏗️ Arquitectura

```
DiagnostiCAT/
├── app/
│   ├── agents/          # Agentes de IA médicos
│   │   ├── base_agent.py
│   │   └── medical_agents.py
│   ├── core/            # Configuración y utilidades
│   │   ├── config.py
│   │   └── database.py
│   ├── models/          # Modelos Pydantic
│   │   ├── medical_models.py
│   │   └── agent_models.py
│   ├── routers/         # Endpoints de la API
│   │   ├── medical_chat.py
│   │   └── agents.py
│   └── services/        # Lógica de negocio
│       └── agent_service.py
├── main.py              # Aplicación principal
├── requirements.txt     # Dependencias
└── README.md           # Documentación
```

## 🤖 Tipos de Agentes

### 1. Médico General (`GeneralPractitionerAgent`)
- **Especialidad**: Atención primaria y consultas generales
- **Funciones**: 
  - Evaluación inicial de síntomas
  - Recomendaciones de tratamiento básico
  - Derivación a especialistas cuando necesario

### 2. Enfermera de Triaje (`TriageNurseAgent`)
- **Especialidad**: Clasificación de urgencia médica
- **Funciones**:
  - Evaluación rápida de síntomas
  - Clasificación de prioridad (Crítico/Alto/Medio/Bajo)
  - Recomendaciones de atención inmediata

### 3. Agentes Futuros (Extensibles)
- Especialista en Cardiología
- Especialista en Salud Mental
- Médico de Emergencias
- Y más...

## 📊 Ejemplos de Uso

### Consulta General
```json
{
  "message": "He tenido tos seca por una semana",
  "patient_context": {
    "age": 35,
    "medical_history": ["asma leve"],
    "current_medications": ["inhalador de salbutamol"]
  }
}
```

### Evaluación de Urgencia
```json
{
  "message": "Tengo dolor intenso en el pecho y dificultad para respirar",
  "patient_context": {
    "age": 55,
    "gender": "masculino"
  }
}
```

## 🔧 Configuración Avanzada

### Variables de Entorno

| Variable | Descripción | Valor por Defecto |
|----------|-------------|-------------------|
| `DEBUG` | Modo debug | `False` |
| `HOST` | Host de la aplicación | `0.0.0.0` |
| `PORT` | Puerto de la aplicación | `8000` |
| `DATABASE_URL` | URL de base de datos | `sqlite:///./diagnosticat.db` |
| `OPENAI_API_KEY` | Clave API de OpenAI | `""` |
| `OPENAI_MODEL` | Modelo de OpenAI | `gpt-4` |

### Integración con OpenAI

Para usar modelos reales de OpenAI:

1. Obtén una API key de OpenAI
2. Configura `OPENAI_API_KEY` en tu `.env`
3. Los agentes automáticamente usarán el modelo configurado

## 🧪 Testing

```bash
# Ejecutar tests
pytest

# Con cobertura
pytest --cov=app tests/
```

## 📖 Documentación API

Una vez ejecutando la aplicación:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contribuciones

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Roadmap

- [ ] Integración completa con OpenAI/GPT-4
- [ ] Soporte para múltiples idiomas
- [ ] Interfaz web frontend
- [ ] Integración con sistemas de historiales médicos
- [ ] Agentes especializados adicionales
- [ ] Sistema de autenticación y autorización
- [ ] Analytics y métricas avanzadas

## ⚠️ Disclaimer Médico

**IMPORTANTE**: Este sistema es una herramienta de asistencia y NO reemplaza la consulta médica profesional. Siempre busca atención médica calificada para diagnósticos y tratamientos definitivos.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 👥 Equipo

Desarrollado con ❤️ para mejorar el acceso a la información médica inicial.

---

¿Tienes preguntas? ¡Abre un issue o contacta al equipo de desarrollo!