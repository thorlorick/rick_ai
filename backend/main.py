"""
Rick_AI Backend Server
FastAPI server with streaming LLM responses, vector memory, and calendar integration
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import json
import re
from datetime import datetime
import asyncio

# Import memory managers
from memory import ConversationMemory
from vector_memory import VectorMemory

# Import calendar tool
try:
    from calendar_tool import GoogleCalendarTool
    calendar_tool = GoogleCalendarTool()
    CALENDAR_ENABLED = True
    print("✓ Google Calendar connected!")
except Exception as e:
    calendar_tool = None
    CALENDAR_ENABLED = False
    print(f"⚠ Google Calendar not available: {e}")

app = FastAPI(title="Rick_AI Backend", version="1.0.0")

# Initialize memory systems
memory = ConversationMemory()
vector_memory = VectorMemory()

# Global LLM instance (initialized on startup)
llm = None

# ============================================================================
# CORS Configuration
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.options("/chat")
async def chat_options():
    """Handle CORS preflight for chat endpoint"""
    return {}

# ============================================================================
# Models / Schemas
# ============================================================================

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []
    max_tokens: int = 1024
    temperature: float = 0.7

class Artifact(BaseModel):
    id: str
    language: str
    code: str
    filename: Optional[str] = None

# ============================================================================
# LLM Engine
# ============================================================================

class LLMEngine:
    """Handles interaction with the language model"""
    
    def __init__(self, model_path: str, n_ctx: int = 4096):
        try:
            from llama_cpp import Llama
            self.llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_threads=4,
                n_batch=512,
                verbose=False
            )
            print(f"✓ Model loaded: {model_path}")
        except Exception as e:
            print(f"✗ Failed to load model: {e}")
            raise
    
    def build_prompt(self, message: str, history: List[ChatMessage], conversation_id: Optional[str] = None) -> str:
        """Build a prompt with conversation history, semantic memory, and calendar context"""
        
        # System prompt
        system = """You are Rick, a skilled coding assistant with access to the user's Google Calendar.

You help users with:
- Writing clean, efficient code
- Debugging and explaining code
- Answering programming questions
- Providing best practices and patterns
- Checking their calendar when asked
- Remembering past conversations

When writing code, use markdown code blocks with the language specified.
Keep responses concise but thorough. Be helpful and encouraging.

If the user asks about their calendar/schedule/meetings, you have access to that information.
If the user references past conversations or asks you to remember something, you can recall it from your memory."""
        
        prompt = f"{system}\n\n"
        
        # Check if this is a calendar query
        calendar_keywords = ['calendar', 'schedule', 'meeting', 'event', 'appointment', 'today', 'tomorrow', 'this week']
        is_calendar_query = any(keyword in message.lower() for keyword in calendar_keywords)
        
        # Add calendar context if relevant
        if is_calendar_query and CALENDAR_ENABLED and calendar_tool:
            try:
                events = calendar_tool.get_events_this_week()
                if events:
                    calendar_context = "=== USER'S CALENDAR ===\n"
                    calendar_context += calendar_tool.format_events_for_llm(events)
                    calendar_context += "=======================\n\n"
                    prompt += calendar_context
            except Exception as e:
                print(f"Error fetching calendar: {e}")
        
        # Get relevant memories from past conversations
        if message and conversation_id:
            memory_context = vector_memory.get_conversation_context(
                query=message,
                n_results=3,
                exclude_conversation=conversation_id
            )
            if memory_context:
                prompt += memory_context
        
        # Add recent history from current conversation
        for msg in history[-6:]:
            role = msg.role.capitalize()
            prompt += f"{role}: {msg.content}\n\n"
        
        # Add current message
        prompt += f"User: {message}\n\nAssistant:"
        
        return prompt
    
    async def generate_stream(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7):
        """Generate streaming response"""
        
        try:
            stream = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
                stream=True,
                stop=["User:", "Human:"]
            )
            
            for output in stream:
                if output and 'choices' in output:
                    token = output['choices'][0]['text']
                    yield token
                    await asyncio.sleep(0)
                    
        except Exception as e:
            print(f"Generation error: {e}")
            yield f"\n\n[Error: {str(e)}]"

# ============================================================================
# Artifact Parser
# ============================================================================

class ArtifactParser:
    """Extract code artifacts from LLM responses"""
    
    @staticmethod
    def extract_artifacts(text: str) -> List[Artifact]:
        """Find all code blocks in markdown format"""
        
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.finditer(pattern, text, re.DOTALL)
        
        artifacts = []
        for i, match in enumerate(matches):
            language = match.group(1) or "text"
            code = match.group(2).strip()
            
            artifact = Artifact(
                id=f"artifact_{i}_{datetime.now().timestamp()}",
                language=language,
                code=code,
                filename=ArtifactParser._suggest_filename(language, code)
            )
            artifacts.append(artifact)
        
        return artifacts
    
    @staticmethod
    def _suggest_filename(language: str, code: str) -> str:
        """Suggest a filename based on language and content"""
        
        filename_patterns = [
            r'#\s*filename:\s*(\S+)',
            r'//\s*filename:\s*(\S+)',
        ]
        
        for pattern in filename_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                return match.group(1)
        
        extensions = {
            "python": "script.py",
            "javascript": "script.js",
            "typescript": "script.ts",
            "html": "index.html",
            "css": "styles.css",
            "rust": "main.rs",
            "go": "main.go",
            "java": "Main.java",
            "cpp": "main.cpp",
            "c": "main.c",
        }
        
        return extensions.get(language.lower(), f"code.{language}")

# ============================================================================
# API Endpoints
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize LLM on server start"""
    global llm
    
    model_path = "../models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
    
    try:
        llm = LLMEngine(model_path=model_path)
        print("✓ Rick_AI backend ready!")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        print("⚠ Server will run but /chat endpoint will fail")

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "model_loaded": llm is not None,
        "calendar_enabled": CALENDAR_ENABLED,
        "message": "Rick_AI Backend API"
    }

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint with streaming support, memory, and calendar
    Returns Server-Sent Events (SSE) stream
    """
    
    if llm is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Generate conversation ID
    conversation_id = f"conv-{datetime.now().timestamp()}"
    
    async def event_generator():
        """Generate SSE events"""
        
        try:
            # Add user message to vector memory
            vector_memory.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                timestamp=datetime.now().isoformat()
            )
            
            # Build prompt with memory and calendar context
            prompt = llm.build_prompt(
                request.message, 
                request.conversation_history,
                conversation_id=conversation_id
            )
            
            # Accumulate response
            full_response = ""
            
            # Stream tokens
            async for token in llm.generate_stream(
                prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            ):
                full_response += token
                
                # Send token as SSE
                data = json.dumps({"type": "token", "content": token})
                yield f"data: {data}\n\n"
            
            # Add assistant response to vector memory
            vector_memory.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
                timestamp=datetime.now().isoformat()
            )
            
            # Extract and send artifacts
            artifacts = ArtifactParser.extract_artifacts(full_response)
            if artifacts:
                for artifact in artifacts:
                    data = json.dumps({
                        "type": "artifact",
                        "artifact": artifact.dict()
                    })
                    yield f"data: {data}\n\n"
            
            # Send completion signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            error_data = json.dumps({
                "type": "error",
                "message": str(e)
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "model_loaded": llm is not None,
        "calendar_enabled": CALENDAR_ENABLED,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# Memory / Conversation Endpoints
# ============================================================================

@app.post("/conversations/save")
async def save_conversation(conversation_id: str, messages: List[ChatMessage], title: Optional[str] = None):
    """Save a conversation"""
    metadata = {"title": title} if title else {}
    success = memory.save_conversation(
        conversation_id,
        [msg.dict() for msg in messages],
        metadata
    )
    
    if success:
        return {"status": "saved", "conversation_id": conversation_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to save conversation")

@app.get("/conversations/list")
async def list_conversations(limit: int = 50):
    """List all saved conversations"""
    conversations = memory.list_conversations(limit)
    return {"conversations": conversations}

@app.get("/conversations/{conversation_id}")
async def load_conversation(conversation_id: str):
    """Load a specific conversation"""
    conversation = memory.load_conversation(conversation_id)
    
    if conversation:
        return conversation
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    success = memory.delete_conversation(conversation_id)
    
    if success:
        return {"status": "deleted", "conversation_id": conversation_id}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")

@app.get("/conversations/stats")
async def get_storage_stats():
    """Get storage statistics"""
    file_stats = memory.get_storage_stats()
    vector_stats = vector_memory.get_stats()
    
    return {
        "file_storage": file_stats,
        "vector_memory": vector_stats
    }

@app.post("/memory/search")
async def search_memory(query: str, n_results: int = 5):
    """Search vector memory"""
    results = vector_memory.search_memory(query, n_results=n_results)
    
    # Format results
    formatted = []
    if results["documents"][0]:
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            formatted.append({
                "content": doc,
                "metadata": meta,
                "similarity": 1 - distance
            })
    
    return {"results": formatted, "count": len(formatted)}

# ============================================================================
# Calendar Endpoints
# ============================================================================

@app.get("/calendar/today")
async def get_calendar_today():
    """Get today's calendar events"""
    if not CALENDAR_ENABLED:
        raise HTTPException(status_code=503, detail="Calendar not available")
    
    try:
        events = calendar_tool.get_events_today()
        return {
            "events": events,
            "count": len(events),
            "formatted": calendar_tool.format_events_for_llm(events)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/calendar/week")
async def get_calendar_week():
    """Get this week's calendar events"""
    if not CALENDAR_ENABLED:
        raise HTTPException(status_code=503, detail="Calendar not available")
    
    try:
        events = calendar_tool.get_events_this_week()
        return {
            "events": events,
            "count": len(events),
            "formatted": calendar_tool.format_events_for_llm(events)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
# ============================================================================
