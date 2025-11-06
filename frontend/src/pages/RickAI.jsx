// frontend/src/pages/RickAI.jsx

import React, { useState, useEffect } from 'react';
import RickChat from '../components/RickAI/RickChat';
import './RickAI.css';

const RickAI = () => {
  const [teacherName, setTeacherName] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch teacher info from your existing auth system
    // This is a placeholder - adjust to your authentication method
    fetchTeacherInfo();
  }, []);

  const fetchTeacherInfo = async () => {
    try {
      // Example: fetch from your existing API
      // Replace this with your actual auth check
      const response = await fetch('/api/auth/me', {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Not authenticated');
      }

      const data = await response.json();
      setTeacherName(data.name || data.username);
      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching teacher info:', error);
      setError('Please log in to use Rick AI');
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="rick-ai-page">
        <div className="loading-screen">
          <div className="loading-spinner-large"></div>
          <p>Loading Rick AI...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rick-ai-page">
        <div className="error-screen">
          <h2>⚠️ Authentication Required</h2>
          <p>{error}</p>
          <a href="/login" className="login-link">Go to Login</a>
        </div>
      </div>
    );
  }

  return (
    <div className="rick-ai-page">
      <div className="rick-ai-content">
        <RickChat teacherName={teacherName} />
      </div>
      
      <aside className="rick-ai-sidebar">
        <div className="sidebar-section">
          <h3>💡 Tips</h3>
          <ul>
            <li>Ask about specific students or groups</li>
            <li>Use /remember to save important notes</li>
            <li>Try Quick Queries for common reports</li>
            <li>Reference students by name for context</li>
          </ul>
        </div>
        
        <div className="sidebar-section">
          <h3>📝 Commands</h3>
          <ul>
            <li><code>/remember [note]</code> - Save a memory</li>
            <li><code>/memories</code> - View all memories</li>
            <li><code>/forget [id]</code> - Delete a memory</li>
            <li><code>/help</code> - Show all commands</li>
          </ul>
        </div>

        <div className="sidebar-section">
          <h3>❓ Example Questions</h3>
          <ul>
            <li>"Who scored below 60 on the last quiz?"</li>
            <li>"Show me students who improved"</li>
            <li>"What's the class average?"</li>
            <li>"Who has been absent the most?"</li>
          </ul>
        </div>
      </aside>
    </div>
  );
};

export default RickAI;
