import React, { useState, useEffect } from 'react';
import './AnamnesisFlow.css';

const AnamnesisFlow = ({ conversationId, onComplete }) => {
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [answers, setAnswers] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadNextQuestion();
  }, [conversationId]);

  const loadNextQuestion = async () => {
    if (!conversationId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const { anamnesisService } = await import('../services/apiService');
      const response = await anamnesisService.getNextQuestion(conversationId);
      
      if (response.completed) {
        setIsCompleted(true);
        await loadSummary();
      } else {
        setCurrentQuestion(response);
      }
    } catch (error) {
      console.error('Error cargando pregunta:', error);
      setError(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSummary = async () => {
    try {
      const { anamnesisService } = await import('../services/apiService');
      const summaryResponse = await anamnesisService.getSummary(conversationId);
      setSummary(summaryResponse);
    } catch (error) {
      console.error('Error cargando resumen:', error);
      setError('Error al generar el resumen de la anamnesis');
    }
  };

  const handleAnswer = async (key, value) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const { anamnesisService } = await import('../services/apiService');
      await anamnesisService.submitAnswer(conversationId, key, value);
      
      // Actualizar respuestas localmente
      setAnswers(prev => ({ ...prev, [key]: value }));
      
      // Cargar siguiente pregunta
      await loadNextQuestion();
    } catch (error) {
      console.error('Error enviando respuesta:', error);
      setError(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const renderQuestionInput = (question) => {
    if (!question) return null;

    const { key, question_text, input_type, options, validation } = question;

    switch (input_type) {
      case 'text':
        return (
          <div className="question-input">
            <textarea
              placeholder="Escriba su respuesta aquí..."
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  const value = e.target.value.trim();
                  if (value) {
                    handleAnswer(key, value);
                  }
                }
              }}
              disabled={isLoading}
              autoFocus
            />
            <div className="input-hint">
              Presione Enter para continuar
            </div>
          </div>
        );

      case 'number':
        return (
          <div className="question-input">
            <input
              type="number"
              placeholder={validation?.placeholder || "Ingrese un número"}
              min={validation?.min}
              max={validation?.max}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const value = parseFloat(e.target.value);
                  if (!isNaN(value)) {
                    handleAnswer(key, value);
                  }
                }
              }}
              disabled={isLoading}
              autoFocus
            />
          </div>
        );

      case 'select':
        return (
          <div className="question-options">
            {options?.map((option, index) => (
              <button
                key={index}
                className="option-button"
                onClick={() => handleAnswer(key, option.value)}
                disabled={isLoading}
              >
                {option.label}
              </button>
            ))}
          </div>
        );

      case 'boolean':
        return (
          <div className="question-options boolean">
            <button
              className="option-button yes"
              onClick={() => handleAnswer(key, true)}
              disabled={isLoading}
            >
              ✅ Sí
            </button>
            <button
              className="option-button no"
              onClick={() => handleAnswer(key, false)}
              disabled={isLoading}
            >
              ❌ No
            </button>
          </div>
        );

      case 'date':
        return (
          <div className="question-input">
            <input
              type="date"
              onChange={(e) => {
                if (e.target.value) {
                  handleAnswer(key, e.target.value);
                }
              }}
              disabled={isLoading}
              autoFocus
            />
          </div>
        );

      default:
        return (
          <div className="question-input">
            <input
              type="text"
              placeholder="Escriba su respuesta..."
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const value = e.target.value.trim();
                  if (value) {
                    handleAnswer(key, value);
                  }
                }
              }}
              disabled={isLoading}
              autoFocus
            />
          </div>
        );
    }
  };

  if (error) {
    return (
      <div className="anamnesis-container">
        <div className="anamnesis-card error">
          <h2>❌ Error</h2>
          <p>{error}</p>
          <button onClick={loadNextQuestion} className="retry-button">
            🔄 Intentar nuevamente
          </button>
        </div>
      </div>
    );
  }

  if (isCompleted && summary) {
    return (
      <div className="anamnesis-container">
        <div className="anamnesis-card completed">
          <div className="completion-header">
            <h2>✅ Anamnesis Completada</h2>
            <p>Hemos registrado toda la información necesaria.</p>
          </div>

          <div className="summary-section">
            <h3>📋 Resumen de la Anamnesis</h3>
            <div className="structured-data">
              {summary.structured && (
                <div className="summary-grid">
                  {Object.entries(summary.structured).map(([key, value]) => (
                    <div key={key} className="summary-item">
                      <strong>{formatFieldName(key)}:</strong>
                      <span>{formatValue(value)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {summary.summary && (
              <div className="ai-summary">
                <h4>🤖 Análisis del Asistente</h4>
                <p>{summary.summary}</p>
              </div>
            )}

            {summary.follow_up_questions && summary.follow_up_questions.length > 0 && (
              <div className="follow-up-section">
                <h4>❓ Preguntas de Seguimiento</h4>
                <ul>
                  {summary.follow_up_questions.map((question, index) => (
                    <li key={index}>{question}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="completion-actions">
            <button 
              className="btn-continue-chat"
              onClick={() => onComplete(summary)}
            >
              💬 Continuar con Chat Médico
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="anamnesis-container">
      <div className="anamnesis-card">
        <div className="anamnesis-header">
          <h1>📝 Anamnesis Médica</h1>
          <p>Recopilación estructurada de información médica</p>
          <div className="progress-indicator">
            <span>Pregunta {Object.keys(answers).length + 1}</span>
          </div>
        </div>

        <div className="question-section">
          {isLoading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Procesando información...</p>
            </div>
          ) : currentQuestion ? (
            <>
              <div className="question-text">
                <h3>{currentQuestion.question_text}</h3>
                {currentQuestion.context && (
                  <p className="question-context">{currentQuestion.context}</p>
                )}
              </div>
              
              {renderQuestionInput(currentQuestion)}
              
              {currentQuestion.help_text && (
                <div className="help-text">
                  💡 {currentQuestion.help_text}
                </div>
              )}
            </>
          ) : (
            <div className="no-question">
              <p>Preparando siguiente pregunta...</p>
            </div>
          )}
        </div>

        {Object.keys(answers).length > 0 && (
          <div className="answers-summary">
            <h4>📋 Respuestas registradas:</h4>
            <div className="answers-list">
              {Object.entries(answers).slice(-3).map(([key, value]) => (
                <div key={key} className="answer-item">
                  <strong>{formatFieldName(key)}:</strong>
                  <span>{formatValue(value)}</span>
                </div>
              ))}
              {Object.keys(answers).length > 3 && (
                <div className="more-answers">
                  ... y {Object.keys(answers).length - 3} más
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Funciones de utilidad
const formatFieldName = (key) => {
  const fieldNames = {
    'chief_complaint': 'Motivo de consulta',
    'symptom_duration': 'Duración de síntomas',
    'pain_scale': 'Escala de dolor',
    'fever': 'Fiebre',
    'allergies': 'Alergias',
    'medications': 'Medicamentos',
    'medical_history': 'Antecedentes médicos',
    'family_history': 'Antecedentes familiares',
    'social_history': 'Historia social',
    'review_of_systems': 'Revisión por sistemas',
  };
  return fieldNames[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

const formatValue = (value) => {
  if (typeof value === 'boolean') {
    return value ? 'Sí' : 'No';
  }
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  return String(value);
};

export default AnamnesisFlow;