import React, { useState, useRef, useEffect } from 'react';
import './ChatInterface.css';

const ChatInterface = ({ conversationId, onNewConversation }) => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '⚠️ **ADVERTENCIA IMPORTANTE** ⚠️\n\n¡Hola! Soy **DiagnostiCAT**, un **asistente de inteligencia artificial** para recopilación de información médica. 🤖🏥\n\n🔴 **IMPORTANTE**: Soy un modelo de lenguaje de IA y **NO sustituyo la valoración médica profesional de un doctor certificado**. Esta herramienta es únicamente para fines informativos.\n\n📋 Antes de continuar, necesito su consentimiento informado para procesar información médica con fines educativos e informativos.\n\n¿Acepta que procese su información médica para brindarle asistencia informativa?\n\nPuede responder:\n• "Sí acepto" para continuar\n• "No acepto" para cancelar\n\n⚠️ **Recordatorio**: Para diagnóstico y tratamiento médico real, consulte siempre a un profesional médico certificado.',
      timestamp: new Date(),
      isWelcome: true
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConsentDenied, setIsConsentDenied] = useState(false); // Nuevo estado para controlar si se negó el consentimiento
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Mantener el foco en el input cuando se carga el componente
  useEffect(() => {
    const focusInput = () => {
      if (inputRef.current && !isLoading) {
        inputRef.current.focus();
      }
    };
    
    focusInput();
    
    // También enfocar cuando termina de cargar
    if (!isLoading) {
      setTimeout(focusInput, 100);
    }
  }, [isLoading]);

  // Foco inicial del componente
  useEffect(() => {
    setTimeout(() => {
      inputRef.current?.focus();
    }, 500);
  }, []);

  // Reiniciar el chat cuando conversationId cambia a null
  useEffect(() => {
    if (conversationId === null) {
      setMessages([
        {
          role: 'assistant',
          content: '⚠️ **ADVERTENCIA IMPORTANTE** ⚠️\n\n¡Hola! Soy **DiagnostiCAT**, un **asistente de inteligencia artificial** para recopilación de información médica. 🤖🏥\n\n🔴 **IMPORTANTE**: Soy un modelo de lenguaje de IA y **NO sustituyo la valoración médica profesional de un doctor certificado**. Esta herramienta es únicamente para fines informativos.\n\n📋 Antes de continuar, necesito su consentimiento informado para procesar información médica con fines educativos e informativos.\n\n¿Acepta que procese su información médica para brindarle asistencia informativa?\n\nPuede responder:\n• "Sí acepto" para continuar\n• "No acepto" para cancelar\n\n⚠️ **Recordatorio**: Para diagnóstico y tratamiento médico real, consulte siempre a un profesional médico certificado.',
          timestamp: new Date(),
          isWelcome: true
        }
      ]);
      setIsConsentDenied(false); // Resetear estado de consentimiento denegado
    }
  }, [conversationId]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading || isConsentDenied) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    // Guardamos el mensaje antes de limpiar el input
    const messageToSend = inputMessage;
    
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    // Detectar si el usuario está negando el consentimiento
    const userMessageLower = messageToSend.toLowerCase().trim();
    const negativePatterns = [
      'no acepto', 'no', 'niego', 'rechazo', 'rechaza', 'no autorizo',
      'no estoy de acuerdo', 'en desacuerdo'
    ];

    const isConsentNegative = negativePatterns.some(pattern => 
      userMessageLower.includes(pattern)
    );

    if (isConsentNegative && !conversationId) {
      // Usuario negó el consentimiento - bloquear el chat
      setIsConsentDenied(true);
      setIsLoading(false);
      
      const denialMessage = {
        role: 'assistant',
        content: '❌ **Consentimiento Denegado**\n\n🚫 Entiendo que no desea otorgar el consentimiento para procesar información médica.\n\n🔒 **El chat ha sido bloqueado** según su decisión.\n\nSin su consentimiento, no puedo proceder con la recopilación de información médica.\n\n🔄 Si cambia de opinión, puede usar el botón "**Reiniciar Conversación**" que aparece abajo para comenzar de nuevo.\n\n¡Que tenga un buen día! 👋',
        timestamp: new Date(),
        isConsentDenied: true
      };
      
      setMessages(prev => [...prev, denialMessage]);
      return;
    }

    try {
      // Importar dinámicamente el servicio
      const { chatService } = await import('../services/apiService');
      
      const response = await chatService.sendMessage(
        messageToSend,
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
      // Mantener el foco en el input después de enviar el mensaje (solo si el chat no está bloqueado)
      if (!isConsentDenied) {
        setTimeout(() => {
          inputRef.current?.focus();
        }, 100);
      }
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !isConsentDenied) {
      e.preventDefault();
      sendMessage();
    }
  };

  const restartConversation = () => {
    setIsConsentDenied(false);
    setInputMessage('');
    onNewConversation(null); // Esto activará el useEffect que resetea los mensajes
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
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role} ${message.isError ? 'error' : ''} ${message.isWelcome ? 'welcome' : ''}`}>
            <div className="message-content">
              <div className="message-text">
                {message.content.split('\n').map((line, i) => (
                  <div key={i}>
                    {line.includes('**') ? (
                      <span dangerouslySetInnerHTML={{ 
                        __html: line
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                          .replace(/• /g, '• ')
                      }} />
                    ) : (
                      line
                    )}
                    {i < message.content.split('\n').length - 1 && <br />}
                  </div>
                ))}
              </div>
              
              {/* Solo mostrar meta información para diagnósticos finales */}
              {message.is_diagnosis && (
                <div className="diagnosis-card">
                  <div className="diagnosis-header">
                    <h3>🏥 Análisis Médico Preliminar</h3>
                  </div>
                  
                  {message.predicted_condition && (
                    <div className="predicted-condition">
                      <strong>Condición Predicha:</strong> {message.predicted_condition}
                    </div>
                  )}
                  
                  {message.confidence_score && (
                    <div className="confidence-score">
                      <strong>Nivel de Confianza:</strong> {Math.round(message.confidence_score * 100)}%
                      <div className="confidence-bar">
                        <div 
                          className="confidence-fill" 
                          style={{ width: `${message.confidence_score * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  )}
                  
                  {message.severity_assessment && (
                    <div className="severity-assessment">
                      <span 
                        className="severity-badge"
                        style={{ backgroundColor: getSeverityColor(message.severity_assessment) }}
                      >
                        📊 Nivel de Urgencia: {message.severity_assessment}
                      </span>
                    </div>
                  )}
                  
                  <div className="diagnosis-disclaimer">
                    ⚠️ <em>Este análisis es preliminar y no reemplaza el diagnóstico médico profesional.</em>
                  </div>
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
        {isConsentDenied ? (
          // Mostrar botón de reiniciar cuando el consentimiento está denegado
          <div className="chat-blocked-state">
            <div className="blocked-message">
              🚫 **Chat Bloqueado**: Consentimiento denegado
            </div>
            <button 
              onClick={restartConversation}
              className="restart-button"
            >
              🔄 Reiniciar Conversación
            </button>
            <div className="blocked-disclaimer">
              Si cambia de opinión, puede reiniciar la conversación
            </div>
          </div>
        ) : (
          // Input normal cuando el chat no está bloqueado
          <>
            <div className="chat-input">
              <textarea
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                onFocus={(e) => e.target.selectionStart = e.target.value.length} // Cursor al final cuando obtiene foco
                placeholder="Describa sus síntomas o haga su consulta médica..."
                rows="3"
                disabled={isLoading}
                autoFocus={true}
                style={{
                  resize: 'none',
                  outline: 'none'
                }}
              />
              <button 
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className="send-button"
                onMouseDown={(e) => e.preventDefault()} // Evita que el botón quite el foco del textarea
              >
                {isLoading ? '...' : '→'}
              </button>
            </div>
            
            <div className="chat-disclaimer">
              ⚠️ Esta es una herramienta de orientación. En emergencias, llame al 123.
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;