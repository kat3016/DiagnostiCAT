import React, { useState, useRef, useEffect } from 'react';
import './ChatInterface.css';

const ChatInterface = ({ conversationId, onNewConversation, onRestart }) => {
  const welcomeMessage = `Hello, Welcome to DiagnostiCAT

I'm a conversational agent designed to conduct basic medical history (anamnesis) and estimate the probability of certain health conditions based on your responses.

What can I do for you?
- Collect information about your symptoms
- Ask structured medical questions
- Provide probabilistic estimations

Estimated Duration: 5-10 minutes

INFORMED CONSENT

Before continuing, it's important that you understand:

This agent is for informational and educational purposes only
It does NOT replace professional medical care
Results are estimates subject to error
Your information is used only during this session
It is not permanently stored or shared

In case of emergency symptoms, seek immediate medical attention

Do you agree to continue under these conditions?

- Type "I agree" to begin the consultation
- Type "I do not agree" to decline

I'm here to help you.`;

  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: welcomeMessage,
      timestamp: new Date(),
      isWelcome: true
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConsentDenied, setIsConsentDenied] = useState(false); // Tracks whether consent was denied
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Keep focus on the input when the component loads
  useEffect(() => {
    const focusInput = () => {
      if (inputRef.current && !isLoading) {
        inputRef.current.focus();
      }
    };
    
    focusInput();
    
    // Also focus when loading finishes
    if (!isLoading) {
      setTimeout(focusInput, 100);
    }
  }, [isLoading]);

  // Initial component focus
  useEffect(() => {
    setTimeout(() => {
      inputRef.current?.focus();
    }, 500);
  }, []);

  // Restart the chat when conversationId changes to null
  useEffect(() => {
    if (conversationId === null) {
      setMessages([
        {
          role: 'assistant',
          content: welcomeMessage,
          timestamp: new Date(),
          isWelcome: true
        }
      ]);
      setIsConsentDenied(false);
      setInputMessage('');
      setIsLoading(false);
      
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 300);
    }
  }, [conversationId]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading || isConsentDenied) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    const messageToSend = inputMessage;
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    const userMessageLower = messageToSend.toLowerCase().trim();
    const negativePatterns = [
      'i do not agree', 'i disagree', 'no', 'reject', 'decline',
      'don\'t agree', 'disagree'
    ];

    const isConsentNegative = negativePatterns.some(pattern => 
      userMessageLower.includes(pattern)
    );

    if (isConsentNegative && !conversationId) {
      setIsConsentDenied(true);
      setIsLoading(false);
      
      const denialMessage = {
        role: 'assistant',
        content: `Consent Denied

I understand that you do not wish to provide consent for processing medical information.

The chat has been blocked according to your decision.

Without your consent, I cannot proceed with collecting medical information.

If you change your mind, you can use the "Reset Chat" button to start over.

Have a good day.`,
        timestamp: new Date(),
        isConsentDenied: true
      };
      
      setMessages(prev => [...prev, denialMessage]);
      return;
    }

    try {
      const { chatService } = await import('../services/apiService');
      
      const response = await chatService.sendMessage(
        messageToSend,
        conversationId,
        null
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

      if (response.conversation_id && response.conversation_id !== conversationId) {
        onNewConversation(response.conversation_id);
      }

    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant',
        content: `Error: ${error.message}. Please verify that the backend is running at http://localhost:8000`,
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
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
    if (onRestart) {
      onRestart();
    } else {
      setIsConsentDenied(false);
      setInputMessage('');
      setIsLoading(false);
      onNewConversation(null);
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
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role} ${message.isError ? 'error' : ''} ${message.isWelcome ? 'welcome' : ''}`}>
            <div className="message-bubble">
              <div className="message-text">
                {message.content.split('\n').map((line, i) => (
                  <div key={i} className="text-line">
                    {line || <br />}
                  </div>
                ))}
              </div>
              <div className="message-time">{formatTime(message.timestamp)}</div>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message assistant loading">
            <div className="message-bubble">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        {isConsentDenied ? (
          <div className="blocked-state">
            <div className="blocked-message">Chat blocked due to consent denial</div>
            <button onClick={restartConversation} className="btn-restart-chat">
              Reset Chat
            </button>
          </div>
        ) : (
          <>
            <div className="input-wrapper">
              <textarea
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Describe your symptoms or ask a medical question..."
                rows="3"
                disabled={isLoading}
                autoFocus={true}
                className="message-input"
              />
              <button 
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className="btn-send"
              >
                {isLoading ? '...' : 'Send'}
              </button>
            </div>
            
            <div className="input-disclaimer">
              This is a guidance tool. In emergencies, call 911.
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;
