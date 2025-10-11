<script>
  import { createEventDispatcher, afterUpdate } from 'svelte';
  import { marked } from 'marked';
  
  export let messages = [];
  export let isGenerating = false;
  
  let inputMessage = '';
  let chatContainer;
  
  const dispatch = createEventDispatcher();
  
  // Auto-scroll to bottom when messages update
  afterUpdate(() => {
    if (chatContainer) {
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  });
  
  function handleSubmit() {
    if (inputMessage.trim() && !isGenerating) {
      dispatch('sendMessage', inputMessage);
      inputMessage = '';
    }
  }
  
  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }
  
  function handleClear() {
    if (confirm('Clear all messages?')) {
      dispatch('clearChat');
    }
  }
  
  function formatMessage(content) {
    return marked.parse(content);
  }
</script>

<div class="chat-panel">
  <div class="chat-header">
    <h2>Conversation</h2>
    <button 
      class="clear-btn" 
      on:click={handleClear}
      disabled={messages.length === 0}
    >
      Clear
    </button>
  </div>
  
  <div class="messages" bind:this={chatContainer}>
    {#if messages.length === 0}
      <div class="empty-state">
        <div class="empty-icon">💬</div>
        <h3>Start a conversation</h3>
        <p>Ask me anything about coding!</p>
        <div class="suggestions">
          <button on:click={() => inputMessage = "Write a Python function to check if a number is prime"}>
            Prime number checker
          </button>
          <button on:click={() => inputMessage = "Create a REST API with FastAPI"}>
            FastAPI REST API
          </button>
          <button on:click={() => inputMessage = "Explain async/await in JavaScript"}>
            Async/await guide
          </button>
        </div>
      </div>
    {:else}
      {#each messages as message}
        <div class="message {message.role}">
          <div class="message-header">
            <span class="role-badge">{message.role === 'user' ? 'You' : 'Rick'}</span>
            <span class="timestamp">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <div class="message-content">
            {@html formatMessage(message.content)}
          </div>
        </div>
      {/each}
      
      {#if isGenerating}
        <div class="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
      {/if}
    {/if}
  </div>
  
  <div class="input-area">
    <textarea
      bind:value={inputMessage}
      on:keydown={handleKeydown}
      placeholder="Ask Rick anything..."
      disabled={isGenerating}
      rows="3"
    ></textarea>
    <button 
      class="send-btn" 
      on:click={handleSubmit}
      disabled={!inputMessage.trim() || isGenerating}
    >
      {isGenerating ? '⏳' : '➤'} Send
    </button>
  </div>
</div>

<style>
  .chat-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #1a1a1a;
  }
  
  .chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #2a2a3e;
  }
  
  .chat-header h2 {
    margin: 0;
    font-size: 1.2rem;
    color: #fff;
  }
  
  .clear-btn {
    padding: 0.4rem 1rem;
    background: transparent;
    border: 1px solid #3a3a4e;
    color: #e0e0e0;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s;
  }
  
  .clear-btn:hover:not(:disabled) {
    background: #2a2a3e;
    border-color: #ff6b6b;
    color: #ff6b6b;
  }
  
  .clear-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
  }
  
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
    color: #7a7a8a;
  }
  
  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }
  
  .empty-state h3 {
    margin: 0 0 0.5rem 0;
    color: #e0e0e0;
  }
  
  .suggestions {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-top: 2rem;
  }
  
  .suggestions button {
    padding: 0.75rem 1.5rem;
    background: #2a2a3e;
    border: 1px solid #3a3a4e;
    color: #e0e0e0;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.9rem;
  }
  
  .suggestions button:hover {
    background: #3a3a4e;
    border-color: #4a9eff;
    transform: translateY(-2px);
  }
  
  .message {
    margin-bottom: 1.5rem;
    animation: fadeIn 0.3s ease-in;
  }
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  .message-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
  }
  
  .role-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
  }
  
  .message.user .role-badge {
    background: #4a9eff;
    color: #fff;
  }
  
  .message.assistant .role-badge {
    background: #2ecc71;
    color: #fff;
  }
  
  .timestamp {
    font-size: 0.75rem;
    color: #7a7a8a;
  }
  
  .message-content {
    padding: 1rem;
    border-radius: 8px;
    line-height: 1.6;
  }
  
  .message.user .message-content {
    background: #2a2a3e;
    color: #e0e0e0;
  }
  
  .message.assistant .message-content {
    background: #1e1e2e;
    color: #e0e0e0;
    border-left: 3px solid #2ecc71;
  }
  
  .message-content :global(pre) {
    background: #0d0d0d;
    padding: 1rem;
    border-radius: 6px;
    overflow-x: auto;
    border: 1px solid #2a2a3e;
  }
  
  .message-content :global(code) {
    font-family: 'Fira Code', 'Courier New', monospace;
    font-size: 0.9rem;
  }
  
  .message-content :global(p) {
    margin: 0.5rem 0;
  }
  
  .typing-indicator {
    display: flex;
    gap: 0.4rem;
    padding: 1rem;
  }
  
  .typing-indicator span {
    width: 8px;
    height: 8px;
    background: #4a9eff;
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out;
  }
  
  .typing-indicator span:nth-child(1) {
    animation-delay: -0.32s;
  }
  
  .typing-indicator span:nth-child(2) {
    animation-delay: -0.16s;
  }
  
  @keyframes bounce {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1); }
  }
  
  .input-area {
    padding: 1rem 1.5rem;
    border-top: 1px solid #2a2a3e;
    background: #1a1a1a;
    display: flex;
    gap: 1rem;
  }
  
  textarea {
    flex: 1;
    padding: 0.75rem;
    background: #2a2a3e;
    border: 1px solid #3a3a4e;
    border-radius: 8px;
    color: #e0e0e0;
    font-family: inherit;
    font-size: 0.95rem;
    resize: none;
    transition: border-color 0.2s;
  }
  
  textarea:focus {
    outline: none;
    border-color: #4a9eff;
  }
  
  textarea:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .send-btn {
    padding: 0.75rem 1.5rem;
    background: #4a9eff;
    border: none;
    color: #fff;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.95rem;
    transition: all 0.2s;
    white-space: nowrap;
  }
  
  .send-btn:hover:not(:disabled) {
    background: #3a8eef;
    transform: translateY(-2px);
  }
  
  .send-btn:disabled {
    background: #3a3a4e;
    cursor: not-allowed;
    transform: none;
  }
</style>
