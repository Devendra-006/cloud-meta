import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, field_validator
from typing import Dict, Optional, List, Tuple
import uuid

from server.environment import CloudCostEnvironment
from models import CloudCostAction, CloudCostObservation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CloudCostEnv",
    description="AI training environment for autonomous cloud infrastructure optimization"
)

# CORS Middleware - restricted origins via environment variable
origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session management - multi-session support
sessions: Dict[str, CloudCostEnvironment] = {}

# Pydantic models for requests
class ResetRequest(BaseModel):
    """Request to start a new episode."""
    task_id: str = "task1"
    
    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v):
        valid_tasks = ['task1', 'task2', 'task3']
        if v not in valid_tasks:
            raise ValueError(f"task_id must be one of {valid_tasks}")
        return v

class StepRequest(BaseModel):
    """Request to execute an action."""
    action: dict
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if not isinstance(v, dict):
            raise ValueError("action must be a dictionary")
        return v

def serialize_observation(obs) -> dict:
    """
    Serialize observation for API response.
    NOTE: ground_truth is NEVER included in responses.
    """
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

def validate_vm_ids(action: CloudCostAction, valid_vm_ids: List[str]) -> List[str]:
    """
    Validate that all VM IDs in the action exist in the current task fleet.
    Returns list of invalid VM IDs.
    """
    invalid_ids = []
    valid_set = set(valid_vm_ids)
    
    all_vm_ids = action.shutdown + action.scale_up + action.scale_down
    for vm_id, _ in action.migrate:
        all_vm_ids.append(vm_id)
    
    for vm_id in all_vm_ids:
        if vm_id not in valid_set:
            invalid_ids.append(vm_id)
    
    return invalid_ids

def validate_action(action: dict, valid_vm_ids: List[str]) -> Tuple[bool, str]:
    """
    Validate action structure and VM IDs.
    Returns (is_valid, error_message).
    """
    if not isinstance(action, dict):
        return False, "action must be a dictionary"
    
    # Check action type
    valid_actions = ['shutdown', 'scale_up', 'scale_down', 'migrate', 'reasoning']
    for key in action.keys():
        if key not in valid_actions:
            return False, f"Invalid action key: {key}"
    
    # Check VM IDs
    all_vm_ids = []
    for key in ['shutdown', 'scale_up', 'scale_down']:
        if key in action and action[key]:
            if not isinstance(action[key], list):
                return False, f"{key} must be a list"
            all_vm_ids.extend(action[key])
    
    if 'migrate' in action and action['migrate']:
        if not isinstance(action['migrate'], list):
            return False, "migrate must be a list"
        for item in action['migrate']:
            if isinstance(item, list) and len(item) >= 1:
                all_vm_ids.append(item[0])
    
    valid_set = set(valid_vm_ids)
    for vm_id in all_vm_ids:
        if vm_id not in valid_set:
            return False, f"Invalid VM ID: {vm_id}. Valid VMs: {valid_vm_ids}"
    
    return True, ""

@app.post("/reset", response_model=dict)
async def reset(request: ResetRequest) -> dict:
    """
    Start a new episode with the specified task.
    
    - **task_id**: Task identifier (task1, task2, task3)
    
    Returns observation and episode_id for subsequent requests.
    """
    logger.info(f"Reset requested: task_id={request.task_id}")
    
    # Create new environment and session
    env = CloudCostEnvironment()
    obs = env.reset(task_id=request.task_id)
    episode_id = str(uuid.uuid4())
    
    # Store session
    sessions[episode_id] = env
    
    logger.info(f"Episode started: episode_id={episode_id}, task={request.task_id}")
    
    return {
        "observation": serialize_observation(obs),
        "reward": obs.reward,
        "done": obs.done,
        "episode_id": episode_id,
    }

@app.post("/step", response_model=dict)
async def step(request: Request, step_request: StepRequest) -> dict:
    """
    Execute an action in the current episode.
    
    - **action**: Dictionary containing:
      - **shutdown**: List of VM IDs to shutdown
      - **scale_up**: List of VM IDs to scale up
      - **scale_down**: List of VM IDs to scale down
      - **migrate**: List of [vm_id, target_region] pairs
      - **reasoning**: Text explaining the action
    
    Requires X-Episode-ID header or episode_id in request body.
    """
    # Get episode ID from header
    episode_id = request.headers.get("X-Episode-ID") or request.headers.get("episode_id")
    
    # Check session exists
    if episode_id not in sessions:
        logger.warning(f"Step failed: session not found, episode_id={episode_id}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Session not found",
                "message": "No active session. Please call /reset first.",
                "episode_id": episode_id
            }
        )
    
    env = sessions[episode_id]
    valid_vm_ids = [vm['id'] for vm in env._task_data.get('vms', [])]
    
    # Validate action
    is_valid, error_msg = validate_action(step_request.action, valid_vm_ids)
    if not is_valid:
        logger.warning(f"Step validation failed: {error_msg}")
        raise HTTPException(status_code=400, detail={"error": "Invalid action", "message": error_msg})
    
    # Parse action
    migrate_list = step_request.action.get("migrate", [])
    if migrate_list and isinstance(migrate_list[0], list):
        migrate_tuples = [tuple(m) for m in migrate_list]
    else:
        migrate_tuples = []
    
    action = CloudCostAction(
        shutdown=list(set(step_request.action.get("shutdown", []))),  # Remove duplicates
        scale_up=list(set(step_request.action.get("scale_up", []))),
        scale_down=list(set(step_request.action.get("scale_down", []))),
        migrate=migrate_tuples,
        reasoning=step_request.action.get("reasoning", ""),
    )
    
    # Execute step
    logger.info(f"Step executing: episode_id={episode_id}, shutdown={action.shutdown}, scale_up={action.scale_up}")
    
    try:
        obs = env.step(action)
    except RuntimeError as e:
        logger.error(f"Step error: {str(e)}")
        raise HTTPException(status_code=400, detail={"error": str(e)})
    
    # Check if episode is done
    if obs.done:
        logger.info(f"Episode completed: episode_id={episode_id}, reward={obs.reward}")
        # Clean up session after episode ends
        del sessions[episode_id]
    
    return {
        "observation": serialize_observation(obs),
        "reward": obs.reward,
        "done": obs.done,
    }

@app.get("/state", response_model=dict)
async def state(request: Request) -> dict:
    """
    Get the current session state.
    
    - **X-Episode-ID**: Episode identifier header
    
    Returns safe state fields only (never exposes ground_truth).
    """
    episode_id = request.headers.get("X-Episode-ID") or request.headers.get("episode_id")
    
    if episode_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail={"error": "Session not found", "message": "No active session. Please call /reset first."}
        )
    
    env = sessions[episode_id]
    
    return {
        "episode_id": episode_id,
        "task_id": env.state.task_id,
        "step_count": env.state.step_count,
        "cumulative_reward": env.state.cumulative_reward,
        "best_step_reward": env.state.best_step_reward,
        "is_done": env._done,
    }

@app.get("/health", response_model=dict)
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "active_sessions": len(sessions)}

@app.get("/metadata", response_model=dict)
async def metadata() -> dict:
    """Get environment metadata."""
    return {
        "name": "CloudCostEnvironment",
        "description": "AI training environment for autonomous cloud infrastructure optimization",
        "version": "1.0.0",
        "tasks": ["task1", "task2", "task3"],
        "author": "CloudCostEnv Team",
    }

@app.get("/schema", response_model=dict)
async def schema() -> dict:
    """Get action and observation schemas."""
    return {
        "observation": {
            "task_id": "str",
            "difficulty": "str",
            "vms": "list[dict]",
            "budget_remaining": "float",
            "traffic_forecast": "list[float]",
            "active_alerts": "list[dict]",
            "time_step": "int",
            "instructions": "str",
            "feedback": "str",
            "step_number": "int",
            "max_steps": "int",
            "done": "bool",
            "reward": "float",
        },
        "action": {
            "shutdown": "list[str]",
            "scale_up": "list[str]",
            "scale_down": "list[str]",
            "migrate": "list[tuple[str,str]]",
            "reasoning": "str",
        }
    }

# Serve UI
ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ui', 'dist')
if os.path.exists(ui_path):
    app.mount("/web", StaticFiles(directory=ui_path, html=True), name="ui")

@app.get("/", response_model=dict)
async def root():
    """Redirect to web UI."""
    return RedirectResponse(url="/web", status_code=302)

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '0.0.0.0')
    uvicorn.run(app, host=host, port=port)
