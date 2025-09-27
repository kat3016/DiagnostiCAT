import React, { useState, useRef, useEffect } from 'react';
import './ChatInterface.css';

const ChatInterface = ({ conversationId, onNewConversation }) => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '¡Hola! Soy su asistente médico virtual de DiagnostiCAT. 🏥\n\nAntes de comenzar con su consulta médica, necesito su consentimiento informado.\n\n¿Acepta que procese su información médica para brindarle asistencia personalizada?\n\nPuede responder:\n• "Sí acepto" para continuar\n• "No acepto" para cancelar',
      timestamp: new Date(),
      isWelcome: true
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Importar dinámicamente el servicio
      const { chatService } = await import('../services/apiService');
      
      const response = await chatService.sendMessage(
        inputMessage,
        conversationId,
        null // No enviamos contexto de paciente por simplicidad
      );

      const assistantMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date(),
        agent_type: response.agent_type,
        confidence_score: response.confidence_score,
        severity_assessment: response.severity_assessment,
        suggestions: response.suggestions,
        follow_up_questions: response.follow_up_questions
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Si es una nueva conversación, actualizar el ID
      if (response.conversation_id && response.conversation_id !== conversationId) {
        onNewConversation(response.conversation_id);
      }

    } catch (error) {
      console.error('Error enviando mensaje:', error);
      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.message}. Por favor, verifique que el backend esté funcionando en http://localhost:8000`,
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getSeverityColor = (severity) => {
    const severityMap = {
      'CRÍTICO': '#dc3545',
      'ALTO': '#fd7e14',
      'MEDIO': '#ffc107',
      'BAJO': '#28a745'
    };
    return severityMap[severity?.toUpperCase()] || '#6c757d';
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('es-CO', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-header-info">
          <h1>🏥 DiagnostiCAT - Asistente Médico</h1>
          <p>Consulta médica asistida por inteligencia artificial</p>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role} ${message.isError ? 'error' : ''} ${message.isWelcome ? 'welcome' : ''}`}>
            <div className="message-content">
              <div className="message-text">{message.content}</div>
              
              {message.agent_type && (
                <div className="message-meta">
                  <span className="agent-type">🤖 {message.agent_type}</span>
                  {message.confidence_score && (
                    <span className="confidence">Confianza: {Math.round(message.confidence_score * 100)}%</span>
                  )}
                </div>
              )}

              {message.severity_assessment && (
                <div className="severity-assessment">
                  <span 
                    className="severity-badge"
                    style={{ backgroundColor: getSeverityColor(message.severity_assessment) }}
                  >
                    📊 Urgencia: {message.severity_assessment}
                  </span>
                </div>
              )}

              {message.suggestions && message.suggestions.length > 0 && (
                <div className="suggestions">
                  <h4>💡 Sugerencias:</h4>
                  <ul>
                    {message.suggestions.map((suggestion, i) => (
                      <li key={i}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}

              {message.follow_up_questions && message.follow_up_questions.length > 0 && (
                <div className="follow-up">
                  <h4>❓ Preguntas de seguimiento:</h4>
                  <ul>
                    {message.follow_up_questions.map((question, i) => (
                      <li key={i}>
                        <button 
                          className="follow-up-btn"
                          onClick={() => setInputMessage(question)}
                        >
                          {question}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            
            <div className="message-time">
              {formatTime(message.timestamp)}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message assistant loading">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div className="message-text">El asistente médico está escribiendo...</div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="chat-input">
          <textarea
            ref={inputRef}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Describa sus síntomas o haga su consulta médica..."
            rows="3"
            disabled={isLoading}
          />
          <button 
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="send-button"
          >
            {isLoading ? '⏳' : '📤'}
          </button>
        </div>
        
        <div className="chat-disclaimer">
          ⚠️ Esta es una herramienta de orientación. En emergencias, llame al 123.
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;