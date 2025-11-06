// frontend/src/components/RickAI/ChatInput.jsx

import React, { useState, useRef, useEffect } from 'react';
import { parseCommand, isValidCommand } from '../../utils/commandParser';
import './ChatInput.css';

const ChatInput = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('');
  const [showCommandHint, setShowCommandHint] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    // Check if message starts with / to show command hint
    if (message.startsWith('/')) {
      const parsed = parseCommand(message);
      setShowCommandHint(parsed.isCommand && !isValidCommand(parsed.command));
    } else {
      setShowCommandHint(false);
    }
  }, [message]);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (message.trim() === '' || disabled) return;
    
    onSendMessage(message.trim());
    setMessage('');
    
    // Focus back on input
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleKeyDown = (e) => {
    // Send on Enter, but allow Shift+Enter for new line
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const insertCommand = (command) => {
    setMessage(`/${command} `);
    inputRef.current?.focus();
  };

  return (
    <div className="chat-input-container">
      {showCommandHint && (
        <div className="command-hint">
          Unknown command. Available: /remember, /memories, /forget, /help
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="chat-input-form">
        <div className="input-wrapper">
          <textarea
            ref={inputRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Rick about your students, grades, or use /commands..."
            disabled={disabled}
            rows={1}
            className="chat-input"
          />
          
          <button 
            type="submit" 
            disabled={disabled || message.trim() === ''}
            className="send-button"
          >
            {disabled ? '...' : '→'}
          </button>
        </div>
      </form>
      
      <div className="quick-commands">
        <button 
          onClick={() => insertCommand('remember')}
          className="command-button"
          type="button"
        >
          /remember
        </button>
        <button 
          onClick={() => insertCommand('memories')}
          className="command-button"
          type="button"
        >
          /memories
        </button>
        <button 
          onClick={() => insertCommand('help')}
          className="command-button"
          type="button"
        >
          /help
        </button>
      </div>
    </div>
  );
};

export default ChatInput;
