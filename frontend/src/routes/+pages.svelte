<script>
  import { onMount } from 'svelte';
  import ChatPanel from '$lib/ChatPanel.svelte';
  import ArtifactPanel from '$lib/ArtifactPanel.svelte';
  
  let messages = [];
  let artifacts = [];
  let isGenerating = false;
  
  // Handle new message from ChatPanel
  async function handleSendMessage(event) {
    const userMessage = event.detail;
    
    // Add user message
    messages = [...messages, {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }];
    
    // Start streaming response
    isGenerating = true;
    await streamResponse(userMessage);
    isGenerating = false;
  }
  
  async function streamResponse(message) {
    const API_URL = 'http://localhost:8000';
    
    // Prepare request
    const payload = {
      message: message,
      conversation_history: messages.slice(-6), // Last 6 messages
      max_tokens: 1024,
      temperature: 0.7
    };
    
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      let assistantMessage = {
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString()
      };
      
      // Add placeholder for assistant message
      messages = [...messages, assistantMessage];
      const messageIndex = messages.length - 1;
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        // Decode chunk
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            
            if (data.type === 'token') {
              // Append token to message
              messages[messageIndex].content += data.content;
              messages = messages; // Trigger reactivity
            } else if (data.type === 'artifact') {
              // Add artifact
              artifacts = [...artifacts, data.artifact];
            } else if (data.type === 'done') {
              // Stream complete
              return;
            } else if (data.type === 'error') {
              console.error('Stream error:', data.message);
              messages[messageIndex].content += `\n\n[Error: ${data.message}]`;
              messages = messages;
              return;
            }
          }
        }
      }
    } catch (error) {
      console.error('Fetch error:', error);
      // Add error message
      messages = [...messages, {
        role: 'assistant',
        content: `Error connecting to backend: ${error.message}`,
        timestamp: new Date().toISOString()
      }];
    }
  }
  
  function handleClearChat() {
    messages = [];
    artifacts = [];
  }
  
  function handleDeleteArtifact(event) {
    const artifactId = event.detail;
    artifacts = artifacts.filter(a => a.id !== artifactId);
  }
</script>

<div class="app-container">
  <header>
    <h1>🤖 Rick_AI</h1>
    <p>Your Personal Coding Assistant</p>
  </header>
  
  <main class="main-content">
    <div class="chat-section">
      <ChatPanel 
        {messages} 
        {isGenerating}
        on:sendMessage={handleSendMessage}
        on:clearChat={handleClearChat}
      />
    </div>
    
    <div class="artifact-section">
      <ArtifactPanel 
        {artifacts}
        on:deleteArtifact={handleDeleteArtifact}
      />
    </div>
  </main>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0f0f0f;
    color: #e0e0e0;
  }
  
  .app-container {
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  
  header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    padding: 1.5rem 2rem;
    border-bottom: 1px solid #2a2a3e;
  }
  
  header h1 {
    margin: 0;
    font-size: 1.8rem;
    font-weight: 700;
    color: #fff;
  }
  
  header p {
    margin: 0.25rem 0 0 0;
    font-size: 0.9rem;
    color: #a0a0b0;
  }
  
  .main-content {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
    overflow: hidden;
  }
  
  .chat-section {
    border-right: 1px solid #2a2a3e;
    overflow: hidden;
  }
  
  .artifact-section {
    overflow: hidden;
  }
  
  @media (max-width: 1024px) {
    .main-content {
      grid-template-columns: 1fr;
      grid-template-rows: 1fr 1fr;
    }
    
    .chat-section {
      border-right: none;
      border-bottom: 1px solid #2a2a3e;
    }
  }
</style>
