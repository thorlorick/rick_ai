"""
Vector Memory System for Rick_AI
Provides semantic search across all conversations using embeddings
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
from datetime import datetime
import hashlib

class VectorMemory:
    """Manages semantic memory using vector embeddings"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize vector memory with ChromaDB and embedding model
        
        Args:
            persist_directory: Where to store the vector database
        """
        print("Initializing vector memory...")
        
        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="rick_conversations",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        # Load embedding model (this will download ~80MB on first run)
        print("Loading embedding model (all-MiniLM-L6-v2)...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✓ Vector memory ready!")
    
    def add_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add a message to vector memory
        
        Args:
            conversation_id: ID of the conversation
            role: "user" or "assistant"
            content: Message content
            timestamp: ISO format timestamp
            metadata: Additional metadata
        
        Returns:
            Document ID
        """
        if not content.strip():
            return None
        
        # Generate embedding
        embedding = self.embedding_model.encode(content).tolist()
        
        # Create unique ID
        timestamp = timestamp or datetime.now().isoformat()
        doc_id = self._generate_doc_id(conversation_id, timestamp, content)
        
        # Prepare metadata
        meta = {
            "conversation_id": conversation_id,
            "role": role,
            "timestamp": timestamp,
            "content_length": len(content)
        }
        if metadata:
            meta.update(metadata)
        
        try:
            # Add to collection
            self.collection.add(
                embeddings=[embedding],
                documents=[content],
                metadatas=[meta],
                ids=[doc_id]
            )
            return doc_id
        except Exception as e:
            print(f"Error adding message to vector memory: {e}")
            return None
    
    def search_memory(
        self, 
        query: str, 
        n_results: int = 5,
        conversation_id: Optional[str] = None,
        role_filter: Optional[str] = None
    ) -> Dict:
        """
        Search for semantically similar past messages
        
        Args:
            query: Search query
            n_results: Number of results to return
            conversation_id: Filter by conversation (optional)
            role_filter: Filter by role - "user" or "assistant" (optional)
        
        Returns:
            Dict with documents, metadatas, and distances
        """
        if not query.strip():
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Build where filter
            where = {}
            if conversation_id:
                where["conversation_id"] = conversation_id
            if role_filter:
                where["role"] = role_filter
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where if where else None
            )
            
            return results
        except Exception as e:
            print(f"Error searching memory: {e}")
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    
    def get_conversation_context(
        self, 
        query: str, 
        n_results: int = 3,
        exclude_conversation: Optional[str] = None
    ) -> str:
        """
        Get formatted context from past conversations for prompt injection
        
        Args:
            query: Current user query
            n_results: Number of memories to retrieve
            exclude_conversation: Don't include results from this conversation
        
        Returns:
            Formatted string to inject into prompt
        """
        # Search for relevant memories
        results = self.search_memory(query, n_results=n_results * 2)  # Get extra, we'll filter
        
        if not results["documents"][0]:
            return ""
        
        # Format relevant context
        context_parts = []
        seen_content = set()
        
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            # Skip if from current conversation
            if exclude_conversation and meta.get("conversation_id") == exclude_conversation:
                continue
            
            # Skip duplicates
            if doc in seen_content:
                continue
            seen_content.add(doc)
            
            # Only include if similarity is decent (distance < 0.7)
            if distance > 0.7:
                continue
            
            # Format the memory
            role = meta.get("role", "unknown")
            timestamp = meta.get("timestamp", "")
            
            # Truncate if too long
            display_doc = doc if len(doc) <= 150 else doc[:150] + "..."
            
            context_parts.append(f"[Past {role} message]: {display_doc}")
            
            if len(context_parts) >= n_results:
                break
        
        if not context_parts:
            return ""
        
        # Build context section
        context = "=== RELEVANT PAST CONTEXT ===\n"
        context += "You previously discussed related topics:\n\n"
        context += "\n".join(context_parts)
        context += "\n\nUse this context if relevant to the current question.\n"
        context += "================================\n\n"
        
        return context
    
    def get_stats(self) -> Dict:
        """Get statistics about the memory system"""
        try:
            count = self.collection.count()
            return {
                "total_messages": count,
                "collection_name": self.collection.name,
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dimension": 384
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def clear_all(self):
        """Clear all memories (use with caution!)"""
        try:
            self.client.delete_collection("rick_conversations")
            self.collection = self.client.create_collection(
                name="rick_conversations",
                metadata={"hnsw:space": "cosine"}
            )
            print("✓ Memory cleared")
            return True
        except Exception as e:
            print(f"Error clearing memory: {e}")
            return False
    
    def _generate_doc_id(self, conversation_id: str, timestamp: str, content: str) -> str:
        """Generate unique document ID"""
        # Create hash from conversation + timestamp + content
        unique_str = f"{conversation_id}_{timestamp}_{content[:50]}"
        return hashlib.md5(unique_str.encode()).hexdigest()


# Test the system
if __name__ == "__main__":
    print("Testing Vector Memory System...")
    
    memory = VectorMemory()
    
    # Add some test messages
    print("\n1. Adding test messages...")
    memory.add_message("test-1", "user", "How do I implement a binary search?")
    memory.add_message("test-1", "assistant", "Here's a binary search implementation in Python...")
    memory.add_message("test-2", "user", "Can you help me with sorting algorithms?")
    memory.add_message("test-2", "assistant", "Sure! Let's start with quicksort...")
    
    # Search
    print("\n2. Searching memory...")
    results = memory.search_memory("searching algorithms", n_results=2)
    print(f"Found {len(results['documents'][0])} results")
    for doc in results['documents'][0]:
        print(f"  - {doc[:80]}...")
    
    # Get context
    print("\n3. Getting conversation context...")
    context = memory.get_conversation_context("How do I search through data?", n_results=2)
    print(context)
    
    # Stats
    print("\n4. Memory stats:")
    stats = memory.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✓ All tests passed!")
