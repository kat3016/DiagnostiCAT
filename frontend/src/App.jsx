import React, { useState } from 'react';
import ChatInterface from './components/ChatInterface';
import './App.css';

function App() {
  const [conversationId, setConversationId] = useState(null);
  const [error, setError] = useState(null);
  const [chatKey, setChatKey] = useState(0);

  const handleRestart = () => {
    setConversationId(null);
    setError(null);
    setChatKey(prev => prev + 1);
  };

  return (
    <div className="app" style={{ background: '#0b1326' }}>
      {/* Modern Header */}
      <header className="app-header">
        <div className="header-container">
          <div className="header-left">
            <div className="logo-area">
              <h1 className="logo-text">DiagnostiCAT</h1>
              <p className="logo-subtitle">AI Medical Assistant</p>
            </div>
          </div>
          <button onClick={handleRestart} className="btn-reset-header">
            Reset Chat
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="app-content">
        {error && (
          <div className="error-notification">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="error-close">×</button>
          </div>
        )}

        <ChatInterface 
          key={chatKey}
          conversationId={conversationId}
          onNewConversation={setConversationId}
          onRestart={handleRestart}
        />
      </div>

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <p>Confidential Information | Emergencies: 911 | Not a substitute for medical consultation</p>
        </div>
      </footer>
    </div>
  );
}

export default App;