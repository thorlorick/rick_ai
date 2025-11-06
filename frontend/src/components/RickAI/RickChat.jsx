// frontend/src/components/RickAI/RickChat.jsx

import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import QuickActions from './QuickActions';
import MemoryList from './MemoryList';
import { sendMessage, getMemories } from '../../services/rickAPI';
import { parseCommand, COMMANDS } from '../../utils/commandParser';
import './RickChat.css';

const RickChat = ({ teacherName }) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showMemories, setShowMemories] = useState(false);
  const [memories, setMemories] = useState([]);
  const messagesEndRef = useRef(null);
  const [error, setError] = useState(null);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Add initial greeting
  useEffect(() => {
    setMessages([
      {
        id: Date.now(),
        content: `Hi${teacherName ? ' ' + teacherName : ''}! I'm Rick, your AI teaching assistant. I can help you analyze student data, track progress, and answer questions about your class. Try asking me something, or use the Quick Queries below!`,
        isUser: false,
        timestamp: new Date(),
        data: null
      }
    ]);
  }, [teacherName]);

  const handleSendMessage = async (messageText) => {
    if (isLoading) return;

    setError(null);
    
    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      content: messageText,
      isUser: true,
      timestamp: new Date(),
      data: null
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Check if it's a /memories command
      const parsed = parseCommand(messageText);
      if (parsed.isCommand && parsed.command === COMMANDS.MEMORIES) {
        await handleMemoriesCommand(parsed.args);
        setIsLoading(false);
        return;
      }

      // Get conversation history (last 10 messages)
      const conversationHistory = messages
        .slice(-10)
        .map(msg => ({
          role: msg.isUser ? 'user' : 'assistant',
          content: msg.content
        }));

      // Send to backend
      const result = await sendMessage(messageText, conversationHistory);

      if (result.success) {
        const rickMessage = {
          id: Date.now() + 1,
          content: result.response,
          isUser: false,
          timestamp: new Date(),
          data: result.data || null
        };
        
        setMessages(prev => [...prev, rickMessage]);
      } else {
        throw new Error(result.error || 'Failed to send message');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setError(error.message);
      
      const errorMessage = {
        id: Date.now() + 1,
        content: `Sorry, I encountered an error: ${error.message}. Please try again.`,
        isUser: false,
        timestamp: new Date(),
        data: null
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickQueryResult = (result) => {
    const rickMessage = {
      id: Date.now(),
      content: result.response,
      isUser: false,
      timestamp: new Date(),
      data: result.data || null
    };
    
    setMessages(prev => [...prev, rickMessage]);
  };

  const handleMemoriesCommand = async (studentName) => {
    try {
      const result = await getMemories(studentName);
      
      if (result.success && result.memories) {
        setMemories(result.memories);
        setShowMemories(true);
      } else {
        const rickMessage = {
          id: Date.now(),
          content: studentName 
            ? `I don't have any memories about ${studentName}.`
            : "I don't have any saved memories yet. Use /remember to save notes!",
          isUser: false,
          timestamp: new Date(),
          data: null
        };
        
        setMessages(prev => [...prev, rickMessage]);
      }
    } catch (error) {
      console.error('Error fetching memories:', error);
    }
  };

  const handleMemoryDeleted = (memoryId) => {
    setMemories(prev => prev.filter(m => m.id !== memoryId));
    
    // If no memories left, close the modal
    if (memories.length <= 1) {
      setShowMemories(false);
    }
  };

  const clearChat = () => {
    if (window.confirm('Clear all messages?')) {
      setMessages([
        {
          id: Date.now(),
          content: `Chat cleared. How can I help you${teacherName ? ', ' + teacherName : ''}?`,
          isUser: false,
          timestamp: new Date(),
          data: null
        }
      ]);
    }
  };

  return (
    <div className="rick-chat-container">
      <div className="chat-header">
        <div className="header-content">
          <h2>🤖 Rick AI Assistant</h2>
          <p className="header-subtitle">
            Your intelligent teaching companion
          </p>
        </div>
        <button onClick={clearChat} className="clear-chat-button">
          🗑️ Clear Chat
        </button>
      </div>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      <QuickActions 
        onQueryResult={handleQuickQueryResult}
        disabled={isLoading}
      />

      <div className="messages-container">
        {messages.map(msg => (
          <ChatMessage
            key={msg.id}
            message={msg.content}
            isUser={msg.isUser}
            timestamp={msg.timestamp}
            data={msg.data}
          />
        ))}
        
        {isLoading && (
          <div className="loading-indicator">
            <div className="typing-animation">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span className="loading-text">Rick is thinking...</span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <ChatInput 
        onSendMessage={handleSendMessage}
        disabled={isLoading}
      />

      {showMemories && (
        <MemoryList
          memories={memories}
          onMemoryDeleted={handleMemoryDeleted}
          onClose={() => setShowMemories(false)}
        />
      )}
    </div>
  );
};

export default RickChat;
