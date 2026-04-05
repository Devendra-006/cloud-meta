from pydantic import Field, BaseModel
from typing import List, Optional, Tuple, Dict, Any
from openenv.core.env_server import Action, Observation, State

class CloudCostAction(Action):
    shutdown: List[str] = Field(default_factory=list)
    scale_up: List[str] = Field(default_factory=list)
    scale_down: List[str] = Field(default_factory=list)
    migrate: List[Tuple[str, str]] = Field(default_factory=list)
    reasoning: str = ""

class AlertInfo(BaseModel):
    type: str
    severity: str
    vm_id: str
    title: str
    message: str
    action: str
    potential_savings: Optional[float] = None
    risk: Optional[str] = None

class CloudCostObservation(Observation):
    done: bool = False
    reward: Optional[float] = None
    task_id: str = ""
    difficulty: str = ""
    vms: List[Dict[str, Any]] = Field(default_factory=list)
    budget_remaining: float = 0.0
    traffic_forecast: List[float] = Field(default_factory=list)
    active_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    time_step: int = 0
    instructions: str = ""
    feedback: str = ""
    step_number: int = 0
    max_steps: int = 1
    total_hourly_cost: float = 0.0
    idle_vm_count: int = 0
    potential_savings: float = 0.0

class CloudCostState(State):
    episode_id: Optional[str] = None
    step_count: int = 0
    task_id: str = ""
    ground_truth: Dict[str, Any] = Field(default_factory=dict)
    cumulative_reward: float = 0.0
    best_step_reward: float = 0.0
    task_data: Dict[str, Any] = Field(default_factory=dict)
