import React, { useState } from 'react';
import ConsentForm from './components/ConsentForm';
import ChatInterface from './components/ChatInterface';
import { consentService } from './services/apiService';
import './App.css';

function App() {
  const [step, setStep] = useState('consent'); // 'consent' | 'chat'
  const [conversationId, setConversationId] = useState(null);
  const [error, setError] = useState(null);

  const handleConsentGiven = async (accepted) => {
    try {
      const response = await consentService.submitConsent(accepted);
      
      if (accepted && response.accepted) {
        // Extraer conversation_id del mensaje
        const match = response.message.match(/conversation_id=([a-f0-9-]+)/);
        const convId = match ? match[1] : null;
        
        setConversationId(convId);
        setStep('chat');
        setError(null);
      } else {
        setError('Debe aceptar el consentimiento para continuar.');
      }
    } catch (error) {
      console.error('Error en consentimiento:', error);
      setError(`Error: ${error.message}`);
    }
  };

  const handleRestart = () => {
    setStep('consent');
    setConversationId(null);
    setError(null);
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
          {step === 'chat' && (
            <button onClick={handleRestart} className="btn-restart">
              🔄 Reiniciar
            </button>
          )}
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

        {step === 'consent' && (
          <ConsentForm onConsentGiven={handleConsentGiven} />
        )}

        {step === 'chat' && (
          <ChatInterface 
            conversationId={conversationId}
            onNewConversation={setConversationId}
          />
        )}
      </div>

      {/* Footer simple */}
      <div className="app-footer">
        <div className="footer-content">
          <div className="footer-info">
            <p>🔒 Información confidencial | 📞 Emergencias: 123 | ⚠️ No reemplaza consulta médica</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;