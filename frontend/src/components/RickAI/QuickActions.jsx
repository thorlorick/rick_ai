// frontend/src/components/RickAI/QuickActions.jsx

import React, { useState, useEffect } from 'react';
import { executeQuickQuery } from '../../services/rickAPI';
import './QuickActions.css';

const QuickActions = ({ onQueryResult, disabled }) => {
  const [loading, setLoading] = useState(null);
  const [expanded, setExpanded] = useState(false);

  const quickQueries = [
    {
      id: 'struggling_students',
      label: '📉 Who is struggling?',
      description: 'Students with average below 60%'
    },
    {
      id: 'missing_assignments',
      label: '📝 Missing assignments',
      description: 'Students with incomplete work'
    },
    {
      id: 'attendance_issues',
      label: '📅 Attendance issues',
      description: 'Students with absences/tardies'
    },
    {
      id: 'class_average',
      label: '📊 Class average',
      description: 'Overall class performance'
    },
    {
      id: 'recent_improvements',
      label: '📈 Recent improvements',
      description: 'Students who improved lately'
    },
    {
      id: 'assignment_completion',
      label: '✅ Assignment completion',
      description: 'Completion rates by assignment'
    }
  ];

  const handleQuickQuery = async (queryId) => {
    if (disabled) return;
    
    setLoading(queryId);
    
    try {
      const result = await executeQuickQuery(queryId);
      
      if (result.success) {
        onQueryResult({
          response: result.response,
          data: result.data,
          queryType: queryId
        });
      } else {
        onQueryResult({
          response: 'Sorry, I had trouble running that query.',
          data: []
        });
      }
    } catch (error) {
      console.error('Error executing quick query:', error);
      onQueryResult({
        response: 'An error occurred while running the query.',
        data: []
      });
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="quick-actions">
      <button 
        className="quick-actions-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        ⚡ Quick Queries {expanded ? '▼' : '▶'}
      </button>
      
      {expanded && (
        <div className="quick-actions-grid">
          {quickQueries.map(query => (
            <button
              key={query.id}
              onClick={() => handleQuickQuery(query.id)}
              disabled={disabled || loading === query.id}
              className="quick-action-button"
              title={query.description}
            >
              {loading === query.id ? (
                <span className="loading-spinner">⏳</span>
              ) : (
                query.label
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default QuickActions;
