import React, { useState } from 'react';
import ChatInterface from './components/ChatInterface';
import './App.css';

function App() {
  const [conversationId, setConversationId] = useState(null);
  const [error, setError] = useState(null);
  const [chatKey, setChatKey] = useState(0); // Key para forzar re-render del chat

  const handleRestart = () => {
    console.log('Reiniciando desde el header...');
    setConversationId(null);
    setError(null);
    setChatKey(prev => prev + 1); // Forzar re-render completo del chat
  };

  return (
    <div className="app">
      {/* Header simple */}
      <div className="app-header">
        <div className="app-nav">
          <div className="nav-brand">
            <h1>🏥 DiagnostiCAT</h1>
            <span>Asistencia Médica IA</span>
          </div>
          <button onClick={handleRestart} className="btn-restart">
            Reiniciar Conversación
          </button>
        </div>
      </div>

      {/* Contenido principal */}
      <div className="app-content">
        {error && (
          <div className="error-banner">
            <span>❌ {error}</span>
            <button onClick={() => setError(null)}>✕</button>
          </div>
        )}

        <ChatInterface 
          key={chatKey}
          conversationId={conversationId}
          onNewConversation={setConversationId}
          onRestart={handleRestart}
        />
      </div>

      {/* Footer simple */}
      <div className="app-footer">
        <div className="footer-content">
          <div className="footer-info">
            <p>🔒 Información confidencial | 📞 Emergencias: 123 | ⚠️ No reemplaza consulta médica</p>
            <p>🤖 Asistente médico basado en Inteligencia Artificial</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;