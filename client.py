from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from models import CloudCostAction, CloudCostObservation, CloudCostState

class CloudCostEnv(EnvClient[CloudCostAction, CloudCostObservation, CloudCostState]):
    """
    Client for CloudCostEnv. Usage:
        with CloudCostEnv(base_url='http://localhost:8000').sync() as env:
            obs = env.reset(task_id='task1')
            action = CloudCostAction(shutdown=['vm-003'])
            result = env.step(action)
            print(result.reward)
    """
    def _step_payload(self, action: CloudCostAction) -> dict:
        """Convert typed Action to wire format dict."""
        return {
            'shutdown':  action.shutdown,
            'scale_up':  action.scale_up,
            'scale_down': action.scale_down,
            'migrate':   [[v, r] for v, r in action.migrate],
            'reasoning': action.reasoning,
        }

    def _parse_result(self, payload: dict) -> StepResult[CloudCostObservation]:
        """Convert wire format dict to typed Observation."""
        obs_data = payload.get('observation', payload)
        obs = CloudCostObservation(
            done=obs_data.get('done', False),
            reward=obs_data.get('reward'),
            task_id=obs_data.get('task_id', ''),
            difficulty=obs_data.get('difficulty', ''),
            vms=obs_data.get('vms', []),
            budget_remaining=obs_data.get('budget_remaining', 0.0),
            traffic_forecast=obs_data.get('traffic_forecast', []),
            active_alerts=obs_data.get('active_alerts', []),
            time_step=obs_data.get('time_step', 0),
            instructions=obs_data.get('instructions', ''),
            feedback=obs_data.get('feedback', ''),
            step_number=obs_data.get('step_number', 0),
            max_steps=obs_data.get('max_steps', 1),
        )
        return StepResult(
            observation=obs,
            reward=payload.get('reward', 0.0),
            done=payload.get('done', False),
        )

    def _parse_state(self, payload: dict) -> CloudCostState:
        """Convert /state response to typed State."""
        return CloudCostState(
            episode_id=payload.get('episode_id'),
            step_count=payload.get('step_count', 0),
            task_id=payload.get('task_id', ''),
            cumulative_reward=payload.get('cumulative_reward', 0.0),
        )
