"""Tests for the environment module."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from server.environment import CloudCostEnvironment
from models import CloudCostAction

@pytest.fixture
def env():
    return CloudCostEnvironment()

class TestReset:
    def test_reset_task1(self, env):
        obs = env.reset('task1')
        assert obs.task_id == 'task1'
        assert obs.difficulty == 'easy'
        assert len(obs.vms) == 5
        assert obs.max_steps == 1

    def test_reset_task2(self, env):
        obs = env.reset('task2')
        assert obs.task_id == 'task2'
        assert obs.difficulty == 'medium'
        assert len(obs.vms) == 15
        assert obs.max_steps == 3

    def test_reset_task3(self, env):
        obs = env.reset('task3')
        assert obs.task_id == 'task3'
        assert obs.difficulty == 'hard'
        assert len(obs.vms) == 30
        assert obs.max_steps == 5

    def test_reset_generates_alerts(self, env):
        obs = env.reset('task1')
        assert len(obs.active_alerts) > 0
        # Should have idle VM alerts
        alert_types = [a.get('type') for a in obs.active_alerts]
        assert 'warning' in alert_types or 'idle' in str(alert_types).lower()

    def test_reset_resets_state(self, env):
        env.reset('task1')
        # Take an action
        action = CloudCostAction(
            shutdown=['vm-003'], scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        env.step(action)
        
        # Reset
        obs = env.reset('task1')
        assert env.state.step_count == 0
        assert env._done is False

class TestStep:
    def test_correct_action(self, env):
        env.reset('task1')
        action = CloudCostAction(
            shutdown=['vm-003', 'vm-005'],
            scale_up=[], scale_down=[], migrate=[],
            reasoning='Idle VMs with CPU below 2%.'
        )
        obs = env.step(action)
        assert obs.reward > 0.9
        assert obs.done is True

    def test_tier1_violation(self, env):
        env.reset('task1')
        action = CloudCostAction(
            shutdown=['vm-001'],  # Tier-1 protected
            scale_up=[], scale_down=[], migrate=[],
            reasoning='Test.'
        )
        obs = env.step(action)
        assert obs.reward < 0.7

    def test_episode_done_after_step(self, env):
        env.reset('task1')
        action = CloudCostAction(
            shutdown=['vm-003', 'vm-005'],
            scale_up=[], scale_down=[], migrate=[],
            reasoning='Test.'
        )
        obs = env.step(action)
        assert env._done is True

    def test_cannot_step_after_done(self, env):
        env.reset('task1')
        action = CloudCostAction(
            shutdown=['vm-003', 'vm-005'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        env.step(action)
        
        with pytest.raises(RuntimeError, match='Episode done'):
            env.step(action)

    def test_feedback_generated(self, env):
        env.reset('task1')
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[],
            reasoning='Test action.'
        )
        obs = env.step(action)
        assert obs.feedback is not None
        assert 'Score' in obs.feedback

class TestMultiStep:
    def test_task2_allows_multiple_steps(self, env):
        env.reset('task2')
        assert env.state.step_count == 0
        
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[],
            reasoning='Test.'
        )
        obs = env.step(action)
        assert env.state.step_count == 1
        assert obs.done is False

    def test_max_steps_limit(self, env):
        env.reset('task2')  # 3 max steps
        
        for i in range(3):
            action = CloudCostAction(
                shutdown=[],
                scale_up=[], scale_down=[], migrate=[],
                reasoning=f'Step {i+1}'
            )
            obs = env.step(action)
        
        assert env._done is True

class TestStateTracking:
    def test_cumulative_reward(self, env):
        env.reset('task1')
        
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[],
            reasoning='Test.'
        )
        env.step(action)
        
        assert env.state.cumulative_reward > 0

    def test_best_step_reward(self, env):
        env.reset('task1')
        
        # First step - partial
        action1 = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        env.step(action1)
        first_reward = env.state.best_step_reward
        
        # Reset and do better
        env.reset('task1')
        action2 = CloudCostAction(
            shutdown=['vm-003', 'vm-005'],
            scale_up=[], scale_down=[], migrate=[],
            reasoning='Better action.'
        )
        env.step(action2)
        
        assert env.state.best_step_reward > first_reward
