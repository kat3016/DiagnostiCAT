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
      console.error('Error loading question:', error);
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
      console.error('Error loading summary:', error);
      setError('Error generating the anamnesis summary');
    }
  };

  const handleAnswer = async (key, value) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const { anamnesisService } = await import('../services/apiService');
      await anamnesisService.submitAnswer(conversationId, key, value);
      
      // Update answers locally
      setAnswers(prev => ({ ...prev, [key]: value }));
      
      // Load next question
      await loadNextQuestion();
    } catch (error) {
      console.error('Error sending answer:', error);
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
              placeholder="Type your answer here..."
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
              Press Enter to continue
            </div>
          </div>
        );

      case 'number':
        return (
          <div className="question-input">
            <input
              type="number"
              placeholder={validation?.placeholder || "Enter a number"}
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
              Yes
            </button>
            <button
              className="option-button no"
              onClick={() => handleAnswer(key, false)}
              disabled={isLoading}
            >
              No
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
              placeholder="Type your answer..."
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
          <h2>Error</h2>
          <p>{error}</p>
          <button onClick={loadNextQuestion} className="retry-button">
            Try again
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
            <h2>Anamnesis Completed</h2>
            <p>We have recorded all the necessary information.</p>
          </div>

          <div className="summary-section">
            <h3>Anamnesis Summary</h3>
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
                <h4>Assistant Analysis</h4>
                <p>{summary.summary}</p>
              </div>
            )}

            {summary.follow_up_questions && summary.follow_up_questions.length > 0 && (
              <div className="follow-up-section">
                <h4>Follow-Up Questions</h4>
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
              Continue with Medical Chat
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
          <h1>Medical Anamnesis</h1>
          <p>Structured medical information collection</p>
          <div className="progress-indicator">
            <span>Question {Object.keys(answers).length + 1}</span>
          </div>
        </div>

        <div className="question-section">
          {isLoading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Processing information...</p>
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
                  {currentQuestion.help_text}
                </div>
              )}
            </>
          ) : (
            <div className="no-question">
              <p>Preparing next question...</p>
            </div>
          )}
        </div>

        {Object.keys(answers).length > 0 && (
          <div className="answers-summary">
            <h4>Recorded answers:</h4>
            <div className="answers-list">
              {Object.entries(answers).slice(-3).map(([key, value]) => (
                <div key={key} className="answer-item">
                  <strong>{formatFieldName(key)}:</strong>
                  <span>{formatValue(value)}</span>
                </div>
              ))}
              {Object.keys(answers).length > 3 && (
                <div className="more-answers">
                  ... and {Object.keys(answers).length - 3} more
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Utility functions
const formatFieldName = (key) => {
  const fieldNames = {
    'chief_complaint': 'Reason for consultation',
    'symptom_duration': 'Symptom duration',
    'pain_scale': 'Pain scale',
    'fever': 'Fever',
    'allergies': 'Allergies',
    'medications': 'Medications',
    'medical_history': 'Medical history',
    'family_history': 'Family history',
    'social_history': 'Social history',
    'review_of_systems': 'Review of systems',
  };
  return fieldNames[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

const formatValue = (value) => {
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  return String(value);
};

export default AnamnesisFlow;
