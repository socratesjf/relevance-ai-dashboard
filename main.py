from dotenv import load_dotenv
import os
import re
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from relevanceai import RelevanceAI

load_dotenv()

app = FastAPI()

# Add CORS middleware with explicit frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default development port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Relevance AI client
try:
    client = RelevanceAI()
except Exception as e:
    print(f"Error initializing Relevance AI client: {str(e)}")
    raise

def parse_agent_string(agent_str):
    # Parse the agent string to extract ID and name
    match = re.search(r'agent_id="([^"]+)", name="([^"]+)"', str(agent_str))
    if match:
        return match.group(1), match.group(2)
    return None, None

@app.get("/")
async def root():
    return {"message": "Relevance AI Backend API"}

@app.get("/agents")
async def get_agents():
    try:
        # Get all agents
        agents_list = client.agents.list_agents()
        
        if not agents_list:
            return []
            
        # Transform the agents into our frontend schema
        agents = []
        for agent in agents_list:
            agent_id, agent_name = parse_agent_string(agent)
            
            if not agent_id:
                print(f"Could not parse agent string: {agent}")
                continue
                
            try:
                # Get detailed agent information
                agent_details = client.agents.retrieve_agent(agent_id=agent_id)
                
                # Try to get agent's tasks
                tasks = []
                try:
                    # Get recent tasks for the agent
                    tasks = client.tasks.list_tasks(agent_id=agent_id, limit=100)
                except Exception as task_error:
                    print(f"Error getting tasks for agent {agent_id}: {str(task_error)}")
                    print(traceback.format_exc())
                
                # Calculate task statistics
                completed_tasks = [t for t in tasks if getattr(t, 'status', '') == 'completed']
                tasks_completed = len(completed_tasks)
                success_rate = (tasks_completed / len(tasks) * 100) if tasks else 0
                
                # Get current task if any
                current_task = next((t for t in tasks if getattr(t, 'status', '') == 'running'), None)
                
                # Format the agent data
                agent_info = {
                    "id": agent_id,
                    "name": agent_name,
                    "status": "active",  # We could check agent's actual status if available
                    "lastActive": getattr(agent_details, 'last_active', '') or '',
                    "tasksCompleted": tasks_completed,
                    "successRate": round(success_rate, 1),
                    "currentTask": getattr(current_task, 'message', '') if current_task else ''
                }
                agents.append(agent_info)
                
            except Exception as detail_error:
                print(f"Error getting details for agent {agent_id}: {str(detail_error)}")
                print(traceback.format_exc())
                # Add basic agent info if details retrieval fails
                agent_info = {
                    "id": agent_id,
                    "name": agent_name,
                    "status": "active",
                    "lastActive": "",
                    "tasksCompleted": 0,
                    "successRate": 0,
                    "currentTask": ""
                }
                agents.append(agent_info)
            
        return agents
    except Exception as e:
        print(f"Error in get_agents: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)