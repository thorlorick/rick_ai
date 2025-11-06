// frontend/src/components/RickAI/MemoryList.jsx

import React, { useState } from 'react';
import { deleteMemory } from '../../services/rickAPI';
import './MemoryList.css';

const MemoryList = ({ memories, onMemoryDeleted, onClose }) => {
  const [deleting, setDeleting] = useState(null);

  const handleDelete = async (memoryId) => {
    if (!window.confirm('Are you sure you want to delete this memory?')) {
      return;
    }

    setDeleting(memoryId);
    
    try {
      const result = await deleteMemory(memoryId);
      
      if (result.success) {
        onMemoryDeleted(memoryId);
      } else {
        alert('Failed to delete memory: ' + result.error);
      }
    } catch (error) {
      console.error('Error deleting memory:', error);
      alert('An error occurred while deleting the memory');
    } finally {
      setDeleting(null);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  };

  if (!memories || memories.length === 0) {
    return (
      <div className="memory-list-modal">
        <div className="memory-list-container">
          <div className="memory-list-header">
            <h3>💭 Saved Memories</h3>
            <button onClick={onClose} className="close-button">✕</button>
          </div>
          <div className="memory-list-empty">
            <p>No memories saved yet.</p>
            <p className="hint">Use /remember to save important notes about students</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="memory-list-modal">
      <div className="memory-list-container">
        <div className="memory-list-header">
          <h3>💭 Saved Memories ({memories.length})</h3>
          <button onClick={onClose} className="close-button">✕</button>
        </div>
        
        <div className="memory-list-content">
          {memories.map(memory => (
            <div key={memory.id} className="memory-item">
              <div className="memory-meta">
                <span className="memory-id">ID: {memory.id}</span>
                <span className="memory-date">{formatDate(memory.createdAt)}</span>
              </div>
              
              <div className="memory-text">
                {memory.content}
              </div>
              
              {memory.studentName && (
                <div className="memory-student">
                  👤 {memory.studentName}
                </div>
              )}
              
              {memory.tags && memory.tags.length > 0 && (
                <div className="memory-tags">
                  {memory.tags.map((tag, index) => (
                    <span key={index} className="memory-tag">{tag}</span>
                  ))}
                </div>
              )}
              
              <button
                onClick={() => handleDelete(memory.id)}
                disabled={deleting === memory.id}
                className="delete-memory-button"
              >
                {deleting === memory.id ? 'Deleting...' : '🗑️ Delete'}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MemoryList;
