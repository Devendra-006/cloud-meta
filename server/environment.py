import json, uuid, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openenv.core.env_server import Environment
from models import CloudCostAction, CloudCostObservation, CloudCostState
from graders.grader import grade

TASKS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tasks')
MAX_STEPS = {'task1': 1, 'task2': 3, 'task3': 5}

class CloudCostEnvironment(Environment):
    def __init__(self, task_id: str = 'task1'):
        self._task_id = task_id
        self._task_data = {}
        self._state = CloudCostState.model_construct(
            episode_id=None,
            step_count=0,
            task_id=task_id,
            ground_truth={},
            cumulative_reward=0.0,
            best_step_reward=0.0,
            task_data={},
        )
        self._done = False
        self._last_reward = 0.0

    def reset(self, task_id: str = None) -> CloudCostObservation:
        if task_id:
            self._task_id = task_id
        task_file = os.path.join(TASKS_DIR, f'{self._task_id}.json')
        with open(task_file) as f:
            self._task_data = json.load(f)
        gt = self._task_data['ground_truth']
        gt['vm_costs'] = {v['id']: v['cost_per_hr'] for v in self._task_data['vms']}
        self._done = False
        self._last_reward = 0.0
        self._state = CloudCostState.model_construct(
            episode_id=str(uuid.uuid4()),
            step_count=0,
            task_id=self._task_id,
            ground_truth=gt,
            cumulative_reward=0.0,
            best_step_reward=0.0,
            task_data=self._task_data,
        )
        return self._make_obs(feedback='')

    def step(self, action: CloudCostAction) -> CloudCostObservation:
        if self._done:
            raise RuntimeError('Episode done. Call reset() to start a new episode.')
        self._state.step_count += 1
        result = grade(action, self._task_id, self._state.ground_truth)
        self._last_reward = result.total_score
        self._state.cumulative_reward = max(
            self._state.cumulative_reward, result.total_score
        )
        self._state.best_step_reward = max(
            self._state.best_step_reward, result.total_score
        )
        max_steps = MAX_STEPS.get(self._task_id, 1)
        done = result.total_score >= 0.95 or self._state.step_count >= max_steps
        self._done = done
        feedback = self._build_feedback(result)
        obs = self._make_obs(feedback=feedback)
        obs.done = done
        obs.reward = result.total_score
        obs.step_number = self._state.step_count
        return obs

    @property
    def state(self) -> CloudCostState:
        return self._state

    def _make_obs(self, feedback: str) -> CloudCostObservation:
        td = self._task_data
        max_steps = MAX_STEPS.get(self._task_id, 1)
        return CloudCostObservation.model_construct(
            done=self._done,
            reward=self._last_reward if self._state.step_count > 0 else None,
            task_id=self._task_id,
            difficulty=td.get('difficulty', ''),
            vms=td.get('vms', []),
            budget_remaining=td.get('budget_remaining', 0.0),
            traffic_forecast=td.get('traffic_forecast', []),
            active_alerts=td.get('active_alerts', []),
            time_step=self._state.step_count,
            instructions=td.get('instructions', ''),
            feedback=feedback,
            step_number=self._state.step_count,
            max_steps=max_steps,
        )

    def _build_feedback(self, result) -> str:
        lines = [
            f'Score: {result.total_score:.3f}',
            f'  Cost Savings:     {result.cost_savings:.3f}  (weight: 0.45)',
            f'  SLA Compliance:   {result.sla_compliance:.3f}  (weight: 0.35)',
            f'  Action Precision: {result.action_precision:.3f}  (weight: 0.15)',
            f'  Reasoning:        {result.reasoning:.3f}  (weight: 0.05)',
        ]
        return '\n'.join(lines)