from dotenv import load_dotenv
import os
import re
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from relevanceai import Client as RelevanceAI

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Relevance AI client with explicit credentials
try:
    RELEVANCE_AI_PROJECT = os.getenv('RELEVANCE_AI_PROJECT')
    RELEVANCE_AI_API_KEY = os.getenv('RELEVANCE_AI_API_KEY')
    
    if not RELEVANCE_AI_PROJECT or not RELEVANCE_AI_API_KEY:
        raise ValueError("Missing Relevance AI credentials in environment variables")
        
    client = RelevanceAI(
        project=RELEVANCE_AI_PROJECT,
        api_key=RELEVANCE_AI_API_KEY
    )
except Exception as e:
    print(f"Error initializing Relevance AI client: {str(e)}")
    print(f"Project: {os.getenv('RELEVANCE_AI_PROJECT', 'Not set')}")
    print(f"API Key: {'Set' if os.getenv('RELEVANCE_AI_API_KEY') else 'Not set'}")
    print(traceback.format_exc())
    raise

def parse_agent_string(agent_str):
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
        agents_list = client.agents.list_agents()
        
        if not agents_list:
            return []
            
        agents = []
        for agent in agents_list:
            agent_id, agent_name = parse_agent_string(agent)
            
            if not agent_id:
                print(f"Could not parse agent string: {agent}")
                continue
                
            try:
                agent_details = client.agents.retrieve_agent(agent_id=agent_id)
                
                tasks = []
                try:
                    tasks = client.tasks.list_tasks(agent_id=agent_id, limit=100)
                except Exception as task_error:
                    print(f"Error getting tasks for agent {agent_id}: {str(task_error)}")
                    print(traceback.format_exc())
                
                completed_tasks = [t for t in tasks if getattr(t, 'status', '') == 'completed']
                tasks_completed = len(completed_tasks)
                success_rate = (tasks_completed / len(tasks) * 100) if tasks else 0
                
                current_task = next((t for t in tasks if getattr(t, 'status', '') == 'running'), None)
                
                agent_info = {
                    "id": agent_id,
                    "name": agent_name,
                    "status": "active",
                    "lastActive": getattr(agent_details, 'last_active', '') or '',
                    "tasksCompleted": tasks_completed,
                    "successRate": round(success_rate, 1),
                    "currentTask": getattr(current_task, 'message', '') if current_task else ''
                }
                agents.append(agent_info)
                
            except Exception as detail_error:
                print(f"Error getting details for agent {agent_id}: {str(detail_error)}")
                print(traceback.format_exc())
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