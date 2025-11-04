"""
Rick AI - GradeInsight Backend (Ollama Local)
FastAPI server for grade analysis with local LLM
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import json
import os
import uuid
import time
import asyncio
import httpx
from datetime import datetime
from contextlib import asynccontextmanager
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database connection
try:
    from db_connection import GradeInsightDB
    db = GradeInsightDB()
    DB_ENABLED = True
    print("✓ GradeInsight database connected!")
except Exception as e:
    db = None
    DB_ENABLED = False
    print(f"⚠ Database not available: {e}")

# Import vector memory for conversation context
try:
    from vector_memory import VectorMemory
    vector_memory = VectorMemory()
    MEMORY_ENABLED = True
    print("✓ Vector memory initialized!")
except Exception as e:
    vector_memory = None
    MEMORY_ENABLED = False
    print(f"⚠ Vector memory disabled (optional feature): {str(e)[:100]}")

# ============================================================================ #
# Application Metrics
# ============================================================================ #
class AppMetrics:
    def __init__(self):
        self.startup_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.active_conversations = set()
        
    def record_request(self, duration: float):
        self.request_count += 1
        self.total_response_time += duration
        
    def record_error(self):
        self.error_count += 1
        
    def get_stats(self):
        uptime = time.time() - self.startup_time
        avg_response = self.total_response_time / max(self.request_count, 1)
        return {
            "uptime_seconds": round(uptime, 2),
            "requests_processed": self.request_count,
            "errors": self.error_count,
            "avg_response_time_seconds": round(avg_response, 2),
            "active_conversations": len(self.active_conversations)
        }

metrics = AppMetrics()

# ============================================================================ #
# Rate Limiting
# ============================================================================ #
class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < self.window_seconds
        ]
        
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        self.requests[client_id].append(now)
        return True

rate_limiter = RateLimiter(max_requests=60, window_seconds=60)

# ============================================================================ #
# FastAPI App
# ============================================================================ #
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Rick GradeInsight starting up...")
    yield
    print("👋 Rick GradeInsight shutting down...")

app = FastAPI(
    title="Rick GradeInsight Backend",
    version="1.0.0-ollama",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================ #
# Ollama LLM Engine
# ============================================================================ #
class OllamaEngine:
    """Handles interaction with local Ollama for grade analysis"""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.max_context_tokens = 4000
        print(f"✓ Ollama engine configured: {self.model_name}")
        print(f"  Endpoint: {self.base_url}")

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation"""
        return len(text) // 4

    def build_system_prompt(self, teacher_id: int) -> str:
        """Build system prompt for teacher assistant"""
        return f"""You are Rick, an intelligent teaching assistant for GradeInsight. You help teachers analyze student grades and performance.

Your role:
- Analyze student performance data from the database
- Identify struggling students and patterns
- Provide actionable insights for teachers
- Answer questions about grades, assignments, and trends
- Be concise, helpful, and data-driven

Current teacher ID: {teacher_id}

When asked about students or grades:
1. Use the provided database query results
2. Present findings clearly with specific numbers
3. Highlight important patterns or concerns
4. Suggest practical next steps

Available data:
- Student grades and averages
- Assignment completion rates
- Missing assignments
- Grade trends over time
- Teacher notes

Be conversational but professional. Focus on helping teachers make informed decisions about student support."""

    def build_prompt_messages(
        self, 
        message: str, 
        history: List, 
        teacher_id: int,
        query_results: Optional[Dict] = None
    ) -> str:
        """Build prompt for Ollama"""
        # System prompt
        prompt = self.build_system_prompt(teacher_id) + "\n\n"

        # Add query results if available
        if query_results:
            prompt += "=== Database Query Results ===\n"
            prompt += json.dumps(query_results, indent=2, default=str)
            prompt += "\n=== End Results ===\n\n"

        # Add conversation history (last 6 messages)
        prompt += "=== Conversation History ===\n"
        for msg in history[-6:]:
            role = msg['role'].upper()
            content = msg.get('content', '')
            prompt += f"{role}: {content}\n\n"

        # Add current message
        prompt += f"USER: {message}\n\nASSISTANT: "

        return prompt

    async def generate_stream(self, prompt: str, **generation_params):
        """Stream responses from Ollama"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    'POST',
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": True,
                        **generation_params
                    }
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if 'response' in data:
                                    yield data['response']
                                if data.get('done', False):
                                    break
                            except json.JSONDecodeError:
                                continue

        except httpx.ConnectError:
            print("❌ Cannot connect to Ollama. Is it running?")
            yield "\n\n[Error: Cannot connect to Ollama. Run: ollama serve]"
        except Exception as e:
            print(f"❌ Error in streaming: {e}")
            yield f"\n\n[Error: {str(e)}]"

    async def test_connection(self) -> bool:
        """Test if Ollama is accessible"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    model_names = [m['name'] for m in models]
                    print(f"✓ Ollama connected. Available models: {model_names}")
                    
                    # Check if our model is available
                    if self.model_name in model_names:
                        print(f"✓ Model '{self.model_name}' is ready")
                        return True
                    else:
                        print(f"⚠ Model '{self.model_name}' not found. Run: ollama pull {self.model_name}")
                        return False
                return False
        except Exception as e:
            print(f"⚠ Ollama not reachable: {e}")
            return False

# ============================================================================ #
# Request/Response Models
# ============================================================================ #
class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_history: List[ChatMessage] = []
    teacher_id: int = Field(..., gt=0)
    conversation_id: Optional[str] = None
    max_tokens: int = Field(2048, ge=100, le=8192)
    temperature: float = Field(0.7, ge=0.0, le=2.0)

# ============================================================================ #
# Grade Analysis Tools
# ============================================================================ #
def analyze_query_intent(message: str, teacher_id: int) -> Optional[Dict]:
    """Determine if message needs database query and execute it"""
    message_lower = message.lower()
    
    # Check for struggling students query
    if any(word in message_lower for word in ['struggling', 'failing', 'below', 'low grade']):
        print(f"[Tool] Detected: Struggling students query")
        results = db.get_struggling_students(teacher_id)
        return {"query_type": "struggling_students", "results": results}
    
    # Check for specific student query
    if 'student' in message_lower and any(word in message_lower for word in ['id', 'number', '#']):
        import re
        match = re.search(r'(?:id|student|#)\s*(\d+)', message_lower)
        if match:
            student_id = int(match.group(1))
            print(f"[Tool] Detected: Student detail query for ID {student_id}")
            result = db.get_student_detail(teacher_id, student_id)
            return {"query_type": "student_detail", "student_id": student_id, "results": result}
    
    # Check for assignment analysis
    if any(word in message_lower for word in ['assignment', 'hardest', 'difficult', 'lowest']):
        print(f"[Tool] Detected: Assignment analysis query")
        results = db.get_assignment_analysis(teacher_id)
        return {"query_type": "assignment_analysis", "results": results}
    
    # Check for missing assignments
    if 'missing' in message_lower:
        print(f"[Tool] Detected: Missing assignments query")
        results = db.get_students_with_missing_work(teacher_id)
        return {"query_type": "missing_assignments", "results": results}
    
    # Check for class overview
    if any(word in message_lower for word in ['class', 'overview', 'summary', 'average']):
        print(f"[Tool] Detected: Class overview query")
        results = db.get_class_overview(teacher_id)
        return {"query_type": "class_overview", "results": results}
    
    return None

def get_client_id(request: Request) -> str:
    """Get client identifier for rate limiting"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else "unknown"

# ============================================================================ #
# API Endpoints
# ============================================================================ #
llm = None

@app.on_event("startup")
async def startup_event():
    global llm
    try:
        llm = OllamaEngine()
        await llm.test_connection()
        print("✓ Rick GradeInsight ready!")
    except Exception as e:
        print(f"⚠ Ollama initialization failed: {e}")
        llm = OllamaEngine()  # Create anyway, will error on use

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Rick GradeInsight",
        "engine": "ollama",
        "model": llm.model_name if llm else "unknown",
        "database_enabled": DB_ENABLED,
        "memory_enabled": MEMORY_ENABLED,
        "version": "1.0.0-ollama"
    }

@app.post("/chat")
async def chat_endpoint(request: ChatRequest, req: Request):
    start_time = time.time()
    
    if llm is None:
        metrics.record_error()
        raise HTTPException(status_code=503, detail="LLM not initialized")

    if not DB_ENABLED:
        metrics.record_error()
        raise HTTPException(status_code=503, detail="Database not available")

    # Rate limiting
    client_id = get_client_id(req)
    if not rate_limiter.is_allowed(client_id):
        metrics.record_error()
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    if conversation_id not in metrics.active_conversations:
        metrics.active_conversations.add(conversation_id)

    async def event_generator():
        try:
            # STEP 1: Send typing indicator
            yield f"data: {json.dumps({'type': 'status', 'content': 'Analyzing...'})}\n\n"

            # STEP 2: Analyze query intent and fetch data if needed
            query_results = None
            if DB_ENABLED:
                query_results = analyze_query_intent(request.message, request.teacher_id)
                
                if query_results:
                    query_type = query_results.get('query_type', 'unknown')
                    yield f"data: {json.dumps({'type': 'status', 'content': f'Fetching {query_type}...'})}\n\n"
                    
                    tool_data = json.dumps({
                        "type": "tool_result",
                        "tool_name": query_type,
                        "success": True,
                        "record_count": len(query_results.get('results', []))
                    })
                    yield f"data: {tool_data}\n\n"

            # STEP 3: Build prompt with query results
            prompt = llm.build_prompt_messages(
                request.message,
                request.conversation_history,
                request.teacher_id,
                query_results=query_results
            )

            # STEP 4: Generate response with streaming
            yield f"data: {json.dumps({'type': 'status', 'content': 'Thinking...'})}\n\n"
            
            full_response = ""
            
            gen_params = {
                "temperature": request.temperature,
            }

            async for token in llm.generate_stream(prompt, **gen_params):
                full_response += token
                data = json.dumps({"type": "token", "content": token})
                yield f"data: {data}\n\n"

            # STEP 5: Save to vector memory if enabled
            if MEMORY_ENABLED and vector_memory:
                vector_memory.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=request.message,
                    timestamp=datetime.now().isoformat()
                )
                vector_memory.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                    timestamp=datetime.now().isoformat()
                )

            # Record metrics
            duration = time.time() - start_time
            metrics.record_request(duration)

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            print(f"[Error] {str(e)}")
            metrics.record_error()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        finally:
            if conversation_id in metrics.active_conversations:
                metrics.active_conversations.discard(conversation_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.get("/health")
async def health_check():
    llm_status = "connected" if llm and await llm.test_connection() else "disconnected"
    
    return {
        "status": "healthy",
        "llm_status": llm_status,
        "database_status": "connected" if DB_ENABLED else "disconnected",
        "memory_status": "enabled" if MEMORY_ENABLED else "disabled",
        "model": llm.model_name if llm else "unknown",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    stats = {
        "app_metrics": metrics.get_stats()
    }
    
    if MEMORY_ENABLED and vector_memory:
        stats["memory_stats"] = vector_memory.get_stats()
    
    return stats

# ============================================================================ #
# Database Query Endpoints
# ============================================================================ #
@app.get("/api/students/struggling/{teacher_id}")
async def get_struggling(teacher_id: int, threshold: float = 70.0):
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Database not available")
    results = db.get_struggling_students(teacher_id, threshold)
    return {"results": results, "count": len(results)}

@app.get("/api/student/{teacher_id}/{student_id}")
async def get_student(teacher_id: int, student_id: int):
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Database not available")
    result = db.get_student_detail(teacher_id, student_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return result

@app.get("/api/assignments/analysis/{teacher_id}")
async def get_assignments(teacher_id: int):
    if not DB_ENABLED:
        raise HTTPException(status_code=503, detail="Database not available")
    results = db.get_assignment_analysis(teacher_id)
    return {"results": results, "count": len(results)}

# Run with: uvicorn main:app --host 127.0.0.1 --port 8090 --reload
