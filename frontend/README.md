# Frontend DiagnostiCAT

Frontend React para el sistema DiagnostiCAT de asistencia médica por IA.

## 🚀 Instalación y Ejecución

### Prerrequisitos
- Node.js 18+ 
- npm o yarn
- Backend DiagnostiCAT ejecutándose en http://localhost:8000

### Instalación
```bash
cd frontend
npm install
```

### Ejecución en desarrollo
```bash
npm run dev
```

La aplicación estará disponible en: http://localhost:3000

## 📋 Funcionalidades Implementadas

### ✅ Flujo Completo de Consulta Médica
1. **Consentimiento Médico**: Formulario con términos y condiciones
2. **Anamnesis Estructurada**: Recolección de datos médicos
3. **Chat Médico**: Interacción con agentes de IA especializados

### 🎨 Interfaz de Usuario
- Diseño limpio y profesional
- Navegación por pasos clara
- Indicadores de progreso
- Mensajes de estado y error
- Animaciones suaves

### 🔧 Características Técnicas
- React 18 con Hooks
- React Router para navegación
- Axios para comunicación con API
- CSS modular por componente
- Gestión de estado local
- Manejo de errores robusto

## 📁 Estructura del Proyecto

```
frontend/
├── public/
│   ├── vite.svg
│   └── index.html
├── src/
│   ├── components/
│   │   ├── ConsentForm.jsx/.css
│   │   ├── ChatInterface.jsx/.css
│   │   └── AnamnesisFlow.jsx/.css
│   ├── services/
│   │   └── apiService.js
│   ├── App.jsx/.css
│   └── main.jsx
├── package.json
└── vite.config.js
```

## 🌐 Integración con Backend

### Endpoints Utilizados
- `POST /api/v1/consent` - Registrar consentimiento
- `GET /api/v1/anamnesis/next` - Obtener siguiente pregunta
- `POST /api/v1/anamnesis/answer` - Enviar respuesta
- `GET /api/v1/anamnesis/summary` - Obtener resumen
- `POST /api/v1/chat/` - Enviar mensaje al chat
- `GET /api/v1/chat/{id}/history` - Historial de conversación

### Configuración de Proxy
El desarrollo usa proxy automático hacia `localhost:8000` para evitar problemas de CORS.

## 🎯 Flujo de Usuario

1. **Pantalla de Consentimiento**
   - Usuario lee términos médicos
   - Acepta o rechaza consentimiento
   - Si acepta, se genera conversation_id

2. **Anamnesis Médica**
   - Preguntas estructuradas dinámicas
   - Validación de respuestas
   - Resumen final con análisis IA

3. **Chat Médico**
   - Formulario de información del paciente
   - Chat en tiempo real con agente IA
   - Evaluación de severidad
   - Sugerencias y preguntas de seguimiento

## 🔧 Scripts Disponibles

```bash
# Desarrollo
npm run dev

# Construcción para producción
npm run build

# Vista previa de producción
npm run preview

# Linting
npm run lint
```

## 🎨 Personalización de Estilos

Los estilos están organizados por componente:
- Cada componente tiene su archivo CSS correspondiente
- `App.css` contiene estilos globales y layout
- Paleta de colores médica profesional
- No es responsive por diseño (MVP)

## 🔒 Consideraciones de Seguridad

- Manejo seguro de datos médicos
- Validación de formularios
- Manejo de errores sin exponer información sensible
- Mensajes claros sobre limitaciones del sistema

## 🚨 Limitaciones Actuales (MVP)

- **No responsive**: Optimizado solo para desktop
- **Sin persistencia local**: Los datos se pierden al recargar
- **Sin autenticación**: Acceso libre
- **Sin historial**: Solo conversación actual
- **Sin offline**: Requiere conexión constante

## 🎯 Próximas Mejoras

- [ ] Diseño responsive
- [ ] Persistencia en localStorage
- [ ] Sistema de autenticación
- [ ] Historial de consultas
- [ ] Modo offline básico
- [ ] Notificaciones push
- [ ] Compartir conversaciones
- [ ] Exportar reportes médicos

## 🤝 Contribuciones

Para agregar nuevas funcionalidades:
1. Crear nuevo componente en `/src/components/`
2. Agregar estilos en archivo `.css` correspondiente
3. Integrar en el flujo principal (`App.jsx`)
4. Actualizar servicios API si es necesario

## 📞 Soporte

En caso de problemas:
1. Verificar que el backend esté ejecutándose
2. Revisar la consola del navegador
3. Verificar conectividad de red
4. Consultar logs del servidor