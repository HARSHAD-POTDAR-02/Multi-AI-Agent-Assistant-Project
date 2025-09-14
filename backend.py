from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
from typing import Dict, List, Optional
import uuid
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from agents.router import route_request
from graph_setup import build_graph

app = FastAPI(title="Simi.ai API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global graph instance
graph = None

# Session storage
sessions: Dict[str, Dict] = {}

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

def init_graph():
    global graph
    if graph is None:
        try:
            print("Building graph...")
            graph = build_graph()
            print("Graph built successfully")
        except Exception as e:
            print(f"Error building graph: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

@app.post("/process")
async def process_request(request: QueryRequest):
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        print(f"Processing query: {request.query}")
        print(f"Received session_id: {request.session_id}")
        
        # Change to src directory for Gmail credentials
        original_cwd = os.getcwd()
        src_dir = os.path.join(os.path.dirname(__file__), 'src')
        os.chdir(src_dir)
        
        try:
            # Initialize graph if needed
            print("Initializing graph...")
            init_graph()
            
            # Route the request
            print("Routing request...")
            routed_agent = route_request(request.query)
            print(f"Routed to: {routed_agent}")
            
            # Get or create session
            session_id = request.session_id or str(uuid.uuid4())
            if session_id not in sessions:
                sessions[session_id] = {
                    'conversation_history': [],
                    'context': {},
                    'created_tasks': [],
                    'project_type': None
                }
            
            session = sessions[session_id]
            
            # Add current query to history
            session['conversation_history'].append({
                'role': 'user',
                'content': request.query,
                'timestamp': str(datetime.now())
            })
            
            # Create state for the agent with session memory
            state = {
                'user_query': request.query,
                'routed_agent': routed_agent,
                'response': '',  # Will be filled by agent
                'conversation_history': session['conversation_history'],
                'context': session['context'],
                'session_id': session_id,
                'task_action': None,
                'task_id': None,
                'task_description': None,
                'supervisor': None
            }
            
            # Debug: Print conversation history
            print(f"Session ID: {session_id}")
            print(f"Conversation history length: {len(session['conversation_history'])}")
            if session['conversation_history']:
                print(f"Last message: {session['conversation_history'][-1]}")
            
            # Process through the graph
            print("Processing through graph...")
            response = graph.invoke(state)
            print(f"Graph response: {response}")
            
            # Add response to session history
            session['conversation_history'].append({
                'role': 'assistant',
                'content': response.get('response', ''),
                'agent': routed_agent,
                'timestamp': str(datetime.now())
            })
            
            # Debug: Print updated history
            print(f"Updated history length: {len(session['conversation_history'])}")
            
        except Exception as graph_error:
            print(f"Graph processing error: {str(graph_error)}")
            import traceback
            traceback.print_exc()
            
            # Fallback response
            return {
                'success': False,
                'response': f"I encountered an issue processing your request. Error: {str(graph_error)}",
                'agent': 'Simi.ai (error)',
                'query': request.query
            }
        finally:
            # Always restore original directory
            os.chdir(original_cwd)
        
        return {
            'success': True,
            'response': response.get('response', 'No response from agent'),
            'agent': f'Simi.ai ({routed_agent})',
            'query': request.query,
            'session_id': session_id
        }
        
    except Exception as e:
        print(f"Backend error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return error response instead of raising HTTPException
        return {
            'success': False,
            'response': f"System error: {str(e)}",
            'agent': 'Simi.ai (system error)',
            'query': request.query
        }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Simi.ai backend is running"}

# For Vercel deployment
handler = app

if __name__ == "__main__":
    import uvicorn
    print("\n[ROCKET] Starting Simi.ai Backend...")
    print("[API] API available at: http://localhost:8003")
    print("[DOCS] API docs at: http://localhost:8003/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=8003)