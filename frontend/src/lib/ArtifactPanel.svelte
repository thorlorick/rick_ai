<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { browser } from '$app/environment';
  
  let Prism;
  
  export let artifacts = [];
  
  let selectedArtifact = null;
  let copySuccess = {};
  
  const dispatch = createEventDispatcher();
  
  // Load Prism.js only in the browser
  onMount(async () => {
    if (browser) {
      const prismModule = await import('prismjs');
      Prism = prismModule.default;
      
      // Import languages
      await import('prismjs/components/prism-python');
      await import('prismjs/components/prism-javascript');
      await import('prismjs/components/prism-typescript');
      await import('prismjs/components/prism-rust');
      await import('prismjs/components/prism-go');
      await import('prismjs/components/prism-java');
      await import('prismjs/components/prism-css');
      await import('prismjs/components/prism-bash');
      
      // Import theme CSS
      await import('prismjs/themes/prism-tomorrow.css');
    }
  });
  
  $: if (artifacts.length > 0 && !selectedArtifact) {
    selectedArtifact = artifacts[artifacts.length - 1];
  }
  
  function selectArtifact(artifact) {
    selectedArtifact = artifact;
  }
  
  async function copyToClipboard(artifactId, code) {
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(code);
      } else {
        // Fallback for older browsers or non-HTTPS
        const textArea = document.createElement('textarea');
        textArea.value = code;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      
      copySuccess[artifactId] = true;
      setTimeout(() => {
        copySuccess[artifactId] = false;
        copySuccess = copySuccess;
      }, 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      alert('Copy failed. Please select and copy manually.');
    }
  }
  
  function downloadArtifact(artifact) {
    const blob = new Blob([artifact.code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = artifact.filename || `code.${artifact.language}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
  
  function deleteArtifact(artifactId) {
    if (selectedArtifact?.id === artifactId) {
      const index = artifacts.findIndex(a => a.id === artifactId);
      selectedArtifact = artifacts[index - 1] || artifacts[index + 1] || null;
    }
    dispatch('deleteArtifact', artifactId);
  }
  
  function getHighlightedCode(code, language) {
    if (!Prism || !browser) return code;
    
    try {
      const grammar = Prism.languages[language] || Prism.languages.text;
      return Prism.highlight(code, grammar, language);
    } catch (e) {
      return code;
    }
  }
</script>

<div class="artifact-panel">
  <div class="artifact-header">
    <h2>Code Artifacts</h2>
    <span class="count">{artifacts.length}</span>
  </div>
  
  {#if artifacts.length === 0}
    <div class="empty-state">
      <div class="empty-icon">📦</div>
      <h3>No artifacts yet</h3>
      <p>Code snippets from Rick will appear here</p>
    </div>
  {:else}
    <div class="artifact-content">
      <div class="artifact-list">
        {#each artifacts as artifact, i}
          <button
            class="artifact-item"
            class:active={selectedArtifact?.id === artifact.id}
            on:click={() => selectArtifact(artifact)}
          >
            <div class="artifact-icon">
              {#if artifact.language === 'python'}
                🐍
              {:else if artifact.language === 'javascript' || artifact.language === 'typescript'}
                📜
              {:else if artifact.language === 'rust'}
                🦀
              {:else if artifact.language === 'go'}
                🐹
              {:else if artifact.language === 'html'}
                🌐
              {:else}
                💾
              {/if}
            </div>
            <div class="artifact-info">
              <div class="artifact-name">{artifact.filename}</div>
              <div class="artifact-lang">{artifact.language}</div>
            </div>
          </button>
        {/each}
      </div>
      
      {#if selectedArtifact}
        <div class="artifact-viewer">
          <div class="viewer-header">
            <div class="file-info">
              <span class="filename">{selectedArtifact.filename}</span>
              <span class="language-badge">{selectedArtifact.language}</span>
            </div>
            <div class="actions">
              <button
                class="action-btn"
                on:click={() => copyToClipboard(selectedArtifact.id, selectedArtifact.code)}
                title="Copy to clipboard"
              >
                {#if copySuccess[selectedArtifact.id]}
                  ✓ Copied
                {:else}
                  📋 Copy
                {/if}
              </button>
              <button
                class="action-btn"
                on:click={() => downloadArtifact(selectedArtifact)}
                title="Download file"
              >
                ⬇️ Download
              </button>
              <button
                class="action-btn delete"
                on:click={() => deleteArtifact(selectedArtifact.id)}
                title="Delete artifact"
              >
                🗑️ Delete
              </button>
            </div>
          </div>
          
          <div class="code-container">
            <pre><code class="language-{selectedArtifact.language}">{@html getHighlightedCode(selectedArtifact.code, selectedArtifact.language)}</code></pre>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .artifact-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: #1a1a1a;
  }
  
  .artifact-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #2a2a3e;
  }
  
  .artifact-header h2 {
    margin: 0;
    font-size: 1.2rem;
    color: #fff;
  }
  
  .count {
    padding: 0.25rem 0.75rem;
    background: #4a9eff;
    color: #fff;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 600;
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
  
  .artifact-content {
    flex: 1;
    display: grid;
    grid-template-columns: 250px 1fr;
    overflow: hidden;
  }
  
  .artifact-list {
    border-right: 1px solid #2a2a3e;
    overflow-y: auto;
    padding: 0.5rem;
  }
  
  .artifact-item {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: 0.5rem;
    text-align: left;
  }
  
  .artifact-item:hover {
    background: #2a2a3e;
    border-color: #3a3a4e;
  }
  
  .artifact-item.active {
    background: #2a2a3e;
    border-color: #4a9eff;
  }
  
  .artifact-icon {
    font-size: 1.5rem;
  }
  
  .artifact-info {
    flex: 1;
    min-width: 0;
  }
  
  .artifact-name {
    font-size: 0.9rem;
    color: #e0e0e0;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .artifact-lang {
    font-size: 0.75rem;
    color: #7a7a8a;
    text-transform: uppercase;
  }
  
  .artifact-viewer {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  
  .viewer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #2a2a3e;
    background: #1e1e2e;
  }
  
  .file-info {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  
  .filename {
    font-weight: 600;
    color: #e0e0e0;
  }
  
  .language-badge {
    padding: 0.25rem 0.75rem;
    background: #3a3a4e;
    color: #4a9eff;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
  }
  
  .actions {
    display: flex;
    gap: 0.5rem;
  }
  
  .action-btn {
    padding: 0.5rem 1rem;
    background: #2a2a3e;
    border: 1px solid #3a3a4e;
    color: #e0e0e0;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.2s;
    white-space: nowrap;
  }
  
  .action-btn:hover {
    background: #3a3a4e;
    transform: translateY(-2px);
  }
  
  .action-btn.delete:hover {
    border-color: #ff6b6b;
    color: #ff6b6b;
  }
  
  .code-container {
    flex: 1;
    overflow: auto;
    padding: 1.5rem;
    background: #0d0d0d;
  }
  
  pre {
    margin: 0;
    padding: 1rem;
    background: #1a1a1a;
    border-radius: 8px;
    border: 1px solid #2a2a3e;
    overflow-x: auto;
  }
  
  code {
    font-family: 'Fira Code', 'Courier New', monospace;
    font-size: 0.9rem;
    line-height: 1.6;
  }
  
  @media (max-width: 768px) {
    .artifact-content {
      grid-template-columns: 1fr;
      grid-template-rows: auto 1fr;
    }
    
    .artifact-list {
      border-right: none;
      border-bottom: 1px solid #2a2a3e;
      max-height: 200px;
    }
  }
</style>
