from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from agents.router import route_request
from graph_setup import build_graph

app = FastAPI(title="Simi.ai API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global graph instance
graph = None

class QueryRequest(BaseModel):
    query: str

def init_graph():
    global graph
    if graph is None:
        graph = build_graph()

@app.post("/process")
async def process_request(request: QueryRequest):
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Change to src directory for Gmail credentials
        original_cwd = os.getcwd()
        src_dir = os.path.join(os.path.dirname(__file__), 'src')
        os.chdir(src_dir)
        
        try:
            # Initialize graph if needed
            init_graph()
            
            # Route the request
            routed_agent = route_request(request.query)
            
            # Create state for the agent
            state = {
                'user_query': request.query,
                'routed_agent': routed_agent,
                'conversation_history': [],
                'context': {}
            }
            
            # Process through the graph
            response = graph.invoke(state)
        finally:
            # Always restore original directory
            os.chdir(original_cwd)
        
        return {
            'success': True,
            'response': response.get('response', 'No response from agent'),
            'agent': f'Simi.ai ({routed_agent})',
            'query': request.query
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Simi.ai backend is running"}

if __name__ == "__main__":
    import uvicorn
    print("\n[ROCKET] Starting Simi.ai Backend...")
    print("[API] API available at: http://localhost:8000")
    print("[DOCS] API docs at: http://localhost:8000/docs\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)