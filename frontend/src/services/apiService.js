import axios from 'axios';

// Configuración base para la API
const API_BASE_URL = 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Servicio para gestión de consentimiento
export const consentService = {
  async submitConsent(accepted) {
    const response = await apiClient.post('/consent', { accepted });
    return response.data;
  },
};

// Servicio para chat médico
export const chatService = {
  async sendMessage(message, conversationId = null, patientContext = null) {
    const payload = {
      message,
      conversation_id: conversationId,
      patient_context: patientContext,
    };
    
    const response = await apiClient.post('/chat/', payload);
    return response.data;
  },

  async getConversationHistory(conversationId) {
    const response = await apiClient.get(`/chat/${conversationId}/history`);
    return response.data;
  },

  async listConversations() {
    const response = await apiClient.get('/chat/conversations/list');
    return response.data;
  },

  async deleteConversation(conversationId) {
    const response = await apiClient.delete(`/chat/${conversationId}`);
    return response.data;
  },
};

// Servicio para anamnesis
export const anamnesisService = {
  async getNextQuestion(conversationId) {
    const response = await apiClient.get(`/anamnesis/next?conversation_id=${conversationId}`);
    return response.data;
  },

  async submitAnswer(conversationId, key, value) {
    const response = await apiClient.post('/anamnesis/answer', value, {
      params: { conversation_id: conversationId, key },
    });
    return response.data;
  },

  async getStructured(conversationId) {
    const response = await apiClient.get(`/anamnesis/structured?conversation_id=${conversationId}`);
    return response.data;
  },

  async getSummary(conversationId) {
    const response = await apiClient.get(`/anamnesis/summary?conversation_id=${conversationId}`);
    return response.data;
  },
};

// Interceptor para manejo de errores
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    
    if (error.response) {
      // Error de respuesta del servidor
      const message = error.response.data?.detail || error.response.data?.message || 'Error del servidor';
      throw new Error(message);
    } else if (error.request) {
      // Error de red
      throw new Error('Error de conexión. Verifique que el backend esté funcionando.');
    } else {
      // Otro tipo de error
      throw new Error('Error inesperado');
    }
  }
);

export default {
  consentService,
  chatService,
  anamnesisService,
};