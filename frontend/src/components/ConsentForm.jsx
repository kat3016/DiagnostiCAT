import React, { useState } from 'react';
import './ConsentForm.css';

const ConsentForm = ({ onConsentGiven }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [showFullText, setShowFullText] = useState(false);

  const handleAccept = async () => {
    setIsLoading(true);
    try {
      await onConsentGiven(true);
    } catch (error) {
      console.error('Error al procesar consentimiento:', error);
      alert('Error al procesar el consentimiento. Intente nuevamente.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDecline = async () => {
    setIsLoading(true);
    try {
      await onConsentGiven(false);
    } catch (error) {
      console.error('Error al procesar consentimiento:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="consent-container">
      <div className="consent-card">
        <div className="consent-header">
          <h1>🏥 DiagnostiCAT</h1>
          <h2>Consentimiento para Asistencia Médica por IA</h2>
        </div>

        <div className="consent-content">
          <div className="disclaimer-box">
            <h3>⚠️ IMPORTANTE - DISCLAIMER MÉDICO</h3>
            <p>
              DiagnostiCAT es una herramienta de <strong>asistencia médica inicial</strong> basada en 
              inteligencia artificial. Esta aplicación <strong>NO reemplaza</strong> la consulta con 
              un profesional médico calificado.
            </p>
          </div>

          <div className="consent-text">
            <h4>Al usar este servicio, usted entiende y acepta que:</h4>
            <ul>
              <li>✓ Esta es una herramienta de orientación médica inicial</li>
              <li>✓ No constituye un diagnóstico médico definitivo</li>
              <li>✓ En caso de emergencia, debe acudir inmediatamente a servicios de urgencias</li>
              <li>✓ Para síntomas graves o persistentes, debe consultar a un médico</li>
              <li>✓ La información proporcionada será tratada de forma confidencial</li>
              <li>✓ Los datos se usan exclusivamente para mejorar la atención médica</li>
            </ul>

            {showFullText && (
              <div className="full-terms">
                <h4>Términos Detallados:</h4>
                <div className="terms-text">
                  <p><strong>Limitaciones del servicio:</strong></p>
                  <ul>
                    <li>No puede realizar diagnósticos definitivos</li>
                    <li>No prescribe medicamentos</li>
                    <li>No reemplaza exámenes médicos físicos</li>
                    <li>Las recomendaciones son orientativas</li>
                  </ul>
                  
                  <p><strong>Privacidad y datos:</strong></p>
                  <ul>
                    <li>Sus datos médicos están protegidos</li>
                    <li>Se almacenan de forma segura y anónima</li>
                    <li>Se usan para mejorar el servicio</li>
                    <li>Puede solicitar eliminarlos en cualquier momento</li>
                  </ul>

                  <p><strong>Cuándo buscar atención médica inmediata:</strong></p>
                  <ul>
                    <li>Dolor en el pecho o dificultad para respirar</li>
                    <li>Síntomas neurológicos graves</li>
                    <li>Sangrado abundante</li>
                    <li>Pérdida de conciencia</li>
                    <li>Cualquier emergencia médica</li>
                  </ul>
                </div>
              </div>
            )}

            <button 
              className="toggle-terms-btn"
              onClick={() => setShowFullText(!showFullText)}
            >
              {showFullText ? 'Ocultar términos detallados ↑' : 'Ver términos detallados ↓'}
            </button>
          </div>
        </div>

        <div className="consent-actions">
          <div className="consent-question">
            <p><strong>¿Acepta estos términos y condiciones?</strong></p>
            <p className="consent-note">
              Al aceptar, podrá continuar con la consulta médica asistida por IA.
            </p>
          </div>

          <div className="consent-buttons">
            <button 
              className="btn-decline" 
              onClick={handleDecline}
              disabled={isLoading}
            >
              {isLoading ? 'Procesando...' : 'No Acepto'}
            </button>
            <button 
              className="btn-accept" 
              onClick={handleAccept}
              disabled={isLoading}
            >
              {isLoading ? 'Procesando...' : 'Sí, Acepto y Continuar'}
            </button>
          </div>
        </div>

        <div className="consent-footer">
          <p>
            <small>
              🔒 Sus datos están protegidos | 
              📞 En emergencias, llame al 123 | 
              💻 Versión MVP 1.0
            </small>
          </p>
        </div>
      </div>
    </div>
  );
};

export default ConsentForm;