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
      console.error('Error processing consent:', error);
      alert('Error processing consent. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDecline = async () => {
    setIsLoading(true);
    try {
      await onConsentGiven(false);
    } catch (error) {
      console.error('Error processing consent:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="consent-container">
      <div className="consent-card">
        <div className="consent-header">
          <h1>DiagnostiCAT</h1>
          <h2>Consent for AI Medical Assistance</h2>
        </div>

        <div className="consent-content">
          <div className="disclaimer-box">
            <h3>IMPORTANT - MEDICAL DISCLAIMER</h3>
            <p>
              DiagnostiCAT is an <strong>initial medical assistance</strong> tool based on
              artificial intelligence. This application <strong>DOES NOT replace</strong> consultation with
              a qualified medical professional.
            </p>
          </div>

          <div className="consent-text">
            <h4>By using this service, you understand and agree that:</h4>
            <ul>
              <li>This is an initial medical guidance tool</li>
              <li>It does not constitute a definitive medical diagnosis</li>
              <li>In an emergency, you should seek emergency services immediately</li>
              <li>For severe or persistent symptoms, you should consult a doctor</li>
              <li>The information provided will be treated confidentially</li>
              <li>Data is used exclusively to improve medical care</li>
            </ul>

            {showFullText && (
              <div className="full-terms">
                <h4>Detailed Terms:</h4>
                <div className="terms-text">
                  <p><strong>Service limitations:</strong></p>
                  <ul>
                    <li>It cannot make definitive diagnoses</li>
                    <li>It does not prescribe medications</li>
                    <li>It does not replace physical medical exams</li>
                    <li>Recommendations are for guidance only</li>
                  </ul>

                  <p><strong>Privacy and data:</strong></p>
                  <ul>
                    <li>Your medical data is protected</li>
                    <li>It is stored securely and anonymously</li>
                    <li>It is used to improve the service</li>
                    <li>You may request deletion at any time</li>
                  </ul>

                  <p><strong>When to seek immediate medical care:</strong></p>
                  <ul>
                    <li>Chest pain or difficulty breathing</li>
                    <li>Severe neurological symptoms</li>
                    <li>Heavy bleeding</li>
                    <li>Loss of consciousness</li>
                    <li>Any medical emergency</li>
                  </ul>
                </div>
              </div>
            )}

            <button
              className="toggle-terms-btn"
              onClick={() => setShowFullText(!showFullText)}
            >
              {showFullText ? 'Hide detailed terms' : 'View detailed terms'}
            </button>
          </div>
        </div>

        <div className="consent-actions">
          <div className="consent-question">
            <p><strong>Do you accept these terms and conditions?</strong></p>
            <p className="consent-note">
              By accepting, you can continue with the AI-assisted medical consultation.
            </p>
          </div>

          <div className="consent-buttons">
            <button
              className="btn-decline"
              onClick={handleDecline}
              disabled={isLoading}
            >
              {isLoading ? 'Processing...' : 'I Do Not Accept'}
            </button>
            <button
              className="btn-accept"
              onClick={handleAccept}
              disabled={isLoading}
            >
              {isLoading ? 'Processing...' : 'I Accept and Continue'}
            </button>
          </div>
        </div>

        <div className="consent-footer">
          <p>
            <small>
              Your data is protected |
              In emergencies, call 911 |
              MVP Version 1.0
            </small>
          </p>
        </div>
      </div>
    </div>
  );
};

export default ConsentForm;
