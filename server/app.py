import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Dict, Optional, List, Tuple
import uuid

from server.environment import CloudCostEnvironment
from models import CloudCostAction, CloudCostObservation

app = FastAPI()

# Single shared environment instance for simplicity
shared_env: Optional[CloudCostEnvironment] = None
current_episode_id: Optional[str] = None

# Pydantic models for requests
class ResetRequest(BaseModel):
    task_id: str = "task1"

class StepRequest(BaseModel):
    action: dict

def serialize_observation(obs) -> dict:
    return {
        "task_id": obs.task_id,
        "difficulty": obs.difficulty,
        "vms": obs.vms,
        "budget_remaining": obs.budget_remaining,
        "traffic_forecast": obs.traffic_forecast,
        "active_alerts": obs.active_alerts,
        "time_step": obs.time_step,
        "instructions": obs.instructions,
        "feedback": obs.feedback or "",
        "step_number": obs.step_number,
        "max_steps": obs.max_steps,
        "done": obs.done,
        "reward": obs.reward,
        "total_hourly_cost": getattr(obs, 'total_hourly_cost', 0),
        "idle_vm_count": getattr(obs, 'idle_vm_count', 0),
        "potential_savings": getattr(obs, 'potential_savings', 0),
    }

@app.post("/reset")
async def reset(request: ResetRequest):
    global shared_env, current_episode_id
    
    shared_env = CloudCostEnvironment()
    obs = shared_env.reset(task_id=request.task_id)
    current_episode_id = str(uuid.uuid4())
    
    return {
        "observation": serialize_observation(obs),
        "reward": obs.reward,
        "done": obs.done,
        "episode_id": current_episode_id,
    }

@app.post("/step")
async def step(step_request: StepRequest):
    global shared_env
    
    if shared_env is None:
        shared_env = CloudCostEnvironment()
        shared_env.reset("task1")
    
    # Parse action
    migrate_list = step_request.action.get("migrate", [])
    if migrate_list and isinstance(migrate_list[0], list):
        migrate_tuples = [tuple(m) for m in migrate_list]
    else:
        migrate_tuples = []
    
    action = CloudCostAction(
        shutdown=step_request.action.get("shutdown", []),
        scale_up=step_request.action.get("scale_up", []),
        scale_down=step_request.action.get("scale_down", []),
        migrate=migrate_tuples,
        reasoning=step_request.action.get("reasoning", ""),
    )
    
    # Execute step
    obs = shared_env.step(action)
    
    return {
        "observation": serialize_observation(obs),
        "reward": obs.reward,
        "done": obs.done,
    }

@app.get("/state")
async def state():
    global shared_env
    if shared_env is None:
        return {"error": "No active session"}
    return {
        "episode_id": current_episode_id,
        "task_id": shared_env.state.task_id,
        "step_count": shared_env.state.step_count,
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/metadata")
async def metadata():
    return {
        "name": "CloudCostEnvironment",
        "description": "CloudCostEnvironment environment",
        "version": "1.0.0",
    }

@app.get("/schema")
async def schema():
    return {
        "observation": {
            "task_id": "str",
            "difficulty": "str",
            "vms": "list",
            "budget_remaining": "float",
        },
        "action": {
            "shutdown": "list[str]",
            "scale_up": "list[str]",
            "scale_down": "list[str]",
            "migrate": "list[tuple[str,str]]",
            "reasoning": "str",
        }
    }

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve UI
ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ui', 'dist')
if os.path.exists(ui_path):
    app.mount("/web", StaticFiles(directory=ui_path, html=True), name="ui")

@app.get("/")
async def root():
    return RedirectResponse(url="/web", status_code=302)

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
