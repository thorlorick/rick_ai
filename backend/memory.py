"""
Conversation Memory Manager for Rick_AI
Handles saving and loading conversation history
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class ConversationMemory:
    """Manages conversation history storage"""
    
    def __init__(self, storage_dir: str = "./conversations"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
    
    def save_conversation(self, conversation_id: str, messages: List[Dict], metadata: Optional[Dict] = None) -> bool:
        """Save a conversation to disk"""
        try:
            conversation_data = {
                "id": conversation_id,
                "messages": messages,
                "metadata": metadata or {},
                "created_at": metadata.get("created_at") if metadata else datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "message_count": len(messages)
            }
            
            filepath = self.storage_dir / f"{conversation_id}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving conversation: {e}")
            return False
    
    def load_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Load a conversation from disk"""
        try:
            filepath = self.storage_dir / f"{conversation_id}.json"
            if not filepath.exists():
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading conversation: {e}")
            return None
    
    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """List all saved conversations"""
        try:
            conversations = []
            
            for filepath in self.storage_dir.glob("*.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        conversations.append({
                            "id": data["id"],
                            "title": self._generate_title(data),
                            "message_count": data.get("message_count", 0),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at")
                        })
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
                    continue
            
            conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return conversations[:limit]
        except Exception as e:
            print(f"Error listing conversations: {e}")
            return []
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        try:
            filepath = self.storage_dir / f"{conversation_id}.json"
            if filepath.exists():
                filepath.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    def _generate_title(self, conversation_data: Dict) -> str:
        """Generate a title from the first user message"""
        messages = conversation_data.get("messages", [])
        
        if "metadata" in conversation_data and "title" in conversation_data["metadata"]:
            return conversation_data["metadata"]["title"]
        
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                return content[:50] + "..." if len(content) > 50 else content
        
        return "Untitled Conversation"
    
    def get_storage_stats(self) -> Dict:
        """Get statistics about stored conversations"""
        try:
            files = list(self.storage_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files)
            
            return {
                "total_conversations": len(files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "storage_dir": str(self.storage_dir.absolute())
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
