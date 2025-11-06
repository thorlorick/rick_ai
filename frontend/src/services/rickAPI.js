// frontend/src/services/rickAPI.js

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000/api';

/**
 * Send a message to Rick
 */
export const sendMessage = async (message, conversationHistory = []) => {
  try {
    const response = await fetch(`${API_BASE_URL}/rick/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Important for sending cookies/session
      body: JSON.stringify({
        message,
        conversation_history: conversationHistory
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to send message');
    }

    return await response.json();
  } catch (error) {
    console.error('Error sending message to Rick:', error);
    throw error;
  }
};

/**
 * Execute a pre-defined query
 */
export const executeQuickQuery = async (queryType) => {
  try {
    const response = await fetch(`${API_BASE_URL}/rick/quick-query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        query_type: queryType
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to execute query');
    }

    return await response.json();
  } catch (error) {
    console.error('Error executing quick query:', error);
    throw error;
  }
};

/**
 * Save a memory
 */
export const saveMemory = async (memoryContent, studentId = null) => {
  try {
    const response = await fetch(`${API_BASE_URL}/rick/memory`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        memory_content: memoryContent,
        student_id: studentId
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to save memory');
    }

    return await response.json();
  } catch (error) {
    console.error('Error saving memory:', error);
    throw error;
  }
};

/**
 * Get memories (optionally filtered by student)
 */
export const getMemories = async (studentName = null) => {
  try {
    const url = studentName 
      ? `${API_BASE_URL}/rick/memories?student=${encodeURIComponent(studentName)}`
      : `${API_BASE_URL}/rick/memories`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include'
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch memories');
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching memories:', error);
    throw error;
  }
};

/**
 * Delete a memory
 */
export const deleteMemory = async (memoryId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/rick/memory/${memoryId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include'
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to delete memory');
    }

    return await response.json();
  } catch (error) {
    console.error('Error deleting memory:', error);
    throw error;
  }
};
