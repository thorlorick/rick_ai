"""
Rick_AI Backend Server with OpenRouter
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
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

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

app = FastAPI(title="Rick_AI Backend", version="2.0.0")

# Initialize memory systems
memory = ConversationMemory()
vector_memory = VectorMemory()

# Initialize OpenRouter client
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("⚠ WARNING: OPENROUTER_API_KEY not found in .env file")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Model configuration
MODEL_NAME = "nvidia/nemotron-nano-9b-v2:free"  # Free tier, upgrade to paid if needed
# MODEL_NAME = "nvidia/nemotron-nano-9b-v2"  # Paid tier (better quality/speed)

# ============================================================================
# CORS Configuration
# ============================================================================


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://thorlorick.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],

)

@app.options("/chat")
async def chat_options():
    """Handle CORS preflight"""
    return {}

# ============================================================================
# Models / Schemas
# ============================================================================

class ChatMessage(BaseModel):
    role: str
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
# LLM Engine (OpenRouter)
# ============================================================================

class OpenRouterEngine:
    """Handles interaction with OpenRouter API"""
    
    def __init__(self):
        self.model = MODEL_NAME
        print(f"✓ Using model: {self.model}")
    
    def build_prompt_messages(
        self, 
        message: str, 
        history: List[ChatMessage],
        conversation_id: Optional[str] = None
    ) -> List[Dict]:
        """Build messages array for OpenRouter API with memory and calendar"""
        
        # System message
        system_content = """You are Rick, a skilled coding assistant with access to the user's Google Calendar and memory of past conversations.

You help users with:
- Writing clean, efficient code
- Debugging and explaining code
- Answering programming questions
- Providing best practices and patterns
- Checking their calendar when asked
- Remembering past conversations

When writing code, use markdown code blocks with the language specified.
Keep responses concise but thorough. Be helpful and encouraging."""

        # Check for calendar query
        calendar_keywords = ['calendar', 'schedule', 'meeting', 'event', 'appointment', 'today', 'tomorrow', 'this week']
        is_calendar_query = any(keyword in message.lower() for keyword in calendar_keywords)
        
        # Add calendar context
        if is_calendar_query and CALENDAR_ENABLED and calendar_tool:
            try:
                events = calendar_tool.get_events_this_week()
                if events:
                    system_content += "\n\n=== USER'S CALENDAR ===\n"
                    system_content += calendar_tool.format_events_for_llm(events)
                    system_content += "=======================\n"
            except Exception as e:
                print(f"Error fetching calendar: {e}")
        
        # Get relevant memories
        if message and conversation_id:
            memory_context = vector_memory.get_conversation_context(
                query=message,
                n_results=3,
                exclude_conversation=conversation_id
            )
            if memory_context:
                system_content += "\n\n" + memory_context
        
        # Build messages array
        messages = [{"role": "system", "content": system_content}]
        
        # Add conversation history (last 6 messages)
        for msg in history[-6:]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": message
        })
        
        return messages
    
    async def generate_stream(
        self,
        messages: List[Dict],
        max_tokens: int = 1024,
        temperature: float = 0.7
    ):
        """Generate streaming response from OpenRouter"""
        
        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            print(f"OpenRouter API error: {e}")
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
        """Suggest a filename based on language"""
        
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

# Global engine instance
llm = None

@app.on_event("startup")
async def startup_event():
    """Initialize OpenRouter engine"""
    global llm
    
    if not OPENROUTER_API_KEY:
        print("✗ OpenRouter API key not found!")
        print("  Add OPENROUTER_API_KEY to .env file")
        return
    
    try:
        llm = OpenRouterEngine()
        print("✓ Rick_AI backend ready with OpenRouter!")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "engine": "openrouter",
        "model": MODEL_NAME,
        "calendar_enabled": CALENDAR_ENABLED,
        "message": "Rick_AI Backend API"
    }

@app.post("/chat")
async def chat_endpoint(request: ChatRequest, conversation_id: Optional[str] = None):
    """Main chat endpoint with streaming, memory, and calendar support"""

    if llm is None:
        raise HTTPException(status_code=503, detail="LLM engine not initialized")
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=503, detail="OpenRouter API key not configured")

    # Use provided conversation_id or create a new one
    conversation_id = conversation_id or f"conv-{datetime.now().timestamp()}"

    async def event_generator():
        """Generate streaming SSE events"""

        try:
            # Store user message in vector memory
            vector_memory.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
                timestamp=datetime.now().isoformat()
            )

            # Build messages for LLM
            messages = await asyncio.to_thread(
                llm.build_prompt_messages,
                request.message,
                request.conversation_history,
                conversation_id
            )

            # Stream LLM response
            full_response = ""
            async for token in llm.generate_stream(
                messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            ):
                full_response += token
                data = json.dumps({"type": "token", "content": token})
                yield f"data: {data}\n\n"

            # Store assistant response in vector memory
            vector_memory.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
                timestamp=datetime.now().isoformat()
            )

            # Extract and send artifacts
            artifacts = ArtifactParser.extract_artifacts(full_response)
            for artifact in artifacts:
                data = json.dumps({"type": "artifact", "artifact": artifact.dict()})
                yield f"data: {data}\n\n"

            # Completion
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)})
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
        "engine": "openrouter",
        "model": MODEL_NAME,
        "calendar_enabled": CALENDAR_ENABLED,
        "api_key_configured": bool(OPENROUTER_API_KEY),
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# Memory Endpoints
# ============================================================================

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
    """Get today's events"""
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
    """Get this week's events"""
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
# Run with: uvicorn main:app --host 0.0.0.0 --port 8000
# ============================================================================
